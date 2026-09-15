"""RCA taxonomy v3 labels, definitions, and adjudication precedence."""

from __future__ import annotations

from dataclasses import dataclass

TAXONOMY_VERSION = "rca-taxonomy-v3"


@dataclass(frozen=True, slots=True)
class CategoryDefinitionV3:
    """Machine-readable researcher-facing definition of one canonical label."""

    label: str
    operational_definition: str
    inclusion_notes: tuple[str, ...] = ()
    exclusion_notes: tuple[str, ...] = ()
    confusables: tuple[str, ...] = ()
    decision_guidance: tuple[str, ...] = ()


def _category(
    label: str,
    operational_definition: str,
    *,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    confusables: tuple[str, ...] = (),
    guidance: tuple[str, ...] = (),
) -> CategoryDefinitionV3:
    return CategoryDefinitionV3(
        label=label,
        operational_definition=operational_definition,
        inclusion_notes=include,
        exclusion_notes=exclude,
        confusables=confusables,
        decision_guidance=guidance,
    )


OUTCOME_DEFINITIONS = (
    _category("degraded_performance", "The service completes work but with materially reduced performance."),
    _category("delayed_effect", "The intended effect occurs later than its required time."),
    _category("duplicate_effect", "One logical operation produces more than one externally meaningful effect."),
    _category("incorrect_effect", "An effect occurs, but its content, target, or value is wrong."),
    _category("inconsistent_state", "Recorded states or externally visible effects contradict one another."),
    _category("missing_effect", "A required externally meaningful effect does not occur."),
    _category("partial_effect", "Only part of a required multi-part effect occurs."),
    _category("service_unavailable", "The service cannot provide its intended operation."),
    _category("unauthorized_effect", "An effect occurs without the required authorization or policy permission."),
    _category("unknown_outcome", "The supplied evidence does not establish a more specific outcome."),
)

TRIGGER_DEFINITIONS = (
    _category("concurrent_activity", "Overlapping activity directly initiates the causal sequence."),
    _category("dependency_error", "An upstream or downstream dependency error initiates the causal sequence."),
    _category("deployment_or_configuration_change", "A deployment or configuration change initiates the causal sequence."),
    _category("malformed_or_unexpected_input", "Input with an unexpected value or structure initiates the causal sequence."),
    _category("operator_action", "A human operational action initiates the causal sequence."),
    _category("process_restart_or_failover", "A restart, crash recovery, or failover initiates the causal sequence."),
    _category("resource_exhaustion", "Exhaustion of a bounded resource initiates the causal sequence."),
    _category("scheduled_event", "A time-scheduled job or event initiates the causal sequence."),
    _category(
        "timeout_or_deadline",
        "A timeout or deadline crossing initiates the causal sequence.",
        exclude=("A later retry, replay, or compensation belongs under subsequent_action.",),
    ),
    _category("traffic_or_load_change", "A material change in traffic or load initiates the causal sequence."),
    _category("unknown_trigger", "The supplied evidence does not establish a more specific trigger."),
)

SUBSEQUENT_ACTION_DEFINITIONS = (
    _category("compensation_or_rollback", "A compensation or rollback action follows the trigger and propagates the failure."),
    _category("concurrent_duplicate_submission", "A separate overlapping submission of the same intended work follows or accompanies the trigger."),
    _category("failover_or_reroute", "A failover or reroute follows the trigger and propagates the failure."),
    _category("manual_reprocessing", "Human-initiated reprocessing follows the trigger."),
    _category("message_redelivery_or_replay", "Automated delivery infrastructure redelivers or replays a message after the trigger."),
    _category("no_follow_on_action", "No distinct post-trigger action is necessary to produce the outcome."),
    _category("retry_or_rearrival", "A retry or repeated request arrival follows the trigger."),
    _category("scheduled_reprocessing", "Scheduled reprocessing follows the trigger."),
    _category("unknown_follow_on_action", "The supplied evidence does not establish a more specific subsequent action."),
)

