"""Deterministic, annotation-driven format-preserving pseudonymization."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import string

from diagbench.schema import Incident, ModelView, SensitiveField
from diagbench.schema.models import JSONValue

TRANSFORMATION_VERSION = "format-preserving-v1"

_ALPHABETS = {
    "upper": string.ascii_uppercase,
    "lower": string.ascii_lowercase,
    "digit": string.digits,
}
_DISPLAY_SYMBOLS = {"upper": "U", "lower": "l", "digit": "D"}

PatternAtom = tuple[str, str | None]
StructuralPattern = tuple[PatternAtom, ...]


@dataclass(frozen=True, slots=True)
class _AnnotationPlan:
    path: str
    source: str
    field: str
    namespace: str


def structural_pattern(value: str) -> str:
    """Return the mechanically observable ASCII character-class pattern."""
    return "".join(
        literal if kind == "literal" else _DISPLAY_SYMBOLS[kind]
        for kind, literal in _parse_pattern(value)
    )


def format_preserving_incident(incident: Incident) -> ModelView:
    """Pseudonymize annotated strings while retaining their exact shape.

    The mapping is built for the complete ModelView in two passes and remains
    local to this function call. Candidate generation is deterministic, skips
    every original sensitive value, and resolves constrained-domain collisions
    by linear probing. No mapping table is returned or persisted.
    """
    data = deepcopy(incident.model_view().to_dict())
    plans = _annotation_plans(incident.sensitive_fields)
    occurrences: dict[str, tuple[tuple[dict[str, JSONValue], str], ...]] = {}
    grouped_values: dict[tuple[str, StructuralPattern], set[str]] = {}
    plaintext_by_pattern: dict[StructuralPattern, set[str]] = {}

    for plan in plans:
        matches = _path_occurrences(data, plan)
        occurrences[plan.path] = matches
        for container, field in matches:
            value = _sensitive_string(container[field], plan.path)
            pattern = _parse_pattern(value)
            grouped_values.setdefault((plan.namespace, pattern), set()).add(value)
            plaintext_by_pattern.setdefault(pattern, set()).add(value)

    _check_pattern_capacity(grouped_values, plaintext_by_pattern)

    mappings: dict[tuple[str, StructuralPattern], dict[str, str]] = {}
    used_by_pattern: dict[StructuralPattern, set[str]] = {}
    for namespace, pattern in sorted(
        grouped_values,
        key=lambda item: (item[0], _pattern_key(item[1])),
    ):
        key = (namespace, pattern)
        mappings[key] = _assign_pattern_values(
            namespace=namespace,
            pattern=pattern,
            values=grouped_values[key],
            forbidden=plaintext_by_pattern[pattern],
            used=used_by_pattern.setdefault(pattern, set()),
        )

    for plan in plans:
        for container, field in occurrences[plan.path]:
            value = _sensitive_string(container[field], plan.path)
            pattern = _parse_pattern(value)
            container[field] = mappings[(plan.namespace, pattern)][value]

    return ModelView.from_dict(data)


def _annotation_plans(
    annotations: tuple[SensitiveField, ...],
) -> tuple[_AnnotationPlan, ...]:
    plans: list[_AnnotationPlan] = []
    seen_paths: set[str] = set()
    namespace_definitions: dict[str, tuple[str, str, str]] = {}

    for annotation in annotations:
        path = annotation.path
        if path in seen_paths:
            raise ValueError(f"Duplicate sensitive-field annotation: {path}")
        seen_paths.add(path)
        if path.count(".") != 1:
            raise ValueError(f"Sensitive path must be source.field: {path}")
        source, field = path.split(".")
        _validate_namespace_component(source, "source", path)
        _validate_namespace_component(field, "field", path)
        _validate_namespace_component(
            annotation.classification, "classification", path
        )
        namespace = _namespace(annotation, field)
        definition = (annotation.policy, annotation.classification, field)
        previous = namespace_definitions.setdefault(namespace, definition)
        if previous != definition:
            raise ValueError(f"Ambiguous sensitive-field namespace: {namespace}")
        plans.append(_AnnotationPlan(path, source, field, namespace))

    return tuple(plans)


def _namespace(annotation: SensitiveField, field: str) -> str:
    if annotation.policy == "consistent_pseudonym":
        return f"shared:{annotation.classification}:{field}"
    if annotation.policy in {"pseudonymize_independently", "remove_or_pseudonymize"}:
        return f"path:{annotation.path}"
    raise ValueError(
        f"Unsupported format-preserving policy for sensitive path "
        f"{annotation.path}: {annotation.policy}"
    )


def _validate_namespace_component(component: str, name: str, path: str) -> None:
    if not component or ":" in component or "\x00" in component:
        raise ValueError(f"Ambiguous {name} in sensitive path: {path}")


def _path_occurrences(
    data: dict[str, JSONValue], plan: _AnnotationPlan
) -> tuple[tuple[dict[str, JSONValue], str], ...]:
    if plan.source != "logs":
        structured = data.get("structured_evidence")
        if not isinstance(structured, dict) or plan.source not in structured:
            raise ValueError(f"Unknown sensitive-field source: {plan.source}")
        rows = structured[plan.source]
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"Sensitive-field source has no rows: {plan.source}")
        matches: list[tuple[dict[str, JSONValue], str]] = []
        for row in rows:
            if not isinstance(row, dict) or plan.field not in row:
                raise ValueError(
                    f"Sensitive field is absent from {plan.source}: {plan.field}"
                )
            matches.append((row, plan.field))
        return tuple(matches)

    logs = data.get("log_evidence")
    if not isinstance(logs, list):
        raise ValueError("ModelView log_evidence must be a list")
    matches = []
    for entry in logs:
        if not isinstance(entry, dict):
            raise ValueError("ModelView log entry must be an object")
        attributes = entry.get("attributes")
        top_level_match = plan.field in entry
        attribute_match = isinstance(attributes, dict) and plan.field in attributes
        if top_level_match and attribute_match:
            raise ValueError(f"Ambiguous sensitive log field location: {plan.field}")
        if top_level_match:
            matches.append((entry, plan.field))
        elif attribute_match:
            matches.append((attributes, plan.field))
    if not matches:
        raise ValueError(f"Sensitive log field is absent: {plan.field}")
    return tuple(matches)


def _sensitive_string(value: JSONValue, path: str) -> str:
    if isinstance(value, (list, dict)):
        raise ValueError(
            f"Format-preserving baseline supports no composite value at: {path}"
        )
    if not isinstance(value, str):
        raise TypeError(
            f"Format-preserving baseline supports only string scalars at: {path}"
        )
    return value


def _parse_pattern(value: str) -> StructuralPattern:
    pattern: list[PatternAtom] = []
    for character in value:
        if character in string.ascii_uppercase:
            pattern.append(("upper", None))
        elif character in string.ascii_lowercase:
            pattern.append(("lower", None))
        elif character in string.digits:
            pattern.append(("digit", None))
        elif character in string.printable and character not in "\t\n\r\x0b\x0c":
            pattern.append(("literal", character))
        else:
            raise ValueError(
                "Format-preserving-v1 supports only printable ASCII strings"
            )
    return tuple(pattern)


def _pattern_key(pattern: StructuralPattern) -> bytes:
    return json.dumps(pattern, ensure_ascii=True, separators=(",", ":")).encode(
        "ascii"
    )


def _pattern_capacity(pattern: StructuralPattern) -> int:
    capacity = 1
    for kind, _ in pattern:
        if kind in _ALPHABETS:
            capacity *= len(_ALPHABETS[kind])
    return capacity


def _check_pattern_capacity(
    grouped_values: dict[tuple[str, StructuralPattern], set[str]],
    plaintext_by_pattern: dict[StructuralPattern, set[str]],
) -> None:
    required_by_pattern: dict[StructuralPattern, int] = {}
    for (_, pattern), values in grouped_values.items():
        required_by_pattern[pattern] = required_by_pattern.get(pattern, 0) + len(values)
    for pattern, required in required_by_pattern.items():
        available = _pattern_capacity(pattern) - len(plaintext_by_pattern[pattern])
        if required > available:
            raise ValueError(
                "Format-preserving output domain is too small to provide "
                "one-to-one plaintext-disjoint pseudonyms"
            )


def _assign_pattern_values(
    *,
    namespace: str,
    pattern: StructuralPattern,
    values: set[str],
    forbidden: set[str],
    used: set[str],
) -> dict[str, str]:
    capacity = _pattern_capacity(pattern)
    mapping: dict[str, str] = {}
    ordered_values = sorted(
        values,
        key=lambda value: (_assignment_order(namespace, pattern, value), value),
    )
    for value in ordered_values:
        start = _initial_rank(namespace, pattern, value, capacity)
        for offset in range(capacity):
            candidate = _render_rank(pattern, (start + offset) % capacity)
            if candidate in forbidden or candidate in used:
                continue
            mapping[value] = candidate
            used.add(candidate)
            break
        else:
            raise ValueError(
                "Format-preserving output domain was exhausted during collision "
                "resolution"
            )
    return mapping


def _assignment_order(
    namespace: str, pattern: StructuralPattern, value: str
) -> bytes:
    return _assignment_digest(namespace, pattern, value, b"order")


def _initial_rank(
    namespace: str, pattern: StructuralPattern, value: str, capacity: int
) -> int:
    digest = _assignment_digest(namespace, pattern, value, b"candidate")
    return int.from_bytes(digest, "big") % capacity


def _assignment_digest(
    namespace: str,
    pattern: StructuralPattern,
    value: str,
    purpose: bytes,
) -> bytes:
    payload = b"\x00".join(
        (
            TRANSFORMATION_VERSION.encode("ascii"),
            purpose,
            namespace.encode("utf-8"),
            _pattern_key(pattern),
            value.encode("ascii"),
        )
    )
    return hashlib.sha256(payload).digest()


def _render_rank(pattern: StructuralPattern, rank: int) -> str:
    capacity = _pattern_capacity(pattern)
    if not 0 <= rank < capacity:
        raise ValueError("Format-preserving candidate rank is outside its domain")
    output = [literal or "" for _, literal in pattern]
    remainder = rank
    for index in range(len(pattern) - 1, -1, -1):
        kind, _ = pattern[index]
        alphabet = _ALPHABETS.get(kind)
        if alphabet is None:
            continue
        remainder, digit = divmod(remainder, len(alphabet))
        output[index] = alphabet[digit]
    return "".join(output)
