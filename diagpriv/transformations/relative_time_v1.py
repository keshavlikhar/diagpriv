"""Incident-local relative-time transformation for annotated timestamps."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from diagbench.relative_time import (
    RELATIVE_TIME_SEMANTICS_VERSION,
    RELATIVE_TIME_UNIT,
    parse_relative_time,
)
from diagbench.schema import Incident, ModelView
from diagbench.schema.models import JSONValue
from diagbench.temporal import parse_timestamp
from diagpriv.transformations.provenance import (
    RELATIVE_TIME_TRANSFORMATION_CONFIGURATION,
    canonical_transformation_configuration_json,
    transformation_configuration_sha256 as _configuration_sha256,
)

TRANSFORMATION_VERSION = RELATIVE_TIME_TRANSFORMATION_CONFIGURATION[
    "transformation_version"
]
ANCHOR_RULE = RELATIVE_TIME_TRANSFORMATION_CONFIGURATION["anchor_rule"]
PRECISION = RELATIVE_TIME_UNIT
TIMESTAMP_CLASSIFICATION = RELATIVE_TIME_TRANSFORMATION_CONFIGURATION[
    "annotation_classification"
]
SCOPE_POLICY = RELATIVE_TIME_TRANSFORMATION_CONFIGURATION["scope_policy"]


def relative_time_incident(incident: Incident) -> ModelView:
    """Replace annotated visible timestamps with incident-local millisecond offsets.

    The anchor is the earliest parsed instant among every annotated timestamp in
    the complete ModelView. The function never consults hidden target or oracle
    metadata. All non-temporal fields and row ordering remain unchanged.
    """
    data = deepcopy(incident.model_view().to_dict())
    paths = _timestamp_paths(incident)
    occurrences = tuple(
        occurrence
        for path, source, field in paths
        for occurrence in _path_occurrences(data, source, field, path)
    )
    if not occurrences:
        raise ValueError("relative-time-v1 requires annotated visible timestamps")

    parsed = tuple(_parse_raw_annotated_timestamp(value) for _, _, value in occurrences)
    anchor = min(parsed)
    replacements: dict[tuple[str, int], str] = {}
    for (container, slot, _), instant in zip(occurrences, parsed, strict=True):
        replacements[(container, slot)] = format_relative_time(instant, anchor)

    _apply_replacements(data, replacements)
    return ModelView.from_dict(data)


def format_relative_time(instant: datetime, anchor: datetime) -> str:
    """Format an exact, nonnegative, millisecond-aligned offset."""
    delta = instant - anchor
    total_microseconds = (
        (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds
    )
    if total_microseconds < 0:
        raise ValueError("relative-time-v1 offsets must be nonnegative")
    if total_microseconds % 1000:
        raise ValueError(
            "relative-time-v1 requires millisecond-aligned source timestamps"
        )
    return f"T+{total_microseconds // 1000}ms"


def transformation_configuration() -> dict[str, str]:
    """Return non-secret, versioned configuration suitable for preregistration."""
    return dict(RELATIVE_TIME_TRANSFORMATION_CONFIGURATION)


def transformation_configuration_json() -> str:
    """Return the canonical JSON whose UTF-8 bytes are hashed for provenance."""
    return canonical_transformation_configuration_json(transformation_configuration())


def transformation_configuration_sha256() -> str:
    """Return the deterministic SHA-256 of the canonical configuration."""
    return _configuration_sha256(transformation_configuration())


def _parse_raw_annotated_timestamp(value: str) -> datetime:
    try:
        return parse_timestamp(value)
    except ValueError as raw_error:
        try:
            parse_relative_time(value)
        except ValueError:
            raise ValueError(
                "relative-time-v1 expects raw annotated RFC3339 timestamps"
            ) from raw_error
        raise ValueError(
            "relative-time-v1 expects raw annotated RFC3339 timestamps and "
            "refuses already-relative evidence"
        ) from raw_error


def _timestamp_paths(incident: Incident) -> tuple[tuple[str, str, str], ...]:
    paths: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for annotation in incident.sensitive_fields:
        if annotation.classification != TIMESTAMP_CLASSIFICATION:
            continue
        if annotation.path in seen:
            raise ValueError(
                f"Duplicate operational timestamp annotation: {annotation.path}"
            )
        seen.add(annotation.path)
        try:
            source, field = annotation.path.split(".", maxsplit=1)
        except ValueError as error:
            raise ValueError(
                f"Timestamp path must be source.field: {annotation.path}"
            ) from error
        paths.append((annotation.path, source, field))
    return tuple(paths)


def _path_occurrences(
    data: dict[str, JSONValue], source: str, field: str, path: str
) -> tuple[tuple[str, int, str], ...]:
    if source != "logs":
        structured = data["structured_evidence"]
        if not isinstance(structured, dict) or source not in structured:
            raise ValueError(f"Unknown timestamp source: {source}")
        rows = structured[source]
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"Timestamp source has no rows: {source}")
        result: list[tuple[str, int, str]] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or field not in row:
                raise ValueError(f"Annotated timestamp is absent: {path}")
            value = row[field]
            if not isinstance(value, str):
                raise ValueError(f"Annotated timestamp must be a string: {path}")
            result.append((f"structured:{source}:{field}", index, value))
        return tuple(result)

    logs = data["log_evidence"]
    if not isinstance(logs, list):
        raise ValueError("ModelView log_evidence must be a list")
    result = []
    for index, entry in enumerate(logs):
        if not isinstance(entry, dict):
            raise ValueError("ModelView log entry must be an object")
        if field in entry:
            value = entry[field]
        else:
            attributes = entry.get("attributes")
            if not isinstance(attributes, dict) or field not in attributes:
                continue
            value = attributes[field]
        if not isinstance(value, str):
            raise ValueError(f"Annotated timestamp must be a string: {path}")
        result.append((f"logs:{field}", index, value))
    if not result:
        raise ValueError(f"Annotated log timestamp is absent: {path}")
    return tuple(result)


def _apply_replacements(
    data: dict[str, JSONValue], replacements: dict[tuple[str, int], str]
) -> None:
    structured = data["structured_evidence"]
    logs = data["log_evidence"]
    assert isinstance(structured, dict)
    assert isinstance(logs, list)
    for (container, index), replacement in replacements.items():
        kind, source_or_field, *remaining = container.split(":")
        if kind == "structured":
            field = remaining[0]
            rows = structured[source_or_field]
            assert isinstance(rows, list)
            row = rows[index]
            assert isinstance(row, dict)
            row[field] = replacement
            continue
        entry = logs[index]
        assert isinstance(entry, dict)
        field = source_or_field
        if field in entry:
            entry[field] = replacement
        else:
            attributes = entry["attributes"]
            assert isinstance(attributes, dict)
            attributes[field] = replacement
