"""Incident 003 v2 declarations for the family-neutral evidence scorer."""

from __future__ import annotations

from diagbench.generators.incident_003_v2 import FAMILY_ID
from diagbench.schema import Incident
from diagpriv.evaluation.evidence_support_v3 import (
    EVIDENCE_SUPPORT_VERSION,
    EvidencePathV3,
    EvidenceRequirementV3,
    EvidenceRubricV3,
    EvidenceSubjectBindingV3,
    RequirementKind,
    SubjectRole,
)


def build_incident_003_v2_evidence_rubric(incident: Incident) -> EvidenceRubricV3:
    """Build preregistered alternatives solely from frozen generator roles."""
    if incident.incident_id != FAMILY_ID:
        raise ValueError("Incident 003 v2 rubric requires Incident 003 v2")
    target = str(incident.metadata["target_operation_id"])
    legitimate = str(incident.metadata["legitimate_compensation_operation_id"])
    slow = str(incident.metadata["slow_control_operation_id"])
    healthy = tuple(
        str(value) for value in incident.metadata["healthy_control_operation_ids"]
    )

    def row(source: str, operation_id: str) -> str:
        matches = [
            str(item["evidence_id"])
            for item in incident.structured_evidence[source]
            if item.get("operation_id") == operation_id
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one {source} row for operation {operation_id}; got {len(matches)}"
            )
        return matches[0]

    def dependency(operation_id: str, *, warning: str | None = None) -> str:
        matches = [
            str(item["evidence_id"])
            for item in incident.structured_evidence["dependency_health"]
            if item.get("operation_id") == operation_id
            and (warning is None or item.get("warning") == warning)
        ]
        if not matches:
            raise ValueError(f"No dependency row for operation {operation_id}")
        return sorted(matches)[0]

    def log(operation_id: str, event_kind: str) -> str:
        matches = [
            entry.evidence_id
            for entry in incident.log_evidence
            if entry.attributes.get("operation_id") == operation_id
            and entry.attributes.get("event_kind") == event_kind
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Expected one {event_kind} log for operation {operation_id}; got {len(matches)}"
            )
        return matches[0]

    def binding_id(operation_id: str) -> str:
        if operation_id == target:
            return "target"
        if operation_id == legitimate:
            return "legitimate-compensation-control"
        return f"healthy-control-{healthy.index(operation_id)}"

    target_workflow = row("workflow_attempts", target)
    target_execution = row("execution_observations", target)
    target_effect = row("effect_records", target)
    target_compensation = row("compensation_records", target)
    target_core = (
        target_workflow,
        target_execution,
        target_effect,
        target_compensation,
    )
    target_log_core = (
        log(target, "execution_started"),
        log(target, "deadline_reached"),
        log(target, "compensation_started"),
        log(target, "execution_completed"),
        log(target, "effect_recorded"),
        log(target, "compensation_completed"),
        log(target, "workflow_state_recorded"),
    )

    requirements = (
        _requirement(
            "target_identity_linkage",
            "essential",
            "The workflow, execution, effect, and compensation belong to one target operation.",
            ("structured", target_core, binding_id(target)),
            ("logs", target_log_core, binding_id(target)),
        ),
        _requirement(
            "deadline_before_original_completion",
            "essential",
            "The target deadline precedes original execution completion.",
            ("structured", (target_workflow, target_execution), binding_id(target)),
            (
                "logs",
                (log(target, "deadline_reached"), log(target, "execution_completed")),
                binding_id(target),
            ),
        ),
        _requirement(
            "compensation_after_deadline",
            "essential",
            "Target compensation begins after the deadline.",
            ("structured", (target_workflow, target_compensation), binding_id(target)),
            (
                "logs",
                (log(target, "deadline_reached"), log(target, "compensation_started")),
                binding_id(target),
            ),
        ),
        _requirement(
            "execution_compensation_overlap",
            "essential",
            "Original execution and compensation overlap in time.",
            ("structured", (target_execution, target_compensation), binding_id(target)),
            (
                "logs",
                (
                    log(target, "execution_started"),
                    log(target, "compensation_started"),
                    log(target, "execution_completed"),
                    log(target, "compensation_completed"),
                ),
                binding_id(target),
            ),
        ),
        _requirement(
            "late_successful_original_effect",
            "essential",
            "The original execution succeeds and records an active effect after compensation starts.",
            (
                "structured",
                (target_execution, target_effect, target_compensation),
                binding_id(target),
            ),
            (
                "logs",
                (
                    log(target, "compensation_started"),
                    log(target, "execution_completed"),
                    log(target, "effect_recorded"),
                ),
                binding_id(target),
            ),
        ),
        _requirement(
            "inconsistent_terminal_workflow_effect_state",
            "essential",
            "Compensated workflow state coexists with completed compensation and an active successful effect.",
            ("structured", target_core, binding_id(target)),
            (
                "logs",
                (
                    log(target, "execution_completed"),
                    log(target, "effect_recorded"),
                    log(target, "compensation_completed"),
                    log(target, "workflow_state_recorded"),
                ),
                binding_id(target),
            ),
        ),
        _requirement(
            "legitimate_compensation_control",
            "contrast",
            "A cancelled control is compensated only after cancellation and creates no effect.",
            (
                "structured",
                (
                    row("workflow_attempts", legitimate),
                    row("execution_observations", legitimate),
                    row("compensation_records", legitimate),
                ),
                binding_id(legitimate),
            ),
            (
                "logs",
                (
                    log(legitimate, "execution_completed"),
                    log(legitimate, "compensation_started"),
                    log(legitimate, "compensation_completed"),
                ),
                binding_id(legitimate),
            ),
        ),
        _requirement(
            "healthy_deadline_or_benign_slow_control",
            "contrast",
            "A healthy control succeeds before its deadline without compensation.",
            *tuple(
                (
                    f"structured-control-{index}",
                    (
                        row("workflow_attempts", operation_id),
                        row("execution_observations", operation_id),
                    ),
                    binding_id(operation_id),
                )
                for index, operation_id in enumerate(healthy)
            ),
            (
                "structured-benign-slow",
                (
                    row("workflow_attempts", slow),
                    row("execution_observations", slow),
                    dependency(slow, warning="latency_elevated"),
                ),
                binding_id(slow),
            ),
        ),
        _requirement(
            "orchestrator_ownership",
            "supportive",
            "The visible orchestrator owns target deadline, compensation, and workflow state.",
            ("structured", (target_workflow, target_compensation), binding_id(target)),
        ),
        _requirement(
            "executor_ownership",
            "supportive",
            "The executor owns original execution and effect recording.",
            ("structured", (target_execution, target_effect), binding_id(target)),
        ),
        _requirement(
            "dependency_available",
            "supportive",
            "The target dependency remains available.",
            ("structured", (dependency(target),), binding_id(target)),
        ),
        _requirement(
            "warning_comparison",
            "supportive",
            "A non-target successful operation supplies a warning comparison.",
            (
                "structured",
                (dependency(slow, warning="latency_elevated"),),
                binding_id(slow),
            ),
        ),
        _requirement(
            "additional_target_lifecycle",
            "supportive",
            "Target lifecycle logs corroborate the structured causal chain.",
            ("logs", target_log_core, binding_id(target)),
        ),
    )
    bindings = (
        _subject_binding(incident, target, "target", "target"),
        _subject_binding(
            incident,
            legitimate,
            "legitimate-compensation-control",
            "contrast",
        ),
        *tuple(
            _subject_binding(
                incident,
                operation_id,
                binding_id(operation_id),
                "contrast",
            )
            for operation_id in healthy
        ),
    )
    return EvidenceRubricV3(EVIDENCE_SUPPORT_VERSION, requirements, bindings)


