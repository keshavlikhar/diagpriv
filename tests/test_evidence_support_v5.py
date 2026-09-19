from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from diagbench.audits.incident_003 import temporally_ablated_model_view
from diagbench.audits.incident_003_v3_evidence_v5 import (
    audit_incident_003_v3_evidence_v5_range,
)
from diagbench.generators.incident_003_v3 import generate_incident_003_v3
from diagbench.relative_time import RELATIVE_TIME_SEMANTICS_VERSION
from diagbench.schema import ModelView
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION
from diagpriv.evaluation.evidence_support_v3 import (
    evidence_requirement_set_sha256_v3,
)
from diagpriv.evaluation.evidence_support_v4 import score_evidence_support_v4
from diagpriv.evaluation.evidence_support_v5 import (
    EVIDENCE_SUPPORT_VERSION,
    RUBRIC_SCHEMA_VERSION,
    score_evidence_support_v5,
)
from diagpriv.evaluation.evidence_support_v5_analysis import (
    FROZEN_STAGE1_SHA256,
    analyze_frozen_stage1_v5,
)
from diagpriv.evaluation.incident_003_v3_evidence import (
    build_incident_003_v3_evidence_rubric,
)
from diagpriv.evaluation.incident_003_v3_evidence_semantics import (
    Incident003V3EvidenceSemanticEvaluator,
)
from diagpriv.evaluation.incident_003_v3_evidence_v5 import (
    PATH_TEMPLATE_VERSION,
    REQUIREMENT_CONSTRUCTOR_VERSION,
    build_incident_003_v3_evidence_rubric_v5,
)
from diagpriv.evaluation.incident_003_v3_evidence_v5_semantics import (
    EVIDENCE_SEMANTIC_EVALUATOR_VERSION,
    Incident003V3EvidenceSemanticEvaluatorV5,
)
from diagpriv.transformations.provenance import TEMPORAL_SEMANTICS_UNAVAILABLE
from diagpriv.transformations.relative_time_v1 import relative_time_incident


def _path(requirement, modality: str):
    return next(
        path
        for path in requirement.acceptable_paths
        if dict(path.semantic_parameters)["modality"] == modality
    )


def _requirement(rubric, name: str):
    return next(item for item in rubric.requirements if item.name == name)


def _complete(rubric, modality: str, kind: str = "essential") -> tuple[str, ...]:
    result: list[str] = []
    for requirement in rubric.requirements:
        if requirement.kind != kind:
            continue
        result.extend(_path(requirement, modality).evidence_ids)
    return tuple(dict.fromkeys(result))


def _score(incident, citations, *, view=None, semantics=TEMPORAL_SEMANTICS_VERSION):
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    return score_evidence_support_v5(
        tuple(citations),
        incident.model_view() if view is None else view,
        rubric,
        Incident003V3EvidenceSemanticEvaluatorV5(semantics),
    )


def _target_interval_view(
    incident,
    *,
    execution_start: int,
    execution_end: int,
    compensation_start: int,
    compensation_end: int,
) -> ModelView:
    """Set identical visible intervals in structured rows and lifecycle logs."""
    data = deepcopy(incident.model_view().to_dict())
    queried = incident.metadata["target_operation_id"]

    def timestamp(second: int) -> str:
        return f"2042-01-01T00:00:{second:02d}.000Z"

    structured = data["structured_evidence"]
    assert isinstance(structured, dict)
    execution = next(
        row
        for row in structured["execution_observations"]
        if row["operation_id"] == queried
    )
    compensation = next(
        row
        for row in structured["compensation_records"]
        if row["operation_id"] == queried
    )
    execution["started_at"] = timestamp(execution_start)
    execution["completed_at"] = timestamp(execution_end)
    compensation["started_at"] = timestamp(compensation_start)
    compensation["completed_at"] = timestamp(compensation_end)

    event_times = {
        "execution_started": execution_start,
        "execution_completed": execution_end,
        "compensation_started": compensation_start,
        "compensation_completed": compensation_end,
    }
    logs = data["log_evidence"]
    assert isinstance(logs, list)
    for entry in logs:
        attributes = entry["attributes"]
        if attributes["operation_id"] != queried:
            continue
        event_kind = attributes["event_kind"]
        if event_kind in event_times:
            entry["timestamp"] = timestamp(event_times[event_kind])
    return ModelView.from_dict(data)