FAILURE_MECHANISM_DEFINITIONS = (
    _category("authorization_or_policy_failure", "Authorization or policy enforcement is absent, incorrect, or bypassed."),
    _category("configuration_or_routing_error", "Incorrect configuration or routing directs the system into the failure."),
    _category("data_integrity_failure", "Stored or transmitted data violates a required integrity constraint."),
    _category("dependency_contract_failure", "A component relies on a dependency behavior that violates or is absent from the dependency contract."),
    _category(
        "incorrect_concurrency_control",
        "Overlapping actors can both proceed or commit because coordination is absent or ineffective.",
        include=("Fencing, locking, serialization, cancellation enforcement, compare-and-set, or version checking would prevent the outcome.",),
        exclude=("An invalid lifecycle edge that remains invalid under serialized execution.",),
        confusables=("incorrect_state_transition", "missing_or_ineffective_idempotency"),
        guidance=("When the inconsistency exists only because concurrent work was not controlled, this category takes precedence over incorrect_state_transition.",),
    ),
    _category(
        "incorrect_retry_policy",
        "The decision to retry, its timing, or its retry bounds are themselves defective.",
        exclude=("Use only when the retry decision remains defective assuming effective idempotency.",),
        confusables=("missing_or_ineffective_idempotency",),
    ),
    _category(
        "incorrect_state_transition",
        "A lifecycle edge is allowed from an invalid source state or without a required state precondition.",
        include=("The edge remains invalid under serialized execution.",),
        exclude=("A state inconsistency caused only by uncontrolled overlapping work.",),
        confusables=("incorrect_concurrency_control",),
    ),
    _category(
        "missing_or_ineffective_idempotency",
        "Repeated execution of one logical identity is not suppressed or safely replayed.",
        include=("Correct deduplication or safe replay alone would prevent the duplicate outcome.",),
        confusables=("incorrect_retry_policy", "incorrect_concurrency_control"),
        guidance=("This specific control takes precedence over generic retry or concurrency framing when its counterfactual is satisfied.",),
    ),
    _category(
        "non_atomic_commit_or_rollback",
        "A logically indivisible multi-part commit or rollback can partially apply during serialized execution.",
        exclude=("Failures that require overlapping actors belong under incorrect_concurrency_control.",),
        confusables=("incorrect_concurrency_control", "data_integrity_failure"),
    ),
    _category("resource_management_failure", "Resource allocation, release, capacity, or lifetime management is defective."),
    _category("stale_or_inconsistent_data", "A decision uses stale, mutually inconsistent, or insufficiently synchronized data."),
    _category("validation_or_input_handling_failure", "Input validation, normalization, parsing, or lookup handling is missing or incorrect."),
    _category("unknown_failure_mechanism", "The supplied evidence does not establish a more specific mechanism."),
)

AFFECTED_COMPONENT_DEFINITIONS = (
    _category("client_or_caller", "The calling client owns the defective or missing control."),
    _category("control_plane", "A control-plane component owns the defective or missing control."),
    _category("external_dependency", "An external dependency owns the defective or missing control."),
    _category("identity_or_policy_service", "An identity, authorization, or policy service owns the defective or missing control."),
    _category("message_delivery_layer", "The queue, broker, or delivery layer owns the defective or missing control."),
    _category("multiple_components", "The mechanism is jointly owned by multiple components and no single owner is defensible."),
    _category("observability_pipeline", "Telemetry collection, processing, or presentation owns the defective or missing control."),
    _category("operation_executor", "The component applying the domain operation or effect owns the defective or missing control."),
    _category("request_ingress", "The ingress, gateway, or request-admission layer owns the defective or missing control."),
    _category("scheduler", "The scheduler or timed-job system owns the defective or missing control."),
    _category("state_store", "The persistent state store or its consistency control owns the defect."),
    _category("workflow_orchestrator", "The workflow coordinator owns the defective transition, timing, compensation, or coordination control."),
    _category("unknown_component", "The supplied evidence does not establish a more specific owning component."),
)

DEFINITIONS_BY_FIELD = {
    "observed_outcome": OUTCOME_DEFINITIONS,
    "trigger": TRIGGER_DEFINITIONS,
    "subsequent_action": SUBSEQUENT_ACTION_DEFINITIONS,
    "failure_mechanism": FAILURE_MECHANISM_DEFINITIONS,
    "affected_component": AFFECTED_COMPONENT_DEFINITIONS,
}

CATEGORIES_BY_FIELD = {
    field: tuple(definition.label for definition in definitions)
    for field, definitions in DEFINITIONS_BY_FIELD.items()
}


@dataclass(frozen=True, slots=True)
class ControlBoundaryFactsV3:
    """Facts used only to adjudicate the five commonly confusable controls."""

    repeated_logical_identity: bool = False
    effective_idempotency_alone_prevents_outcome: bool = False
    overlapping_actors_required: bool = False
    concurrency_control_prevents_outcome: bool = False
    invalid_transition_remains_under_serialization: bool = False
    serialized_multi_part_operation_can_partially_apply: bool = False
    retry_decision_defective_with_effective_idempotency: bool = False


def adjudicate_control_boundary_v3(facts: ControlBoundaryFactsV3) -> str:
    """Apply the approved precedence among confusable mechanism categories."""
    if (
        facts.repeated_logical_identity
        and facts.effective_idempotency_alone_prevents_outcome
    ):
        return "missing_or_ineffective_idempotency"
    if facts.overlapping_actors_required and facts.concurrency_control_prevents_outcome:
        return "incorrect_concurrency_control"
    if facts.invalid_transition_remains_under_serialization:
        return "incorrect_state_transition"
    if facts.serialized_multi_part_operation_can_partially_apply:
        return "non_atomic_commit_or_rollback"
    if facts.retry_decision_defective_with_effective_idempotency:
        return "incorrect_retry_policy"
    return "unknown_failure_mechanism"


def canonical_category_v3(field: str, value: str) -> str | None:
    """Accept an exact canonical v3 label; v3 has no semantic alias table."""
    categories = CATEGORIES_BY_FIELD[field]
    return value if value in categories else None
