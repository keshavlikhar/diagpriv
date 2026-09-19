"""Strict model-visible semantic predicates for Incident 003 evidence v5."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from diagbench.relative_time import RELATIVE_TIME_SEMANTICS_VERSION, parse_relative_time
from diagbench.schema import ModelView
from diagbench.schema.models import JSONValue
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION, parse_timestamp
from diagpriv.evaluation.evidence_support_v3 import EvidencePathV3, EvidenceRubricV3
from diagpriv.transformations.provenance import TEMPORAL_SEMANTICS_UNAVAILABLE

EVIDENCE_SEMANTIC_EVALUATOR_VERSION = (
    "incident-003-v3-evidence-semantic-evaluator-v3"
)

_TEMPORAL_RELATIONSHIPS = frozenset(
    {
        "target_deadline_before_completion",
        "target_compensation_after_deadline",
        "target_execution_compensation_overlap",
        "target_late_successful_effect",
        "twin_successful_effect_before_deadline",
        "twin_compensation_after_committed_success",
        "twin_serialized_execution_before_compensation",
        "safe_compensation_control",
        "deadline_then_compensation_support",
    }
)


@dataclass(frozen=True, slots=True)
class _EvidenceItem:
    source: str
    data: dict[str, JSONValue]


@dataclass(frozen=True, slots=True)
class Incident003V3EvidenceSemanticEvaluatorV5:
    temporal_semantics_version: str
    version: str = EVIDENCE_SEMANTIC_EVALUATOR_VERSION

    def __post_init__(self) -> None:
        if self.temporal_semantics_version not in {
            TEMPORAL_SEMANTICS_VERSION,
            RELATIVE_TIME_SEMANTICS_VERSION,
            TEMPORAL_SEMANTICS_UNAVAILABLE,
        }:
            raise ValueError("Unsupported Incident 003 v5 temporal semantics")

    def evaluate_path(
        self,
        path: EvidencePathV3,
        model_view: ModelView,
        rubric: EvidenceRubricV3,
    ) -> bool:
        parameters = dict(path.semantic_parameters)
        relationship = parameters.get("relationship_id")
        if not isinstance(relationship, str):
            raise ValueError("V5 evidence path requires a relationship_id")
        if relationship in _TEMPORAL_RELATIONSHIPS and not self._has_parser:
            return False
        index = _evidence_index(model_view)
        try:
            items = tuple(index[evidence_id] for evidence_id in path.evidence_ids)
            if not _matches_subject_binding(path, items, rubric):
                return False
            return self._evaluate_relationship(relationship, items)
        except (KeyError, TypeError, ValueError):
            return False

    def _evaluate_relationship(
        self, relationship: str, items: tuple[_EvidenceItem, ...]
    ) -> bool:
        if relationship == "queried_subject_identity":
            return len(items) == 1 and bool(_one_operation_id(items))
        if relationship == "queried_cross_source_linkage":
            return _cross_representation_linkage(items)
        if relationship == "target_deadline_before_completion":
            return self._target_deadline_before_completion(items)
        if relationship == "target_compensation_after_deadline":
            return self._target_compensation_after_deadline(items)
        if relationship == "target_execution_compensation_overlap":
            return self._target_overlap(items)
        if relationship == "target_late_successful_effect":
            return self._target_late_success(items)
        if relationship == "twin_successful_effect_before_deadline":
            return self._twin_success_before_deadline(items)
        if relationship == "twin_compensation_after_committed_success":
            return self._twin_compensation_after_success(items)
        if relationship == "twin_serialized_execution_before_compensation":
            return self._twin_serialized(items)
        if relationship == "inconsistent_terminal_state":
            return _inconsistent_terminal_state(items)
        if relationship == "safe_compensation_control":
            return self._safe_control(items)
        if relationship == "deadline_then_compensation_support":
            return self._before(
                _log(items, "deadline_reached").data["timestamp"],
                _log(items, "compensation_started").data["timestamp"],
            )
        raise ValueError(f"Unsupported Incident 003 v5 relationship: {relationship}")

    def _target_deadline_before_completion(
        self, items: tuple[_EvidenceItem, ...]
    ) -> bool:
        if _is_log_path(items):
            completed = _log(items, "execution_completed").data
            return _nested(completed, "result") == "success" and self._before(
                _log(items, "deadline_reached").data["timestamp"],
                completed["timestamp"],
            )
        execution = _source(items, "execution_observations").data
        return execution.get("result") == "success" and self._before(
            _source(items, "workflow_attempts").data["deadline_at"],
            execution["completed_at"],
        )

    def _target_compensation_after_deadline(
        self, items: tuple[_EvidenceItem, ...]
    ) -> bool:
        if _is_log_path(items):
            return self._before(
                _log(items, "deadline_reached").data["timestamp"],
                _log(items, "compensation_started").data["timestamp"],
            )
        return self._before(
            _source(items, "workflow_attempts").data["deadline_at"],
            _source(items, "compensation_records").data["started_at"],
        )

    def _target_overlap(self, items: tuple[_EvidenceItem, ...]) -> bool:
        if _is_log_path(items):
            return self._overlap(
                _log(items, "execution_started").data["timestamp"],
                _log(items, "execution_completed").data["timestamp"],
                _log(items, "compensation_started").data["timestamp"],
                _log(items, "compensation_completed").data["timestamp"],
            )
        execution = _source(items, "execution_observations").data
        compensation = _source(items, "compensation_records").data
        return self._overlap(
            execution["started_at"],
            execution["completed_at"],
            compensation["started_at"],
            compensation["completed_at"],
        )

    def _target_late_success(self, items: tuple[_EvidenceItem, ...]) -> bool:
        if _is_log_path(items):
            completed = _log(items, "execution_completed").data
            effect = _log(items, "effect_recorded").data
            compensation = _log(items, "compensation_started").data
            return bool(
                _nested(completed, "result") == "success"
                and _nested(effect, "state") == "active"
                and self._before(compensation["timestamp"], completed["timestamp"])
                and self._before(completed["timestamp"], effect["timestamp"])
            )
        execution = _source(items, "execution_observations").data
        effect = _source(items, "effect_records").data
        compensation = _source(items, "compensation_records").data
        return bool(
            execution.get("result") == "success"
            and effect.get("state") == "active"
            and self._before(compensation["started_at"], execution["completed_at"])
            and self._before(execution["completed_at"], effect["created_at"])
        )

    def _twin_success_before_deadline(
        self, items: tuple[_EvidenceItem, ...]
    ) -> bool:
        if _is_log_path(items):
            completed = _log(items, "execution_completed").data
            effect = _log(items, "effect_recorded").data
            deadline = _log(items, "deadline_reached").data
            return bool(
                _nested(completed, "result") == "success"
                and _nested(effect, "state") == "active"
                and self._before(completed["timestamp"], effect["timestamp"])
                and self._before(effect["timestamp"], deadline["timestamp"])
            )
        workflow = _source(items, "workflow_attempts").data
        execution = _source(items, "execution_observations").data
        effect = _source(items, "effect_records").data
        return bool(
            execution.get("result") == "success"
            and effect.get("state") == "active"
            and self._before(execution["completed_at"], effect["created_at"])
            and self._before(effect["created_at"], workflow["deadline_at"])
        )

    def _twin_compensation_after_success(
        self, items: tuple[_EvidenceItem, ...]
    ) -> bool:
        if _is_log_path(items):
            effect = _log(items, "effect_recorded").data
            deadline = _log(items, "deadline_reached").data
            started = _log(items, "compensation_started").data
            return bool(
                _nested(effect, "state") == "active"
                and self._before(effect["timestamp"], deadline["timestamp"])
                and self._before(deadline["timestamp"], started["timestamp"])
            )
        workflow = _source(items, "workflow_attempts").data
        effect = _source(items, "effect_records").data
        compensation = _source(items, "compensation_records").data
        return bool(
            effect.get("state") == "active"
            and self._before(effect["created_at"], workflow["deadline_at"])
            and self._before(workflow["deadline_at"], compensation["started_at"])
        )

    def _twin_serialized(self, items: tuple[_EvidenceItem, ...]) -> bool:
        if _is_log_path(items):
            completed = _log(items, "execution_completed").data
            started = _log(items, "compensation_started").data
            return bool(
                _nested(completed, "result") == "success"
                and self._before(
                    completed["timestamp"],
                    started["timestamp"],
                )
            )
        execution = _source(items, "execution_observations").data
        compensation = _source(items, "compensation_records").data
        return bool(
            execution.get("result") == "success"
            and self._before(
                execution["completed_at"],
                compensation["started_at"],
            )
        )

    def _safe_control(self, items: tuple[_EvidenceItem, ...]) -> bool:
        if _is_log_path(items):
            execution = _log(items, "execution_completed").data
            effect = _log(items, "effect_recorded").data
            started = _log(items, "compensation_started").data
            completed = _log(items, "compensation_completed").data
            workflow = _log(items, "workflow_state_recorded").data
            return bool(
                _nested(execution, "result") == "cancelled"
                and _nested(effect, "state") == "inactive"
                and _nested(completed, "result") == "completed"
                and _nested(workflow, "workflow_state") == "compensated"
                and self._before(execution["timestamp"], started["timestamp"])
                and self._before(started["timestamp"], completed["timestamp"])
            )
        workflow = _source(items, "workflow_attempts").data
        execution = _source(items, "execution_observations").data
        effect = _source(items, "effect_records").data
        compensation = _source(items, "compensation_records").data
        return bool(
            workflow.get("workflow_state") == "compensated"
            and execution.get("result") == "cancelled"
            and effect.get("state") == "inactive"
            and compensation.get("result") == "completed"
            and self._before(execution["completed_at"], compensation["started_at"])
            and self._before(compensation["started_at"], compensation["completed_at"])
        )

    @property
    def _has_parser(self) -> bool:
        return self.temporal_semantics_version != TEMPORAL_SEMANTICS_UNAVAILABLE

    @property
    def _parse_time(self) -> Callable[[str], object]:
        if self.temporal_semantics_version == TEMPORAL_SEMANTICS_VERSION:
            return parse_timestamp
        if self.temporal_semantics_version == RELATIVE_TIME_SEMANTICS_VERSION:
            return parse_relative_time
        raise ValueError("Temporal semantics unavailable")

    def _before(self, left: object, right: object) -> bool:
        return bool(self._parse_time(_string(left)) < self._parse_time(_string(right)))  # type: ignore[operator]

    def _overlap(self, a_start: object, a_end: object, b_start: object, b_end: object) -> bool:
        parse = self._parse_time
        start_a, end_a = parse(_string(a_start)), parse(_string(a_end))
        start_b, end_b = parse(_string(b_start)), parse(_string(b_end))
        return bool(
            start_a < end_a  # type: ignore[operator]
            and start_b < end_b  # type: ignore[operator]
            and max(start_a, start_b) < min(end_a, end_b)  # type: ignore[type-var,operator]
        )


def _evidence_index(view: ModelView) -> dict[str, _EvidenceItem]:
    result: dict[str, _EvidenceItem] = {}
    for source, rows in view.structured_evidence.items():
        for row in rows:
            result[_string(row["evidence_id"])] = _EvidenceItem(source, row)
    for entry in view.log_evidence:
        result[entry.evidence_id] = _EvidenceItem("logs", entry.to_dict())
    return result


def _matches_subject_binding(
    path: EvidencePathV3,
    items: tuple[_EvidenceItem, ...],
    rubric: EvidenceRubricV3,
) -> bool:
    binding = next(
        (item for item in rubric.subject_bindings if item.binding_id == path.subject_binding_id),
        None,
    )
    if binding is None:
        return False
    return _one_operation_id(items) == binding.subject_id


def _cross_representation_linkage(items: tuple[_EvidenceItem, ...]) -> bool:
    if len(items) < 2 or not _one_operation_id(items):
        return False
    if _is_log_path(items):
        services = {_string(item.data["service"]) for item in items}
        events = {_string(_nested(item.data, "event_kind")) for item in items}
        return len(services) >= 2 and len(events) == len(items)
    return len({item.source for item in items}) == len(items)


def _inconsistent_terminal_state(items: tuple[_EvidenceItem, ...]) -> bool:
    if _is_log_path(items):
        return bool(
            _nested(_log(items, "execution_completed").data, "result") == "success"
            and _nested(_log(items, "effect_recorded").data, "state") == "active"
            and _nested(_log(items, "workflow_state_recorded").data, "workflow_state")
            == "compensated"
        )
    workflow = _source(items, "workflow_attempts").data
    return bool(
        workflow.get("workflow_state") == "compensated"
        and _source(items, "execution_observations").data.get("result") == "success"
        and _source(items, "effect_records").data.get("state") == "active"
    )


def _one_operation_id(items: tuple[_EvidenceItem, ...]) -> str:
    values = {_string(_nested(item.data, "operation_id")) for item in items}
    if len(values) != 1:
        raise ValueError("V5 path does not expose exactly one operation identity")
    return next(iter(values))


def _source(items: tuple[_EvidenceItem, ...], source: str) -> _EvidenceItem:
    matches = tuple(item for item in items if item.source == source)
    if len(matches) != 1:
        raise ValueError(f"Expected one {source} evidence item")
    return matches[0]


def _log(items: tuple[_EvidenceItem, ...], event_kind: str) -> _EvidenceItem:
    matches = tuple(
        item for item in items if _nested(item.data, "event_kind") == event_kind
    )
    if len(matches) != 1:
        raise ValueError(f"Expected one {event_kind} log item")
    return matches[0]


def _is_log_path(items: tuple[_EvidenceItem, ...]) -> bool:
    return bool(items) and all(item.source == "logs" for item in items)


def _nested(data: dict[str, JSONValue], field: str) -> object:
    if field in data:
        return data[field]
    attributes = data.get("attributes")
    if isinstance(attributes, dict) and field in attributes:
        return attributes[field]
    raise ValueError(f"Evidence item does not expose {field}")


def _string(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("Expected a non-empty model-visible string")
    return value
