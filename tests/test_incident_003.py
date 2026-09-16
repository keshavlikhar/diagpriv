from __future__ import annotations

import json
from pathlib import Path

import pytest

from diagbench.audits.incident_003 import (
    TEMPORAL_ABLATION_VERSION,
    audit_incident_003_sample,
    audit_temporal_ablation,
    audit_timestamp_transformations,
    chronological_ids,
    temporally_ablated_model_view,
)
from diagbench.generators.incident_001 import generate_incident_001
from diagbench.generators.incident_002 import generate_incident_002
from diagbench.generators.incident_003 import (
    DEFAULT_SEED,
    FAMILY_ID,
    GENERATOR_VERSION,
    PROTOCOL_VERSION,
    TEMPORAL_TEMPLATES,
    generate_incident_003,
)
from diagbench.schema import Incident
from diagbench.temporal import (
    TEMPORAL_SEMANTICS_VERSION,
    after,
    before,
    equal,
    interval_duration_seconds,
    intervals_overlap,
    ordered_sequence,
    paired_before,
    parse_timestamp,
)
from diagpriv.invariants import evaluate_invariants

ROOT = Path(__file__).parents[1]
FIXTURE = (
    ROOT
    / "diagbench"
    / "incidents"
    / "incident_003_temporal_compensation"
    / "incident.json"
)
PUBLIC_TEST_KEY = bytes(range(32))
PROHIBITED_VISIBLE_PHRASES = {
    "premature compensation",
    "compensation started too early",
    "race condition",
    "overlap caused inconsistency",
    "deadline bug",
    "rollback raced success",
    "invalid transition",
    "state machine bug",
    "incorrect_state_transition",
    "inconsistent_state",
    "ground_truth",
    "diagnostic_invariants",
    "expected_evidence",
    "sensitive_fields",
    "component_mappings",
}


def _invariant_map(incident: Incident, view=None):
    selected = incident.model_view() if view is None else view
    return {result.name: result for result in evaluate_invariants(incident, selected)}


def _rows(incident: Incident, source: str) -> dict[str, dict[str, object]]:
    return {
        str(row["operation_id"]): row
        for row in incident.structured_evidence[source]
    }


def test_temporal_semantics_v1_is_strict_timezone_aware_and_deterministic() -> None:
    assert TEMPORAL_SEMANTICS_VERSION == "temporal-semantics-v1"
    first = "2036-02-03T10:00:00.000Z"
    second = "2036-02-03T10:00:08.500Z"
    equivalent = "2036-02-03T03:00:00.000-07:00"
    assert parse_timestamp(first).tzinfo is not None
    assert before(first, second)
    assert after(second, first)
    assert equal(first, equivalent)
    assert interval_duration_seconds(first, second) == 8.5
    assert ordered_sequence((first, second))
    assert paired_before((first, second, first, second))


@pytest.mark.parametrize(
    "value",
    [
        "2036-02-03T10:00:00",
        "2036-02-03 10:00:00Z",
        "2036-02-30T10:00:00Z",
        "2036-02-03T10:00Z",
        "2036-02-03T10:00:00 UTC",
        "not-a-timestamp",
        "",
    ],
)
def test_temporal_parser_rejects_malformed_or_ambiguous_values(value: str) -> None:
    with pytest.raises(ValueError, match="temporal-semantics-v1"):
        parse_timestamp(value)


def test_overlap_uses_positive_half_open_intervals() -> None:
    assert intervals_overlap(
        "2036-01-01T00:00:00Z",
        "2036-01-01T00:00:10Z",
        "2036-01-01T00:00:05Z",
        "2036-01-01T00:00:12Z",
    )
    assert not intervals_overlap(
        "2036-01-01T00:00:00Z",
        "2036-01-01T00:00:10Z",
        "2036-01-01T00:00:10Z",
        "2036-01-01T00:00:12Z",
    )
    with pytest.raises(ValueError, match="positive-duration"):
        intervals_overlap(
            "2036-01-01T00:00:10Z",
            "2036-01-01T00:00:00Z",
            "2036-01-01T00:00:05Z",
            "2036-01-01T00:00:12Z",
        )


