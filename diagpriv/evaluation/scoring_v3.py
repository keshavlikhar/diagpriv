"""Five-dimensional RCA and semantic evidence scoring for raw-rca-v3."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Self

from diagbench.schema import Incident, ModelView
from diagpriv.evaluation.evidence_support_v3 import (
    EVIDENCE_SUPPORT_VERSION as EVIDENCE_SUPPORT_VERSION_V3,
    EvidenceRubricV3,
    score_evidence_support_v3,
)
from diagpriv.evaluation.evidence_support_v4 import (
    EVIDENCE_SUPPORT_VERSION as EVIDENCE_SUPPORT_VERSION_V4,
    EvidenceSemanticEvaluatorV4,
    score_evidence_support_v4,
)
from diagpriv.evaluation.evidence_support_v5 import (
    EVIDENCE_SUPPORT_VERSION as EVIDENCE_SUPPORT_VERSION_V5,
    EvidenceSemanticEvaluatorV5,
    score_evidence_support_v5,
)
from diagpriv.evaluation.response import RCAResponseV3
from diagpriv.evaluation.scoring_v2 import ProtocolVersionError

SCORER_VERSION = "raw-rca-scorer-v3"


@dataclass(frozen=True, slots=True)
class RCAScoreV3:
    outcome_correct: bool
    trigger_correct: bool
    subsequent_action_correct: bool
    failure_mechanism_correct: bool
    affected_component_correct: bool
    exact_root_cause_correct: bool
    essential_requirement_coverage: float
    contrast_requirement_coverage: float
    supportive_requirement_coverage: float
    useful_citation_precision: float
    invalid_citation_count: int
    invalid_citation_rate: float
    wrong_subject_citation_count: int
    contextual_citation_count: int
    redundant_citation_count: int
    redundant_citation_rate: float
    evidence_supported: bool
    satisfied_essential_requirements: tuple[str, ...]
    missing_essential_requirements: tuple[str, ...]
    satisfied_contrast_requirements: tuple[str, ...]
    satisfied_supportive_requirements: tuple[str, ...]
    selected_evidence_paths: tuple[str, ...]
    valid_evidence_ids: tuple[str, ...]
    useful_evidence_ids: tuple[str, ...]
    unknown_evidence_ids: tuple[str, ...]
    wrong_subject_evidence_ids: tuple[str, ...]
    contextual_evidence_ids: tuple[str, ...]
    redundant_evidence_ids: tuple[str, ...]
    evidence_precision: float
    evidence_recall: float
    evidence_f1: float
    overall_correct: bool

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        for field in (
            "satisfied_essential_requirements",
            "missing_essential_requirements",
            "satisfied_contrast_requirements",
            "satisfied_supportive_requirements",
            "selected_evidence_paths",
            "valid_evidence_ids",
            "useful_evidence_ids",
            "unknown_evidence_ids",
            "wrong_subject_evidence_ids",
            "contextual_evidence_ids",
            "redundant_evidence_ids",
        ):
            data[field] = list(data[field])
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        converted = dict(data)
        for field in (
            "satisfied_essential_requirements",
            "missing_essential_requirements",
            "satisfied_contrast_requirements",
            "satisfied_supportive_requirements",
            "selected_evidence_paths",
            "valid_evidence_ids",
            "useful_evidence_ids",
            "unknown_evidence_ids",
            "wrong_subject_evidence_ids",
            "contextual_evidence_ids",
            "redundant_evidence_ids",
        ):
            converted[field] = tuple(converted[field])
        return cls(**converted)


def score_response_v3(
    incident: Incident,
    response: RCAResponseV3,
    rubric: EvidenceRubricV3,
    *,
    evidence_support_version: str = EVIDENCE_SUPPORT_VERSION_V3,
    model_view: ModelView | None = None,
    semantic_evaluator: EvidenceSemanticEvaluatorV4 | EvidenceSemanticEvaluatorV5 | None = None,
) -> RCAScoreV3:
    """Score unchanged RCA-v3 labels with an explicit evidence protocol."""
    if not isinstance(response, RCAResponseV3):
        raise ProtocolVersionError("raw-rca-v3 scoring requires an RCAResponseV3")
    oracle = getattr(incident, "ground_truth_v3", None)
    if oracle is None:
        raise ProtocolVersionError("raw-rca-v3 scoring requires a v3 incident oracle")

    outcome_correct = response.observed_outcome == oracle.observed_outcome
    trigger_correct = response.trigger == oracle.trigger
    subsequent_action_correct = response.subsequent_action == oracle.subsequent_action
    mechanism_correct = response.failure_mechanism == oracle.failure_mechanism
    component_correct = response.affected_component == oracle.affected_component
    exact = all(
        (
            outcome_correct,
            trigger_correct,
            subsequent_action_correct,
            mechanism_correct,
            component_correct,
        )
    )
    if evidence_support_version == EVIDENCE_SUPPORT_VERSION_V3:
        # Historical evidence-support-v3 evaluated citation paths against the
        # raw incident view.  Keep that behavior available for interpreting
        # frozen raw and relative-time observations.
        evidence = score_evidence_support_v3(
            response.supporting_evidence,
            incident.model_view(),
            rubric,
        )
    elif evidence_support_version == EVIDENCE_SUPPORT_VERSION_V4:
        if model_view is None or semantic_evaluator is None:
            raise ProtocolVersionError(
                "evidence-support-v4 requires a transformed ModelView and "
                "semantic evaluator"
            )
        evidence = score_evidence_support_v4(
            response.supporting_evidence,
            model_view,
            rubric,
            semantic_evaluator,
        )
    elif evidence_support_version == EVIDENCE_SUPPORT_VERSION_V5:
        if model_view is None or semantic_evaluator is None:
            raise ProtocolVersionError(
                "evidence-support-v5 requires a transformed ModelView and "
                "semantic evaluator"
            )
        evidence = score_evidence_support_v5(
            response.supporting_evidence,
            model_view,
            rubric,
            semantic_evaluator,
        )
    else:
        raise ProtocolVersionError(
            f"Unsupported evidence protocol: {evidence_support_version}"
        )
    return RCAScoreV3(
        outcome_correct=outcome_correct,
        trigger_correct=trigger_correct,
        subsequent_action_correct=subsequent_action_correct,
        failure_mechanism_correct=mechanism_correct,
        affected_component_correct=component_correct,
        exact_root_cause_correct=exact,
        **asdict(evidence),
        overall_correct=exact and evidence.evidence_supported,
    )
