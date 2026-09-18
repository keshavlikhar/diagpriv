"""Incident 003 v3 evidence requirements for evidence-support-v4."""

from __future__ import annotations

from diagbench.generators.incident_003_v3 import FAMILY_ID
from diagbench.schema import Incident
from diagpriv.evaluation.evidence_support_v3 import (
    EVIDENCE_SUPPORT_VERSION as RUBRIC_SCHEMA_VERSION,
    EvidencePathV3,
    EvidenceRequirementV3,
    EvidenceRubricV3,
    EvidenceSubjectBindingV3,
    RequirementKind,
)

REQUIREMENT_CONSTRUCTOR_VERSION = "incident-003-v3-evidence-requirements-v2"


def build_incident_003_v3_evidence_rubric(incident: Incident) -> EvidenceRubricV3:
    """Build query-role-specific proof obligations over one shared construction."""
    if incident.incident_id != FAMILY_ID:
        raise ValueError("Incident 003 v3 rubric requires Incident 003 v3")
    target = str(incident.metadata["target_operation_id"])
    twin = str(incident.metadata["temporal_twin_operation_id"])
    safe = str(incident.metadata["safe_control_operation_id"])
    query_role = str(incident.metadata.get("query_role", "target"))
    if query_role not in {"target", "temporal_twin"}:
        raise ValueError(f"Unsupported Incident 003 v3 query role: {query_role}")

    def row(source: str, operation_id: str) -> str:
        matches = [
            str(item["evidence_id"])
            for item in incident.structured_evidence[source]
            if item.get("operation_id") == operation_id
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one {source} row for {operation_id}")
        return matches[0]

    def log(operation_id: str, event_kind: str) -> str:
        matches = [
            item.evidence_id
            for item in incident.log_evidence
            if item.attributes.get("operation_id") == operation_id
            and item.attributes.get("event_kind") == event_kind
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one {event_kind} log for {operation_id}")
        return matches[0]

    queried = target if query_role == "target" else twin
    paired_contrast = twin if query_role == "target" else target
    queried_core = tuple(
        row(source, queried)
        for source in (
            "workflow_attempts",
            "execution_observations",
            "effect_records",
            "compensation_records",
        )
    )
    if query_role == "target":
        requirements = (
            _requirement(
                "queried_identity_linkage",
                "essential",
                "The queried workflow, execution, effect, and compensation belong to one operation.",
                queried_core,
                "queried-subject",
                relationship_id="target_identity_linkage",
            ),
            _requirement(
                "deadline_before_original_completion",
                "essential",
                "The queried operation deadline precedes original completion.",
                (
                    row("workflow_attempts", target),
                    row("execution_observations", target),
                ),
                "queried-subject",
            ),
            _requirement(
                "compensation_after_deadline",
                "essential",
                "Compensation begins after the queried operation deadline.",
                (
                    row("workflow_attempts", target),
                    row("compensation_records", target),
                ),
                "queried-subject",
            ),
            _requirement(
                "execution_compensation_overlap",
                "essential",
                "Original execution and compensation overlap for the queried operation.",
                (
                    row("execution_observations", target),
                    row("compensation_records", target),
                ),
                "queried-subject",
            ),
            _requirement(
                "late_successful_original_effect",
                "essential",
                (
                    "The original execution succeeds and records an active effect "
                    "after compensation starts."
                ),
                (
                    row("execution_observations", target),
                    row("effect_records", target),
                    row("compensation_records", target),
                ),
                "queried-subject",
            ),
            _requirement(
                "inconsistent_terminal_workflow_effect_state",
                "essential",
                (
                    "Compensated workflow state coexists with completed compensation "
                    "and an active successful effect."
                ),
                queried_core,
                "queried-subject",
            ),
            _requirement(
                "temporal_twin_serialized_contrast",
                "contrast",
                (
                    "The paired twin has the same terminal tuple but completes before "
                    "deadline compensation and does not overlap."
                ),
                (
                    row("workflow_attempts", twin),
                    row("execution_observations", twin),
                    row("effect_records", twin),
                    row("compensation_records", twin),
                ),
                "paired-contrast",
            ),
            _safe_requirement(row, safe),
            _requirement(
                "queried_lifecycle_support",
                "supportive",
                "Queried lifecycle logs corroborate the overlapping temporal chain.",
                tuple(
                    log(target, kind)
                    for kind in (
                        "execution_started",
                        "deadline_reached",
                        "compensation_started",
                        "execution_completed",
                        "effect_recorded",
                        "compensation_completed",
                        "workflow_state_recorded",
                    )
                ),
                "queried-subject",
                relationship_id="additional_target_lifecycle",
            ),
        )
    else:
        requirements = (
            _requirement(
                "queried_identity_linkage",
                "essential",
                "The queried workflow, execution, effect, and compensation belong to one operation.",
                queried_core,
                "queried-subject",
                relationship_id="target_identity_linkage",
            ),
            _requirement(
                "successful_effect_before_deadline",
                "essential",
                (
                    "The queried execution succeeds and records its active effect "
                    "before the workflow deadline."
                ),
                (
                    row("workflow_attempts", twin),
                    row("execution_observations", twin),
                    row("effect_records", twin),
                ),
                "queried-subject",
                relationship_id="twin_success_effect_before_deadline",
            ),
            _requirement(
                "compensation_after_committed_success",
                "essential",
                (
                    "After the successful effect is committed, the workflow crosses "
                    "its deadline and still applies compensation."
                ),
                (
                    row("workflow_attempts", twin),
                    row("effect_records", twin),
                    row("compensation_records", twin),
                ),
                "queried-subject",
                relationship_id="twin_compensation_after_committed_success",
            ),
            _requirement(
                "serialized_execution_before_compensation",
                "essential",
                (
                    "The queried execution is fully complete before compensation "
                    "starts, so the invalid transition persists without concurrency."
                ),
                (
                    row("execution_observations", twin),
                    row("compensation_records", twin),
                ),
                "queried-subject",
                relationship_id="twin_serialized_no_overlap",
            ),
            _requirement(
                "inconsistent_terminal_workflow_effect_state",
                "essential",
                (
                    "The serialized post-success transition leaves compensated "
                    "workflow state with a completed active effect."
                ),
                queried_core,
                "queried-subject",
            ),
            _requirement(
                "concurrency_target_overlap_contrast",
                "contrast",
                (
                    "The paired concurrency case differs because execution and "
                    "compensation overlap."
                ),
                (
                    row("execution_observations", target),
                    row("compensation_records", target),
                ),
                "paired-contrast",
                relationship_id="execution_compensation_overlap",
            ),
            _safe_requirement(row, safe),
            _requirement(
                "queried_lifecycle_support",
                "supportive",
                (
                    "Queried structured lifecycle records corroborate the serialized "
                    "post-success compensation transition."
                ),
                queried_core,
                "queried-subject",
                relationship_id="temporal_twin_serialized_contrast",
            ),
        )
    return EvidenceRubricV3(
        RUBRIC_SCHEMA_VERSION,
        requirements,
        (
            _binding(incident, queried, "queried-subject", "target"),
            _binding(incident, paired_contrast, "paired-contrast", "contrast"),
            _binding(incident, safe, "safe-control", "contrast"),
        ),
    )


def _safe_requirement(row, safe: str) -> EvidenceRequirementV3:
    return _requirement(
        "safe_compensation_control",
        "contrast",
        "The safe control is cancelled and settled before compensation begins.",
        (
            row("workflow_attempts", safe),
            row("execution_observations", safe),
            row("effect_records", safe),
            row("compensation_records", safe),
        ),
        "safe-control",
    )


def _requirement(
    name: str,
    kind: RequirementKind,
    description: str,
    evidence_ids: tuple[str, ...],
    binding_id: str,
    *,
    relationship_id: str | None = None,
) -> EvidenceRequirementV3:
    relationship = relationship_id or name
    return EvidenceRequirementV3(
        name=name,
        kind=kind,
        description=description,
        acceptable_paths=(
            EvidencePathV3(
                path_id=f"{name}:structured-or-logs",
                evidence_ids=evidence_ids,
                optional_evidence_ids=(),
                semantic_predicate_id="bound_minimum_evidence_present",
                semantic_parameters=(
                    ("relationship_id", relationship),
                    ("subject_binding_required", True),
                ),
                subject_binding_id=binding_id,
                redundancy_class=name,
                minimum_group_requirement=len(evidence_ids),
            ),
        ),
    )


def _binding(
    incident: Incident,
    operation_id: str,
    binding_id: str,
    role: str,
) -> EvidenceSubjectBindingV3:
    evidence_ids = tuple(
        str(row["evidence_id"])
        for rows in incident.structured_evidence.values()
        for row in rows
        if row.get("operation_id") == operation_id
    ) + tuple(
        entry.evidence_id
        for entry in incident.log_evidence
        if entry.attributes.get("operation_id") == operation_id
    )
    return EvidenceSubjectBindingV3(
        binding_id=binding_id,
        subject_id=operation_id,
        role=role,  # type: ignore[arg-type]
        evidence_ids=evidence_ids,
    )
