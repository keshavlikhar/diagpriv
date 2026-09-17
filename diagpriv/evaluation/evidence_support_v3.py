"""Family-neutral semantic evidence evaluation for RCA protocol v3."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Literal

from diagbench.schema import ModelView

EVIDENCE_SUPPORT_VERSION = "evidence-support-v3"
RequirementKind = Literal["essential", "contrast", "supportive"]
SubjectRole = Literal["target", "contrast", "supportive"]
ParameterValue = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class EvidenceSubjectBindingV3:
    """One allowed evidence subject and its complete visible evidence domain."""

    binding_id: str
    subject_id: str
    role: SubjectRole
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidencePathV3:
    """One preregistered alternative capable of satisfying a requirement."""

    path_id: str
    evidence_ids: tuple[str, ...]
    optional_evidence_ids: tuple[str, ...]
    semantic_predicate_id: str
    semantic_parameters: tuple[tuple[str, ParameterValue], ...]
    subject_binding_id: str
    redundancy_class: str
    minimum_group_requirement: int


@dataclass(frozen=True, slots=True)
class EvidenceRequirementV3:
    """One semantic proof obligation with interchangeable evidence paths."""

    name: str
    kind: RequirementKind
    description: str
    acceptable_paths: tuple[EvidencePathV3, ...]


@dataclass(frozen=True, slots=True)
class EvidenceRubricV3:
    """A complete preregistered evidence protocol for one generated instance."""

    version: str
    requirements: tuple[EvidenceRequirementV3, ...]
    subject_bindings: tuple[EvidenceSubjectBindingV3, ...]


@dataclass(frozen=True, slots=True)
class EvidenceSupportScoreV3:
    essential_requirement_coverage: float
    contrast_requirement_coverage: float
    supportive_requirement_coverage: float
    useful_citation_precision: float
    invalid_citation_count: int
    invalid_citation_rate: float
    wrong_subject_citation_count: int
    contextual_citation_count: int
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
    contextual_evidence_ids: tuple[str, ...]
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
            "contextual_evidence_ids",
            "redundant_evidence_ids",
        ):
            data[field] = list(data[field])
        return data


def canonical_rubric_dict_v3(rubric: EvidenceRubricV3) -> dict[str, object]:
    """Return the normative, fully semantic rubric representation."""
    return {
        "version": rubric.version,
        "subject_bindings": [
            {
                "binding_id": binding.binding_id,
                "subject_id": binding.subject_id,
                "role": binding.role,
                "evidence_ids": sorted(binding.evidence_ids),
            }
            for binding in sorted(
                rubric.subject_bindings, key=lambda item: item.binding_id
            )
        ],
        "requirements": [
            {
                "requirement_id": requirement.name,
                "necessity_class": requirement.kind,
                "description": requirement.description,
                "alternatives": [
                    {
                        "alternative_id": path.path_id,
                        "required_evidence_ids": sorted(path.evidence_ids),
                        "optional_evidence_ids": sorted(path.optional_evidence_ids),
                        "semantic_predicate_id": path.semantic_predicate_id,
                        "semantic_parameters": [
                            {"name": name, "value": value}
                            for name, value in sorted(path.semantic_parameters)
                        ],
                        "subject_binding_id": path.subject_binding_id,
                        "redundancy_class": path.redundancy_class,
                        "minimum_group_requirement": path.minimum_group_requirement,
                    }
                    for path in sorted(
                        requirement.acceptable_paths, key=lambda item: item.path_id
                    )
                ],
            }
            for requirement in sorted(
                rubric.requirements, key=lambda item: item.name
            )
        ],
    }


def canonical_rubric_json_v3(rubric: EvidenceRubricV3) -> str:
    """Serialize a rubric without whitespace, key-order, or newline ambiguity."""
    return json.dumps(
        canonical_rubric_dict_v3(rubric),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def evidence_requirement_set_sha256_v3(rubric: EvidenceRubricV3) -> str:
    return hashlib.sha256(canonical_rubric_json_v3(rubric).encode("utf-8")).hexdigest()


def validate_evidence_rubric_v3(
    model_view: ModelView, rubric: EvidenceRubricV3
) -> None:
    """Fail closed on malformed, unresolved, or cross-subject rubric paths."""
    if rubric.version != EVIDENCE_SUPPORT_VERSION:
        raise ValueError(f"Unsupported evidence rubric version: {rubric.version}")
    if not rubric.requirements:
        raise ValueError("Evidence rubric must contain requirements")
    visible = _visible_evidence_ids(model_view)

    binding_ids: set[str] = set()
    subject_ids: set[str] = set()
    evidence_to_binding: dict[str, str] = {}
    for binding in rubric.subject_bindings:
        if not binding.binding_id or binding.binding_id in binding_ids:
            raise ValueError("Evidence subject binding IDs must be unique and non-empty")
        binding_ids.add(binding.binding_id)
        if (
            not binding.subject_id
            or binding.subject_id in subject_ids
            or not binding.evidence_ids
        ):
            raise ValueError("Evidence subject bindings require a subject and evidence")
        subject_ids.add(binding.subject_id)
        if binding.role not in {"target", "contrast", "supportive"}:
            raise ValueError(f"Unsupported evidence subject role: {binding.role}")
        for evidence_id in binding.evidence_ids:
            if evidence_id not in visible:
                raise ValueError(
                    f"Subject binding references nonexistent evidence: {evidence_id}"
                )
            if evidence_id in evidence_to_binding:
                raise ValueError(
                    f"Evidence ID is assigned to multiple subjects: {evidence_id}"
                )
            evidence_to_binding[evidence_id] = binding.binding_id

    requirement_ids: set[str] = set()
    path_ids: set[str] = set()
    for requirement in rubric.requirements:
        if requirement.kind not in {"essential", "contrast", "supportive"}:
            raise ValueError(f"Unsupported evidence necessity: {requirement.kind}")
        if not requirement.name or requirement.name in requirement_ids:
            raise ValueError("Evidence requirement IDs must be unique and non-empty")
        requirement_ids.add(requirement.name)
        if not requirement.description or not requirement.acceptable_paths:
            raise ValueError("Every evidence requirement needs a description and path")
        for path in requirement.acceptable_paths:
            if not path.path_id or path.path_id in path_ids:
                raise ValueError("Evidence path IDs must be globally unique and non-empty")
            path_ids.add(path.path_id)
            if path.semantic_predicate_id != "bound_minimum_evidence_present":
                raise ValueError(
                    f"Unsupported evidence predicate: {path.semantic_predicate_id}"
                )
            if path.subject_binding_id not in binding_ids:
                raise ValueError(
                    f"Evidence path has unresolved subject binding: {path.path_id}"
                )
            if not path.redundancy_class:
                raise ValueError("Evidence paths require a redundancy class")
            all_path_ids = (*path.evidence_ids, *path.optional_evidence_ids)
            if not path.evidence_ids or len(set(all_path_ids)) != len(all_path_ids):
                raise ValueError("Evidence paths require unique required evidence IDs")
            if not 1 <= path.minimum_group_requirement <= len(path.evidence_ids):
                raise ValueError("Evidence path minimum-group requirement is invalid")
            parameter_names = tuple(name for name, _ in path.semantic_parameters)
            if tuple(sorted(parameter_names)) != parameter_names or len(
                set(parameter_names)
            ) != len(parameter_names):
                raise ValueError("Semantic parameters must be unique and sorted")
            for evidence_id in all_path_ids:
                if evidence_id not in visible:
                    raise ValueError(
                        f"Evidence path references nonexistent evidence: {evidence_id}"
                    )
                if evidence_to_binding.get(evidence_id) != path.subject_binding_id:
                    raise ValueError(
                        f"Evidence path mixes incompatible subjects: {path.path_id}"
                    )


def score_evidence_support_v3(
    supporting_evidence: tuple[str, ...],
    model_view: ModelView,
    rubric: EvidenceRubricV3,
) -> EvidenceSupportScoreV3:
    """Score citations using the frozen historical v3 path-presence semantics."""
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
    """Evaluate only the citation half of a registered semantic path."""
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