def _twin_semantics_view(
    incident,
    *,
    execution_completed: int = 10,
    execution_result: str = "success",
    effect_created: int = 12,
    effect_state: str = "active",
    deadline: int = 20,
    compensation_started: int = 30,
    compensation_completed: int = 40,
    compensation_result: str = "completed",
    compensation_state: str = "completed",
    workflow_state: str = "compensated",
) -> ModelView:
    """Set matching twin facts in structured rows and lifecycle logs."""
    data = deepcopy(incident.model_view().to_dict())
    queried = incident.metadata["temporal_twin_operation_id"]

    def timestamp(second: int) -> str:
        return f"2042-01-01T00:00:{second:02d}.000Z"

    structured = data["structured_evidence"]
    assert isinstance(structured, dict)

    def row(source: str):
        return next(
            item for item in structured[source] if item["operation_id"] == queried
        )

    workflow = row("workflow_attempts")
    execution = row("execution_observations")
    effect = row("effect_records")
    compensation = row("compensation_records")
    workflow["deadline_at"] = timestamp(deadline)
    workflow["compensation_state"] = compensation_state
    workflow["workflow_state"] = workflow_state
    execution["completed_at"] = timestamp(execution_completed)
    execution["result"] = execution_result
    effect["created_at"] = timestamp(effect_created)
    effect["state"] = effect_state
    compensation["started_at"] = timestamp(compensation_started)
    compensation["completed_at"] = timestamp(compensation_completed)
    compensation["result"] = compensation_result

    event_times = {
        "execution_completed": execution_completed,
        "effect_recorded": effect_created,
        "deadline_reached": deadline,
        "compensation_started": compensation_started,
        "compensation_completed": compensation_completed,
    }
    logs = data["log_evidence"]
    assert isinstance(logs, list)
    for entry in logs:
        attributes = entry["attributes"]
        if attributes["operation_id"] != queried:
            continue
        event_kind = attributes["event_kind"]
        if event_kind in event_times:
            entry["timestamp"] = timestamp(event_times[event_kind])
        if event_kind == "execution_completed":
            attributes["result"] = execution_result
        elif event_kind == "effect_recorded":
            attributes["state"] = effect_state
        elif event_kind == "compensation_completed":
            attributes["result"] = compensation_result
        elif event_kind == "workflow_state_recorded":
            attributes["workflow_state"] = workflow_state
    return ModelView.from_dict(data)


def _assert_modality_truth(
    incident, requirement_name: str, view: ModelView, expected: bool
) -> None:
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    requirement = _requirement(rubric, requirement_name)
    evaluator = Incident003V3EvidenceSemanticEvaluatorV5(
        TEMPORAL_SEMANTICS_VERSION
    )
    structured_truth = evaluator.evaluate_path(
        _path(requirement, "structured"), view, rubric
    )
    log_truth = evaluator.evaluate_path(_path(requirement, "logs"), view, rubric)
    assert structured_truth is expected
    assert log_truth is expected
    assert structured_truth is log_truth


def test_v5_protocol_is_new_and_v4_requirement_hashes_are_unchanged() -> None:
    assert EVIDENCE_SUPPORT_VERSION == "evidence-support-v5"
    assert RUBRIC_SCHEMA_VERSION == "evidence-rubric-v5"
    assert REQUIREMENT_CONSTRUCTOR_VERSION == (
        "incident-003-v3-evidence-requirements-v3"
    )
    assert PATH_TEMPLATE_VERSION == "incident-003-v3-evidence-path-templates-v1"
    assert EVIDENCE_SEMANTIC_EVALUATOR_VERSION == (
        "incident-003-v3-evidence-semantic-evaluator-v3"
    )
    expected = {
        "target": "b682898351b664929d0a24976e3117e22cfb93adba320423f4d22964174bd52e",
        "temporal_twin": "989419045590e2ce8ce1c14733c83f1a848bfee3ae505c68cfc3385a8aa86c52",
    }
    for role, digest in expected.items():
        incident = generate_incident_003_v3(1200, role)  # type: ignore[arg-type]
        assert evidence_requirement_set_sha256_v3(
            build_incident_003_v3_evidence_rubric(incident)
        ) == digest


