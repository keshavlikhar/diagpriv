"""Versioned Incident 003 v2 oracle over the frozen v1 construction."""

from __future__ import annotations

from copy import deepcopy

from diagbench.generators.incident_003 import generate_incident_003
from diagbench.schema import IncidentV3, StructuredRootCauseV3

FAMILY_ID = "incident_003_temporal_compensation_v2"
GENERATOR_VERSION = "incident-003-generator-v2"
PROTOCOL_VERSION = "incident-003-temporal-protocol-v2"
EVIDENCE_SUPPORT_VERSION = "evidence-support-v3"
DEFAULT_SEED = 1019
DEVELOPMENT_SEEDS = range(1000, 2000)


def generate_incident_003_v2(seed: int = DEFAULT_SEED) -> IncidentV3:
    """Attach the approved v3 oracle without changing v1 model-visible evidence."""
    base = generate_incident_003(seed)
    metadata = deepcopy(base.metadata)
    metadata.update(
        {
            "benchmark_version": "diagbench-v0.5",
            "family_id": FAMILY_ID,
            "generator_version": GENERATOR_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "construction_generator_version": base.metadata["generator_version"],
            "construction_protocol_version": base.metadata["protocol_version"],
            "evidence_support_version": EVIDENCE_SUPPORT_VERSION,
        }
    )
    return IncidentV3(
        incident_id=FAMILY_ID,
        title=base.title,
        category=base.category,
        description=base.description,
        troubleshooting_question=base.troubleshooting_question,
        ground_truth=base.ground_truth,
        ground_truth_v2=base.ground_truth_v2,
        component_mappings=base.component_mappings,
        structured_evidence=base.structured_evidence,
        log_evidence=base.log_evidence,
        sensitive_fields=base.sensitive_fields,
        diagnostic_invariants=base.diagnostic_invariants,
        expected_evidence=base.expected_evidence,
        difficulty=base.difficulty,
        metadata=metadata,
        ground_truth_v3=StructuredRootCauseV3(
            observed_outcome="inconsistent_state",
            trigger="timeout_or_deadline",
            subsequent_action="compensation_or_rollback",
            failure_mechanism="incorrect_concurrency_control",
            affected_component="workflow_orchestrator",
            logical_operation_repeated=False,
            explanation=(
                "The workflow deadline initiated compensation while original execution "
                "was still active; ineffective coordination allowed both overlapping "
                "operations to take effect and leave contradictory terminal state."
            ),
        ),
    )
