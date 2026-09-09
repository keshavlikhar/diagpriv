"""Explicit deterministic scoring for structured RCA responses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Self

from diagbench.schema import Incident
from diagpriv.evaluation.response import RCAResponse
from diagpriv.evaluation.taxonomy import canonical_category, normalize_label


@dataclass(frozen=True, slots=True)
class RCAScore:
    outcome_correct: bool
    trigger_correct: bool
    failure_mechanism_correct: bool
    affected_component_correct: bool
    exact_root_cause_correct: bool
    evidence_precision: float
    evidence_recall: float
    evidence_f1: float
    evidence_supported: bool
    valid_evidence_ids: tuple[str, ...]
    matched_evidence_ids: tuple[str, ...]
    unknown_evidence_ids: tuple[str, ...]
    expected_evidence_ids: tuple[str, ...]
    overall_correct: bool

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        for field in (
            "valid_evidence_ids",
            "matched_evidence_ids",
            "unknown_evidence_ids",
            "expected_evidence_ids",
        ):
            data[field] = list(data[field])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        converted = dict(data)
        for field in (
            "valid_evidence_ids",
            "matched_evidence_ids",
            "unknown_evidence_ids",
            "expected_evidence_ids",
        ):
            converted[field] = tuple(converted[field])
        return cls(**converted)


def _visible_evidence_ids(incident: Incident) -> set[str]:
    identifiers = {
        str(row["evidence_id"])
        for rows in incident.model_view().structured_evidence.values()
        for row in rows
    }
    identifiers.update(entry.evidence_id for entry in incident.model_view().log_evidence)
    return identifiers


def _expected_evidence_ids(incident: Incident) -> set[str]:
    return {
        str(reference.selector["evidence_id"])
        for expected in incident.expected_evidence
        for reference in expected.references
    }


def _component_is_correct(incident: Incident, submitted: str) -> bool:
    expected = normalize_label(incident.ground_truth.affected_component)
    accepted = {expected}
    for mapping in incident.component_mappings:
        if normalize_label(mapping.canonical_role) == expected:
            accepted.update(normalize_label(name) for name in mapping.visible_names)
    return normalize_label(submitted) in accepted


def score_response(incident: Incident, response: RCAResponse) -> RCAScore:
    """Score categories and evidence with fixed, inspectable rules."""
    outcome_correct = (
        canonical_category("observed_outcome", response.observed_outcome)
        == incident.ground_truth.outcome
    )
    trigger_correct = (
        canonical_category("trigger", response.trigger) == incident.ground_truth.trigger
    )
    mechanism_correct = (
        canonical_category("failure_mechanism", response.failure_mechanism)
        == incident.ground_truth.failure_mechanism
    )
    component_correct = _component_is_correct(incident, response.affected_component)
    exact = outcome_correct and trigger_correct and mechanism_correct and component_correct

    submitted = set(response.supporting_evidence)
    visible = _visible_evidence_ids(incident)
    expected = _expected_evidence_ids(incident)
    valid = submitted & visible
    matched = valid & expected
    unknown = submitted - visible
    precision = len(matched) / len(submitted) if submitted else 0.0
    recall = len(matched) / len(expected) if expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    evidence_supported = bool(matched) and not unknown

    return RCAScore(
        outcome_correct=outcome_correct,
        trigger_correct=trigger_correct,
        failure_mechanism_correct=mechanism_correct,
        affected_component_correct=component_correct,
        exact_root_cause_correct=exact,
        evidence_precision=precision,
        evidence_recall=recall,
        evidence_f1=f1,
        evidence_supported=evidence_supported,
        valid_evidence_ids=tuple(sorted(valid)),
        matched_evidence_ids=tuple(sorted(matched)),
        unknown_evidence_ids=tuple(sorted(unknown)),
        expected_evidence_ids=tuple(sorted(expected)),
        overall_correct=exact and evidence_supported,
    )

