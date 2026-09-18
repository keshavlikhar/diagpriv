"""Generate Incident 003 v3 with a causally isolated temporal twin."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
import hashlib
import random
from typing import Literal

from diagbench.schema import (
    ComponentMapping,
    DiagnosticInvariant,
    EvidenceReference,
    ExpectedEvidence,
    IncidentV3,
    LogEntry,
    SensitiveField,
    StructuredRootCause,
    StructuredRootCauseV2,
    StructuredRootCauseV3,
)
from diagbench.schema.models import JSONValue

FAMILY_ID = "incident_003_temporal_compensation_v3"
GENERATOR_VERSION = "incident-003-generator-v3"
PROTOCOL_VERSION = "incident-003-temporal-protocol-v3"
EVIDENCE_SUPPORT_VERSION = "evidence-support-v4"
QueryRole = Literal["target", "temporal_twin"]
QUERY_ROLES: tuple[QueryRole, ...] = ("target", "temporal_twin")
RAW_LOG_SERIALIZATION_CONTRACT = "globally-chronological-v1"
ANCHOR_ALLOCATION_VERSION = "incident-003-v3-role-neutral-anchor-allocation-v1"
DEFAULT_SEED = 1200
DEVELOPMENT_SEEDS = range(1000, 2000)
AUDIT_SEEDS = range(1200, 1400)

NEUTRAL_QUESTION_TEMPLATE = (
    "Determine the root cause for operation {operation_id} from the available "
    "operational evidence and cite supporting evidence IDs."
)

_COORDINATOR_ALIASES = ("svc-cedar", "svc-lattice", "svc-north", "svc-sable")
_EXECUTOR_ALIASES = ("svc-ember", "svc-flint", "svc-river", "svc-violet")
_DEPENDENCY_ALIASES = ("dep-amber", "dep-cobalt", "dep-mica", "dep-umber")
_MESSAGE_FAMILIES = (
    "Lifecycle observation recorded",
    "Operational observation recorded",
    "State observation recorded",
)

_EVENT_KINDS = (
    "dispatch_recorded",
    "execution_started",
    "dependency_observed",
    "deadline_reached",
    "compensation_started",
    "execution_completed",
    "effect_recorded",
    "compensation_completed",
    "workflow_state_recorded",
)


@dataclass(frozen=True, slots=True)
class _OperationTimes:
    dispatch: datetime
    execution_start: datetime
    deadline: datetime
    compensation_start: datetime
    execution_complete: datetime
    effect_created: datetime
    compensation_complete: datetime
    workflow_recorded: datetime
    dependency_observed: datetime


def generate_incident_003_v3(
    seed: int = DEFAULT_SEED, query_role: QueryRole = "target"
) -> IncidentV3:
    """Create one deterministic construction and select a paired query role."""
    incident = _generate_incident_003_v3_construction(seed)
    return incident_003_v3_query_case(incident, query_role)


def _generate_incident_003_v3_construction(seed: int) -> IncidentV3:
    """Create the query-independent v3 evidence construction."""
    rng, generation_domain = _rng_for(seed)
    anchor_offsets, anchor_domain = _role_neutral_anchor_offsets(seed)
    used: set[str] = set()
    coordinator = rng.choice(_COORDINATOR_ALIASES)
    executor = rng.choice(_EXECUTOR_ALIASES)
    dependency = rng.choice(_DEPENDENCY_ALIASES)
    message = rng.choice(_MESSAGE_FAMILIES)
    deadline_seconds = rng.randint(18, 28)
    base = datetime(2039, 1, 1, tzinfo=UTC) + timedelta(
        days=rng.randrange(730),
        hours=rng.randrange(4, 20),
        minutes=rng.randrange(60),
        seconds=rng.randrange(60),
        milliseconds=rng.randrange(100, 900),
    )

    target_times = _target_times(
        base + anchor_offsets["target"], deadline_seconds, rng
    )
    twin_times = _twin_times(
        base + anchor_offsets["temporal_twin"], deadline_seconds, rng
    )
    safe_times = _safe_times(
        base + anchor_offsets["safe_control"], deadline_seconds, rng
    )

    structured: dict[str, list[dict[str, JSONValue]]] = {
        "workflow_attempts": [],
        "execution_observations": [],
        "effect_records": [],
        "compensation_records": [],
        "dependency_health": [],
    }
    logs: list[LogEntry] = []
    operation_data: dict[str, dict[str, object]] = {}
    for role, times in (
        ("target", target_times),
        ("temporal-twin", twin_times),
        ("safe-compensation", safe_times),
    ):
        values = (
            {
                "execution_result": "success",
                "effect_state": "active",
                "workflow_state": "compensated",
                "compensation_state": "completed",
            }
            if role != "safe-compensation"
            else {
                "execution_result": "cancelled",
                "effect_state": "inactive",
                "workflow_state": "compensated",
                "compensation_state": "completed",
            }
        )
        operation_data[role] = _add_operation(
            rng=rng,
            used=used,
            role=role,
            times=times,
            values=values,
            coordinator=coordinator,
            executor=executor,
            dependency=dependency,
            message=message,
            structured=structured,
            logs=logs,
        )

    for rows in structured.values():
        rng.shuffle(rows)
    logs.sort(key=lambda entry: (entry.timestamp, entry.evidence_id))

    target_id = str(operation_data["target"]["operation_id"])
    twin_id = str(operation_data["temporal-twin"]["operation_id"])
    safe_id = str(operation_data["safe-compensation"]["operation_id"])
    invariants = _invariants(operation_data)
    expected = _expected_evidence(operation_data)
    sensitive = _sensitive_fields()
    metadata: dict[str, JSONValue] = {
        "benchmark_version": "diagbench-v0.7",
        "family_id": FAMILY_ID,
        "generator_version": GENERATOR_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "evidence_support_version": EVIDENCE_SUPPORT_VERSION,
        "seed": seed,
        "generation_domain_sha256": generation_domain,
        "raw_log_serialization_contract": RAW_LOG_SERIALIZATION_CONTRACT,
        "anchor_allocation_version": ANCHOR_ALLOCATION_VERSION,
        "anchor_allocation_domain_sha256": anchor_domain,
        "target_operation_id": target_id,
        "temporal_twin_operation_id": twin_id,
        "safe_control_operation_id": safe_id,
        "target_mechanism": "incorrect_concurrency_control",
        "temporal_twin_mechanism": "incorrect_state_transition",
        "safe_control_mechanism": "no_failure",
        "question_template": NEUTRAL_QUESTION_TEMPLATE,
        "temporal_twin_pairing_version": "incident-003-v3-temporal-twin-v1",
        "coordinator_alias": coordinator,
        "executor_alias": executor,
        "dependency_alias": dependency,
        "message_template": message,
        "operation_roles": {
            "target": target_id,
            "temporal_twin": twin_id,
            "safe_compensation": safe_id,
        },
    }
    return IncidentV3(
        incident_id=FAMILY_ID,
        title="Incident 003 v3: temporally isolated compensation concurrency",
        category="temporal-causality",
        description=(
            "A target and temporal twin share non-temporal evidence but differ in "
            "whether original execution overlaps compensation."
        ),
        troubleshooting_question=NEUTRAL_QUESTION_TEMPLATE.format(
            operation_id=target_id
        ),
        ground_truth=StructuredRootCause(
            outcome="inconsistent_state",
            trigger="timeout_or_deadline",
            failure_mechanism="incorrect_concurrency_control",
            affected_component="workflow_orchestrator",
            logical_operation_repeated=False,
            explanation=(
                "Deadline compensation overlaps an unfenced original execution."
            ),
        ),
        ground_truth_v2=StructuredRootCauseV2(
            observed_outcome="inconsistent_state",
            trigger="timeout_or_deadline",
            subsequent_action="compensation_or_rollback",
            failure_mechanism="incorrect_concurrency_control",
            affected_component="workflow_orchestrator",
            logical_operation_repeated=False,
            explanation=(
                "Deadline compensation overlaps an unfenced original execution."
            ),
        ),
        ground_truth_v3=StructuredRootCauseV3(
            observed_outcome="inconsistent_state",
            trigger="timeout_or_deadline",
            subsequent_action="compensation_or_rollback",
            failure_mechanism="incorrect_concurrency_control",
            affected_component="workflow_orchestrator",
            logical_operation_repeated=False,
            explanation=(
                "The queried execution remains active when deadline compensation "
                "starts; both overlap and complete without effective cancellation "
                "or fencing, leaving compensated workflow state with an active effect."
            ),
        ),
        component_mappings=(
            ComponentMapping("workflow_orchestrator", (coordinator,)),
            ComponentMapping("operation_executor", (executor,)),
            ComponentMapping("external_dependency", (dependency,)),
        ),
        structured_evidence=structured,
        log_evidence=tuple(logs),
        sensitive_fields=sensitive,
        diagnostic_invariants=invariants,
        expected_evidence=expected,
        difficulty="hard",
        metadata=metadata,
    )


def incident_003_v3_query_case(
    incident: IncidentV3, query_role: QueryRole
) -> IncidentV3:
    """Return one query case without changing evidence or its serialization."""
    if incident.incident_id != FAMILY_ID:
        raise ValueError("Incident 003 v3 query cases require Incident 003 v3")
    if query_role not in QUERY_ROLES:
        raise ValueError(f"Unsupported Incident 003 v3 query role: {query_role}")
    metadata_key = (
        "target_operation_id"
        if query_role == "target"
        else "temporal_twin_operation_id"
    )
    operation_id = str(incident.metadata[metadata_key])
    mechanism = (
        "incorrect_concurrency_control"
        if query_role == "target"
        else "incorrect_state_transition"
    )
    explanation = (
        (
            "The queried execution remains active when deadline compensation "
            "starts; both overlap and complete without effective cancellation "
            "or fencing, leaving compensated workflow state with an active effect."
        )
        if query_role == "target"
        else (
            "The queried execution succeeds and records its active effect before "
            "the deadline, yet the serialized workflow later applies compensation "
            "and transitions to compensated state after the committed success."
        )
    )
    metadata = deepcopy(incident.metadata)
    metadata["query_case_version"] = "incident-003-v3-paired-query-v1"
    metadata["query_role"] = query_role
    metadata["queried_operation_id"] = operation_id
    return replace(
        incident,
        troubleshooting_question=NEUTRAL_QUESTION_TEMPLATE.format(
            operation_id=operation_id
        ),
        ground_truth=replace(
            incident.ground_truth,
            failure_mechanism=mechanism,
            explanation=explanation,
        ),
        ground_truth_v2=replace(
            incident.ground_truth_v2,
            failure_mechanism=mechanism,
            explanation=explanation,
        ),
        ground_truth_v3=replace(
            incident.ground_truth_v3,
            failure_mechanism=mechanism,
            explanation=explanation,
        ),
        metadata=metadata,
    )


def _rng_for(seed: int) -> tuple[random.Random, str]:
    if seed not in DEVELOPMENT_SEEDS:
        raise ValueError(
            "Incident 003 v3 construction is development-only; seed must be in 1000-1999"
        )
    domain = f"{FAMILY_ID}\0{GENERATOR_VERSION}\0{seed}".encode("ascii")
    digest = hashlib.sha256(domain).digest()
    return random.Random(int.from_bytes(digest, "big")), digest.hex()


def _role_neutral_anchor_offsets(
    seed: int,
) -> tuple[dict[str, timedelta], str]:
    """Assign absolute operation windows with a role-independent RNG stream."""
    domain = (
        f"{FAMILY_ID}\0{GENERATOR_VERSION}\0{ANCHOR_ALLOCATION_VERSION}\0{seed}"
    ).encode("ascii")
    digest = hashlib.sha256(domain).digest()
    rng = random.Random(int.from_bytes(digest, "big"))
    slots = [timedelta(seconds=0), timedelta(seconds=180), timedelta(seconds=360)]
    rng.shuffle(slots)
    return dict(zip(("target", "temporal_twin", "safe_control"), slots, strict=True)), digest.hex()


def _target_times(
    base: datetime, deadline_seconds: int, rng: random.Random
) -> _OperationTimes:
    dispatch = base
    start = dispatch + timedelta(seconds=2)
    deadline = dispatch + timedelta(seconds=deadline_seconds)
    compensation_start = deadline + timedelta(seconds=2)
    execution_complete = compensation_start + timedelta(seconds=rng.randint(7, 10))
    effect_created = execution_complete + timedelta(milliseconds=200)
    compensation_complete = compensation_start + timedelta(seconds=rng.randint(12, 15))
    workflow_recorded = max(effect_created, compensation_complete) + timedelta(seconds=1)
    return _OperationTimes(
        dispatch,
        start,
        deadline,
        compensation_start,
        execution_complete,
        effect_created,
        compensation_complete,
        workflow_recorded,
        start + timedelta(seconds=5),
    )


def _twin_times(
    base: datetime, deadline_seconds: int, rng: random.Random
) -> _OperationTimes:
    dispatch = base
    start = dispatch + timedelta(seconds=2)
    deadline = dispatch + timedelta(seconds=deadline_seconds)
    execution_complete = deadline - timedelta(seconds=rng.randint(5, 7))
    effect_created = execution_complete + timedelta(milliseconds=200)
    compensation_start = deadline + timedelta(seconds=2)
    compensation_complete = compensation_start + timedelta(seconds=rng.randint(8, 11))
    workflow_recorded = compensation_complete + timedelta(seconds=1)
    return _OperationTimes(
        dispatch,
        start,
        deadline,
        compensation_start,
        execution_complete,
        effect_created,
        compensation_complete,
        workflow_recorded,
        start + timedelta(seconds=5),
    )


def _safe_times(
    base: datetime, deadline_seconds: int, rng: random.Random
) -> _OperationTimes:
    dispatch = base
    start = dispatch + timedelta(seconds=2)
    deadline = dispatch + timedelta(seconds=deadline_seconds)
    execution_complete = deadline + timedelta(seconds=2)
    effect_created = execution_complete + timedelta(milliseconds=200)
    compensation_start = execution_complete + timedelta(seconds=2)
    compensation_complete = compensation_start + timedelta(seconds=rng.randint(7, 10))
    workflow_recorded = compensation_complete + timedelta(seconds=1)
    return _OperationTimes(
        dispatch,
        start,
        deadline,
        compensation_start,
        execution_complete,
        effect_created,
        compensation_complete,
        workflow_recorded,
        start + timedelta(seconds=5),
    )


def _add_operation(
    *,
    rng: random.Random,
    used: set[str],
    role: str,
    times: _OperationTimes,
    values: dict[str, str],
    coordinator: str,
    executor: str,
    dependency: str,
    message: str,
    structured: dict[str, list[dict[str, JSONValue]]],
    logs: list[LogEntry],
) -> dict[str, object]:
    operation_id = _neutral_id(rng, "OP", used)
    effect_id = _neutral_id(rng, "EF", used)
    compensation_id = _neutral_id(rng, "CP", used)
    row_ids: dict[str, str] = {}

    def row(source: str, data: dict[str, JSONValue]) -> str:
        evidence_id = _neutral_id(rng, "EV", used)
        row_ids[source] = evidence_id
        structured[source].append({"evidence_id": evidence_id, **data})
        return evidence_id

    row(
        "workflow_attempts",
        {
            "operation_id": operation_id,
            "dispatched_at": _timestamp(times.dispatch),
            "deadline_at": _timestamp(times.deadline),
            "compensation_state": values["compensation_state"],
            "workflow_state": values["workflow_state"],
            "service_alias": coordinator,
        },
    )
    row(
        "execution_observations",
        {
            "operation_id": operation_id,
            "started_at": _timestamp(times.execution_start),
            "completed_at": _timestamp(times.execution_complete),
            "result": values["execution_result"],
            "service_alias": executor,
        },
    )
    row(
        "effect_records",
        {
            "operation_id": operation_id,
            "effect_id": effect_id,
            "created_at": _timestamp(times.effect_created),
            "state": values["effect_state"],
            "service_alias": executor,
        },
    )
    row(
        "compensation_records",
        {
            "operation_id": operation_id,
            "compensation_id": compensation_id,
            "started_at": _timestamp(times.compensation_start),
            "completed_at": _timestamp(times.compensation_complete),
            "result": "completed",
            "service_alias": coordinator,
        },
    )
    row(
        "dependency_health",
        {
            "operation_id": operation_id,
            "service_alias": dependency,
            "observed_at": _timestamp(times.dependency_observed),
            "availability_state": "available",
            "warning": "none",
        },
    )

    log_ids: dict[str, str] = {}

    def log(
        event_kind: str,
        when: datetime,
        service: str,
        attributes: dict[str, JSONValue] | None = None,
    ) -> None:
        evidence_id = _neutral_id(rng, "EV", used)
        payload: dict[str, JSONValue] = {
            "operation_id": operation_id,
            "event_kind": event_kind,
        }
        if attributes:
            payload.update(attributes)
        logs.append(
            LogEntry(
                evidence_id=evidence_id,
                timestamp=_timestamp(when),
                level="INFO",
                service=service,
                message=message,
                attributes=payload,
            )
        )
        log_ids[event_kind] = evidence_id

    log("dispatch_recorded", times.dispatch, coordinator)
    log("execution_started", times.execution_start, executor)
    log("dependency_observed", times.dependency_observed, dependency, {"warning": "none"})
    log("deadline_reached", times.deadline, coordinator)
    log(
        "compensation_started",
        times.compensation_start,
        coordinator,
        {"compensation_id": compensation_id, "phase": "started"},
    )
    log(
        "execution_completed",
        times.execution_complete,
        executor,
        {"result": values["execution_result"]},
    )
    log(
        "effect_recorded",
        times.effect_created,
        executor,
        {"effect_id": effect_id, "state": values["effect_state"]},
    )
    log(
        "compensation_completed",
        times.compensation_complete,
        coordinator,
        {"compensation_id": compensation_id, "result": "completed"},
    )
    log(
        "workflow_state_recorded",
        times.workflow_recorded,
        coordinator,
        {"workflow_state": values["workflow_state"]},
    )
    if set(log_ids) != set(_EVENT_KINDS):
        raise AssertionError("Every v3 operation must expose the same event inventory")
    return {
        "role": role,
        "operation_id": operation_id,
        "effect_id": effect_id,
        "compensation_id": compensation_id,
        "row_ids": row_ids,
        "log_ids": log_ids,
        "times": times,
    }


def _invariants(
    operation_data: dict[str, dict[str, object]],
) -> tuple[DiagnosticInvariant, ...]:
    def ref(role: str, source: str, field: str) -> EvidenceReference:
        data = operation_data[role]
        row_ids = data["row_ids"]
        assert isinstance(row_ids, dict)
        return EvidenceReference(source, {"evidence_id": str(row_ids[source])}, field)

    target_order = (
        ref("target", "workflow_attempts", "dispatched_at"),
        ref("target", "execution_observations", "started_at"),
        ref("target", "workflow_attempts", "deadline_at"),
        ref("target", "compensation_records", "started_at"),
        ref("target", "execution_observations", "completed_at"),
    )
    twin_order = (
        ref("temporal-twin", "workflow_attempts", "dispatched_at"),
        ref("temporal-twin", "execution_observations", "started_at"),
        ref("temporal-twin", "execution_observations", "completed_at"),
        ref("temporal-twin", "effect_records", "created_at"),
        ref("temporal-twin", "workflow_attempts", "deadline_at"),
        ref("temporal-twin", "compensation_records", "started_at"),
        ref("temporal-twin", "compensation_records", "completed_at"),
    )
    safe_order = (
        ref("safe-compensation", "workflow_attempts", "dispatched_at"),
        ref("safe-compensation", "execution_observations", "started_at"),
        ref("safe-compensation", "workflow_attempts", "deadline_at"),
        ref("safe-compensation", "execution_observations", "completed_at"),
        ref("safe-compensation", "compensation_records", "started_at"),
        ref("safe-compensation", "compensation_records", "completed_at"),
    )
    result = [
        DiagnosticInvariant(
            "v3_target_event_order",
            "ordered_before",
            target_order,
            True,
            "essential",
            (
                "Target dispatch, execution start, deadline, compensation start, "
                "and original completion are ordered."
            ),
        ),
        DiagnosticInvariant(
            "v3_target_execution_compensation_overlap",
            "intervals_overlap",
            (
                ref("target", "execution_observations", "started_at"),
                ref("target", "execution_observations", "completed_at"),
                ref("target", "compensation_records", "started_at"),
                ref("target", "compensation_records", "completed_at"),
            ),
            True,
            "essential",
            "Target execution and compensation overlap for positive time.",
        ),
        DiagnosticInvariant(
            "v3_target_effect_after_compensation_start",
            "ordered_before",
            (
                ref("target", "compensation_records", "started_at"),
                ref("target", "effect_records", "created_at"),
            ),
            True,
            "essential",
            "The original successful effect is recorded after compensation starts.",
        ),
        DiagnosticInvariant(
            "v3_temporal_twin_serialized_order",
            "ordered_before",
            twin_order,
            True,
            "essential",
            "The twin completes and records its effect before deadline compensation.",
        ),
        DiagnosticInvariant(
            "v3_temporal_twin_no_overlap",
            "intervals_overlap",
            (
                ref("temporal-twin", "execution_observations", "started_at"),
                ref("temporal-twin", "execution_observations", "completed_at"),
                ref("temporal-twin", "compensation_records", "started_at"),
                ref("temporal-twin", "compensation_records", "completed_at"),
            ),
            False,
            "essential",
            "The state-transition twin remains serialized, so concurrency is not required.",
        ),
        DiagnosticInvariant(
            "v3_safe_control_settled_before_compensation",
            "ordered_before",
            safe_order,
            True,
            "supportive",
            "The safe control is cancelled and settled before compensation begins.",
        ),
        DiagnosticInvariant(
            "v3_safe_control_no_overlap",
            "intervals_overlap",
            (
                ref("safe-compensation", "execution_observations", "started_at"),
                ref("safe-compensation", "execution_observations", "completed_at"),
                ref("safe-compensation", "compensation_records", "started_at"),
                ref("safe-compensation", "compensation_records", "completed_at"),
            ),
            False,
            "supportive",
            "The safe control has no execution/compensation overlap.",
        ),
    ]
    for role in ("target", "temporal-twin"):
        result.append(
            DiagnosticInvariant(
                f"v3_{role.replace('-', '_')}_terminal_tuple",
                "sequence_equals",
                (
                    ref(role, "workflow_attempts", "workflow_state"),
                    ref(role, "execution_observations", "result"),
                    ref(role, "effect_records", "state"),
                    ref(role, "compensation_records", "result"),
                ),
                ["compensated", "success", "active", "completed"],
                "essential",
                "Target and twin deliberately share the same non-temporal terminal tuple.",
            )
        )
        result.append(
            DiagnosticInvariant(
                f"v3_{role.replace('-', '_')}_cross_source_identity",
                "equal",
                tuple(
                    ref(role, source, "operation_id")
                    for source in (
                        "workflow_attempts",
                        "execution_observations",
                        "effect_records",
                        "compensation_records",
                        "dependency_health",
                    )
                ),
                True,
                "essential",
                "Each paired operation remains genuinely linked across all sources.",
            )
        )
    return tuple(result)


def _expected_evidence(
    operation_data: dict[str, dict[str, object]],
) -> tuple[ExpectedEvidence, ...]:
    target = operation_data["target"]
    row_ids = target["row_ids"]
    assert isinstance(row_ids, dict)
    refs = tuple(
        EvidenceReference(source, {"evidence_id": str(row_ids[source])})
        for source in (
            "workflow_attempts",
            "execution_observations",
            "effect_records",
            "compensation_records",
        )
    )
    return (
        ExpectedEvidence(
            (
                "Target-linked workflow, execution, effect, and compensation "
                "records establish the temporal causal chain."
            ),
            refs,
        ),
    )


def _sensitive_fields() -> tuple[SensitiveField, ...]:
    timestamps = (
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
    identifiers = (
        "workflow_attempts.operation_id",
        "execution_observations.operation_id",
        "effect_records.operation_id",
        "compensation_records.operation_id",
        "dependency_health.operation_id",
        "logs.operation_id",
        "effect_records.effect_id",
        "compensation_records.compensation_id",
    )
    return tuple(
        SensitiveField(
            path,
            "operational_timestamp",
            "preserve_temporal_relationships",
            "Temporal relations are causal evidence but absolute wall-clock time is sensitive.",
        )
        for path in timestamps
    ) + tuple(
        SensitiveField(
            path,
            "operational_identifier",
            "preserve_equality",
            "Identity is required only for subject linkage across sources.",
        )
        for path in identifiers
    )


def _neutral_id(rng: random.Random, prefix: str, used: set[str]) -> str:
    while True:
        value = f"{prefix}-{rng.randrange(10_000_000, 99_999_999)}"
        if value not in used:
            used.add(value)
            return value


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")
