"""Semantic evidence evaluation for Incident 003 v3 under v4 scoring."""

from __future__ import annotations

from dataclasses import dataclass

from diagbench.relative_time import RELATIVE_TIME_SEMANTICS_VERSION, parse_relative_time
from diagbench.schema import ModelView
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION, parse_timestamp
from diagpriv.evaluation.evidence_support_v3 import EvidencePathV3, EvidenceRubricV3
from diagpriv.evaluation.incident_003_v2_evidence_semantics import (
    Incident003V2EvidenceSemanticEvaluator,
)
from diagpriv.transformations.provenance import TEMPORAL_SEMANTICS_UNAVAILABLE

EVIDENCE_SEMANTIC_EVALUATOR_VERSION = (
    "incident-003-v3-evidence-semantic-evaluator-v2"
)


@dataclass(frozen=True, slots=True)
class Incident003V3EvidenceSemanticEvaluator:
    temporal_semantics_version: str
    version: str = EVIDENCE_SEMANTIC_EVALUATOR_VERSION

    def __post_init__(self) -> None:
        if self.temporal_semantics_version not in {
            TEMPORAL_SEMANTICS_VERSION,
            RELATIVE_TIME_SEMANTICS_VERSION,
            TEMPORAL_SEMANTICS_UNAVAILABLE,
        }:
            raise ValueError("Unsupported Incident 003 v3 temporal semantics")

    def evaluate_path(
        self,
        path: EvidencePathV3,
        model_view: ModelView,
        rubric: EvidenceRubricV3,
    ) -> bool:
        relationship = dict(path.semantic_parameters).get("relationship_id")
        if relationship == "temporal_twin_serialized_contrast":
            return self._serialized_twin(path, model_view)
        if relationship == "twin_success_effect_before_deadline":
            return self._twin_success_effect_before_deadline(path, model_view)
        if relationship == "twin_compensation_after_committed_success":
            return self._twin_compensation_after_committed_success(path, model_view)
        if relationship == "twin_serialized_no_overlap":
            return self._twin_serialized_no_overlap(path, model_view)
        if relationship == "safe_compensation_control":
            return self._safe_control(path, model_view)
        delegate = Incident003V2EvidenceSemanticEvaluator(
            self.temporal_semantics_version
        )
        return delegate.evaluate_path(path, model_view, rubric)

    def _serialized_twin(self, path: EvidencePathV3, view: ModelView) -> bool:
        if not self._has_parser:
            return False
        rows = _rows(path, view)
        try:
            workflow = rows["workflow_attempts"]
            execution = rows["execution_observations"]
            effect = rows["effect_records"]
            compensation = rows["compensation_records"]
            return bool(
                execution["result"] == "success"
                and effect["state"] == "active"
                and workflow["workflow_state"] == "compensated"
                and compensation["result"] == "completed"
                and self._before(execution["completed_at"], effect["created_at"])
                and self._before(effect["created_at"], workflow["deadline_at"])
                and self._before(workflow["deadline_at"], compensation["started_at"])
                and self._before(compensation["started_at"], compensation["completed_at"])
            )
        except (KeyError, TypeError, ValueError):
            return False

    def _twin_success_effect_before_deadline(
        self, path: EvidencePathV3, view: ModelView
    ) -> bool:
        if not self._has_parser:
            return False
        rows = _rows(path, view)
        try:
            workflow = rows["workflow_attempts"]
            execution = rows["execution_observations"]
            effect = rows["effect_records"]
            return bool(
                execution["result"] == "success"
                and effect["state"] == "active"
                and self._before(execution["completed_at"], effect["created_at"])
                and self._before(effect["created_at"], workflow["deadline_at"])
            )
        except (KeyError, TypeError, ValueError):
            return False

    def _twin_compensation_after_committed_success(
        self, path: EvidencePathV3, view: ModelView
    ) -> bool:
        if not self._has_parser:
            return False
        rows = _rows(path, view)
        try:
            workflow = rows["workflow_attempts"]
            effect = rows["effect_records"]
            compensation = rows["compensation_records"]
            return bool(
                effect["state"] == "active"
                and compensation["result"] == "completed"
                and self._before(effect["created_at"], workflow["deadline_at"])
                and self._before(
                    workflow["deadline_at"], compensation["started_at"]
                )
                and self._before(
                    compensation["started_at"], compensation["completed_at"]
                )
            )
        except (KeyError, TypeError, ValueError):
            return False

    def _twin_serialized_no_overlap(
        self, path: EvidencePathV3, view: ModelView
    ) -> bool:
        if not self._has_parser:
            return False
        rows = _rows(path, view)
        try:
            execution = rows["execution_observations"]
            compensation = rows["compensation_records"]
            return bool(
                self._before(execution["started_at"], execution["completed_at"])
                and self._before(
                    execution["completed_at"], compensation["started_at"]
                )
                and self._before(
                    compensation["started_at"], compensation["completed_at"]
                )
            )
        except (KeyError, TypeError, ValueError):
            return False

    def _safe_control(self, path: EvidencePathV3, view: ModelView) -> bool:
        if not self._has_parser:
            return False
        rows = _rows(path, view)
        try:
            workflow = rows["workflow_attempts"]
            execution = rows["execution_observations"]
            effect = rows["effect_records"]
            compensation = rows["compensation_records"]
            return bool(
                execution["result"] == "cancelled"
                and effect["state"] == "inactive"
                and workflow["workflow_state"] == "compensated"
                and compensation["result"] == "completed"
                and self._before(workflow["deadline_at"], execution["completed_at"])
                and self._before(execution["completed_at"], compensation["started_at"])
                and self._before(compensation["started_at"], compensation["completed_at"])
            )
        except (KeyError, TypeError, ValueError):
            return False

    @property
    def _has_parser(self) -> bool:
        return self.temporal_semantics_version != TEMPORAL_SEMANTICS_UNAVAILABLE

    def _before(self, left: object, right: object) -> bool:
        parser = (
            parse_timestamp
            if self.temporal_semantics_version == TEMPORAL_SEMANTICS_VERSION
            else parse_relative_time
        )
        return bool(parser(str(left)) < parser(str(right)))


def _rows(path: EvidencePathV3, view: ModelView) -> dict[str, dict]:
    wanted = set(path.evidence_ids)
    result: dict[str, dict] = {}
    operation_ids: set[object] = set()
    for source, rows in view.structured_evidence.items():
        for row in rows:
            if row.get("evidence_id") in wanted:
                result[source] = row
                operation_ids.add(row.get("operation_id"))
    if len(result) != len(wanted) or len(operation_ids) != 1:
        raise ValueError("Evidence path must bind one complete operation")
    return result
