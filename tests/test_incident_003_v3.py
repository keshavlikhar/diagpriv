from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess

import pytest

from diagbench.audits.incident_003 import temporally_ablated_model_view
from diagbench.audits.incident_003_v3 import (
    audit_incident_003_v3,
    audit_incident_003_v3_range,
    non_temporal_operation_projection,
)
from diagbench.generators.incident_003_v2 import generate_incident_003_v2
from diagbench.generators.incident_003_v3 import (
    ANCHOR_ALLOCATION_VERSION,
    AUDIT_SEEDS,
    FAMILY_ID,
    GENERATOR_VERSION,
    PROTOCOL_VERSION,
    RAW_LOG_SERIALIZATION_CONTRACT,
    generate_incident_003_v3,
    incident_003_v3_query_case,
)
from diagbench.relative_time import RELATIVE_TIME_SEMANTICS_VERSION
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION, parse_timestamp
from diagpriv.evaluation.evidence_support_v4 import score_evidence_support_v4
from diagpriv.evaluation.incident_003_v3_evidence import (
    REQUIREMENT_CONSTRUCTOR_VERSION,
    build_incident_003_v3_evidence_rubric,
)
from diagpriv.evaluation.incident_003_v3_evidence_semantics import (
    Incident003V3EvidenceSemanticEvaluator,
)
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations.provenance import TEMPORAL_SEMANTICS_UNAVAILABLE
from diagpriv.transformations.relative_time_v1 import relative_time_incident

ROOT = Path(__file__).parents[1]
V2_SEED_1019_INCIDENT_SHA256 = (
    "d5af965927b73cc401a5ac99be03563810216606860a7366c60e4fca4ac6ad44"
)
V2_SEED_1019_MODEL_VIEW_SHA256 = (
    "f0900f518905fb490d07a74877badb95e52f5779110c75bc2de439f22549a3bb"
)


def test_incident_003_v2_historical_generation_is_unchanged() -> None:
    incident = generate_incident_003_v2(1019)
    assert hashlib.sha256(incident.to_json(indent=None).encode()).hexdigest() == (
        V2_SEED_1019_INCIDENT_SHA256
    )
    assert hashlib.sha256(
        incident.model_view().to_json(indent=None).encode()
    ).hexdigest() == V2_SEED_1019_MODEL_VIEW_SHA256


def test_v3_generation_is_versioned_deterministic_and_oracle_hidden() -> None:
    first = generate_incident_003_v3(1200)
    second = generate_incident_003_v3(1200)
    assert first == second
    assert first.incident_id == FAMILY_ID
    assert first.metadata["generator_version"] == GENERATOR_VERSION
    assert first.metadata["protocol_version"] == PROTOCOL_VERSION
    assert first.metadata["query_role"] == "target"
    assert first.metadata["queried_operation_id"] == first.metadata["target_operation_id"]
    model_json = first.model_view().to_json()
    assert "incorrect_concurrency_control" not in model_json
    assert "target_mechanism" not in model_json
    assert "temporal_twin_mechanism" not in model_json
    assert "ground_truth" not in model_json


def test_v3_temporal_twin_matches_non_temporal_projection_exactly() -> None:
    incident = generate_incident_003_v3(1200)
    view = temporally_ablated_model_view(incident)
    target = str(incident.metadata["target_operation_id"])
    twin = str(incident.metadata["temporal_twin_operation_id"])
    assert non_temporal_operation_projection(
        view, target
    ) == non_temporal_operation_projection(view, twin)


def test_v3_question_is_neutral_and_subject_specific_without_cause_leakage() -> None:
    incident = generate_incident_003_v3(1200)
    question = incident.troubleshooting_question
    assert str(incident.metadata["target_operation_id"]) in question
    assert "root cause" in question.lower()
    for leaked in (
        "inconsistent",
        "deadline",
        "overlap",
        "concurrency",
        "compensation",
        "orchestrator",
    ):
        assert leaked not in question.lower()


def test_v3_target_and_controls_pass_raw_and_relative_temporal_invariants() -> None:
    incident = generate_incident_003_v3(1200)
    raw = evaluate_invariants(
        incident,
        incident.model_view(),
        temporal_semantics_version=TEMPORAL_SEMANTICS_VERSION,
    )
    relative = evaluate_invariants(
        incident,
        relative_time_incident(incident),
        temporal_semantics_version=RELATIVE_TIME_SEMANTICS_VERSION,
    )
    assert raw and all(item.preserved for item in raw)
    assert relative and all(
        item.preserved and item.status == "genuine_preservation"
        for item in relative
    )


