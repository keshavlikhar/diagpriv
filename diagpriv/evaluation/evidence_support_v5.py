"""Representation-invariant semantic evidence evaluation for evidence-support-v5.

V5 is intentionally separate from the frozen v3/v4 implementations.  A path is
accepted only when the response cites every member of one preregistered minimal
path *and* the family evaluator proves the path's semantic predicate from the
model-visible values.  Alternative paths may use different representations of
the same fact (for example, structured rows or lifecycle logs).
"""

from __future__ import annotations

from typing import Protocol

from diagbench.schema import ModelView
from diagpriv.evaluation.evidence_support_v3 import (
    EvidencePathV3,
    EvidenceRubricV3,
    EvidenceSupportScoreV3,
    RequirementKind,
)

EVIDENCE_SUPPORT_VERSION = "evidence-support-v5"
RUBRIC_SCHEMA_VERSION = "evidence-rubric-v5"
SEMANTIC_PREDICATE_ID = "bound_semantic_evidence_v5"


class EvidenceSemanticEvaluatorV5(Protocol):
    """Family evaluator for one resolved, representation-specific v5 path."""

    version: str
    temporal_semantics_version: str

    def evaluate_path(
        self,
        path: EvidencePathV3,
        model_view: ModelView,
        rubric: EvidenceRubricV3,
    ) -> bool: ...


def validate_evidence_rubric_v5(
    model_view: ModelView, rubric: EvidenceRubricV3
) -> None:
    """Fail closed on unresolved, cross-subject, or non-minimal v5 paths."""
    if rubric.version != RUBRIC_SCHEMA_VERSION:
        raise ValueError(f"Unsupported v5 evidence rubric version: {rubric.version}")
    if not rubric.requirements:
        raise ValueError("V5 evidence rubric must contain requirements")
    visible = _visible_evidence_ids(model_view)

    binding_ids: set[str] = set()
    subject_ids: set[str] = set()
    evidence_to_binding: dict[str, str] = {}
    for binding in rubric.subject_bindings:
        if not binding.binding_id or binding.binding_id in binding_ids:
            raise ValueError("V5 subject binding IDs must be unique and non-empty")
        if not binding.subject_id or binding.subject_id in subject_ids:
            raise ValueError("V5 subject IDs must be unique and non-empty")
        if not binding.evidence_ids:
            raise ValueError("V5 subject bindings require evidence")
        if binding.role not in {"target", "contrast", "supportive"}:
            raise ValueError(f"Unsupported v5 subject role: {binding.role}")
        binding_ids.add(binding.binding_id)
        subject_ids.add(binding.subject_id)
        for evidence_id in binding.evidence_ids:
            if evidence_id not in visible:
                raise ValueError(
                    f"V5 subject binding references nonexistent evidence: {evidence_id}"
                )
            if evidence_id in evidence_to_binding:
                raise ValueError(
                    f"V5 evidence ID is assigned to multiple subjects: {evidence_id}"
                )
            evidence_to_binding[evidence_id] = binding.binding_id

    requirement_ids: set[str] = set()
    path_ids: set[str] = set()
    for requirement in rubric.requirements:
        if requirement.kind not in {"essential", "contrast", "supportive"}:
            raise ValueError(f"Unsupported v5 evidence necessity: {requirement.kind}")
        if not requirement.name or requirement.name in requirement_ids:
            raise ValueError("V5 requirement IDs must be unique and non-empty")
        if not requirement.description or not requirement.acceptable_paths:
            raise ValueError("Every v5 requirement needs a description and path")
        requirement_ids.add(requirement.name)
        for path in requirement.acceptable_paths:
            if not path.path_id or path.path_id in path_ids:
                raise ValueError("V5 path IDs must be globally unique and non-empty")
            path_ids.add(path.path_id)
            if path.semantic_predicate_id != SEMANTIC_PREDICATE_ID:
                raise ValueError(
                    f"Unsupported v5 evidence predicate: {path.semantic_predicate_id}"
                )
            if path.subject_binding_id not in binding_ids:
                raise ValueError(f"Unresolved v5 subject binding: {path.path_id}")
            if not path.redundancy_class:
                raise ValueError("V5 paths require a redundancy class")
            all_ids = (*path.evidence_ids, *path.optional_evidence_ids)
            if not path.evidence_ids or len(set(all_ids)) != len(all_ids):
                raise ValueError("V5 paths require unique evidence IDs")
            if path.optional_evidence_ids:
                raise ValueError("V5 minimal paths cannot contain optional evidence")
            if path.minimum_group_requirement != len(path.evidence_ids):
                raise ValueError("V5 paths require every registered evidence item")
            parameters = dict(path.semantic_parameters)
            if tuple(sorted(parameters)) != tuple(
                name for name, _ in path.semantic_parameters
            ) or len(parameters) != len(path.semantic_parameters):
                raise ValueError("V5 semantic parameters must be unique and sorted")
            if parameters.get("modality") not in {"structured", "logs", "mixed"}:
                raise ValueError("V5 paths require an explicit modality")
            if not isinstance(parameters.get("relationship_id"), str):
                raise ValueError("V5 paths require a relationship_id")
            if parameters.get("subject_binding_required") is not True:
                raise ValueError("V5 paths require subject binding")
            for evidence_id in all_ids:
                if evidence_id not in visible:
                    raise ValueError(
                        f"V5 path references nonexistent evidence: {evidence_id}"
                    )
                if evidence_to_binding.get(evidence_id) != path.subject_binding_id:
                    raise ValueError(f"V5 path mixes subjects: {path.path_id}")