@pytest.mark.parametrize("query_role", ("target", "temporal_twin"))
def test_v5_structured_and_log_paths_are_representation_invariant(
    query_role: str,
) -> None:
    incident = generate_incident_003_v3(1200, query_role)  # type: ignore[arg-type]
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    evaluator = Incident003V3EvidenceSemanticEvaluatorV5(TEMPORAL_SEMANTICS_VERSION)
    dual_requirements = tuple(
        requirement
        for requirement in rubric.requirements
        if {dict(path.semantic_parameters)["modality"] for path in requirement.acceptable_paths}
        >= {"structured", "logs"}
    )
    assert dual_requirements
    for requirement in dual_requirements:
        assert evaluator.evaluate_path(
            _path(requirement, "structured"), incident.model_view(), rubric
        )
        assert evaluator.evaluate_path(
            _path(requirement, "logs"), incident.model_view(), rubric
        )

    structured = _score(incident, _complete(rubric, "structured"))
    logs = _score(incident, _complete(rubric, "logs"))
    assert structured.evidence_supported is True
    assert logs.evidence_supported is True
    assert structured.satisfied_essential_requirements == (
        logs.satisfied_essential_requirements
    )
    assert structured.missing_essential_requirements == ()
    assert logs.missing_essential_requirements == ()


@pytest.mark.parametrize("query_role", ("target", "temporal_twin"))
def test_v5_relative_time_preserves_and_ablation_rejects_temporal_proof(
    query_role: str,
) -> None:
    incident = generate_incident_003_v3(1200, query_role)  # type: ignore[arg-type]
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    for modality in ("structured", "logs"):
        citations = _complete(rubric, modality)
        relative = _score(
            incident,
            citations,
            view=relative_time_incident(incident),
            semantics=RELATIVE_TIME_SEMANTICS_VERSION,
        )
        ablated = _score(
            incident,
            citations,
            view=temporally_ablated_model_view(incident),
            semantics=TEMPORAL_SEMANTICS_UNAVAILABLE,
        )
        assert relative.evidence_supported is True
        assert ablated.evidence_supported is False
        assert ablated.essential_requirement_coverage < 1.0
        assert "inconsistent_terminal_workflow_effect_state" in (
            ablated.satisfied_essential_requirements
        )


def test_v5_identity_is_query_bound_and_cross_source_linkage_is_supportive() -> None:
    incident = generate_incident_003_v3(1200, "target")
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    identity = _requirement(rubric, "queried_subject_identity")
    linkage = _requirement(rubric, "queried_cross_source_linkage")
    assert identity.kind == "essential"
    assert linkage.kind == "supportive"
    assert len(identity.acceptable_paths) == 14
    assert {dict(path.semantic_parameters)["modality"] for path in linkage.acceptable_paths} == {
        "structured",
        "logs",
    }
    wrong = build_incident_003_v3_evidence_rubric_v5(
        generate_incident_003_v3(1200, "temporal_twin")
    )
    wrong_id = _path(_requirement(wrong, "queried_subject_identity"), "logs").evidence_ids
    score = _score(incident, wrong_id)
    assert score.evidence_supported is False
    assert score.wrong_subject_citation_count == 1
    assert score.satisfied_essential_requirements == ()