def test_v3_pair_balances_records_events_roles_messages_and_question() -> None:
    report = audit_incident_003_v3(generate_incident_003_v3(1200))
    assert report["projection_equal"] is True
    assert all(report["signature_collisions"].values())
    assert report["single_feature_target_only"] == []
    assert report["single_feature_twin_only"] == []
    assert report["conjunction_separators"] == {"2": [], "3": [], "4": []}
    assert report["message_audit"]["passed"] is True
    assert report["message_audit"]["banned_relation_terms"] == []
    assert report["schema_audit"]["passed"] is True
    assert report["schema_audit"]["near_label_leakage"] == []


def test_v3_relative_time_preserves_and_ablation_destroys_temporal_semantics() -> None:
    report = audit_incident_003_v3(generate_incident_003_v3(1200))
    assert report["relative_time_pairwise_checks"] == {
        "equality": True,
        "strict_ordering": True,
        "duration": True,
    }
    assert report["temporal_ablation"] == {
        "timestamp_count": 51,
        "all_unavailable": True,
        "all_unique": True,
        "chronological_log_order_removed": True,
    }
    assert report["checks"]["raw_target_overlaps_twin_does_not"] is True
    assert report["checks"]["relative_target_overlaps_twin_does_not"] is True
    assert report["checks"]["ablation_non_temporal_pair_collision"] is True


def test_v3_evidence_v4_is_satisfiable_raw_and_relative_but_not_ablated() -> None:
    incident = generate_incident_003_v3(1200)
    report = audit_incident_003_v3(incident)["evidence_support_v4"]
    assert REQUIREMENT_CONSTRUCTOR_VERSION == (
        "incident-003-v3-evidence-requirements-v2"
    )
    assert report["raw"]["evidence_supported"] is True
    assert report["raw"]["essential_requirement_coverage"] == 1.0
    assert report["relative-time-v1"]["evidence_supported"] is True
    assert report["relative-time-v1"]["essential_requirement_coverage"] == 1.0
    assert report["temporal-ablation-v1"]["evidence_supported"] is False
    assert report["temporal-ablation-v1"]["temporal_requirements_missing"] is True


def test_v3_evidence_rubric_fails_temporal_requirements_closed_when_unavailable() -> None:
    incident = generate_incident_003_v3(1200)
    rubric = build_incident_003_v3_evidence_rubric(incident)
    cited = tuple(
        evidence_id
        for binding in rubric.subject_bindings
        for evidence_id in binding.evidence_ids
    )
    score = score_evidence_support_v4(
        cited,
        temporally_ablated_model_view(incident),
        rubric,
        Incident003V3EvidenceSemanticEvaluator(TEMPORAL_SEMANTICS_UNAVAILABLE),
    )
    assert score.evidence_supported is False
    assert "execution_compensation_overlap" in score.missing_essential_requirements


def test_v3_200_instance_causal_isolation_audit_passes_all_gates() -> None:
    report = audit_incident_003_v3_range(AUDIT_SEEDS)
    assert report["sample_size"] == 200
    assert report["exact_projection_match_count"] == 200
    assert report["signature_collision_counts"] == {
        "full_categorical_signature": 200,
        "terminal_state_signature": 200,
        "record_type_signature": 200,
        "message_event_signature": 200,
    }
    assert report["single_feature_separator_count"] == 0
    assert report["conjunction_separator_counts"] == {"2": 0, "3": 0, "4": 0}
    assert report["failed_seeds"] == []
    assert report["passed"] is True
    assert report["provider_calls"] == 0


@pytest.mark.parametrize("seed", (999, 2000, 2001, 2999, 20000, 20999))
def test_v3_generator_rejects_non_development_and_protected_seeds(seed: int) -> None:
    with pytest.raises(ValueError, match="development-only"):
        generate_incident_003_v3(seed)


@pytest.mark.parametrize("seeds", ((), (1199,), (1400,), (2000,), (20000,)))
def test_v3_audit_rejects_non_audit_and_protected_seed_ranges(
    seeds: tuple[int, ...],
) -> None:
    with pytest.raises(ValueError, match="1200-1399"):
        audit_incident_003_v3_range(seeds)


