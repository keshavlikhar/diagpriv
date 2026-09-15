"""Generate Incident 003: inconsistent state after overlapping compensation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
from pathlib import Path
import random

from diagbench.schema import (
    ComponentMapping,
    DiagnosticInvariant,
    EvidenceReference,
    ExpectedEvidence,
    Incident,
    LogEntry,
    SensitiveField,
    StructuredRootCause,
    StructuredRootCauseV2,
)
from diagbench.schema.models import JSONValue
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION

FAMILY_ID = "incident_003_temporal_compensation"
GENERATOR_VERSION = "incident-003-generator-v1"
PROTOCOL_VERSION = "incident-003-temporal-protocol-v1"
DEFAULT_SEED = 1001
DEVELOPMENT_SEEDS = range(1000, 2000)
DEFAULT_OUTPUT = (
    Path(__file__).parents[1]
    / "incidents"
    / "incident_003_temporal_compensation"
    / "incident.json"
)


@dataclass(frozen=True, slots=True)
class TemporalTemplate:
    deadline_seconds: tuple[int, int]
    compensation_delay_seconds: tuple[int, int]
    completion_after_compensation_seconds: tuple[int, int]
    compensation_duration_seconds: tuple[int, int]


TEMPORAL_TEMPLATES = {
    "short_overlap": TemporalTemplate((12, 17), (1, 3), (4, 8), (2, 6)),
    "tight_overlap": TemporalTemplate((18, 25), (1, 4), (6, 11), (3, 9)),
    "wide_overlap": TemporalTemplate((35, 48), (3, 7), (13, 22), (10, 27)),
    "delayed_compensation": TemporalTemplate((25, 34), (7, 12), (4, 9), (5, 14)),
}

_ORCHESTRATOR_ALIASES = (
    "flow-coordinator",
    "workflow-controller",
    "process-supervisor",
    "journey-manager",
)
_EXECUTOR_ALIASES = (
    "action-runner",
    "operation-worker",
    "effect-processor",
    "task-executor",
)
_DEPENDENCY_ALIASES = (
    "remote-ledger",
    "state-service",
    "partner-endpoint",
    "execution-backend",
)

_MESSAGES = {
    "dispatch_recorded": ("Workflow dispatch recorded", "Operation dispatch recorded"),
    "execution_started": ("Execution lifecycle update", "Worker lifecycle update"),
    "dependency_observed": ("Dependency sample recorded", "Backend sample recorded"),
    "execution_progress": ("Execution progress sample", "Worker progress sample"),
    "deadline_reached": ("Workflow deadline reached", "Deadline checkpoint reached"),
    "compensation_started": (
        "Compensation lifecycle update",
        "Rollback lifecycle update",
    ),
    "compensation_completed": (
        "Compensation result recorded",
        "Rollback result recorded",
    ),
    "execution_completed": ("Execution result recorded", "Worker result recorded"),
    "effect_recorded": ("Effect record stored", "Operation effect stored"),
    "workflow_state_recorded": (
        "Workflow state recorded",
        "Process state recorded",
    ),
    "workflow_checkpoint": (
        "Workflow observation recorded",
        "Process observation recorded",
    ),
}


def _rng_for(seed: int) -> tuple[random.Random, str]:
    if seed not in DEVELOPMENT_SEEDS:
        raise ValueError(
            "Incident 003 construction is development-only; seed must be in 1000-1999"
        )
    domain = f"{FAMILY_ID}\0{GENERATOR_VERSION}\0{seed}".encode("ascii")
    digest = hashlib.sha256(domain).digest()
    return random.Random(int.from_bytes(digest, "big")), digest.hex()


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _draw(rng: random.Random, bounds: tuple[int, int]) -> int:
    return rng.randint(bounds[0], bounds[1])


def _neutral_id(rng: random.Random, prefix: str, used: set[str]) -> str:
    while True:
        candidate = f"{prefix}-{rng.randrange(10_000_000, 99_999_999)}"
        if candidate not in used:
            used.add(candidate)
            return candidate


def _reference(
    source: str,
    evidence_id: str | None = None,
    field: str | None = None,
    **selector: str,
) -> EvidenceReference:
    if evidence_id is not None:
        selector["evidence_id"] = evidence_id
    return EvidenceReference(source, selector, field)


def generate_incident_003(seed: int = DEFAULT_SEED) -> Incident:
    """Create one deterministic development instance of Incident Family 003."""
    rng, generation_domain = _rng_for(seed)
    used_ids: set[str] = set()
    template_name, template = rng.choice(tuple(TEMPORAL_TEMPLATES.items()))
    orchestrator_alias = rng.choice(_ORCHESTRATOR_ALIASES)
    executor_alias = rng.choice(_EXECUTOR_ALIASES)
    dependency_alias = rng.choice(_DEPENDENCY_ALIASES)
    healthy_control_count = rng.randint(4, 7)
    slow_control_index = rng.randrange(healthy_control_count)
    target_warning = rng.choice((False, True))

    base = datetime(2036, 1, 1, tzinfo=UTC) + timedelta(
        days=rng.randrange(730),
        hours=rng.randrange(5, 21),
        minutes=rng.randrange(60),
        seconds=rng.randrange(60),
    )

    healthy_roles = [f"healthy-{index}" for index in range(healthy_control_count)]
    target_insert = rng.randint(1, healthy_control_count - 1)
    chronological_roles = healthy_roles.copy()
    chronological_roles.insert(target_insert, "target")
    legitimate_insert = rng.randrange(len(chronological_roles) + 1)
    chronological_roles.insert(legitimate_insert, "legitimate-compensation")

    workflow_attempts: list[dict[str, JSONValue]] = []
    execution_observations: list[dict[str, JSONValue]] = []
    effect_records: list[dict[str, JSONValue]] = []
    compensation_records: list[dict[str, JSONValue]] = []
    dependency_health: list[dict[str, JSONValue]] = []
    logs: list[LogEntry] = []
    operation_data: dict[str, dict[str, object]] = {}

    for chronological_index, role in enumerate(chronological_roles):
        operation_id = _neutral_id(rng, "OP", used_ids)
        operation_base = base + timedelta(
            seconds=chronological_index * 180,
            milliseconds=rng.randrange(20, 850),
        )
        dispatch = operation_base
        execution_start = dispatch + timedelta(seconds=rng.uniform(0.8, 2.8))
        deadline_seconds = _draw(rng, template.deadline_seconds)
        deadline = dispatch + timedelta(seconds=deadline_seconds)
        is_target = role == "target"
        is_legitimate = role == "legitimate-compensation"
        healthy_index = (
            int(role.split("-", maxsplit=1)[1]) if role.startswith("healthy-") else None
        )
        is_slow = healthy_index == slow_control_index

        if is_target:
            compensation_start = deadline + timedelta(
                seconds=_draw(rng, template.compensation_delay_seconds)
            )
            execution_complete = compensation_start + timedelta(
                seconds=_draw(rng, template.completion_after_compensation_seconds)
            )
            compensation_complete = compensation_start + timedelta(
                seconds=_draw(rng, template.compensation_duration_seconds)
            )
            execution_result = "success"
            workflow_state = "compensated"
            compensation_state = "completed"
        elif is_legitimate:
            execution_complete = deadline + timedelta(seconds=rng.randint(1, 3))
            compensation_start = execution_complete + timedelta(seconds=rng.randint(1, 3))
            compensation_complete = compensation_start + timedelta(seconds=rng.randint(3, 8))
            execution_result = "cancelled"
            workflow_state = "compensated"
            compensation_state = "completed"
        else:
            compensation_start = None
            compensation_complete = None
            if is_slow:
                execution_complete = deadline - timedelta(
                    seconds=rng.uniform(1.2, 4.2)
                )
            else:
                duration = rng.uniform(4.0, min(13.0, deadline_seconds - 4.0))
                execution_complete = execution_start + timedelta(seconds=duration)
            execution_result = "success"
            workflow_state = "completed"
            compensation_state = "not_started"

        workflow_evidence_id = _neutral_id(rng, "EV", used_ids)
        execution_evidence_id = _neutral_id(rng, "EV", used_ids)
        workflow_attempts.append(
            {
                "evidence_id": workflow_evidence_id,
                "operation_id": operation_id,
                "dispatched_at": _timestamp(dispatch),
                "deadline_at": _timestamp(deadline),
                "compensation_state": compensation_state,
                "workflow_state": workflow_state,
                "orchestrator_alias": orchestrator_alias,
            }
        )
        execution_observations.append(
            {
                "evidence_id": execution_evidence_id,
                "operation_id": operation_id,
                "started_at": _timestamp(execution_start),
                "completed_at": _timestamp(execution_complete),
                "result": execution_result,
                "executor_alias": executor_alias,
            }
        )

        effect_evidence_id: str | None = None
        effect_id: str | None = None
        effect_created: datetime | None = None
        if not is_legitimate:
            effect_evidence_id = _neutral_id(rng, "EV", used_ids)
            effect_id = _neutral_id(rng, "EF", used_ids)
            effect_created = execution_complete + timedelta(milliseconds=rng.randrange(80, 280))
            effect_records.append(
                {
                    "evidence_id": effect_evidence_id,
                    "operation_id": operation_id,
                    "effect_id": effect_id,
                    "created_at": _timestamp(effect_created),
                    "state": "active",
                    "executor_alias": executor_alias,
                }
            )

        compensation_evidence_id: str | None = None
        compensation_id: str | None = None
        if is_target or is_legitimate:
            assert compensation_start is not None
            assert compensation_complete is not None
            compensation_evidence_id = _neutral_id(rng, "EV", used_ids)
            compensation_id = _neutral_id(rng, "CP", used_ids)
            compensation_records.append(
                {
                    "evidence_id": compensation_evidence_id,
                    "operation_id": operation_id,
                    "compensation_id": compensation_id,
                    "started_at": _timestamp(compensation_start),
                    "completed_at": _timestamp(compensation_complete),
                    "result": "completed",
                    "orchestrator_alias": orchestrator_alias,
                }
            )

        dependency_count = 1 if is_target else 2
        dependency_ids: list[str] = []
        dependency_times: list[datetime] = []
        warnings: list[str] = []
        for sample_index in range(dependency_count):
            sample_fraction = (sample_index + 1) / (dependency_count + 1)
            observed_at = execution_start + (
                execution_complete - execution_start
            ) * sample_fraction
            warning = (
                "latency_elevated"
                if (is_slow and sample_index == 0) or (is_target and target_warning)
                else "none"
            )
            dependency_evidence_id = _neutral_id(rng, "EV", used_ids)
            dependency_ids.append(dependency_evidence_id)
            dependency_times.append(observed_at)
            warnings.append(warning)
            dependency_health.append(
                {
                    "evidence_id": dependency_evidence_id,
                    "operation_id": operation_id,
                    "dependency_alias": dependency_alias,
                    "observed_at": _timestamp(observed_at),
                    "availability_state": "available",
                    "latency_ms": (
                        rng.randint(720, 1450) if warning != "none" else rng.randint(35, 180)
                    ),
                    "warning": warning,
                }
            )

        def add_log(
            when: datetime,
            service: str,
            event_kind: str,
            attributes: dict[str, JSONValue] | None = None,
            *,
            level: str = "INFO",
        ) -> str:
            evidence_id = _neutral_id(rng, "EV", used_ids)
            event_attributes: dict[str, JSONValue] = {
                "operation_id": operation_id,
                "event_kind": event_kind,
            }
            if attributes:
                event_attributes.update(attributes)
            logs.append(
                LogEntry(
                    evidence_id=evidence_id,
                    timestamp=_timestamp(when),
                    level=level,
                    service=service,
                    message=rng.choice(_MESSAGES[event_kind]),
                    attributes=event_attributes,
                )
            )
            return evidence_id

        log_ids: dict[str, str] = {}
        log_ids["dispatch_recorded"] = add_log(
            dispatch, orchestrator_alias, "dispatch_recorded"
        )
        log_ids["execution_started"] = add_log(
            execution_start, executor_alias, "execution_started"
        )

        for index, (dependency_time, warning) in enumerate(
            zip(dependency_times, warnings, strict=True)
        ):
            log_ids[f"dependency_observed_{index}"] = add_log(
                dependency_time,
                dependency_alias,
                "dependency_observed",
                {"warning": warning},
                level="WARN" if warning != "none" else "INFO",
            )

        if is_target:
            assert compensation_start is not None
            assert compensation_complete is not None
            assert compensation_id is not None
            assert effect_id is not None
            assert effect_created is not None
            log_ids["deadline_reached"] = add_log(
                deadline, orchestrator_alias, "deadline_reached"
            )
            log_ids["compensation_started"] = add_log(
                compensation_start,
                orchestrator_alias,
                "compensation_started",
                {"compensation_id": compensation_id, "phase": "started"},
            )
            log_ids["execution_completed"] = add_log(
                execution_complete,
                executor_alias,
                "execution_completed",
                {"result": "success"},
            )
            log_ids["effect_recorded"] = add_log(
                effect_created,
                executor_alias,
                "effect_recorded",
                {"effect_id": effect_id, "state": "active"},
            )
            log_ids["compensation_completed"] = add_log(
                compensation_complete,
                orchestrator_alias,
                "compensation_completed",
                {"compensation_id": compensation_id, "result": "completed"},
            )
            final_time = max(effect_created, compensation_complete) + timedelta(seconds=1)
            log_ids["workflow_state_recorded"] = add_log(
                final_time,
                orchestrator_alias,
                "workflow_state_recorded",
                {"workflow_state": "compensated"},
            )
        elif is_legitimate:
            assert compensation_start is not None
            assert compensation_complete is not None
            assert compensation_id is not None
            log_ids["deadline_reached"] = add_log(
                deadline, orchestrator_alias, "deadline_reached"
            )
            log_ids["execution_completed"] = add_log(
                execution_complete,
                executor_alias,
                "execution_completed",
                {"result": "cancelled"},
            )
            log_ids["compensation_started"] = add_log(
                compensation_start,
                orchestrator_alias,
                "compensation_started",
                {"compensation_id": compensation_id, "phase": "started"},
            )
            log_ids["compensation_completed"] = add_log(
                compensation_complete,
                orchestrator_alias,
                "compensation_completed",
                {"compensation_id": compensation_id, "result": "completed"},
            )
            log_ids["workflow_state_recorded"] = add_log(
                compensation_complete + timedelta(seconds=1),
                orchestrator_alias,
                "workflow_state_recorded",
                {"workflow_state": "compensated"},
            )
        else:
            assert effect_id is not None
            assert effect_created is not None
            progress_time = execution_start + (execution_complete - execution_start) / 2
            log_ids["execution_progress"] = add_log(
                progress_time, executor_alias, "execution_progress"
            )
            log_ids["execution_completed"] = add_log(
                execution_complete,
                executor_alias,
                "execution_completed",
                {"result": "success"},
            )
            log_ids["effect_recorded"] = add_log(
                effect_created,
                executor_alias,
                "effect_recorded",
                {"effect_id": effect_id, "state": "active"},
            )
            log_ids["workflow_state_recorded"] = add_log(
                effect_created + timedelta(milliseconds=300),
                orchestrator_alias,
                "workflow_state_recorded",
                {"workflow_state": "completed"},
            )
            log_ids["workflow_checkpoint"] = add_log(
                deadline + timedelta(milliseconds=500),
                orchestrator_alias,
                "workflow_checkpoint",
                {"workflow_state": "completed"},
            )

        if len(log_ids) != 9:
            raise AssertionError(f"Expected nine neutral logs for {role}; got {len(log_ids)}")

        operation_data[operation_id] = {
            "role": role,
            "chronological_index": chronological_index,
            "workflow_evidence_id": workflow_evidence_id,
            "execution_evidence_id": execution_evidence_id,
            "effect_evidence_id": effect_evidence_id,
            "compensation_evidence_id": compensation_evidence_id,
            "dependency_evidence_ids": tuple(dependency_ids),
            "log_ids": log_ids,
            "dispatch": dispatch,
            "execution_start": execution_start,
            "execution_complete": execution_complete,
            "deadline": deadline,
            "compensation_start": compensation_start,
            "compensation_complete": compensation_complete,
            "effect_created": effect_created,
            "is_slow": is_slow,
            "warnings": tuple(warnings),
        }

    target_operation_id = next(
        operation_id
        for operation_id, data in operation_data.items()
        if data["role"] == "target"
    )
    legitimate_compensation_operation_id = next(
        operation_id
        for operation_id, data in operation_data.items()
        if data["role"] == "legitimate-compensation"
    )
    healthy_control_ids = tuple(
        operation_id
        for operation_id, data in operation_data.items()
        if str(data["role"]).startswith("healthy-")
    )
    slow_control_id = next(
        operation_id
        for operation_id in healthy_control_ids
        if operation_data[operation_id]["is_slow"]
    )

    rng.shuffle(workflow_attempts)
    rng.shuffle(execution_observations)
    rng.shuffle(effect_records)
    rng.shuffle(compensation_records)
    rng.shuffle(dependency_health)
    logs.sort(key=lambda entry: (entry.timestamp, entry.evidence_id))
    structured_evidence = {
        "workflow_attempts": workflow_attempts,
        "execution_observations": execution_observations,
        "effect_records": effect_records,
        "compensation_records": compensation_records,
        "dependency_health": dependency_health,
    }

    def operation_ref(
        operation_id: str,
        source: str,
        field: str,
        *,
        dependency_index: int = 0,
    ) -> EvidenceReference:
        data = operation_data[operation_id]
        key_by_source = {
            "workflow_attempts": "workflow_evidence_id",
            "execution_observations": "execution_evidence_id",
            "effect_records": "effect_evidence_id",
            "compensation_records": "compensation_evidence_id",
        }
        if source == "dependency_health":
            evidence_ids = data["dependency_evidence_ids"]
            assert isinstance(evidence_ids, tuple)
            return _reference(source, str(evidence_ids[dependency_index]), field)
        if source == "logs":
            log_ids = data["log_ids"]
            assert isinstance(log_ids, dict)
            return _reference(source, str(log_ids[field]), field=None)
        evidence_id = data[key_by_source[source]]
        if evidence_id is None:
            raise ValueError(f"Operation {operation_id} has no {source} row")
        return _reference(source, str(evidence_id), field)

    target_workflow = lambda field: operation_ref(  # noqa: E731
        target_operation_id, "workflow_attempts", field
    )
    target_execution = lambda field: operation_ref(  # noqa: E731
        target_operation_id, "execution_observations", field
    )
    target_compensation = lambda field: operation_ref(  # noqa: E731
        target_operation_id, "compensation_records", field
    )
    target_effect = lambda field: operation_ref(  # noqa: E731
        target_operation_id, "effect_records", field
    )

    control_completion_deadline_operands = tuple(
        reference
        for operation_id in healthy_control_ids
        for reference in (
            operation_ref(operation_id, "execution_observations", "completed_at"),
            operation_ref(operation_id, "workflow_attempts", "deadline_at"),
        )
    )
    all_operation_ids = (
        target_operation_id,
        *healthy_control_ids,
        legitimate_compensation_operation_id,
    )
    ordered_healthy = sorted(
        healthy_control_ids,
        key=lambda operation_id: int(operation_data[operation_id]["chronological_index"]),
    )
    before_control_id = max(
        (
            operation_id
            for operation_id in ordered_healthy
            if int(operation_data[operation_id]["chronological_index"])
            < int(operation_data[target_operation_id]["chronological_index"])
        ),
        key=lambda operation_id: int(operation_data[operation_id]["chronological_index"]),
    )
    after_control_id = min(
        (
            operation_id
            for operation_id in ordered_healthy
            if int(operation_data[operation_id]["chronological_index"])
            > int(operation_data[target_operation_id]["chronological_index"])
        ),
        key=lambda operation_id: int(operation_data[operation_id]["chronological_index"]),
    )

    target_deadline_seconds = int(
        (
            operation_data[target_operation_id]["deadline"]
            - operation_data[target_operation_id]["dispatch"]
        ).total_seconds()  # type: ignore[union-attr]
    )

    invariants = (
        DiagnosticInvariant(
            "target_deadline_precedes_original_completion",
            "ordered_before",
            (target_workflow("deadline_at"), target_execution("completed_at")),
            True,
            "essential",
            "The orchestrator deadline occurs before original execution completion.",
        ),
        DiagnosticInvariant(
            "target_compensation_after_deadline",
            "ordered_before",
            (target_workflow("deadline_at"), target_compensation("started_at")),
            True,
            "essential",
            "Target compensation begins after the workflow deadline.",
        ),
        DiagnosticInvariant(
            "target_compensation_precedes_original_completion",
            "ordered_before",
            (target_compensation("started_at"), target_execution("completed_at")),
            True,
            "essential",
            "Compensation begins before original execution completes.",
        ),
        DiagnosticInvariant(
            "target_execution_compensation_overlap",
            "intervals_overlap",
            (
                target_execution("started_at"),
                target_execution("completed_at"),
                target_compensation("started_at"),
                target_compensation("completed_at"),
            ),
            True,
            "essential",
            "Original execution and compensation overlap for a positive duration.",
        ),
        DiagnosticInvariant(
            "target_success_after_compensation_start",
            "ordered_before",
            (target_compensation("started_at"), target_effect("created_at")),
            True,
            "essential",
            "The successful target effect is recorded after compensation starts.",
        ),
        DiagnosticInvariant(
            "control_completion_precedes_deadline",
            "paired_before",
            control_completion_deadline_operands,
            True,
            "essential",
            "Every successful control completes before its own deadline.",
        ),
        DiagnosticInvariant(
            "control_no_compensation",
            "equal",
            tuple(
                operation_ref(operation_id, "workflow_attempts", "compensation_state")
                for operation_id in healthy_control_ids
            ),
            "not_started",
            "essential",
            "Successful controls require no compensation.",
        ),
        DiagnosticInvariant(
            "target_event_order",
            "ordered_before",
            (
                target_workflow("dispatched_at"),
                target_execution("started_at"),
                target_workflow("deadline_at"),
                target_compensation("started_at"),
                target_execution("completed_at"),
            ),
            True,
            "essential",
            "The target follows dispatch, start, deadline, compensation, completion order.",
        ),
        DiagnosticInvariant(
            "target_inconsistent_state",
            "sequence_equals",
            (
                target_workflow("workflow_state"),
                target_execution("result"),
                target_compensation("result"),
                target_effect("state"),
            ),
            ["compensated", "success", "completed", "active"],
            "essential",
            "Completed compensation coexists with a successful active original effect.",
        ),
        DiagnosticInvariant(
            "target_effect_presence",
            "equal",
            (target_effect("state"),),
            "active",
            "essential",
            "The target original execution created an active effect.",
        ),
        DiagnosticInvariant(
            "target_execution_success_state",
            "equal",
            (target_execution("result"),),
            "success",
            "essential",
            "The original target execution ultimately succeeded.",
        ),
        DiagnosticInvariant(
            "target_and_control_operation_distinctness",
            "all_distinct",
            tuple(
                operation_ref(operation_id, "workflow_attempts", "operation_id")
                for operation_id in all_operation_ids
            ),
            True,
            "essential",
            "Target, successful controls, and compensated control remain distinct.",
        ),
        DiagnosticInvariant(
            "target_operation_cross_source_identity",
            "equal",
            (
                target_workflow("operation_id"),
                target_execution("operation_id"),
                target_effect("operation_id"),
                target_compensation("operation_id"),
                operation_ref(target_operation_id, "dependency_health", "operation_id"),
            ),
            True,
            "essential",
            "Target workflow, execution, effect, compensation, and health rows link.",
        ),
        DiagnosticInvariant(
            "control_execution_success_state",
            "equal",
            tuple(
                operation_ref(operation_id, "execution_observations", "result")
                for operation_id in healthy_control_ids
            ),
            "success",
            "essential",
            "Every healthy control execution succeeds.",
        ),
        DiagnosticInvariant(
            "shared_orchestrator_role",
            "equal",
            tuple(
                operation_ref(operation_id, "workflow_attempts", "orchestrator_alias")
                for operation_id in all_operation_ids
            )
            + tuple(
                operation_ref(operation_id, "compensation_records", "orchestrator_alias")
                for operation_id in (
                    target_operation_id,
                    legitimate_compensation_operation_id,
                )
            ),
            orchestrator_alias,
            "supportive",
            "One visible orchestrator role owns deadlines, compensation, and state.",
        ),
        DiagnosticInvariant(
            "shared_executor_role",
            "equal",
            tuple(
                operation_ref(operation_id, "execution_observations", "executor_alias")
                for operation_id in all_operation_ids
            ),
            executor_alias,
            "supportive",
            "The executor role performs original operations without owning deadlines.",
        ),
        DiagnosticInvariant(
            "dependency_remained_available",
            "equal",
            tuple(
                _reference("dependency_health", str(row["evidence_id"]), "availability_state")
                for row in dependency_health
            ),
            "available",
            "supportive",
            "All dependency samples remain available despite bounded warnings.",
        ),
        DiagnosticInvariant(
            "successful_controls_bracket_target_chronologically",
            "ordered_before",
            (
                operation_ref(before_control_id, "workflow_attempts", "dispatched_at"),
                target_workflow("dispatched_at"),
                operation_ref(after_control_id, "workflow_attempts", "dispatched_at"),
            ),
            True,
            "supportive",
            "Successful controls occur before and after the target dispatch.",
        ),
        DiagnosticInvariant(
            "benign_slow_control_succeeds_before_deadline",
            "ordered_before",
            (
                operation_ref(slow_control_id, "execution_observations", "completed_at"),
                operation_ref(slow_control_id, "workflow_attempts", "deadline_at"),
            ),
            True,
            "supportive",
            "The warned slow control still succeeds before its deadline.",
        ),
        DiagnosticInvariant(
            "benign_slow_control_warning",
            "equal",
            (operation_ref(slow_control_id, "dependency_health", "warning"),),
            "latency_elevated",
            "supportive",
            "A non-target successful control carries a latency warning.",
        ),
        DiagnosticInvariant(
            "target_compensation_record_presence",
            "equal",
            (target_compensation("result"),),
            "completed",
            "supportive",
            "A completed target compensation record exists.",
        ),
        DiagnosticInvariant(
            "legitimate_compensation_event_order",
            "ordered_before",
            (
                operation_ref(
                    legitimate_compensation_operation_id,
                    "workflow_attempts",
                    "dispatched_at",
                ),
                operation_ref(
                    legitimate_compensation_operation_id,
                    "execution_observations",
                    "started_at",
                ),
                operation_ref(
                    legitimate_compensation_operation_id,
                    "workflow_attempts",
                    "deadline_at",
                ),
                operation_ref(
                    legitimate_compensation_operation_id,
                    "execution_observations",
                    "completed_at",
                ),
                operation_ref(
                    legitimate_compensation_operation_id,
                    "compensation_records",
                    "started_at",
                ),
                operation_ref(
                    legitimate_compensation_operation_id,
                    "compensation_records",
                    "completed_at",
                ),
            ),
            True,
            "supportive",
            "The compensated control confirms cancellation before compensation.",
        ),
        DiagnosticInvariant(
            "legitimate_compensation_terminal_state",
            "sequence_equals",
            (
                operation_ref(
                    legitimate_compensation_operation_id,
                    "execution_observations",
                    "result",
                ),
                operation_ref(
                    legitimate_compensation_operation_id,
                    "compensation_records",
                    "result",
                ),
                operation_ref(
                    legitimate_compensation_operation_id,
                    "workflow_attempts",
                    "workflow_state",
                ),
            ),
            ["cancelled", "completed", "compensated"],
            "supportive",
            "A cancelled execution is cleanly compensated without original success.",
        ),
        DiagnosticInvariant(
            "legitimate_compensation_effect_absence",
            "match_count",
            (
                _reference(
                    "effect_records",
                    operation_id=legitimate_compensation_operation_id,
                ),
            ),
            0,
            "supportive",
            "No original effect exists for the legitimately compensated control.",
        ),
        DiagnosticInvariant(
            "target_workflow_state_cardinality",
            "match_count",
            (_reference("workflow_attempts", operation_id=target_operation_id),),
            1,
            "supportive",
            "Exactly one final workflow row identifies the target state.",
        ),
        DiagnosticInvariant(
            "literal_target_dispatch_timestamp",
            "preserve_literal",
            (target_workflow("dispatched_at"),),
            False,
            "discardable",
            "The original target calendar timestamp is unnecessary for RCA.",
        ),
        DiagnosticInvariant(
            "literal_target_deadline_timestamp",
            "preserve_literal",
            (target_workflow("deadline_at"),),
            False,
            "discardable",
            "The original target wall-clock deadline value is unnecessary for RCA.",
        ),
        DiagnosticInvariant(
            "exact_target_deadline_interval",
            "interval_seconds",
            (target_workflow("dispatched_at"), target_workflow("deadline_at")),
            target_deadline_seconds,
            "discardable",
            "The exact deadline duration is not required beyond its causal ordering.",
        ),
    )

    expected_evidence = (
        ExpectedEvidence(
            "Target deadline, execution completion, and compensation timing establish overlap.",
            (
                _reference(
                    "workflow_attempts",
                    str(operation_data[target_operation_id]["workflow_evidence_id"]),
                ),
                _reference(
                    "execution_observations",
                    str(operation_data[target_operation_id]["execution_evidence_id"]),
                ),
                _reference(
                    "compensation_records",
                    str(operation_data[target_operation_id]["compensation_evidence_id"]),
                ),
            ),
        ),
        ExpectedEvidence(
            "Target success and active effect coexist with compensated workflow state.",
            (
                _reference(
                    "effect_records",
                    str(operation_data[target_operation_id]["effect_evidence_id"]),
                ),
            ),
        ),
        ExpectedEvidence(
            "Healthy and legitimately compensated controls distinguish deadline behavior.",
            (
                _reference(
                    "workflow_attempts",
                    str(operation_data[slow_control_id]["workflow_evidence_id"]),
                ),
                _reference(
                    "execution_observations",
                    str(operation_data[slow_control_id]["execution_evidence_id"]),
                ),
                _reference(
                    "compensation_records",
                    str(
                        operation_data[legitimate_compensation_operation_id][
                            "compensation_evidence_id"
                        ]
                    ),
                ),
            ),
        ),
    )

    return Incident(
        incident_id=FAMILY_ID,
        title="Incident 003 — Inconsistent State from Premature Compensation",
        category="workflow_state_inconsistency",
        description=(
            "A workflow deadline initiates compensation while original execution remains "
            "in progress; the original success and compensation leave contradictory state."
        ),
        troubleshooting_question=(
            "One workflow finished with a state that does not agree with its recorded "
            "downstream effect. Review the surrounding evidence and identify the most "
            "likely root cause."
        ),
        ground_truth=StructuredRootCause(
            outcome="inconsistent_workflow_effect_state",
            trigger="workflow_deadline",
            failure_mechanism="compensation_overlapped_original_success",
            affected_component="workflow_orchestrator",
            logical_operation_repeated=False,
            explanation=(
                "The orchestrator compensated at its deadline while the original execution "
                "was still in progress, then that execution succeeded and created an effect."
            ),
        ),
        ground_truth_v2=StructuredRootCauseV2(
            observed_outcome="inconsistent_state",
            trigger="timeout_or_deadline",
            subsequent_action="compensation_or_rollback",
            failure_mechanism="incorrect_state_transition",
            affected_component="workflow_orchestrator",
            logical_operation_repeated=False,
            explanation=(
                "The workflow orchestrator transitioned into compensation at the deadline "
                "before original execution completed, allowing a later success to coexist "
                "with the compensated workflow state."
            ),
        ),
        component_mappings=(
            ComponentMapping("workflow_orchestrator", (orchestrator_alias,)),
            ComponentMapping("operation_executor", (executor_alias,)),
            ComponentMapping("external_dependency", (dependency_alias,)),
        ),
        structured_evidence=structured_evidence,
        log_evidence=tuple(logs),
        sensitive_fields=(
            SensitiveField(
                "workflow_attempts.operation_id",
                "workflow_operation_identifier",
                "consistent_pseudonym",
                "Operation identity is sensitive but must remain linkable across sources.",
            ),
            SensitiveField(
                "execution_observations.operation_id",
                "workflow_operation_identifier",
                "consistent_pseudonym",
                "Operation identity is sensitive but must remain linkable across sources.",
            ),
            SensitiveField(
                "effect_records.operation_id",
                "workflow_operation_identifier",
                "consistent_pseudonym",
                "Operation identity is sensitive but must remain linkable across sources.",
            ),
            SensitiveField(
                "compensation_records.operation_id",
                "workflow_operation_identifier",
                "consistent_pseudonym",
                "Operation identity is sensitive but must remain linkable across sources.",
            ),
            SensitiveField(
                "dependency_health.operation_id",
                "workflow_operation_identifier",
                "consistent_pseudonym",
                "Operation identity is sensitive but must remain linkable across sources.",
            ),
            SensitiveField(
                "logs.operation_id",
                "workflow_operation_identifier",
                "consistent_pseudonym",
                "Log operation identity is sensitive and shares the structured namespace.",
            ),
            SensitiveField(
                "effect_records.effect_id",
                "effect_identifier",
                "consistent_pseudonym",
                "Effect identities are sensitive and remain linkable to effect logs.",
            ),
            SensitiveField(
                "logs.effect_id",
                "effect_identifier",
                "consistent_pseudonym",
                "Logged effect identities share the effect-record namespace.",
            ),
            SensitiveField(
                "compensation_records.compensation_id",
                "compensation_identifier",
                "consistent_pseudonym",
                "Compensation identities are sensitive and remain linkable to logs.",
            ),
            SensitiveField(
                "logs.compensation_id",
                "compensation_identifier",
                "consistent_pseudonym",
                "Logged compensation identities share the compensation-record namespace.",
            ),
            *tuple(
                SensitiveField(
                    path,
                    "operational_timestamp",
                    "remove_or_pseudonymize",
                    "Literal time is sensitive; RCA needs relative temporal semantics only.",
                )
                for path in (
                    "workflow_attempts.dispatched_at",
                    "workflow_attempts.deadline_at",
                    "execution_observations.started_at",
                    "execution_observations.completed_at",
                    "effect_records.created_at",
                    "compensation_records.started_at",
                    "compensation_records.completed_at",
                    "dependency_health.observed_at",
                    "logs.timestamp",
                )
            ),
        ),
        diagnostic_invariants=invariants,
        expected_evidence=expected_evidence,
        difficulty="hard",
        metadata={
            "benchmark_version": "diagbench-v0.4",
            "family_id": FAMILY_ID,
            "generator_version": GENERATOR_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "temporal_semantics_version": TEMPORAL_SEMANTICS_VERSION,
            "seed": seed,
            "seed_split": "development",
            "generation_domain_sha256": generation_domain,
            "temporal_template_name": template_name,
            "target_operation_id": target_operation_id,
            "healthy_control_operation_ids": list(healthy_control_ids),
            "legitimate_compensation_operation_id": legitimate_compensation_operation_id,
            "slow_control_operation_id": slow_control_id,
            "target_chronological_position": int(
                operation_data[target_operation_id]["chronological_index"]
            ),
            "target_dependency_warning": target_warning,
            "orchestrator_alias": orchestrator_alias,
            "executor_alias": executor_alias,
            "dependency_alias": dependency_alias,
            "target_deadline_seconds": target_deadline_seconds,
            "target_compensation_delay_seconds": int(
                (
                    operation_data[target_operation_id]["compensation_start"]
                    - operation_data[target_operation_id]["deadline"]
                ).total_seconds()  # type: ignore[union-attr]
            ),
            "target_completion_after_compensation_seconds": int(
                (
                    operation_data[target_operation_id]["execution_complete"]
                    - operation_data[target_operation_id]["compensation_start"]
                ).total_seconds()  # type: ignore[union-attr]
            ),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    incident = generate_incident_003(args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(incident.to_json(), encoding="utf-8")


if __name__ == "__main__":
    main()