def test_strict_and_nonstrict_sequence_semantics_are_explicit() -> None:
    same = "2036-01-01T00:00:00Z"
    later = "2036-01-01T00:00:01Z"
    assert not ordered_sequence((same, same, later))
    assert ordered_sequence((same, same, later), allow_equal=True)
    with pytest.raises(ValueError, match="even sequence"):
        paired_before((same, later, same))
    with pytest.raises(ValueError, match="precedes"):
        interval_duration_seconds(later, same)


def test_canonical_fixture_equals_generator_and_round_trips() -> None:
    generated = generate_incident_003(DEFAULT_SEED)
    fixture = Incident.load(FIXTURE)
    assert fixture == generated
    assert Incident.from_json(fixture.to_json()) == fixture
    assert fixture.incident_id == FAMILY_ID
    json.dumps(fixture.to_dict())


def test_generation_is_deterministic_and_domain_separated() -> None:
    first = generate_incident_003(1001)
    second = generate_incident_003(1001)
    assert first == second
    assert first.metadata["generator_version"] == GENERATOR_VERSION
    assert first.metadata["protocol_version"] == PROTOCOL_VERSION
    assert first.metadata["benchmark_version"] == "diagbench-v0.4"
    assert first.metadata["generation_domain_sha256"] not in (
        generate_incident_001(1001).to_json(),
        generate_incident_002(1001).to_json(),
    )
    assert first.model_view() != generate_incident_002(1001).model_view()


def test_exact_v2_oracle_and_component_ownership_are_hidden() -> None:
    incident = generate_incident_003(1001)
    assert incident.ground_truth_v2.to_dict() == {
        "observed_outcome": "inconsistent_state",
        "trigger": "timeout_or_deadline",
        "subsequent_action": "compensation_or_rollback",
        "failure_mechanism": "incorrect_state_transition",
        "affected_component": "workflow_orchestrator",
        "logical_operation_repeated": False,
        "explanation": (
            "The workflow orchestrator transitioned into compensation at the deadline "
            "before original execution completed, allowing a later success to coexist "
            "with the compensated workflow state."
        ),
    }
    mappings = {
        mapping.canonical_role: mapping.visible_names
        for mapping in incident.component_mappings
    }
    assert mappings["workflow_orchestrator"] == (
        incident.metadata["orchestrator_alias"],
    )
    assert mappings["operation_executor"] == (incident.metadata["executor_alias"],)
    visible = incident.model_view().to_json().lower()
    assert all(term not in visible for term in PROHIBITED_VISIBLE_PHRASES)


def test_model_view_has_exact_neutral_source_schemas() -> None:
    incident = generate_incident_003(1001)
    evidence = incident.model_view().structured_evidence
    assert set(evidence) == {
        "workflow_attempts",
        "execution_observations",
        "effect_records",
        "compensation_records",
        "dependency_health",
    }
    assert set(evidence["workflow_attempts"][0]) == {
        "evidence_id",
        "operation_id",
        "dispatched_at",
        "deadline_at",
        "compensation_state",
        "workflow_state",
        "orchestrator_alias",
    }
    assert set(evidence["execution_observations"][0]) == {
        "evidence_id",
        "operation_id",
        "started_at",
        "completed_at",
        "result",
        "executor_alias",
    }
    assert set(evidence["effect_records"][0]) == {
        "evidence_id",
        "operation_id",
        "effect_id",
        "created_at",
        "state",
        "executor_alias",
    }
    assert set(evidence["compensation_records"][0]) == {
        "evidence_id",
        "operation_id",
        "compensation_id",
        "started_at",
        "completed_at",
        "result",
        "orchestrator_alias",
    }