def test_v3_preparation_has_only_reviewed_configs_and_no_tracked_result() -> None:
    assert {
        path.name for path in (ROOT / "experiments").glob("*incident_003*v3*")
    } == {
        "incident_003_v3_raw_paired_sol_development.toml",
        "incident_003_v3_relative_time_v1_paired_sol_development.toml",
        "incident_003_v3_relative_time_v1_paired_sol_development_v5.toml",
        "incident_003_v3_temporal_ablation_v1_paired_sol_development.toml",
    }
    artifacts = list((ROOT / "results").glob("*incident_003*v3*"))
    # A locally completed historical or future observation may exist; the
    # invariant is that none is ever tracked, not that local results are absent.
    for path in artifacts:
        assert subprocess.run(
            ["git", "check-ignore", "-q", str(path)], cwd=ROOT, check=False
        ).returncode == 0
        assert not subprocess.check_output(
            ["git", "ls-files", "--", str(path)], cwd=ROOT
        ).strip()


def test_all_v3_raw_timestamps_are_strictly_parseable() -> None:
    incident = generate_incident_003_v3(1200)
    for annotation in incident.sensitive_fields:
        if annotation.classification != "operational_timestamp":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        if source == "logs":
            values = [entry.timestamp for entry in incident.log_evidence]
        else:
            values = [row[field] for row in incident.structured_evidence[source]]
        assert all(parse_timestamp(str(value)) for value in values)


def test_v3_raw_logs_remain_globally_chronological_with_role_neutral_anchors() -> None:
    incident = generate_incident_003_v3(1200)
    timestamps = tuple(parse_timestamp(entry.timestamp) for entry in incident.log_evidence)
    assert timestamps == tuple(sorted(timestamps))
    assert incident.metadata["raw_log_serialization_contract"] == (
        RAW_LOG_SERIALIZATION_CONTRACT
    )
    assert incident.metadata["anchor_allocation_version"] == ANCHOR_ALLOCATION_VERSION


def test_v3_paired_queries_share_evidence_order_and_change_only_mechanism() -> None:
    target = generate_incident_003_v3(1200, "target")
    twin = generate_incident_003_v3(1200, "temporal_twin")
    assert target.structured_evidence == twin.structured_evidence
    assert target.log_evidence == twin.log_evidence
    assert target.metadata["query_role"] == "target"
    assert twin.metadata["query_role"] == "temporal_twin"
    assert target.metadata["queried_operation_id"] == target.metadata["target_operation_id"]
    assert twin.metadata["queried_operation_id"] == twin.metadata[
        "temporal_twin_operation_id"
    ]
    assert target.ground_truth_v3.failure_mechanism == (
        "incorrect_concurrency_control"
    )
    assert twin.ground_truth_v3.failure_mechanism == "incorrect_state_transition"
    for field in (
        "observed_outcome",
        "trigger",
        "subsequent_action",
        "affected_component",
        "logical_operation_repeated",
    ):
        assert getattr(target.ground_truth_v3, field) == getattr(
            twin.ground_truth_v3, field
        )


def test_v3_twin_query_has_positive_raw_and_relative_evidence_but_not_ablated() -> None:
    incident = generate_incident_003_v3(1200, "temporal_twin")
    rubric = build_incident_003_v3_evidence_rubric(incident)
    cited = tuple(
        evidence_id
        for binding in rubric.subject_bindings
        for evidence_id in binding.evidence_ids
    )
    expected_essentials = {
        "queried_identity_linkage",
        "successful_effect_before_deadline",
        "compensation_after_committed_success",
        "serialized_execution_before_compensation",
        "inconsistent_terminal_workflow_effect_state",
    }
    assert {
        requirement.name
        for requirement in rubric.requirements
        if requirement.kind == "essential"
    } == expected_essentials
    raw = score_evidence_support_v4(
        cited,
        incident.model_view(),
        rubric,
        Incident003V3EvidenceSemanticEvaluator(TEMPORAL_SEMANTICS_VERSION),
    )
    relative = score_evidence_support_v4(
        cited,
        relative_time_incident(incident),
        rubric,
        Incident003V3EvidenceSemanticEvaluator(RELATIVE_TIME_SEMANTICS_VERSION),
    )
    ablated = score_evidence_support_v4(
        cited,
        temporally_ablated_model_view(incident),
        rubric,
        Incident003V3EvidenceSemanticEvaluator(TEMPORAL_SEMANTICS_UNAVAILABLE),
    )
    assert raw.evidence_supported is True
    assert relative.evidence_supported is True
    assert ablated.evidence_supported is False
    assert set(ablated.missing_essential_requirements) == {
        "successful_effect_before_deadline",
        "compensation_after_committed_success",
        "serialized_execution_before_compensation",
    }


def test_v3_query_case_rejects_unknown_role() -> None:
    with pytest.raises(ValueError, match="query role"):
        incident_003_v3_query_case(generate_incident_003_v3(1200), "safe_control")  # type: ignore[arg-type]
