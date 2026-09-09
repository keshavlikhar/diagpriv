"""Fixed benchmark-wide canonical vocabulary for RCA protocol v2."""

from __future__ import annotations

TAXONOMY_VERSION = "rca-taxonomy-v2"

OUTCOME_CATEGORIES = (
    "degraded_performance",
    "delayed_effect",
    "duplicate_effect",
    "incorrect_effect",
    "inconsistent_state",
    "missing_effect",
    "partial_effect",
    "service_unavailable",
    "unauthorized_effect",
    "unknown_outcome",
)

TRIGGER_CATEGORIES = (
    "concurrent_activity",
    "dependency_error",
    "deployment_or_configuration_change",
    "malformed_or_unexpected_input",
    "operator_action",
    "process_restart_or_failover",
    "resource_exhaustion",
    "scheduled_event",
    "timeout_or_deadline",
    "traffic_or_load_change",
    "unknown_trigger",
)

SUBSEQUENT_ACTION_CATEGORIES = (
    "compensation_or_rollback",
    "concurrent_duplicate_submission",
    "failover_or_reroute",
    "manual_reprocessing",
    "message_redelivery_or_replay",
    "no_follow_on_action",
    "retry_or_rearrival",
    "scheduled_reprocessing",
    "unknown_follow_on_action",
)

FAILURE_MECHANISM_CATEGORIES = (
    "authorization_or_policy_failure",
    "configuration_or_routing_error",
    "data_integrity_failure",
    "dependency_contract_failure",
    "incorrect_concurrency_control",
    "incorrect_retry_policy",
    "incorrect_state_transition",
    "missing_or_ineffective_idempotency",
    "non_atomic_commit_or_rollback",
    "resource_management_failure",
    "stale_or_inconsistent_data",
    "validation_or_input_handling_failure",
    "unknown_failure_mechanism",
)

AFFECTED_COMPONENT_CATEGORIES = (
    "client_or_caller",
    "control_plane",
    "external_dependency",
    "identity_or_policy_service",
    "message_delivery_layer",
    "multiple_components",
    "observability_pipeline",
    "operation_executor",
    "request_ingress",
    "scheduler",
    "state_store",
    "workflow_orchestrator",
    "unknown_component",
)

CATEGORIES_BY_FIELD = {
    "observed_outcome": OUTCOME_CATEGORIES,
    "trigger": TRIGGER_CATEGORIES,
    "subsequent_action": SUBSEQUENT_ACTION_CATEGORIES,
    "failure_mechanism": FAILURE_MECHANISM_CATEGORIES,
    "affected_component": AFFECTED_COMPONENT_CATEGORIES,
}


def canonical_category_v2(field: str, value: str) -> str | None:
    """Accept an exact canonical v2 label; v2 has no semantic alias table."""
    categories = CATEGORIES_BY_FIELD[field]
    return value if value in categories else None