def test_v5_contrast_and_supportive_coverage_do_not_gate_essential_support() -> None:
    incident = generate_incident_003_v3(1200, "target")
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    score = _score(incident, _complete(rubric, "structured"))
    assert score.evidence_supported is True
    assert score.essential_requirement_coverage == 1.0
    assert score.contrast_requirement_coverage == 0.0
    assert score.supportive_requirement_coverage < 1.0


def test_v5_target_negative_citation_sets_fail_closed() -> None:
    incident = generate_incident_003_v3(1200, "target")
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    overlap = _path(_requirement(rubric, "execution_compensation_overlap"), "logs")
    deadline = _path(_requirement(rubric, "deadline_before_original_completion"), "logs")
    compensation = _path(_requirement(rubric, "compensation_after_deadline"), "logs")
    for citations in (
        deadline.evidence_ids[:1],
        deadline.evidence_ids[1:],
        compensation.evidence_ids[1:],
        overlap.evidence_ids[:-1],
        ("EV-NONEXISTENT",),
    ):
        score = _score(incident, citations)
        assert score.evidence_supported is False
    assert _score(incident, ("EV-NONEXISTENT",)).invalid_citation_count == 1


def test_v5_twin_requires_positive_serialized_completion_proof() -> None:
    incident = generate_incident_003_v3(1200, "temporal_twin")
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    serialized = _path(
        _requirement(rubric, "serialized_execution_before_compensation"), "logs"
    )
    assert len(serialized.evidence_ids) == 2
    score = _score(incident, serialized.evidence_ids[:-1])
    assert score.evidence_supported is False
    assert "serialized_execution_before_compensation" in (
        score.missing_essential_requirements
    )


@pytest.mark.parametrize("query_role", ("target", "temporal_twin"))
def test_v5_other_operation_and_safe_control_cannot_support_query(
    query_role: str,
) -> None:
    incident = generate_incident_003_v3(1200, query_role)  # type: ignore[arg-type]
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    other_role = "temporal_twin" if query_role == "target" else "target"
    other_rubric = build_incident_003_v3_evidence_rubric_v5(
        generate_incident_003_v3(1200, other_role)  # type: ignore[arg-type]
    )
    assert _score(incident, _complete(other_rubric, "logs")).evidence_supported is False
    safe = next(
        binding.evidence_ids
        for binding in rubric.subject_bindings
        if binding.binding_id == "safe-control"
    )
    assert _score(incident, safe).evidence_supported is False


def test_v5_correct_subject_with_wrong_temporal_relation_fails() -> None:
    incident = generate_incident_003_v3(1200, "target")
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    data = deepcopy(incident.model_view().to_dict())
    queried = incident.metadata["target_operation_id"]
    workflow = next(
        row
        for row in data["structured_evidence"]["workflow_attempts"]  # type: ignore[index]
        if row["operation_id"] == queried
    )
    execution = next(
        row
        for row in data["structured_evidence"]["execution_observations"]  # type: ignore[index]
        if row["operation_id"] == queried
    )
    execution["completed_at"] = workflow["deadline_at"]
    view = ModelView.from_dict(data)
    score = _score(incident, _complete(rubric, "structured"), view=view)
    assert score.evidence_supported is False
    assert "deadline_before_original_completion" in score.missing_essential_requirements
    assert "execution_compensation_overlap" in score.missing_essential_requirements


