"""Generic v5 evidence-path templates for Incident 003 v3.

The templates name schema roles and event kinds, never case-specific evidence
IDs.  ``build_incident_003_v3_evidence_rubric_v5`` resolves them against one
generated construction after the protocol is fixed.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from diagbench.generators.incident_003_v3 import FAMILY_ID
from diagbench.schema import Incident
from diagpriv.evaluation.evidence_support_v3 import (
    EvidencePathV3,
    EvidenceRequirementV3,
    EvidenceRubricV3,
    EvidenceSubjectBindingV3,
    RequirementKind,
    canonical_rubric_json_v3,
)
from diagpriv.evaluation.evidence_support_v5 import (
    RUBRIC_SCHEMA_VERSION,
    SEMANTIC_PREDICATE_ID,
)

REQUIREMENT_CONSTRUCTOR_VERSION = "incident-003-v3-evidence-requirements-v3"
PATH_TEMPLATE_VERSION = "incident-003-v3-evidence-path-templates-v1"


@dataclass(frozen=True, slots=True)
class EvidencePathTemplateV5:
    """Case-independent recipe for one minimal representation-specific proof."""

    name: str
    modality: str
    relationship_id: str
    structured_sources: tuple[str, ...] = ()
    log_event_kinds: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.modality == "structured":
            if not self.structured_sources or self.log_event_kinds:
                raise ValueError("Structured templates require only structured roles")
        elif self.modality == "logs":
            if not self.log_event_kinds or self.structured_sources:
                raise ValueError("Log templates require only event roles")
        elif self.modality == "mixed":
            if not self.structured_sources or not self.log_event_kinds:
                raise ValueError("Mixed templates require both role types")
        else:
            raise ValueError(f"Unsupported v5 path modality: {self.modality}")


@dataclass(frozen=True, slots=True)
class _RequirementTemplate:
    name: str
    kind: RequirementKind
    description: str
    binding_id: str
    subject_role: str
    paths: tuple[EvidencePathTemplateV5, ...]


def build_incident_003_v3_evidence_rubric_v5(
    incident: Incident,
) -> EvidenceRubricV3:
    """Resolve generic v5 templates for one target or temporal-twin query."""
    if incident.incident_id != FAMILY_ID:
        raise ValueError("Incident 003 v3 evidence v5 requires Incident 003 v3")
    query_role = str(incident.metadata.get("query_role", "target"))
    if query_role not in {"target", "temporal_twin"}:
        raise ValueError(f"Unsupported Incident 003 v3 query role: {query_role}")

    operation_ids = {
        "target": str(incident.metadata["target_operation_id"]),
        "temporal_twin": str(incident.metadata["temporal_twin_operation_id"]),
        "safe_control": str(incident.metadata["safe_control_operation_id"]),
    }
    queried_role = query_role
    paired_role = "temporal_twin" if query_role == "target" else "target"
    bindings = (
        _binding(incident, operation_ids[queried_role], "queried-subject", "target"),
        _binding(incident, operation_ids[paired_role], "paired-contrast", "contrast"),
        _binding(incident, operation_ids["safe_control"], "safe-control", "contrast"),
    )
    templates = _target_requirements() if query_role == "target" else _twin_requirements()
    requirements = tuple(
        EvidenceRequirementV3(
            name=template.name,
            kind=template.kind,
            description=template.description,
            acceptable_paths=tuple(
                _resolve_path(
                    incident,
                    path,
                    operation_ids[template.subject_role],
                    template.binding_id,
                    template.name,
                )
                for path in template.paths
            ),
        )
        for template in templates
    )
    return EvidenceRubricV3(RUBRIC_SCHEMA_VERSION, requirements, bindings)


def evidence_requirement_set_sha256_v5(rubric: EvidenceRubricV3) -> str:
    """Hash the resolved, normative v5 requirement set."""
    return hashlib.sha256(canonical_rubric_json_v3(rubric).encode("utf-8")).hexdigest()


def _target_requirements() -> tuple[_RequirementTemplate, ...]:
    return (
        _identity_requirement("target"),
        _requirement(
            "deadline_before_original_completion",
            "essential",
            "The queried deadline precedes successful original completion.",
            "queried-subject",
            "target",
            "target_deadline_before_completion",
            ("workflow_attempts", "execution_observations"),
            ("deadline_reached", "execution_completed"),
        ),
        _requirement(
            "compensation_after_deadline",
            "essential",
            "Compensation begins after the queried deadline.",
            "queried-subject",
            "target",
            "target_compensation_after_deadline",
            ("workflow_attempts", "compensation_records"),
            ("deadline_reached", "compensation_started"),
        ),
        _requirement(
            "execution_compensation_overlap",
            "essential",
            "Original execution and compensation overlap for positive time.",
            "queried-subject",
            "target",
            "target_execution_compensation_overlap",
            ("execution_observations", "compensation_records"),
            (
                "execution_started",
                "execution_completed",
                "compensation_started",
                "compensation_completed",
            ),
        ),
        _requirement(
            "late_successful_original_effect",
            "essential",
            "A successful original execution records an active effect after compensation begins.",
            "queried-subject",
            "target",
            "target_late_successful_effect",
            ("execution_observations", "effect_records", "compensation_records"),
            ("execution_completed", "effect_recorded", "compensation_started"),
        ),
        _requirement(
            "inconsistent_terminal_workflow_effect_state",
            "essential",
            "Compensated workflow state coexists with an active successful effect.",
            "queried-subject",
            "target",
            "inconsistent_terminal_state",
            (
                "workflow_attempts",
                "execution_observations",
                "effect_records",
            ),
            (
                "execution_completed",
                "effect_recorded",
                "workflow_state_recorded",
            ),
        ),
        _requirement(
            "paired_temporal_twin_serialized_contrast",
            "contrast",
            "The paired twin completes successfully before later compensation begins.",
            "paired-contrast",
            "temporal_twin",
            "twin_serialized_execution_before_compensation",
            ("execution_observations", "compensation_records"),
            ("execution_completed", "compensation_started"),
        ),
        _safe_control_requirement(),
        *_supportive_requirements("target"),
    )


def _twin_requirements() -> tuple[_RequirementTemplate, ...]:
    return (
        _identity_requirement("temporal_twin"),
        _requirement(
            "successful_execution_and_active_effect_before_deadline",
            "essential",
            "The queried execution succeeds and records an active effect before its deadline.",
            "queried-subject",
            "temporal_twin",
            "twin_successful_effect_before_deadline",
            ("workflow_attempts", "execution_observations", "effect_records"),
            ("execution_completed", "effect_recorded", "deadline_reached"),
        ),
        _requirement(
            "compensation_after_committed_success",
            "essential",
            "Compensation begins only after the committed active effect and deadline.",
            "queried-subject",
            "temporal_twin",
            "twin_compensation_after_committed_success",
            ("workflow_attempts", "effect_records", "compensation_records"),
            (
                "effect_recorded",
                "deadline_reached",
                "compensation_started",
            ),
        ),
        _requirement(
            "serialized_execution_before_compensation",
            "essential",
            "Successful execution affirmatively completes before compensation begins.",
            "queried-subject",
            "temporal_twin",
            "twin_serialized_execution_before_compensation",
            ("execution_observations", "compensation_records"),
            ("execution_completed", "compensation_started"),
        ),
        _requirement(
            "inconsistent_terminal_workflow_effect_state",
            "essential",
            "A serialized post-success transition leaves compensated workflow state with an active effect.",
            "queried-subject",
            "temporal_twin",
            "inconsistent_terminal_state",
            (
                "workflow_attempts",
                "execution_observations",
                "effect_records",
            ),
            (
                "execution_completed",
                "effect_recorded",
                "workflow_state_recorded",
            ),
        ),
        _requirement(
            "paired_concurrency_overlap_contrast",
            "contrast",
            "The paired target differs because execution and compensation overlap.",
            "paired-contrast",
            "target",
            "target_execution_compensation_overlap",
            ("execution_observations", "compensation_records"),
            (
                "execution_started",
                "execution_completed",
                "compensation_started",
                "compensation_completed",
            ),
        ),
        _safe_control_requirement(),
        *_supportive_requirements("temporal_twin"),
    )


def _identity_requirement(subject_role: str) -> _RequirementTemplate:
    structured = tuple(
        EvidencePathTemplateV5(
            f"structured-{source}",
            "structured",
            "queried_subject_identity",
            structured_sources=(source,),
        )
        for source in (
            "workflow_attempts",
            "execution_observations",
            "effect_records",
            "compensation_records",
            "dependency_health",
        )
    )
    logs = tuple(
        EvidencePathTemplateV5(
            f"logs-{event}",
            "logs",
            "queried_subject_identity",
            log_event_kinds=(event,),
        )
        for event in (
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
    )
    return _RequirementTemplate(
        "queried_subject_identity",
        "essential",
        "At least one cited record is visibly bound to the queried operation.",
        "queried-subject",
        subject_role,
        structured + logs,
    )


def _supportive_requirements(subject_role: str) -> tuple[_RequirementTemplate, ...]:
    return (
        _requirement(
            "queried_cross_source_linkage",
            "supportive",
            "Two distinct operational representations expose the same queried identity.",
            "queried-subject",
            subject_role,
            "queried_cross_source_linkage",
            ("workflow_attempts", "execution_observations"),
            ("execution_started", "deadline_reached"),
        ),
        _logs_only_requirement(
            "queried_deadline_action_support",
            "supportive",
            "Lifecycle logs show the deadline followed by compensation initiation.",
            subject_role,
            "deadline_then_compensation_support",
            ("deadline_reached", "compensation_started"),
        ),
        _logs_only_requirement(
            "queried_terminal_outcome_support",
            "supportive",
            "Lifecycle logs show successful execution, an active effect, and compensated workflow state.",
            subject_role,
            "inconsistent_terminal_state",
            (
                "execution_completed",
                "effect_recorded",
                "workflow_state_recorded",
            ),
        ),
    )


def _safe_control_requirement() -> _RequirementTemplate:
    return _requirement(
        "safe_compensation_control",
        "contrast",
        "The safe control is cancelled, inactive, and settled before compensation.",
        "safe-control",
        "safe_control",
        "safe_compensation_control",
        (
            "workflow_attempts",
            "execution_observations",
            "effect_records",
            "compensation_records",
        ),
        (
            "execution_completed",
            "effect_recorded",
            "compensation_started",
            "compensation_completed",
            "workflow_state_recorded",
        ),
    )


def _requirement(
    name: str,
    kind: RequirementKind,
    description: str,
    binding_id: str,
    subject_role: str,
    relationship_id: str,
    structured_sources: tuple[str, ...],
    log_event_kinds: tuple[str, ...],
) -> _RequirementTemplate:
    return _RequirementTemplate(
        name,
        kind,
        description,
        binding_id,
        subject_role,
        (
            EvidencePathTemplateV5(
                "structured",
                "structured",
                relationship_id,
                structured_sources=structured_sources,
            ),
            EvidencePathTemplateV5(
                "logs",
                "logs",
                relationship_id,
                log_event_kinds=log_event_kinds,
            ),
        ),
    )


def _logs_only_requirement(
    name: str,
    kind: RequirementKind,
    description: str,
    subject_role: str,
    relationship_id: str,
    log_event_kinds: tuple[str, ...],
) -> _RequirementTemplate:
    return _RequirementTemplate(
        name,
        kind,
        description,
        "queried-subject",
        subject_role,
        (
            EvidencePathTemplateV5(
                "logs",
                "logs",
                relationship_id,
                log_event_kinds=log_event_kinds,
            ),
        ),
    )


def _resolve_path(
    incident: Incident,
    template: EvidencePathTemplateV5,
    operation_id: str,
    binding_id: str,
    requirement_name: str,
) -> EvidencePathV3:
    evidence_ids = tuple(
        _one_structured_id(incident, source, operation_id)
        for source in template.structured_sources
    ) + tuple(
        _one_log_id(incident, event_kind, operation_id)
        for event_kind in template.log_event_kinds
    )
    role_names = (*template.structured_sources, *template.log_event_kinds)
    return EvidencePathV3(
        path_id=f"{requirement_name}:{template.name}",
        evidence_ids=evidence_ids,
        optional_evidence_ids=(),
        semantic_predicate_id=SEMANTIC_PREDICATE_ID,
        semantic_parameters=tuple(
            sorted(
                (
                    ("modality", template.modality),
                    ("path_template_version", PATH_TEMPLATE_VERSION),
                    ("record_roles", ",".join(role_names)),
                    ("relationship_id", template.relationship_id),
                    ("subject_binding_required", True),
                )
            )
        ),
        subject_binding_id=binding_id,
        redundancy_class=requirement_name,
        minimum_group_requirement=len(evidence_ids),
    )


def _one_structured_id(incident: Incident, source: str, operation_id: str) -> str:
    matches = tuple(
        str(row["evidence_id"])
        for row in incident.structured_evidence[source]
        if row.get("operation_id") == operation_id
    )
    if len(matches) != 1:
        raise ValueError(f"Expected one {source} row for {operation_id}")
    return matches[0]


def _one_log_id(incident: Incident, event_kind: str, operation_id: str) -> str:
    matches = tuple(
        entry.evidence_id
        for entry in incident.log_evidence
        if entry.attributes.get("operation_id") == operation_id
        and entry.attributes.get("event_kind") == event_kind
    )
    if len(matches) != 1:
        raise ValueError(f"Expected one {event_kind} log for {operation_id}")
    return matches[0]


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
