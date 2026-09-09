"""Deterministic, annotation-driven synthetic tokenization baseline."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from diagbench.schema import Incident, ModelView, SensitiveField
from diagbench.schema.models import JSONPrimitive, JSONValue

TRANSFORMATION_VERSION = "tokenization-v1"

_FIELD_TAGS = {
    "account_id": "ACCT",
    "customer_id": "CUST",
    "email": "EMAIL",
    "name": "NAME",
    "payment_id": "PAY",
    "request_id": "REQ",
    "ssn": "SSN",
    "transport_id": "TRANS",
}


def tokenize_incident(incident: Incident) -> ModelView:
    """Replace annotated sensitive scalars using an ephemeral deterministic map.

    Assignment is a two-pass process. Values are first grouped by their
    annotation-derived namespace and sorted by a stable SHA-256 ordering key.
    One-based ordinal tokens are then substituted in a defensive ModelView copy.
    The plaintext-to-token mapping remains local to this call and is discarded.
    """
    data = deepcopy(incident.model_view().to_dict())
    plans = _annotation_plans(incident.sensitive_fields)
    canonical_values: dict[str, set[bytes]] = {}
    prefixes: dict[str, str] = {}

    for path, source, field, namespace, prefix in plans:
        existing_prefix = prefixes.setdefault(namespace, prefix)
        if existing_prefix != prefix:
            raise ValueError(f"Inconsistent token prefix for namespace: {namespace}")
        values = canonical_values.setdefault(namespace, set())
        for value in _path_values(data, source, field, path):
            values.add(_canonical_scalar(value, path))

    _validate_unique_prefixes(prefixes)
    mappings = {
        namespace: {
            canonical: f"{prefixes[namespace]}_{index:06d}"
            for index, canonical in enumerate(
                sorted(
                    values,
                    key=lambda item: _assignment_order(namespace, item),
                ),
                start=1,
            )
        }
        for namespace, values in canonical_values.items()
    }

    for path, source, field, namespace, _ in plans:
        _replace_path_values(data, source, field, path, mappings[namespace])

    return ModelView.from_dict(data)


def _annotation_plans(
    annotations: tuple[SensitiveField, ...],
) -> tuple[tuple[str, str, str, str, str], ...]:
    plans: list[tuple[str, str, str, str, str]] = []
    seen_paths: set[str] = set()
    for annotation in annotations:
        path = annotation.path
        if path in seen_paths:
            raise ValueError(f"Duplicate sensitive-field annotation: {path}")
        seen_paths.add(path)
        try:
            source, field = path.split(".", maxsplit=1)
        except ValueError as error:
            raise ValueError(f"Sensitive path must be source.field: {path}") from error
        namespace = _namespace(annotation, field)
        prefix = _token_prefix(annotation, source, field)
        plans.append((path, source, field, namespace, prefix))
    return tuple(plans)


def _namespace(annotation: SensitiveField, field: str) -> str:
    if annotation.policy == "consistent_pseudonym":
        return f"shared:{annotation.classification}:{field}"
    if annotation.policy in {"pseudonymize_independently", "remove_or_pseudonymize"}:
        return f"path:{annotation.path}"
    raise ValueError(
        f"Unsupported tokenization policy for sensitive path {annotation.path}: "
        f"{annotation.policy}"
    )


def _token_prefix(annotation: SensitiveField, source: str, field: str) -> str:
    field_tag = _FIELD_TAGS.get(field, _slug(field))
    if annotation.policy == "consistent_pseudonym":
        return f"TOK_{field_tag}"
    return f"TOK_{field_tag}_{_slug(source)}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    if not slug:
        raise ValueError("Token namespace component must contain a letter or digit")
    return slug


def _validate_unique_prefixes(prefixes: dict[str, str]) -> None:
    namespaces_by_prefix: dict[str, list[str]] = {}
    for namespace, prefix in prefixes.items():
        namespaces_by_prefix.setdefault(prefix, []).append(namespace)
    collisions = {
        prefix: namespaces
        for prefix, namespaces in namespaces_by_prefix.items()
        if len(namespaces) > 1
    }
    if collisions:
        raise ValueError(
            "Token prefix collision across sensitive-field namespaces: "
            + ", ".join(sorted(collisions))
        )


def _path_values(
    data: dict[str, JSONValue], source: str, field: str, path: str
) -> tuple[JSONValue, ...]:
    if source != "logs":
        structured = data["structured_evidence"]
        if not isinstance(structured, dict) or source not in structured:
            raise ValueError(f"Unknown sensitive-field source: {source}")
        rows = structured[source]
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"Sensitive-field source has no rows: {source}")
        values: list[JSONValue] = []
        for row in rows:
            if not isinstance(row, dict) or field not in row:
                raise ValueError(f"Sensitive field is absent from {source}: {field}")
            values.append(row[field])
        return tuple(values)

    logs = data["log_evidence"]
    if not isinstance(logs, list):
        raise ValueError("ModelView log_evidence must be a list")
    values = []
    for entry in logs:
        if not isinstance(entry, dict):
            raise ValueError("ModelView log entry must be an object")
        if field in entry:
            values.append(entry[field])
            continue
        attributes = entry.get("attributes")
        if isinstance(attributes, dict) and field in attributes:
            values.append(attributes[field])
    if not values:
        raise ValueError(f"Sensitive log field is absent: {field}")
    return tuple(values)


def _replace_path_values(
    data: dict[str, JSONValue],
    source: str,
    field: str,
    path: str,
    mapping: dict[bytes, str],
) -> None:
    if source != "logs":
        structured = data["structured_evidence"]
        if not isinstance(structured, dict):
            raise ValueError("ModelView structured_evidence must be an object")
        rows = structured[source]
        if not isinstance(rows, list):
            raise ValueError(f"Sensitive-field source must be a list: {source}")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"Sensitive-field source row must be an object: {source}")
            row[field] = mapping[_canonical_scalar(row[field], path)]
        return

    logs = data["log_evidence"]
    if not isinstance(logs, list):
        raise ValueError("ModelView log_evidence must be a list")
    for entry in logs:
        if not isinstance(entry, dict):
            raise ValueError("ModelView log entry must be an object")
        if field in entry:
            entry[field] = mapping[_canonical_scalar(entry[field], path)]
            continue
        attributes = entry.get("attributes")
        if isinstance(attributes, dict) and field in attributes:
            attributes[field] = mapping[
                _canonical_scalar(attributes[field], path)
            ]


def _canonical_scalar(value: JSONValue, path: str) -> bytes:
    if isinstance(value, (list, dict)):
        raise ValueError(
            f"Tokenization baseline supports only sensitive scalars: {path}"
        )
    type_name = _primitive_type_name(value)
    canonical_value = json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    return b"\x00".join((type_name.encode("ascii"), canonical_value))


def _assignment_order(namespace: str, canonical: bytes) -> tuple[bytes, bytes]:
    payload = b"\x00".join(
        (
            TRANSFORMATION_VERSION.encode("ascii"),
            namespace.encode("utf-8"),
            canonical,
        )
    )
    return hashlib.sha256(payload).digest(), canonical


def _primitive_type_name(value: JSONPrimitive) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    raise TypeError(f"Unsupported sensitive scalar type: {type(value)}")
