from __future__ import annotations

import pytest

from diagbench.audits.incident_003_cue_audit import (
    CUE_AUDIT_VERSION,
    audit_incident_003_cue_range,
    audit_incident_003_cues,
)
from diagbench.generators.incident_003_v2 import generate_incident_003_v2


FROZEN_OBSERVED_SEEDS = (1019, 1020, 1021, 1022, 1023, 1025, 1026, 1028)


def test_single_incident_cue_audit_is_deterministic_and_non_mutating() -> None:
    incident = generate_incident_003_v2(1019)
    before = incident.model_view()
    first = audit_incident_003_cues(incident)
    second = audit_incident_003_cues(incident)

    assert first == second
    assert incident.model_view() == before
    assert first["audit_version"] == CUE_AUDIT_VERSION
    assert first["temporal_semantics"] == "unavailable"
    assert all(not collisions for collisions in first["signature_collisions"].values())


def test_frozen_observed_targets_share_the_same_surviving_shortcut_cues() -> None:
    for seed in FROZEN_OBSERVED_SEEDS:
        profile = audit_incident_003_cues(generate_incident_003_v2(seed))[
            "target_profile"
        ]
        assert profile["explicit_deadline_lexical_cue"] is True
        assert profile["deadline_schema_name_cue"] is True
        assert profile["compensation_record_cue"] is True
        assert profile["compensation_lexical_cue"] is True
        assert profile["successful_execution_cue"] is True
        assert profile["active_effect_cue"] is True
        assert profile["compensated_workflow_cue"] is True
        assert profile["terminal_state_contradiction"] is True
        assert profile["orchestrator_role_cue"] is True
        assert profile["executor_role_cue"] is True
        assert profile["cancellation_or_fencing_lexical_cue"] is False
        assert profile["late_or_overlap_lexical_cue"] is False
        assert profile["temporal_relation_available"] is False


def test_200_instance_frequency_and_separability_audit_is_frozen() -> None:
    report = audit_incident_003_cue_range(range(1000, 1200))
    assert report["sample_size"] == 200
    assert report["seed_min"] == 1000
    assert report["seed_max"] == 1199
    assert report["provider_calls"] == 0
    assert report["role_counts"] == {
        "target": 200,
        "healthy": 1076,
        "legitimate": 200,
        "benign_slow": 200,
    }

    frequencies = report["cue_frequency"]
    target_always = {
        "explicit_deadline_lexical_cue",
        "deadline_schema_name_cue",
        "compensation_record_cue",
        "compensation_lexical_cue",
        "successful_execution_cue",
        "active_effect_cue",
        "compensated_workflow_cue",
        "terminal_state_contradiction",
        "orchestrator_role_cue",
        "executor_role_cue",
    }
    for cue in target_always:
        assert frequencies[cue]["target"] == {
            "count": 200,
            "total": 200,
            "rate": 1.0,
        }
    assert frequencies["temporal_relation_available"]["target"]["count"] == 0
    assert frequencies["late_or_overlap_lexical_cue"]["target"]["count"] == 0
    assert frequencies["cancellation_or_fencing_lexical_cue"]["target"]["count"] == 0

    assert frequencies["terminal_state_contradiction"]["healthy"]["count"] == 0
    assert frequencies["terminal_state_contradiction"]["legitimate"]["count"] == 0
    for result in report["counterfactual_separability"].values():
        assert result["perfectly_separable"] is True
        assert result["target_control_collision_count"] == 0
        assert result["target_operations_with_colliding_signature"] == 0


def test_message_and_schema_leakage_inventory_is_exhaustive_for_generated_views() -> None:
    report = audit_incident_003_cue_range(range(1000, 1200))
    messages = {entry["event_kind"]: entry for entry in report["message_inventory"]}
    assert set(messages) == {
        "compensation_completed",
        "compensation_started",
        "deadline_reached",
        "dependency_observed",
        "dispatch_recorded",
        "effect_recorded",
        "execution_completed",
        "execution_progress",
        "execution_started",
        "workflow_checkpoint",
        "workflow_state_recorded",
    }
    assert messages["deadline_reached"]["leaked_concepts"] == ["deadline"]
    assert messages["compensation_started"]["leaked_concepts"] == [
        "compensation_or_rollback"
    ]
    assert not any(
        entry["explicitly_implies_late_overlap_or_control_failure"]
        for entry in messages.values()
    )

    schema = {entry["path"]: entry for entry in report["schema_inventory"]}
    assert len(schema) == 54
    assert schema["troubleshooting_question"]["classification"] == "strong cue"
    assert schema["structured_evidence.workflow_attempts.deadline_at"][
        "classification"
    ] == "strong cue"
    assert schema["structured_evidence.workflow_attempts.orchestrator_alias"][
        "classification"
    ] == "near-label leakage"
    assert schema["log_evidence.timestamp"]["representative_values"] == [
        "<opaque-temporal-marker>"
    ]


@pytest.mark.parametrize("seeds", [(), (999,), (1200,), (1000, 1200)])
def test_cue_audit_rejects_empty_or_protected_seed_ranges(
    seeds: tuple[int, ...],
) -> None:
    with pytest.raises(ValueError, match="development seeds 1000-1199"):
        audit_incident_003_cue_range(seeds)
