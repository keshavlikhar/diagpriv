"""Small, dependency-free, JSON-compatible benchmark models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Literal, Self

JSONPrimitive = str | int | float | bool | None
JSONValue = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
InvariantType = Literal[
    "equality",
    "uniqueness",
    "duplicates",
    "row_cardinality",
    "null_placement",
    "referential_relationship",
    "joinability",
    "ordering",
    "temporal_interval",
    "numeric_equality",
    "numeric_ordering",
    "string_format",
    "malformed_format",
    "state_transition",
    "cross_source_identity",
]


@dataclass(frozen=True, slots=True)
class SensitiveField:
    """A field classified as sensitive for an incident."""

    path: str
    classification: str
    policy: str
    rationale: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data)


@dataclass(frozen=True, slots=True)
class DiagnosticInvariant:
    """A relationship a future transformation should preserve or may discard."""

    name: str
    type: InvariantType
    fields: tuple[str, ...]
    must_preserve: bool
    description: str

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "name": self.name,
            "type": self.type,
            "fields": list(self.fields),
            "must_preserve": self.must_preserve,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            name=data["name"],
            type=data["type"],
            fields=tuple(data["fields"]),
            must_preserve=data["must_preserve"],
            description=data["description"],
        )


@dataclass(frozen=True, slots=True)
class LogEntry:
    timestamp: str
    level: str
    service: str
    message: str
    attributes: dict[str, JSONValue]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ExpectedEvidence:
    description: str
    references: tuple[str, ...]

    def to_dict(self) -> dict[str, JSONValue]:
        return {"description": self.description, "references": list(self.references)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(data["description"], tuple(data["references"]))


@dataclass(frozen=True, slots=True)
class Incident:
    incident_id: str
    title: str
    category: str
    description: str
    troubleshooting_question: str
    ground_truth_root_cause: str
    structured_evidence: dict[str, list[dict[str, JSONValue]]]
    log_evidence: tuple[LogEntry, ...]
    sensitive_fields: tuple[SensitiveField, ...]
    diagnostic_invariants: tuple[DiagnosticInvariant, ...]
    expected_evidence: tuple[ExpectedEvidence, ...]
    difficulty: Literal["easy", "medium", "hard"]
    metadata: dict[str, JSONValue]

    def to_dict(self) -> dict[str, JSONValue]:
        """Return a structure accepted by the standard JSON encoder."""
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "troubleshooting_question": self.troubleshooting_question,
            "ground_truth_root_cause": self.ground_truth_root_cause,
            "structured_evidence": self.structured_evidence,
            "log_evidence": [asdict(entry) for entry in self.log_evidence],
            "sensitive_fields": [asdict(field) for field in self.sensitive_fields],
            "diagnostic_invariants": [item.to_dict() for item in self.diagnostic_invariants],
            "expected_evidence": [item.to_dict() for item in self.expected_evidence],
            "difficulty": self.difficulty,
            "metadata": self.metadata,
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        required = {field.name for field in cls.__dataclass_fields__.values()}
        missing = required.difference(data)
        if missing:
            raise ValueError(f"Missing incident fields: {sorted(missing)}")
        return cls(
            incident_id=data["incident_id"],
            title=data["title"],
            category=data["category"],
            description=data["description"],
            troubleshooting_question=data["troubleshooting_question"],
            ground_truth_root_cause=data["ground_truth_root_cause"],
            structured_evidence=data["structured_evidence"],
            log_evidence=tuple(LogEntry.from_dict(item) for item in data["log_evidence"]),
            sensitive_fields=tuple(
                SensitiveField.from_dict(item) for item in data["sensitive_fields"]
            ),
            diagnostic_invariants=tuple(
                DiagnosticInvariant.from_dict(item)
                for item in data["diagnostic_invariants"]
            ),
            expected_evidence=tuple(
                ExpectedEvidence.from_dict(item) for item in data["expected_evidence"]
            ),
            difficulty=data["difficulty"],
            metadata=data["metadata"],
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("An incident JSON document must contain an object")
        return cls.from_dict(data)

    @classmethod
    def load(cls, path: Path) -> Self:
        return cls.from_json(path.read_text(encoding="utf-8"))