def test_invariant_classification_is_fixed_and_complete() -> None:
    incident = generate_incident_003(1001)
    by_name = {item.name: item for item in incident.diagnostic_invariants}
    essential = {
        "target_deadline_precedes_original_completion",
        "target_compensation_after_deadline",
        "target_compensation_precedes_original_completion",
        "target_execution_compensation_overlap",
        "target_success_after_compensation_start",
        "control_completion_precedes_deadline",
        "control_no_compensation",
        "target_event_order",
        "target_inconsistent_state",
        "target_effect_presence",
        "target_execution_success_state",
        "target_and_control_operation_distinctness",
        "target_operation_cross_source_identity",
        "control_execution_success_state",
    }
    supportive = {
        "shared_orchestrator_role",
        "shared_executor_role",
        "dependency_remained_available",
        "successful_controls_bracket_target_chronologically",
        "benign_slow_control_succeeds_before_deadline",
        "benign_slow_control_warning",
        "target_compensation_record_presence",
        "legitimate_compensation_event_order",
        "legitimate_compensation_terminal_state",
        "legitimate_compensation_effect_absence",
        "target_workflow_state_cardinality",
    }
    discardable = {
        "literal_target_dispatch_timestamp",
        "literal_target_deadline_timestamp",
        "exact_target_deadline_interval",
    }
    assert {name for name, item in by_name.items() if item.necessity == "essential"} == essential
    assert {name for name, item in by_name.items() if item.necessity == "supportive"} == supportive
    assert {name for name, item in by_name.items() if item.necessity == "discardable"} == discardable


@pytest.mark.parametrize("seed", range(1000, 1020))
def test_target_and_control_temporal_relations_hold(seed: int) -> None:
    incident = generate_incident_003(seed)
    results = evaluate_invariants(incident, incident.model_view())
    assert all(result.preserved for result in results if result.necessity != "discardable")
    target = str(incident.metadata["target_operation_id"])
    workflow = _rows(incident, "workflow_attempts")[target]
    execution = _rows(incident, "execution_observations")[target]
    compensation = _rows(incident, "compensation_records")[target]
    assert ordered_sequence(
        (
            str(workflow["dispatched_at"]),
            str(execution["started_at"]),
            str(workflow["deadline_at"]),
            str(compensation["started_at"]),
            str(execution["completed_at"]),
        )
    )


@pytest.mark.parametrize("seed", range(1000, 1010))
def test_distractors_and_component_ownership_are_unambiguous(seed: int) -> None:
    incident = generate_incident_003(seed)
    workflows = _rows(incident, "workflow_attempts")
    executions = _rows(incident, "execution_observations")
    effects = _rows(incident, "effect_records")
    compensations = _rows(incident, "compensation_records")
    target = str(incident.metadata["target_operation_id"])
    legitimate = str(incident.metadata["legitimate_compensation_operation_id"])
    slow = str(incident.metadata["slow_control_operation_id"])
    healthy = tuple(str(item) for item in incident.metadata["healthy_control_operation_ids"])
    assert target in effects and target in compensations
    assert executions[target]["result"] == "success"
    assert legitimate in compensations and legitimate not in effects
    assert executions[legitimate]["result"] == "cancelled"
    assert all(workflows[item]["compensation_state"] == "not_started" for item in healthy)
    assert executions[slow]["result"] == "success"
    assert before(str(executions[slow]["completed_at"]), str(workflows[slow]["deadline_at"]))
    warned = {
        str(row["operation_id"])
        for row in incident.structured_evidence["dependency_health"]
        if row["warning"] != "none"
    }
    assert slow in warned and slow != target
    assert {row["orchestrator_alias"] for row in workflows.values()} == {
        incident.metadata["orchestrator_alias"]
    }
    assert {row["executor_alias"] for row in executions.values()} == {
        incident.metadata["executor_alias"]
    }