@pytest.mark.parametrize(
    ("name", "execution_start", "execution_end", "compensation_start", "compensation_end", "expected"),
    (
        ("genuine_overlap", 10, 30, 20, 40, True),
        ("compensation_fully_before_execution", 20, 30, 0, 10, False),
        ("execution_fully_before_compensation", 0, 10, 20, 30, False),
        ("boundary_touch", 0, 10, 10, 20, False),
        ("malformed_execution_interval", 20, 10, 5, 25, False),
        ("malformed_compensation_interval", 0, 30, 20, 10, False),
    ),
)
def test_v5_overlap_representation_invariance_under_adversarial_intervals(
    name: str,
    execution_start: int,
    execution_end: int,
    compensation_start: int,
    compensation_end: int,
    expected: bool,
) -> None:
    incident = generate_incident_003_v3(1200, "target")
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    requirement = _requirement(rubric, "execution_compensation_overlap")
    view = _target_interval_view(
        incident,
        execution_start=execution_start,
        execution_end=execution_end,
        compensation_start=compensation_start,
        compensation_end=compensation_end,
    )
    evaluator = Incident003V3EvidenceSemanticEvaluatorV5(
        TEMPORAL_SEMANTICS_VERSION
    )
    structured = _path(requirement, "structured")
    logs = _path(requirement, "logs")
    assert len(logs.evidence_ids) == 4
    structured_truth = evaluator.evaluate_path(structured, view, rubric)
    log_truth = evaluator.evaluate_path(logs, view, rubric)
    assert structured_truth is expected, name
    assert log_truth is expected, name
    assert structured_truth is log_truth, name


@pytest.mark.parametrize(
    ("name", "changes", "expected"),
    (
        ("valid_minimal_order", {}, True),
        ("compensation_before_deadline", {"compensation_started": 18}, False),
        ("effect_after_deadline", {"effect_created": 22}, False),
        ("inactive_effect", {"effect_state": "inactive"}, False),
    ),
)
def test_v5_compensation_after_success_modality_equivalence(
    name: str, changes: dict[str, object], expected: bool
) -> None:
    incident = generate_incident_003_v3(1200, "temporal_twin")
    # Completion/result are deliberately non-normative for this requirement.
    view = _twin_semantics_view(
        incident,
        compensation_completed=25,
        compensation_result="failed",
        **changes,
    )
    _assert_modality_truth(
        incident, "compensation_after_committed_success", view, expected
    )


@pytest.mark.parametrize(
    ("name", "changes", "expected"),
    (
        ("success_active_compensated", {}, True),
        ("cancelled_execution", {"execution_result": "cancelled"}, False),
        ("inactive_effect", {"effect_state": "inactive"}, False),
        ("non_compensated_workflow", {"workflow_state": "completed"}, False),
    ),
)
def test_v5_terminal_inconsistency_modality_equivalence(
    name: str, changes: dict[str, object], expected: bool
) -> None:
    incident = generate_incident_003_v3(1200, "temporal_twin")
    # The workflow's compensation-state field is deliberately non-normative:
    # both paths prove only success + active effect + compensated workflow.
    view = _twin_semantics_view(
        incident,
        compensation_state="not_started",
        **changes,
    )
    _assert_modality_truth(
        incident,
        "inconsistent_terminal_workflow_effect_state",
        view,
        expected,
    )


@pytest.mark.parametrize(
    ("name", "changes", "expected"),
    (
        ("valid_serialized_order", {}, True),
        ("completion_after_compensation_start", {"execution_completed": 32}, False),
        ("equality_at_boundary", {"execution_completed": 30}, False),
        ("cancelled_execution", {"execution_result": "cancelled"}, False),
    ),
)
def test_v5_serialized_completion_modality_equivalence(
    name: str, changes: dict[str, object], expected: bool
) -> None:
    incident = generate_incident_003_v3(1200, "temporal_twin")
    view = _twin_semantics_view(incident, **changes)
    _assert_modality_truth(
        incident, "serialized_execution_before_compensation", view, expected
    )


def test_v5_twin_rejects_success_after_deadline_and_compensation() -> None:
    incident = generate_incident_003_v3(1200, "temporal_twin")
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    data = deepcopy(incident.model_view().to_dict())
    queried = incident.metadata["temporal_twin_operation_id"]
    workflow = next(
        row
        for row in data["structured_evidence"]["workflow_attempts"]  # type: ignore[index]
        if row["operation_id"] == queried
    )
    effect = next(
        row
        for row in data["structured_evidence"]["effect_records"]  # type: ignore[index]
        if row["operation_id"] == queried
    )
    effect["created_at"] = workflow["deadline_at"]
    score = _score(
        incident,
        _complete(rubric, "structured"),
        view=ModelView.from_dict(data),
    )
    assert score.evidence_supported is False
    assert "successful_execution_and_active_effect_before_deadline" in (
        score.missing_essential_requirements
    )
    assert "compensation_after_committed_success" in (
        score.missing_essential_requirements
    )