def _requirement(
    name: str,
    kind: RequirementKind,
    description: str,
    *paths: tuple[str, tuple[str, ...], str],
) -> EvidenceRequirementV3:
    return EvidenceRequirementV3(
        name=name,
        kind=kind,
        description=description,
        acceptable_paths=tuple(
            EvidencePathV3(
                path_id=f"{name}:{path_name}",
                evidence_ids=evidence_ids,
                optional_evidence_ids=(),
                semantic_predicate_id="bound_minimum_evidence_present",
                semantic_parameters=(
                    ("relationship_id", name),
                    ("subject_binding_required", True),
                ),
                subject_binding_id=subject_binding_id,
                redundancy_class=name,
                minimum_group_requirement=len(evidence_ids),
            )
            for path_name, evidence_ids, subject_binding_id in paths
        ),
    )


def _subject_binding(
    incident: Incident,
    operation_id: str,
    binding_id: str,
    role: SubjectRole,
) -> EvidenceSubjectBindingV3:
    structured = tuple(
        str(row["evidence_id"])
        for rows in incident.structured_evidence.values()
        for row in rows
        if row.get("operation_id") == operation_id
    )
    logs = tuple(
        entry.evidence_id
        for entry in incident.log_evidence
        if entry.attributes.get("operation_id") == operation_id
    )
    return EvidenceSubjectBindingV3(
        binding_id=binding_id,
        subject_id=operation_id,
        role=role,
        evidence_ids=tuple(sorted((*structured, *logs))),
    )
