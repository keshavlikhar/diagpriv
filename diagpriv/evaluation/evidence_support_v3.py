"""Semantic evidence obligations for RCA protocol v3."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from diagbench.generators.incident_003_v2 import FAMILY_ID
from diagbench.schema import Incident

EVIDENCE_SUPPORT_VERSION = "evidence-support-v3"
RequirementKind = Literal["essential", "contrast", "supportive"]


@dataclass(frozen=True, slots=True)
class EvidencePathV3:
    """One preregistered set of citations that establishes a requirement."""

    path_id: str
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceRequirementV3:
    """One semantic proof obligation with interchangeable evidence paths."""

    name: str
    kind: RequirementKind
    description: str
    acceptable_paths: tuple[EvidencePathV3, ...]


@dataclass(frozen=True, slots=True)
class EvidenceRubricV3:
    version: str
    requirements: tuple[EvidenceRequirementV3, ...]


@dataclass(frozen=True, slots=True)
class EvidenceSupportScoreV3:
    essential_requirement_coverage: float
    contrast_requirement_coverage: float
    supportive_requirement_coverage: float
    useful_citation_precision: float
    invalid_citation_count: int
    invalid_citation_rate: float
    wrong_subject_citation_count: int
    redundant_citation_count: int
    redundant_citation_rate: float
    evidence_supported: bool
    satisfied_essential_requirements: tuple[str, ...]
    missing_essential_requirements: tuple[str, ...]
    satisfied_contrast_requirements: tuple[str, ...]
    satisfied_supportive_requirements: tuple[str, ...]
    selected_evidence_paths: tuple[str, ...]
    valid_evidence_ids: tuple[str, ...]
    useful_evidence_ids: tuple[str, ...]
    unknown_evidence_ids: tuple[str, ...]
    wrong_subject_evidence_ids: tuple[str, ...]
    redundant_evidence_ids: tuple[str, ...]
    evidence_precision: float
    evidence_recall: float
    evidence_f1: float

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        for field in (
            "satisfied_essential_requirements",
            "missing_essential_requirements",
            "satisfied_contrast_requirements",
            "satisfied_supportive_requirements",
            "selected_evidence_paths",
            "valid_evidence_ids",
            "useful_evidence_ids",
            "unknown_evidence_ids",
            "wrong_subject_evidence_ids",
            "redundant_evidence_ids",
        ):
            data[field] = list(data[field])
        return data


def incident_003_evidence_rubric_v3(incident: Incident) -> EvidenceRubricV3:
    """Build frozen structured and log paths from hidden generator roles."""
    if incident.incident_id != FAMILY_ID:
        raise ValueError("evidence-support-v3 currently supports Incident 003 v2 only")
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
            ("structured", target_core),
            ("logs", target_log_core),
        ),
        _requirement(
            "deadline_before_original_completion",
            "essential",
            "The target deadline precedes original execution completion.",
            ("structured", (target_workflow, target_execution)),
            (
                "logs",
                (log(target, "deadline_reached"), log(target, "execution_completed")),
            ),
        ),
        _requirement(
            "compensation_after_deadline",
            "essential",
            "Target compensation begins after the deadline.",
            ("structured", (target_workflow, target_compensation)),
            (
                "logs",
                (log(target, "deadline_reached"), log(target, "compensation_started")),
            ),
        ),
        _requirement(
            "execution_compensation_overlap",
            "essential",
            "Original execution and compensation overlap in time.",
            ("structured", (target_execution, target_compensation)),
            (
                "logs",
                (
                    log(target, "execution_started"),
                    log(target, "compensation_started"),
                    log(target, "execution_completed"),
                    log(target, "compensation_completed"),
                ),
            ),
        ),
        _requirement(
            "late_successful_original_effect",
            "essential",
            "The original execution succeeds and records an active effect after compensation starts.",
            ("structured", (target_execution, target_effect, target_compensation)),
            (
                "logs",
                (
                    log(target, "compensation_started"),
                    log(target, "execution_completed"),
                    log(target, "effect_recorded"),
                ),
            ),
        ),
        _requirement(
            "inconsistent_terminal_workflow_effect_state",
            "essential",
            "Compensated workflow state coexists with completed compensation and an active successful effect.",
            ("structured", target_core),
            (
                "logs",
                (
                    log(target, "execution_completed"),
                    log(target, "effect_recorded"),
                    log(target, "compensation_completed"),
                    log(target, "workflow_state_recorded"),
                ),
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
            ),
            (
                "logs",
                (
                    log(legitimate, "execution_completed"),
                    log(legitimate, "compensation_started"),
                    log(legitimate, "compensation_completed"),
                ),
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
            ),
        ),
        _requirement(
            "orchestrator_ownership",
            "supportive",
            "The visible orchestrator owns target deadline, compensation, and workflow state.",
            ("structured", (target_workflow, target_compensation)),
        ),
        _requirement(
            "executor_ownership",
            "supportive",
            "The executor owns original execution and effect recording.",
            ("structured", (target_execution, target_effect)),
        ),
        _requirement(
            "dependency_available",
            "supportive",
            "The target dependency remains available.",
            ("structured", (dependency(target),)),
        ),
        _requirement(
            "warning_comparison",
            "supportive",
            "A non-target successful operation supplies a warning comparison.",
            ("structured", (dependency(slow, warning="latency_elevated"),)),
        ),
        _requirement(
            "additional_target_lifecycle",
            "supportive",
            "Target lifecycle logs corroborate the structured causal chain.",
            ("logs", target_log_core),
        ),
    )
    return EvidenceRubricV3(EVIDENCE_SUPPORT_VERSION, requirements)


def score_evidence_support_v3(
    incident: Incident, supporting_evidence: tuple[str, ...]
) -> EvidenceSupportScoreV3:
    """Score citations against semantic requirements with deterministic path choice."""
    rubric = incident_003_evidence_rubric_v3(incident)
    visible_subjects = _visible_evidence_subjects(incident)
    visible = set(visible_subjects)
    submitted = tuple(supporting_evidence)
    cited = set(submitted)
    valid = cited & visible
    unknown_occurrences = tuple(item for item in submitted if item not in visible)

    selected_paths: list[EvidencePathV3] = []
    satisfied_by_kind: dict[RequirementKind, list[str]] = {
        "essential": [],
        "contrast": [],
        "supportive": [],
    }
    missing_essential: list[str] = []
    for requirement in rubric.requirements:
        matches = [
            path
            for path in requirement.acceptable_paths
            if set(path.evidence_ids).issubset(cited)
        ]
        if matches:
            selected = min(matches, key=lambda path: (len(path.evidence_ids), path.path_id))
            selected_paths.append(selected)
            satisfied_by_kind[requirement.kind].append(requirement.name)
        elif requirement.kind == "essential":
            missing_essential.append(requirement.name)

    useful = {
        evidence_id for path in selected_paths for evidence_id in path.evidence_ids
    }
    target = str(incident.metadata["target_operation_id"])
    wrong_subject_occurrences = tuple(
        evidence_id
        for evidence_id in submitted
        if evidence_id in visible
        and visible_subjects[evidence_id] != target
        and evidence_id not in useful
    )

    seen: set[str] = set()
    redundant_occurrences: list[str] = []
    for evidence_id in submitted:
        if evidence_id in visible and (evidence_id not in useful or evidence_id in seen):
            redundant_occurrences.append(evidence_id)
        seen.add(evidence_id)

    total = len(submitted)
    essential_total = sum(
        requirement.kind == "essential" for requirement in rubric.requirements
    )
    contrast_total = sum(
        requirement.kind == "contrast" for requirement in rubric.requirements
    )
    supportive_total = sum(
        requirement.kind == "supportive" for requirement in rubric.requirements
    )
    essential_coverage = len(satisfied_by_kind["essential"]) / essential_total
    contrast_coverage = len(satisfied_by_kind["contrast"]) / contrast_total
    supportive_coverage = len(satisfied_by_kind["supportive"]) / supportive_total
    useful_precision = len(useful) / total if total else 0.0
    secondary_recall = essential_coverage
    secondary_f1 = (
        2 * useful_precision * secondary_recall / (useful_precision + secondary_recall)
        if useful_precision + secondary_recall
        else 0.0
    )
    return EvidenceSupportScoreV3(
        essential_requirement_coverage=essential_coverage,
        contrast_requirement_coverage=contrast_coverage,
        supportive_requirement_coverage=supportive_coverage,
        useful_citation_precision=useful_precision,
        invalid_citation_count=len(unknown_occurrences),
        invalid_citation_rate=(len(unknown_occurrences) / total if total else 0.0),
        wrong_subject_citation_count=len(wrong_subject_occurrences),
        redundant_citation_count=len(redundant_occurrences),
        redundant_citation_rate=(len(redundant_occurrences) / total if total else 0.0),
        evidence_supported=(not missing_essential and not unknown_occurrences),
        satisfied_essential_requirements=tuple(satisfied_by_kind["essential"]),
        missing_essential_requirements=tuple(missing_essential),
        satisfied_contrast_requirements=tuple(satisfied_by_kind["contrast"]),
        satisfied_supportive_requirements=tuple(satisfied_by_kind["supportive"]),
        selected_evidence_paths=tuple(path.path_id for path in selected_paths),
        valid_evidence_ids=tuple(sorted(valid)),
        useful_evidence_ids=tuple(sorted(useful)),
        unknown_evidence_ids=tuple(sorted(set(unknown_occurrences))),
        wrong_subject_evidence_ids=tuple(sorted(set(wrong_subject_occurrences))),
        redundant_evidence_ids=tuple(sorted(set(redundant_occurrences))),
        evidence_precision=useful_precision,
        evidence_recall=secondary_recall,
        evidence_f1=secondary_f1,
    )


def _requirement(
    name: str,
    kind: RequirementKind,
    description: str,
    *paths: tuple[str, tuple[str, ...]],
) -> EvidenceRequirementV3:
    return EvidenceRequirementV3(
        name=name,
        kind=kind,
        description=description,
        acceptable_paths=tuple(
            EvidencePathV3(f"{name}:{path_name}", evidence_ids)
            for path_name, evidence_ids in paths
        ),
    )


def _visible_evidence_subjects(incident: Incident) -> dict[str, str | None]:
    subjects: dict[str, str | None] = {}
    for rows in incident.structured_evidence.values():
        for row in rows:
            subjects[str(row["evidence_id"])] = (
                None if row.get("operation_id") is None else str(row["operation_id"])
            )
    for entry in incident.log_evidence:
        operation_id = entry.attributes.get("operation_id")
        subjects[entry.evidence_id] = (
            None if operation_id is None else str(operation_id)
        )
    return subjects