def score_evidence_support_v5(
    supporting_evidence: tuple[str, ...],
    model_view: ModelView,
    rubric: EvidenceRubricV3,
    semantic_evaluator: EvidenceSemanticEvaluatorV5,
) -> EvidenceSupportScoreV3:
    """Score cited facts against strict, representation-invariant v5 paths."""
    validate_evidence_rubric_v5(model_view, rubric)
    visible = _visible_evidence_ids(model_view)
    bindings = {binding.binding_id: binding for binding in rubric.subject_bindings}
    evidence_to_binding = {
        evidence_id: binding.binding_id
        for binding in rubric.subject_bindings
        for evidence_id in binding.evidence_ids
    }
    queried_binding_ids = {
        binding.binding_id
        for binding in rubric.subject_bindings
        if binding.role == "target"
    }

    submitted = tuple(supporting_evidence)
    cited = set(submitted)
    valid = cited & visible
    unknown_occurrences = tuple(item for item in submitted if item not in visible)

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
            if set(path.evidence_ids).issubset(cited)
            and semantic_evaluator.evaluate_path(path, model_view, rubric)
        ]
        if matches:
            selected = min(matches, key=lambda item: (len(item.evidence_ids), item.path_id))
            selected_paths.append(selected)
            unselected_matching_paths.extend(
                path for path in matches if path.path_id != selected.path_id
            )
            satisfied_by_kind[requirement.kind].append(requirement.name)
        elif requirement.kind == "essential":
            missing_essential.append(requirement.name)

    accepted_nonquery_bindings = {
        path.subject_binding_id
        for path in selected_paths
        if bindings[path.subject_binding_id].role != "target"
        and any(
            requirement.kind == "contrast"
            and path in requirement.acceptable_paths
            for requirement in rubric.requirements
        )
    }
    allowed_binding_ids = queried_binding_ids | accepted_nonquery_bindings
    wrong_subject_occurrences = tuple(
        item
        for item in submitted
        if item in visible and evidence_to_binding.get(item) not in allowed_binding_ids
    )

    useful = {
        evidence_id
        for path in selected_paths
        for evidence_id in path.evidence_ids
    }
    alternative_redundant = {
        evidence_id
        for path in unselected_matching_paths
        for evidence_id in path.evidence_ids
        if evidence_id in cited and evidence_id not in useful
    }
    wrong_subject_set = set(wrong_subject_occurrences)
    seen: set[str] = set()
    redundant_occurrences: list[str] = []
    contextual_occurrences: list[str] = []
    for evidence_id in submitted:
        if evidence_id not in visible or evidence_id in wrong_subject_set:
            continue
        if evidence_id in seen or evidence_id in alternative_redundant:
            redundant_occurrences.append(evidence_id)
        elif evidence_id not in useful:
            contextual_occurrences.append(evidence_id)
        seen.add(evidence_id)

    essential_total = sum(req.kind == "essential" for req in rubric.requirements)
    contrast_total = sum(req.kind == "contrast" for req in rubric.requirements)
    supportive_total = sum(req.kind == "supportive" for req in rubric.requirements)
    total = len(submitted)
    essential_coverage = len(satisfied_by_kind["essential"]) / essential_total
    contrast_coverage = (
        len(satisfied_by_kind["contrast"]) / contrast_total if contrast_total else 1.0
    )
    supportive_coverage = (
        len(satisfied_by_kind["supportive"]) / supportive_total
        if supportive_total
        else 1.0
    )
    useful_precision = len(useful) / total if total else 0.0
    evidence_f1 = (
        2 * useful_precision * essential_coverage
        / (useful_precision + essential_coverage)
        if useful_precision + essential_coverage
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
        wrong_subject_evidence_ids=tuple(sorted(wrong_subject_set)),
        contextual_evidence_ids=tuple(sorted(set(contextual_occurrences))),
        redundant_evidence_ids=tuple(sorted(set(redundant_occurrences))),
        evidence_precision=useful_precision,
        evidence_recall=essential_coverage,
        evidence_f1=evidence_f1,
    )


def _visible_evidence_ids(model_view: ModelView) -> set[str]:
    evidence_ids: list[str] = []
    for rows in model_view.structured_evidence.values():
        for row in rows:
            evidence_id = row.get("evidence_id")
            if not isinstance(evidence_id, str) or not evidence_id:
                raise ValueError("Every structured row requires an evidence_id")
            evidence_ids.append(evidence_id)
    for entry in model_view.log_evidence:
        if not entry.evidence_id:
            raise ValueError("Every log row requires an evidence_id")
        evidence_ids.append(entry.evidence_id)
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("ModelView evidence IDs must be globally unique")
    return set(evidence_ids)