def test_v5_templates_are_case_independent_and_resolve_new_ids() -> None:
    first = build_incident_003_v3_evidence_rubric_v5(
        generate_incident_003_v3(1200, "target")
    )
    second = build_incident_003_v3_evidence_rubric_v5(
        generate_incident_003_v3(1201, "target")
    )
    first_shape = tuple(
        (
            requirement.name,
            requirement.kind,
            tuple(
                (path.path_id, path.semantic_parameters, len(path.evidence_ids))
                for path in requirement.acceptable_paths
            ),
        )
        for requirement in first.requirements
    )
    second_shape = tuple(
        (
            requirement.name,
            requirement.kind,
            tuple(
                (path.path_id, path.semantic_parameters, len(path.evidence_ids))
                for path in requirement.acceptable_paths
            ),
        )
        for requirement in second.requirements
    )
    assert first_shape == second_shape
    assert {
        evidence_id
        for requirement in first.requirements
        for path in requirement.acceptable_paths
        for evidence_id in path.evidence_ids
    }.isdisjoint(
        {
            evidence_id
            for requirement in second.requirements
            for path in requirement.acceptable_paths
            for evidence_id in path.evidence_ids
        }
    )


def test_v5_full_200_construction_audit_passes() -> None:
    report = audit_incident_003_v3_evidence_v5_range()
    assert report["sample_size"] == 200
    assert report["case_count"] == 400
    assert report["failures"] == []
    assert report["passed"] is True
    assert report["provider_calls"] == 0
    for role in ("target", "temporal_twin"):
        assert set(report["roles"][role].values()) == {200}  # type: ignore[union-attr,index]


@pytest.mark.parametrize("seed", (1319, 1299, 1387, 1222))
@pytest.mark.parametrize("query_role", ("target", "temporal_twin"))
def test_v5_frozen_qualification_constructions_pass_benchmark_complete_paths(
    seed: int, query_role: str
) -> None:
    incident = generate_incident_003_v3(seed, query_role)  # type: ignore[arg-type]
    rubric = build_incident_003_v3_evidence_rubric_v5(incident)
    assert _score(incident, _complete(rubric, "structured")).evidence_supported
    assert _score(incident, _complete(rubric, "logs")).evidence_supported


def test_v4_scoring_behavior_remains_available_and_unchanged() -> None:
    incident = generate_incident_003_v3(1200, "target")
    rubric = build_incident_003_v3_evidence_rubric(incident)
    citations = tuple(
        evidence_id
        for binding in rubric.subject_bindings
        for evidence_id in binding.evidence_ids
    )
    score = score_evidence_support_v4(
        citations,
        incident.model_view(),
        rubric,
        Incident003V3EvidenceSemanticEvaluator(TEMPORAL_SEMANTICS_VERSION),
    )
    assert score.evidence_supported is True
    assert score.essential_requirement_coverage == 1.0


STAGE1 = (
    Path(__file__).parents[1]
    / "results/incident_003_v3_raw_paired_sol_development_gpt_5_6_sol_medium.jsonl"
)


@pytest.mark.skipif(not STAGE1.exists(), reason="ignored frozen Stage-1 artifact absent")
def test_v5_secondary_rescore_is_explicit_and_does_not_mutate_history() -> None:
    before = STAGE1.read_bytes()
    assert hashlib.sha256(before).hexdigest() == FROZEN_STAGE1_SHA256
    report = analyze_frozen_stage1_v5(STAGE1)
    assert report["v4_evidence_supported_count"] == 0
    assert report["v5_evidence_supported_count"] == 3
    assert report["frozen_rca_exact_count"] == 7
    assert report["frozen_mechanism_failure_case_ids"] == ["1222:temporal_twin"]
    assert STAGE1.read_bytes() == before
