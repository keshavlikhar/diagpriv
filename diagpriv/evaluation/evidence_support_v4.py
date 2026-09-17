"""Family-neutral semantic evidence evaluation for evidence-support-v4.

The normative requirement set remains the frozen v3 rubric so its canonical
serialization and SHA-256 do not change.  V4 versions the *evaluation rule*:
an acceptable path must satisfy both its citation requirements and its
family-supplied semantic predicate over the exact transformed ModelView.
"""

from __future__ import annotations

from typing import Protocol

from diagbench.schema import ModelView
from diagpriv.evaluation.evidence_support_v3 import (
    EvidencePathV3,
    EvidenceRubricV3,
    EvidenceSupportScoreV3,
    RequirementKind,
    validate_evidence_rubric_v3,
)

EVIDENCE_SUPPORT_VERSION = "evidence-support-v4"


class EvidenceSemanticEvaluatorV4(Protocol):
    """Family-supplied evaluator for one frozen semantic evidence path."""

    version: str
    temporal_semantics_version: str

    def evaluate_path(
        self,
        path: EvidencePathV3,
        model_view: ModelView,
        rubric: EvidenceRubricV3,
    ) -> bool: ...


def score_evidence_support_v4(
    supporting_evidence: tuple[str, ...],
    model_view: ModelView,
    rubric: EvidenceRubricV3,
    semantic_evaluator: EvidenceSemanticEvaluatorV4,
) -> EvidenceSupportScoreV3:
    """Require citation satisfaction and model-visible semantic satisfaction."""
    validate_evidence_rubric_v3(model_view, rubric)
    visible = _visible_evidence_ids(model_view)
    bound = {
        evidence_id
        for binding in rubric.subject_bindings
        for evidence_id in binding.evidence_ids
    }
    submitted = tuple(supporting_evidence)
    cited = set(submitted)
    valid = cited & visible
    unknown_occurrences = tuple(item for item in submitted if item not in visible)
    wrong_subject_occurrences = tuple(
        item for item in submitted if item in visible and item not in bound
    )

    selected_paths: list[EvidencePathV3] = []
    unselected_matching_paths: list[EvidencePathV3] = []
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
            if _citation_requirements_satisfied(path, cited)
            and semantic_evaluator.evaluate_path(path, model_view, rubric)
        ]
        if matches:
            selected = min(
                matches,
                key=lambda path: (len(path.evidence_ids), path.path_id),
            )
            selected_paths.append(selected)
            unselected_matching_paths.extend(
                path for path in matches if path.path_id != selected.path_id
            )
            satisfied_by_kind[requirement.kind].append(requirement.name)
        elif requirement.kind == "essential":
            missing_essential.append(requirement.name)

    useful = {
        evidence_id
        for path in selected_paths
        for evidence_id in (
            *path.evidence_ids,
            *(item for item in path.optional_evidence_ids if item in cited),
        )
    }
    alternative_redundant = {
        evidence_id
        for path in unselected_matching_paths
        for evidence_id in (*path.evidence_ids, *path.optional_evidence_ids)
        if evidence_id in cited and evidence_id not in useful
    }
    seen: set[str] = set()
    redundant_occurrences: list[str] = []
    contextual_occurrences: list[str] = []
    for evidence_id in submitted:
        if evidence_id not in visible or evidence_id not in bound:
            continue
        if evidence_id in seen or evidence_id in alternative_redundant:
            redundant_occurrences.append(evidence_id)
        elif evidence_id not in useful:
            contextual_occurrences.append(evidence_id)
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
        contextual_citation_count=len(contextual_occurrences),
        redundant_citation_count=len(redundant_occurrences),
        redundant_citation_rate=(len(redundant_occurrences) / total if total else 0.0),
        evidence_supported=(
            not missing_essential
            and not unknown_occurrences
            and not wrong_subject_occurrences
        ),
        satisfied_essential_requirements=tuple(satisfied_by_kind["essential"]),
        missing_essential_requirements=tuple(missing_essential),
        satisfied_contrast_requirements=tuple(satisfied_by_kind["contrast"]),
        satisfied_supportive_requirements=tuple(satisfied_by_kind["supportive"]),
        selected_evidence_paths=tuple(path.path_id for path in selected_paths),
        valid_evidence_ids=tuple(sorted(valid)),
        useful_evidence_ids=tuple(sorted(useful)),
        unknown_evidence_ids=tuple(sorted(set(unknown_occurrences))),
        wrong_subject_evidence_ids=tuple(sorted(set(wrong_subject_occurrences))),
        contextual_evidence_ids=tuple(sorted(set(contextual_occurrences))),
        redundant_evidence_ids=tuple(sorted(set(redundant_occurrences))),
        evidence_precision=useful_precision,
        evidence_recall=secondary_recall,
        evidence_f1=secondary_f1,
    )


def _citation_requirements_satisfied(
    path: EvidencePathV3, cited: set[str]
) -> bool:
    if path.semantic_predicate_id != "bound_minimum_evidence_present":
        raise ValueError(f"Unsupported evidence predicate: {path.semantic_predicate_id}")
    return (
        len(set(path.evidence_ids) & cited) >= path.minimum_group_requirement
        and set(path.evidence_ids).issubset(cited)
    )


def _visible_evidence_ids(model_view: ModelView) -> set[str]:
    evidence_ids: list[str] = []
    for rows in model_view.structured_evidence.values():
        for row in rows:
            evidence_id = row.get("evidence_id")
            if not isinstance(evidence_id, str) or not evidence_id:
                raise ValueError("Every structured evidence row requires an evidence_id")
            evidence_ids.append(evidence_id)
    for entry in model_view.log_evidence:
        if not entry.evidence_id:
            raise ValueError("Every log evidence row requires an evidence_id")
        evidence_ids.append(entry.evidence_id)
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("ModelView evidence IDs must be globally unique")
    return set(evidence_ids)
