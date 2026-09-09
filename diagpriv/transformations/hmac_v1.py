"""Deterministic, annotation-driven HMAC privacy baseline."""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import hmac
import json
import string

from diagbench.schema import Incident, ModelView, SensitiveField
from diagbench.schema.models import JSONPrimitive, JSONValue

TRANSFORMATION_VERSION = "hmac-v1"
HMAC_KEY_ENVIRONMENT_VARIABLE = "DIAGPRIV_HMAC_KEY_HEX"
HMAC_KEY_BYTES = 32
_TOKEN_PREFIX = "HMAC1_"


def parse_hmac_key_hex(value: str) -> bytes:
    """Parse the external 256-bit experimental key without echoing it."""
    if len(value) != HMAC_KEY_BYTES * 2 or any(
        character not in string.hexdigits for character in value
    ):
        raise ValueError("HMAC key must contain exactly 64 hexadecimal characters")
    key = bytes.fromhex(value)
    if len(key) != HMAC_KEY_BYTES:
        raise ValueError("HMAC key must contain exactly 32 bytes")
    return key


def hmac_key_fingerprint(key: bytes) -> str:
    """Return the non-secret SHA-256 audit fingerprint for an experimental key."""
    _validate_key(key)
    return hashlib.sha256(key).hexdigest()


def hmac_token(value: JSONPrimitive, *, key: bytes, namespace: str) -> str:
    """Return a domain-separated HMAC-SHA-256 pseudonym for one scalar."""
    _validate_key(key)
    type_name = _primitive_type_name(value)
    canonical_value = json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    ).encode("utf-8")
    payload = b"\x00".join(
        (
            TRANSFORMATION_VERSION.encode("ascii"),
            namespace.encode("utf-8"),
            type_name.encode("ascii"),
            canonical_value,
        )
    )
    digest = hmac.new(key, payload, hashlib.sha256).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"{_TOKEN_PREFIX}{encoded}"


def hmac_incident(incident: Incident, *, key: bytes) -> ModelView:
    """Pseudonymize only annotated sensitive scalars and return a ModelView."""
    _validate_key(key)
    data = deepcopy(incident.model_view().to_dict())
    seen_paths: set[str] = set()

    for annotation in incident.sensitive_fields:
        path = annotation.path
        if path in seen_paths:
            raise ValueError(f"Duplicate sensitive-field annotation: {path}")
        seen_paths.add(path)
        try:
            source, field = path.split(".", maxsplit=1)
        except ValueError as error:
            raise ValueError(f"Sensitive path must be source.field: {path}") from error
        namespace = _namespace(annotation, field)

        if source == "logs":
            _transform_logs(data, field, path, namespace, key)
        else:
            _transform_structured_rows(data, source, field, path, namespace, key)

    return ModelView.from_dict(data)


def _namespace(annotation: SensitiveField, field: str) -> str:
    if annotation.policy == "consistent_pseudonym":
        return f"shared:{annotation.classification}:{field}"
    if annotation.policy in {"pseudonymize_independently", "remove_or_pseudonymize"}:
        return f"path:{annotation.path}"
    raise ValueError(
        f"Unsupported HMAC policy for sensitive path {annotation.path}: "
        f"{annotation.policy}"
    )


def _transform_structured_rows(
    data: dict[str, JSONValue],
    source: str,
    field: str,
    path: str,
    namespace: str,
    key: bytes,
) -> None:
    structured = data["structured_evidence"]
    if not isinstance(structured, dict) or source not in structured:
        raise ValueError(f"Unknown sensitive-field source: {source}")
    rows = structured[source]
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Sensitive-field source has no rows: {source}")
    for row in rows:
        if not isinstance(row, dict) or field not in row:
            raise ValueError(f"Sensitive field is absent from {source}: {field}")
        row[field] = _tokenize_scalar(row[field], path, namespace, key)


def _transform_logs(
    data: dict[str, JSONValue],
    field: str,
    path: str,
    namespace: str,
    key: bytes,
) -> None:
    logs = data["log_evidence"]
    if not isinstance(logs, list):
        raise ValueError("ModelView log_evidence must be a list")
    matches = 0
    for entry in logs:
        if not isinstance(entry, dict):
            raise ValueError("ModelView log entry must be an object")
        if field in entry:
            entry[field] = _tokenize_scalar(entry[field], path, namespace, key)
            matches += 1
            continue
        attributes = entry.get("attributes")
        if isinstance(attributes, dict) and field in attributes:
            attributes[field] = _tokenize_scalar(
                attributes[field], path, namespace, key
            )
            matches += 1
    if matches == 0:
        raise ValueError(f"Sensitive log field is absent: {field}")


def _tokenize_scalar(
    value: JSONValue, path: str, namespace: str, key: bytes
) -> str:
    if isinstance(value, (list, dict)):
        raise ValueError(f"HMAC baseline supports only sensitive scalars: {path}")
    return hmac_token(value, key=key, namespace=namespace)


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


def _validate_key(key: bytes) -> None:
    if not isinstance(key, bytes) or len(key) != HMAC_KEY_BYTES:
        raise ValueError("HMAC key must contain exactly 32 bytes")