def test_operation_identity_row_count_and_positions_do_not_name_target() -> None:
    incident = generate_incident_003(1001)
    view = incident.model_view()
    operation_counts: dict[str, int] = {}
    for rows in view.structured_evidence.values():
        for row in rows:
            operation_id = str(row["operation_id"])
            operation_counts[operation_id] = operation_counts.get(operation_id, 0) + 1
    for entry in view.log_evidence:
        operation_id = str(entry.attributes["operation_id"])
        operation_counts[operation_id] = operation_counts.get(operation_id, 0) + 1
    assert len(set(operation_counts.values())) == 1
    assert set(chronological_ids(view)) == set(operation_counts)


@pytest.mark.parametrize("seed", range(1000, 1010))
def test_temporal_ablation_removes_only_the_unique_temporal_cause(seed: int) -> None:
    incident = generate_incident_003(seed)
    report = audit_temporal_ablation(incident)
    assert report["audit_version"] == TEMPORAL_ABLATION_VERSION
    assert report["passed"] is True
    assert report["original_target_has_causal_signature"] is True
    assert report["ablated_causal_signature_operation_count"] == 0
    assert report["non_temporal_evidence_preserved"] is True
    assert report["row_cardinality_preserved"] is True
    assert report["outcome_state_preserved"] is True
    assert report["effect_presence_preserved"] is True
    assert report["compensation_presence_preserved"] is True
    assert report["pre_ablation_profile_matches_required_signature"] is True
    assert report["timestamp_ablation_classification"] == (
        "unavailable_not_preserved"
    )
    assert report["post_ablation_all_applicable_temporal_predicates_unavailable"] is True
    assert report["post_ablation_target_unique_true_temporal_predicates"] == []
    assert report["post_success_compensation_anomaly_status"] == "unavailable"
    assert report["pre_ablation_target_log_order_has_causal_subsequence"] is True
    assert report["post_ablation_operations_with_causal_log_order"] == []
    assert report["chronological_log_row_order_neutralized"] is True
    assert report["timestamp_markers_unique"] is True
    assert report["timestamp_markers_non_parseable"] is True
    assert report["degenerate_temporal_equality_count"] == 0
    assert set(report["neutralized_temporal_invariants"].values()) == {
        "unavailable"
    }


def test_temporal_ablation_preserves_slots_without_creating_a_new_timeline() -> None:
    incident = generate_incident_003(1001)
    original = incident.model_view()
    ablated = temporally_ablated_model_view(incident)
    target = str(incident.metadata["target_operation_id"])
    workflows = {
        str(row["operation_id"]): row
        for row in ablated.structured_evidence["workflow_attempts"]
    }
    executions = {
        str(row["operation_id"]): row
        for row in ablated.structured_evidence["execution_observations"]
    }
    compensations = {
        str(row["operation_id"]): row
        for row in ablated.structured_evidence["compensation_records"]
    }
    target_values = (
        str(executions[target]["completed_at"]),
        str(workflows[target]["deadline_at"]),
        str(compensations[target]["started_at"]),
    )
    assert len(set(target_values)) == 3
    assert all(value.startswith("TA1::") for value in target_values)
    assert {entry.evidence_id for entry in ablated.log_evidence} == {
        entry.evidence_id for entry in original.log_evidence
    }
    assert tuple(entry.evidence_id for entry in ablated.log_evidence) != tuple(
        entry.evidence_id for entry in original.log_evidence
    )
    for value in target_values:
        with pytest.raises(ValueError, match="temporal-semantics-v1"):
            parse_timestamp(value)

    report = audit_temporal_ablation(incident)
    profile = report["post_ablation_target_temporal_profile"]
    assert profile["execution_completion_before_deadline"] == "unavailable"
    assert profile["deadline_before_compensation_start"] == "unavailable"
    assert profile[
        "successful_completion_before_deadline_then_compensation"
    ] == "unavailable"
    assert not any(status == "true" for status in profile.values())


