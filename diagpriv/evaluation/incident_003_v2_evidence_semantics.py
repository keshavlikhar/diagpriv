"""Model-visible semantic evidence evaluation for Incident 003 v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from diagbench.relative_time import (
    RELATIVE_TIME_SEMANTICS_VERSION,
    parse_relative_time,
)
from diagbench.schema import ModelView
from diagbench.schema.models import JSONValue
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION, parse_timestamp
from diagpriv.evaluation.evidence_support_v3 import (
    EvidencePathV3,
    EvidenceRubricV3,
)
from diagpriv.transformations.provenance import TEMPORAL_SEMANTICS_UNAVAILABLE

EVIDENCE_SEMANTIC_EVALUATOR_VERSION = (
    "incident-003-v2-evidence-semantic-evaluator-v1"
)

_TEMPORAL_RELATIONSHIPS = frozenset(
    {
        "deadline_before_original_completion",
        "compensation_after_deadline",
        "execution_compensation_overlap",
        "late_successful_original_effect",
        "legitimate_compensation_control",
        "healthy_deadline_or_benign_slow_control",
        "additional_target_lifecycle",
    }
)


@dataclass(frozen=True, slots=True)
class _EvidenceItem:
    source: str
    data: dict[str, JSONValue]


@dataclass(frozen=True, slots=True)
class Incident003V2EvidenceSemanticEvaluator:
    """Evaluate frozen relationships from transformed, model-visible values."""

    temporal_semantics_version: str
    version: str = EVIDENCE_SEMANTIC_EVALUATOR_VERSION

    def __post_init__(self) -> None:
        if self.temporal_semantics_version not in {
            TEMPORAL_SEMANTICS_VERSION,
            RELATIVE_TIME_SEMANTICS_VERSION,
            TEMPORAL_SEMANTICS_UNAVAILABLE,
        }:
            raise ValueError(
                "Unsupported Incident 003 v2 temporal semantics: "
                f"{self.temporal_semantics_version}"
            )

    def evaluate_path(
        self,
        path: EvidencePathV3,
        model_view: ModelView,
        rubric: EvidenceRubricV3,
    ) -> bool:
        parameters = dict(path.semantic_parameters)
        relationship = parameters.get("relationship_id")
        if not isinstance(relationship, str):
            raise ValueError("Evidence path requires a relationship_id")
        if relationship in _TEMPORAL_RELATIONSHIPS and not self._has_time_parser:
            return False

        index = _evidence_index(model_view)
        items = tuple(index[evidence_id] for evidence_id in path.evidence_ids)
        try:
            return self._evaluate_relationship(
                relationship, path, items, index, rubric
            )
        except (KeyError, TypeError, ValueError):
            # Malformed or semantically unavailable model-visible values fail
            # closed; they are never coerced or lexically compared as time.
            return False

    @property
    def _has_time_parser(self) -> bool:
        return self.temporal_semantics_version != TEMPORAL_SEMANTICS_UNAVAILABLE

    @property
    def _parse_time(self) -> Callable[[str], object]:
        if self.temporal_semantics_version == TEMPORAL_SEMANTICS_VERSION:
            return parse_timestamp
        if self.temporal_semantics_version == RELATIVE_TIME_SEMANTICS_VERSION:
            return parse_relative_time
        raise ValueError("Temporal semantics are unavailable")

    def _before(self, first: object, second: object) -> bool:
        left = self._parse_time(_string(first))
        right = self._parse_time(_string(second))
        return bool(left < right)  # type: ignore[operator]

    def _overlap(
        self,
        first_start: object,
        first_end: object,
        second_start: object,
        second_end: object,
    ) -> bool:
        parse = self._parse_time
        start_a = parse(_string(first_start))
        end_a = parse(_string(first_end))
        start_b = parse(_string(second_start))
        end_b = parse(_string(second_end))
        if not (start_a < end_a and start_b < end_b):  # type: ignore[operator]
            return False
        return bool(max(start_a, start_b) < min(end_a, end_b))  # type: ignore[type-var,operator]

    def _evaluate_relationship(
        self,
        relationship: str,
        path: EvidencePathV3,
        items: tuple[_EvidenceItem, ...],
        index: dict[str, _EvidenceItem],
        rubric: EvidenceRubricV3,
    ) -> bool:
        same_subject = _has_genuine_subject_linkage(path, items, index, rubric)
        if relationship == "target_identity_linkage":
            return same_subject
        if relationship == "deadline_before_original_completion":
            return same_subject and self._deadline_before_completion(items)
        if relationship == "compensation_after_deadline":
            return same_subject and self._compensation_after_deadline(items)
        if relationship == "execution_compensation_overlap":
            return same_subject and self._execution_compensation_overlap(items)
        if relationship == "late_successful_original_effect":
            return same_subject and self._late_successful_effect(items)
        if relationship == "inconsistent_terminal_workflow_effect_state":
            return same_subject and _inconsistent_terminal_state(items)
        if relationship == "legitimate_compensation_control":
            return same_subject and self._legitimate_compensation(items, index)
        if relationship == "healthy_deadline_or_benign_slow_control":
            return same_subject and self._healthy_control(items)
        if relationship == "orchestrator_ownership":
            return same_subject and _shared_nonempty_value(items, "orchestrator_alias")
        if relationship == "executor_ownership":
            return same_subject and _shared_nonempty_value(items, "executor_alias")
        if relationship == "dependency_available":
            return len(items) == 1 and items[0].data.get("availability_state") == "available"
        if relationship == "warning_comparison":
            return len(items) == 1 and items[0].data.get("warning") == "latency_elevated"
        if relationship == "additional_target_lifecycle":
            return same_subject and self._target_lifecycle(items)
        raise ValueError(f"Unsupported Incident 003 v2 relationship: {relationship}")

    def _deadline_before_completion(self, items: tuple[_EvidenceItem, ...]) -> bool:
        if _is_log_path(items):
            return self._before(
                _log(items, "deadline_reached").data["timestamp"],
                _log(items, "execution_completed").data["timestamp"],
            )
        return self._before(
            _source(items, "workflow_attempts").data["deadline_at"],
            _source(items, "execution_observations").data["completed_at"],
        )

    def _compensation_after_deadline(self, items: tuple[_EvidenceItem, ...]) -> bool:
        if _is_log_path(items):
            return self._before(
                _log(items, "deadline_reached").data["timestamp"],
                _log(items, "compensation_started").data["timestamp"],
            )
        return self._before(
            _source(items, "workflow_attempts").data["deadline_at"],
            _source(items, "compensation_records").data["started_at"],
        )

    def _execution_compensation_overlap(
        self, items: tuple[_EvidenceItem, ...]
    ) -> bool:
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

    def _late_successful_effect(self, items: tuple[_EvidenceItem, ...]) -> bool:
        if _is_log_path(items):
            completed = _log(items, "execution_completed").data
            effect = _log(items, "effect_recorded").data
            return (
                _nested_value(completed, "result") == "success"
                and _nested_value(effect, "state") == "active"
                and self._before(
                    _log(items, "compensation_started").data["timestamp"],
                    effect["timestamp"],
                )
            )
        execution = _source(items, "execution_observations").data
        effect = _source(items, "effect_records").data
        compensation = _source(items, "compensation_records").data
        return (
            execution.get("result") == "success"
            and effect.get("state") == "active"
            and self._before(compensation["started_at"], effect["created_at"])
        )

    def _legitimate_compensation(
        self,
        items: tuple[_EvidenceItem, ...],
        index: dict[str, _EvidenceItem],
    ) -> bool:
        operation_id = _one_operation_id(items)
        has_effect = any(
            item.source == "effect_records"
            and _operation_id(item) == operation_id
            for item in index.values()
        ) or any(
            item.source == "logs"
            and _operation_id(item) == operation_id
            and _event_kind(item) == "effect_recorded"
            for item in index.values()
        )
        if has_effect:
            return False
        if _is_log_path(items):
            completed = _log(items, "execution_completed").data
            compensation_start = _log(items, "compensation_started").data
            compensation_end = _log(items, "compensation_completed").data
            return (
                _nested_value(completed, "result") == "cancelled"
                and _nested_value(compensation_end, "result") == "completed"
                and self._before(completed["timestamp"], compensation_start["timestamp"])
                and self._before(compensation_start["timestamp"], compensation_end["timestamp"])
            )
        workflow = _source(items, "workflow_attempts").data
        execution = _source(items, "execution_observations").data
        compensation = _source(items, "compensation_records").data
        return (
            workflow.get("workflow_state") == "compensated"
            and workflow.get("compensation_state") == "completed"
            and execution.get("result") == "cancelled"
            and compensation.get("result") == "completed"
            and self._before(execution["completed_at"], compensation["started_at"])
            and self._before(compensation["started_at"], compensation["completed_at"])
        )

    def _healthy_control(self, items: tuple[_EvidenceItem, ...]) -> bool:
        workflow = _source(items, "workflow_attempts").data
        execution = _source(items, "execution_observations").data
        dependency = next(
            (item.data for item in items if item.source == "dependency_health"), None
        )
        return (
            workflow.get("workflow_state") == "completed"
            and workflow.get("compensation_state") == "not_started"
            and execution.get("result") == "success"
            and self._before(execution["completed_at"], workflow["deadline_at"])
            and (
                dependency is None
                or (
                    dependency.get("availability_state") == "available"
                    and dependency.get("warning") == "latency_elevated"
                )
            )
        )

    def _target_lifecycle(self, items: tuple[_EvidenceItem, ...]) -> bool:
        start = _log(items, "execution_started").data["timestamp"]
        deadline = _log(items, "deadline_reached").data["timestamp"]
        compensation_start = _log(items, "compensation_started").data["timestamp"]
        execution_end = _log(items, "execution_completed").data["timestamp"]
        effect = _log(items, "effect_recorded").data["timestamp"]
        compensation_end = _log(items, "compensation_completed").data["timestamp"]
        workflow = _log(items, "workflow_state_recorded").data["timestamp"]
        return all(
            (
                self._before(start, execution_end),
                self._before(deadline, compensation_start),
                self._before(compensation_start, execution_end),
                self._before(compensation_start, effect),
                self._before(compensation_start, compensation_end),
                self._before(execution_end, workflow),
                self._before(compensation_end, workflow),
            )
        )


def _evidence_index(model_view: ModelView) -> dict[str, _EvidenceItem]:
    result: dict[str, _EvidenceItem] = {}
    for source, rows in model_view.structured_evidence.items():
        for row in rows:
            evidence_id = _string(row["evidence_id"])
            result[evidence_id] = _EvidenceItem(source, row)
    for entry in model_view.log_evidence:
        result[entry.evidence_id] = _EvidenceItem("logs", entry.to_dict())
    return result


def _has_genuine_subject_linkage(
    path: EvidencePathV3,
    items: tuple[_EvidenceItem, ...],
    index: dict[str, _EvidenceItem],
    rubric: EvidenceRubricV3,
) -> bool:
    try:
        candidate = _one_operation_id(items)
    except ValueError:
        return False
    for binding in rubric.subject_bindings:
        if binding.binding_id == path.subject_binding_id:
            continue
        other_values = {
            _operation_id(index[evidence_id])
            for evidence_id in binding.evidence_ids
            if evidence_id in index
        }
        if candidate in other_values:
            return False
    return True


def _one_operation_id(items: tuple[_EvidenceItem, ...]) -> str:
    values = {_operation_id(item) for item in items}
    if len(values) != 1:
        raise ValueError("Path does not expose one genuine operation identity")
    return next(iter(values))


def _inconsistent_terminal_state(items: tuple[_EvidenceItem, ...]) -> bool:
    if _is_log_path(items):
        return (
            _nested_value(_log(items, "execution_completed").data, "result")
            == "success"
            and _nested_value(_log(items, "effect_recorded").data, "state")
            == "active"
            and _nested_value(
                _log(items, "compensation_completed").data, "result"
            )
            == "completed"
            and _nested_value(
                _log(items, "workflow_state_recorded").data, "workflow_state"
            )
            == "compensated"
        )
    return (
        _source(items, "workflow_attempts").data.get("workflow_state")
        == "compensated"
        and _source(items, "workflow_attempts").data.get("compensation_state")
        == "completed"
        and _source(items, "execution_observations").data.get("result") == "success"
        and _source(items, "effect_records").data.get("state") == "active"
        and _source(items, "compensation_records").data.get("result") == "completed"
    )


def _shared_nonempty_value(items: tuple[_EvidenceItem, ...], field: str) -> bool:
    values = {_string(item.data[field]) for item in items if field in item.data}
    return len(values) == 1 and bool(next(iter(values)))


def _source(items: tuple[_EvidenceItem, ...], source: str) -> _EvidenceItem:
    matches = tuple(item for item in items if item.source == source)
    if len(matches) != 1:
        raise ValueError(f"Expected one {source} evidence item")
    return matches[0]


def _log(items: tuple[_EvidenceItem, ...], event_kind: str) -> _EvidenceItem:
    matches = tuple(item for item in items if _event_kind(item) == event_kind)
    if len(matches) != 1:
        raise ValueError(f"Expected one {event_kind} log item")
    return matches[0]


def _event_kind(item: _EvidenceItem) -> object:
    attributes = item.data.get("attributes")
    return attributes.get("event_kind") if isinstance(attributes, dict) else None


def _operation_id(item: _EvidenceItem) -> str:
    return _string(_nested_value(item.data, "operation_id"))


def _nested_value(data: dict[str, JSONValue], field: str) -> object:
    if field in data:
        return data[field]
    attributes = data.get("attributes")
    if isinstance(attributes, dict) and field in attributes:
        return attributes[field]
    raise ValueError(f"Evidence item does not expose {field}")


def _is_log_path(items: tuple[_EvidenceItem, ...]) -> bool:
    return bool(items) and all(item.source == "logs" for item in items)


def _string(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("Expected a non-empty model-visible string")
    return value
