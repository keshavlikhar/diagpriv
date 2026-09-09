"""Deterministic five-dimensional scoring for raw-rca-v2."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Self

from diagbench.schema import Incident
from diagpriv.evaluation.response import RCAResponseV2
from diagpriv.evaluation.scoring import _expected_evidence_ids, _visible_evidence_ids

SCORER_VERSION = "raw-rca-scorer-v2"


class ProtocolVersionError(TypeError):
    """Raised when a response from one protocol is scored under another."""


@dataclass(frozen=True, slots=True)
class RCAScoreV2:
    outcome_correct: bool
    trigger_correct: bool
    subsequent_action_correct: bool
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


def score_response_v2(incident: Incident, response: RCAResponseV2) -> RCAScoreV2:
    """Require exact agreement on all five v2 dimensions and score evidence as v1."""
    if not isinstance(response, RCAResponseV2):
        raise ProtocolVersionError("raw-rca-v2 scoring requires an RCAResponseV2")

    expected_root_cause = incident.ground_truth_v2
    outcome_correct = response.observed_outcome == expected_root_cause.observed_outcome
    trigger_correct = response.trigger == expected_root_cause.trigger
    subsequent_action_correct = (
        response.subsequent_action == expected_root_cause.subsequent_action
    )
    mechanism_correct = (
        response.failure_mechanism == expected_root_cause.failure_mechanism
    )
    component_correct = (
        response.affected_component == expected_root_cause.affected_component
    )
    exact = all(
        (
            outcome_correct,
            trigger_correct,
            subsequent_action_correct,
            mechanism_correct,
            component_correct,
        )
    )

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

    return RCAScoreV2(
        outcome_correct=outcome_correct,
        trigger_correct=trigger_correct,
        subsequent_action_correct=subsequent_action_correct,
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