def test_existing_transformations_do_not_preserve_temporal_semantics() -> None:
    incident = generate_incident_003(1001)
    original = incident.model_view()
    report = audit_timestamp_transformations(incident, hmac_key=PUBLIC_TEST_KEY)
    assert report["raw"]["required_temporal_invariants_preserved"] is True
    assert report["raw"]["all_literal_timestamps_removed"] is False
    for condition in (
        "redaction-v1",
        "hmac-v1",
        "tokenization-v1",
        "format-preserving-v1",
    ):
        assert report[condition]["implemented"] is True
        assert report[condition]["all_literal_timestamps_removed"] is True
        assert report[condition]["required_temporal_invariants_preserved"] is False
        assert report[condition]["preserves_cross_field_temporal_semantics_by_design"] is False
    assert report["relative-time-v1"]["implemented"] is True
    assert report["relative-time-v1"]["all_literal_timestamps_removed"] is True
    assert report["relative-time-v1"][
        "required_temporal_invariants_preserved"
    ] is True
    assert report["relative-time-v1"][
        "preserves_cross_field_temporal_semantics_by_design"
    ] is True
    assert incident.model_view() == original


def test_timestamp_annotations_are_explicit_and_exhaustive() -> None:
    incident = generate_incident_003(1001)
    paths = {
        item.path
        for item in incident.sensitive_fields
        if item.classification == "operational_timestamp"
    }
    assert paths == {
        "workflow_attempts.dispatched_at",
        "workflow_attempts.deadline_at",
        "execution_observations.started_at",
        "execution_observations.completed_at",
        "effect_records.created_at",
        "compensation_records.started_at",
        "compensation_records.completed_at",
        "dependency_health.observed_at",
        "logs.timestamp",
    }
    assert all(
        item.policy == "remove_or_pseudonymize"
        for item in incident.sensitive_fields
        if item.classification == "operational_timestamp"
    )


def test_construction_audit_covers_200_development_instances() -> None:
    report = audit_incident_003_sample(range(1000, 1200))
    assert report["sample_size"] == 200
    assert report["check_count"] >= 22
    assert report["failed_check_evaluations"] == 0
    assert report["passed_check_evaluations"] == report["check_evaluations"]
    assert all(check["passed"] is True for check in report["checks"].values())
    assert set(report["template_distribution"]) == set(TEMPORAL_TEMPLATES)
    assert set(report["control_count_distribution"]) == {"4", "5", "6", "7"}
    assert report["templates_vary"] is True
    assert report["control_counts_vary"] is True
    assert report["target_chronological_positions_vary"] is True
    assert report["row_positions_vary"] is True
    assert report["aliases_vary"] is True
    assert report["messages_vary"] is True
    assert report["dates_vary"] is True
    assert report["warning_placement_varies"] is True
    assert report["collision_count"] == 0
    assert report["temporal_ablation_pass_count"] == 200
    assert set(report["compensation_completion_order_distribution"]) == {
        "compensation_completes_before_original",
        "original_completes_before_compensation",
    }


@pytest.mark.parametrize("seed", [999, 2000, 2999, 10_000, 20_000, 20_999])
def test_incident_003_rejects_non_development_seeds_before_generation(seed: int) -> None:
    with pytest.raises(ValueError, match="development-only"):
        generate_incident_003(seed)


def test_incident_001_and_002_canonical_fixtures_remain_unchanged() -> None:
    incident_001_fixture = Incident.load(
        ROOT
        / "diagbench"
        / "incidents"
        / "incident_001_duplicate_payment"
        / "incident.json"
    )
    incident_002_fixture = Incident.load(
        ROOT
        / "diagbench"
        / "incidents"
        / "incident_002_format_defect"
        / "incident.json"
    )
    assert incident_001_fixture == generate_incident_001(1001)
    assert incident_002_fixture == generate_incident_002(1001)
