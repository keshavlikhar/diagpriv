"""Naive, annotation-driven redaction baseline."""

from __future__ import annotations

from copy import deepcopy

from diagbench.schema import Incident, ModelView
from diagbench.schema.models import JSONValue

TRANSFORMATION_VERSION = "redaction-v1"


def redaction_placeholder(path: str, value: JSONValue) -> JSONValue:
    """Return a many-to-one placeholder that is not derived from the value."""
    if value is None:
        return None
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        return 0.0
    if isinstance(value, str):
        return f"[REDACTED:{path}]"
    if isinstance(value, list):
        return []
    if isinstance(value, dict):
        return {}
    raise TypeError(f"Unsupported sensitive value type at {path}: {type(value)}")


def redact_incident(incident: Incident) -> ModelView:
    """Redact annotated fields and return model-visible evidence only.

    Every occurrence at a source-qualified field path receives the same generic
    many-to-one placeholder. Placeholders are not keyed to plaintext values, so
    this condition neither tokenizes values nor intentionally preserves identity.
    """
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

        if source == "logs":
            _redact_logs(data, field, path)
        else:
            _redact_structured_rows(data, source, field, path)

    return ModelView.from_dict(data)


def _redact_structured_rows(
    data: dict[str, JSONValue], source: str, field: str, path: str
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
        row[field] = redaction_placeholder(path, row[field])


def _redact_logs(data: dict[str, JSONValue], field: str, path: str) -> None:
    logs = data["log_evidence"]
    if not isinstance(logs, list):
        raise ValueError("ModelView log_evidence must be a list")
    matches = 0
    for entry in logs:
        if not isinstance(entry, dict):
            raise ValueError("ModelView log entry must be an object")
        if field in entry:
            entry[field] = redaction_placeholder(path, entry[field])
            matches += 1
            continue
        attributes = entry.get("attributes")
        if isinstance(attributes, dict) and field in attributes:
            attributes[field] = redaction_placeholder(path, attributes[field])
            matches += 1
    if matches == 0:
        raise ValueError(f"Sensitive log field is absent: {field}")
