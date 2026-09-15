"""JSON-compatible models for benchmark oracle data and model-visible evidence."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Literal, Self

JSONPrimitive = str | int | float | bool | None
JSONValue = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
InvariantNecessity = Literal["essential", "supportive", "discardable"]
EvidenceRelation = Literal[
    "equal",
    "not_equal",
    "all_distinct",
    "ordered_before",
    "paired_before",
    "interval_seconds",
    "intervals_overlap",
    "row_count",
    "match_count",
    "preserve_literal",
    "same_structural_pattern",
    "structural_pattern_anomaly",
    "structural_defect",
    "length_delta",
    "sequence_equals",
]


@dataclass(frozen=True, slots=True)
class SensitiveField:
    """An oracle-only sensitive-field classification."""

    path: str
    classification: str
    policy: str
    rationale: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data)


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """A stable reference to one field on one selected evidence element."""

    source: str
    selector: dict[str, JSONPrimitive]
    field: str | None = None

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "source": self.source,
            "selector": self.selector,
            "field": self.field,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            source=data["source"],
            selector=data["selector"],
            field=data.get("field"),
        )


@dataclass(frozen=True, slots=True)
class DiagnosticInvariant:
    """An oracle relationship over specifically selected evidence elements."""

    name: str
    relation: EvidenceRelation
    operands: tuple[EvidenceReference, ...]
    expected: JSONValue
    necessity: InvariantNecessity
    description: str

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "name": self.name,
            "relation": self.relation,
            "operands": [item.to_dict() for item in self.operands],
            "expected": self.expected,
            "necessity": self.necessity,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            name=data["name"],
            relation=data["relation"],
            operands=tuple(
                EvidenceReference.from_dict(item) for item in data["operands"]
            ),
            expected=data["expected"],
            necessity=data["necessity"],
            description=data["description"],
        )


@dataclass(frozen=True, slots=True)
class LogEntry:
    evidence_id: str
    timestamp: str
    level: str
    service: str
    message: str
    attributes: dict[str, JSONValue]

    def to_dict(self) -> dict[str, JSONValue]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ExpectedEvidence:
    """Oracle-only evidence expected in a well-supported diagnosis."""

    description: str
    references: tuple[EvidenceReference, ...]

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "description": self.description,
            "references": [item.to_dict() for item in self.references],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            description=data["description"],
            references=tuple(
                EvidenceReference.from_dict(item) for item in data["references"]
            ),
        )


@dataclass(frozen=True, slots=True)
class StructuredRootCause:
    """Oracle-only components used for future component-level RCA scoring."""

    outcome: str
    trigger: str
    failure_mechanism: str
    affected_component: str
    logical_operation_repeated: bool
    explanation: str | None = None

    def to_dict(self) -> dict[str, JSONValue]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data)


@dataclass(frozen=True, slots=True)
class StructuredRootCauseV2:
    """Oracle-only five-dimensional RCA target for rca-taxonomy-v2."""

    observed_outcome: str
    trigger: str
    subsequent_action: str
    failure_mechanism: str
    affected_component: str
    logical_operation_repeated: bool
    explanation: str | None = None

    def to_dict(self) -> dict[str, JSONValue]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data)


@dataclass(frozen=True, slots=True)
class ComponentMapping:
    """Oracle-only mapping from a canonical role to visible service names."""

    canonical_role: str
    visible_names: tuple[str, ...]

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "canonical_role": self.canonical_role,
            "visible_names": list(self.visible_names),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(data["canonical_role"], tuple(data["visible_names"]))


@dataclass(frozen=True, slots=True)
class ModelView:
    """The complete and exclusive representation an evaluated model may receive."""

    troubleshooting_question: str
    structured_evidence: dict[str, list[dict[str, JSONValue]]]
    log_evidence: tuple[LogEntry, ...]

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "troubleshooting_question": self.troubleshooting_question,
            "structured_evidence": self.structured_evidence,
            "log_evidence": [entry.to_dict() for entry in self.log_evidence],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        allowed = {"troubleshooting_question", "structured_evidence", "log_evidence"}
        if set(data) != allowed:
            raise ValueError("ModelView must contain only model-visible fields")
        return cls(
            troubleshooting_question=data["troubleshooting_question"],
            structured_evidence=data["structured_evidence"],
            log_evidence=tuple(LogEntry.from_dict(item) for item in data["log_evidence"]),
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("A ModelView JSON document must contain an object")
        return cls.from_dict(data)


@dataclass(frozen=True, slots=True)
class Incident:
    """Complete benchmark definition, including model-hidden oracle information."""

    incident_id: str
    title: str
    category: str
    description: str
    troubleshooting_question: str
    ground_truth: StructuredRootCause
    ground_truth_v2: StructuredRootCauseV2
    component_mappings: tuple[ComponentMapping, ...]
    structured_evidence: dict[str, list[dict[str, JSONValue]]]
    log_evidence: tuple[LogEntry, ...]
    sensitive_fields: tuple[SensitiveField, ...]
    diagnostic_invariants: tuple[DiagnosticInvariant, ...]
    expected_evidence: tuple[ExpectedEvidence, ...]
    difficulty: Literal["easy", "medium", "hard"]
    metadata: dict[str, JSONValue]

    def model_view(self) -> ModelView:
        """Return a defensive copy of only evidence allowed in model input."""
        return ModelView(
            troubleshooting_question=self.troubleshooting_question,
            structured_evidence=deepcopy(self.structured_evidence),
            log_evidence=deepcopy(self.log_evidence),
        )

    def resolve_reference(self, reference: EvidenceReference) -> JSONValue:
        """Resolve one oracle reference and require exactly one matching element."""
        if reference.source == "logs":
            candidates = [entry.to_dict() for entry in self.log_evidence]
        else:
            try:
                candidates = self.structured_evidence[reference.source]
            except KeyError as error:
                raise ValueError(f"Unknown evidence source: {reference.source}") from error

        matches = [
            item
            for item in candidates
            if all(item.get(key) == value for key, value in reference.selector.items())
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Reference must resolve once; found {len(matches)} matches: {reference}"
            )
        selected = matches[0]
        if reference.field is None:
            return selected
        if reference.field in selected:
            return selected[reference.field]
        attributes = selected.get("attributes")
        if isinstance(attributes, dict) and reference.field in attributes:
            return attributes[reference.field]
        raise ValueError(f"Unknown referenced field: {reference.field}")

    def to_dict(self) -> dict[str, JSONValue]:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "troubleshooting_question": self.troubleshooting_question,
            "ground_truth": self.ground_truth.to_dict(),
            "ground_truth_v2": self.ground_truth_v2.to_dict(),
            "component_mappings": [item.to_dict() for item in self.component_mappings],
            "structured_evidence": self.structured_evidence,
            "log_evidence": [entry.to_dict() for entry in self.log_evidence],
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
            ground_truth=StructuredRootCause.from_dict(data["ground_truth"]),
            ground_truth_v2=StructuredRootCauseV2.from_dict(data["ground_truth_v2"]),
            component_mappings=tuple(
                ComponentMapping.from_dict(item) for item in data["component_mappings"]
            ),
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
