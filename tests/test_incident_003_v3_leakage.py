from __future__ import annotations

import pytest

from diagbench.audits.incident_003_v3_leakage import (
    audit_incident_003_v3_leakage_range,
)
from diagbench.generators.incident_003_v3 import AUDIT_SEEDS


@pytest.fixture(scope="module")
def leakage_report() -> dict:
    return audit_incident_003_v3_leakage_range(AUDIT_SEEDS)


def test_v3_literal_identifiers_have_no_perfect_pattern_separator(
    leakage_report: dict,
) -> None:
    identifiers = leakage_report["identifier_generation"]
    assert identifiers["perfect_separators"] == []
    assert identifiers["evidence_id_separators"] == []
    assert identifiers["generation_order"]["ordinal_encoded_in_identifier"] is False


def test_v3_structured_and_ablated_positions_are_not_perfect_separators(
    leakage_report: dict,
) -> None:
    positions = leakage_report["target_position"]
    assert not any(
        item.startswith("structured_evidence.")
        for item in positions["perfect_separators"]
    )
    assert positions["ablated_log_perfect_separators"] == []


def test_v3_role_neutral_raw_log_anchors_remove_position_blocker(
    leakage_report: dict,
) -> None:
    distributions = leakage_report["target_position"][
        "raw_log_group_ordinal_distributions"
    ]
    assert all(set(distributions[role]) == {"0", "1", "2"} for role in distributions)
    assert leakage_report["target_position"]["perfect_separators"] == []
    assert (
        leakage_report["acceptance_gates"][
            "no_queried_subject_positional_perfect_separator"
        ]
        is True
    )
    assert leakage_report["acceptance_gates"][
        "raw_log_role_position_not_perfect_separator"
    ] is True


def test_v3_canonical_renaming_and_rendered_isomorphism_pass_200_of_200(
    leakage_report: dict,
) -> None:
    assert leakage_report["canonical_renaming"]["passed_count"] == 200
    assert leakage_report["rendered_nontemporal_isomorphism"] == {
        "comparison_view": "temporal-ablation-v1",
        "preserves_model_visible_row_order": True,
        "passed_count": 200,
        "pair_count": 200,
    }


def test_v3_id_and_row_permutations_preserve_oracle_and_evidence(
    leakage_report: dict,
) -> None:
    assert leakage_report["id_permutation"]["passed_count"] == 200
    assert leakage_report["row_permutation"]["passed_count"] == 200


def test_v3_question_wording_and_queried_position_are_neutral(
    leakage_report: dict,
) -> None:
    question = leakage_report["question_identity_position"]
    assert question["normalized_template_passed_count"] == 200
    assert question["position_perfect_separators"] == []


def test_v3_paired_queries_are_balanced_and_share_serialized_evidence(
    leakage_report: dict,
) -> None:
    paired = leakage_report["paired_queries"]
    assert paired["target_query_count"] == 200
    assert paired["twin_query_count"] == 200
    assert paired["balanced_population_size"] == 400
    assert paired["underlying_evidence_equal_count"] == 200
    assert paired["serialized_evidence_equal_count"] == 200
    assert paired["normalized_question_equal_count"] == 200
    assert paired["only_mechanism_dimension_differs_count"] == 200
    assert paired["conflicting_mechanism_oracle_count"] == 200


def test_v3_both_query_roles_have_raw_and_relative_evidence_support(
    leakage_report: dict,
) -> None:
    paired = leakage_report["paired_queries"]
    assert paired["raw_target_evidence_supported_count"] == 200
    assert paired["raw_twin_evidence_supported_count"] == 200
    assert paired["relative_target_evidence_supported_count"] == 200
    assert paired["relative_twin_evidence_supported_count"] == 200
    assert paired["ablated_target_evidence_unsupported_count"] == 200
    assert paired["ablated_twin_evidence_unsupported_count"] == 200


def test_v3_ablated_query_pair_isomorphic_with_conflicting_oracles(
    leakage_report: dict,
) -> None:
    paired = leakage_report["paired_queries"]
    assert paired["ablated_query_pair_isomorphism_count"] == 200
    assert leakage_report["acceptance_gates"][
        "ablated_query_pair_rendered_inputs_isomorphic"
    ] is True
    assert leakage_report["acceptance_gates"][
        "ablated_pair_has_conflicting_mechanism_oracles"
    ] is True


def test_v3_hidden_metadata_is_absent_and_ta1_adds_no_separator(
    leakage_report: dict,
) -> None:
    assert leakage_report["hidden_metadata_exclusion"]["passed_count"] == 200
    assert leakage_report["temporal_ablation_marker"][
        "structure_role_neutral_count"
    ] == 200
    assert leakage_report["temporal_ablation_marker"]["perfect_separators"] == []


def test_v3_existing_25_acceptance_gates_still_pass(
    leakage_report: dict,
) -> None:
    assert leakage_report["existing_audit"] == {
        "acceptance_gate_count": 25,
        "passed": True,
    }
    assert leakage_report["acceptance_gates"][
        "existing_25_acceptance_gates_pass"
    ] is True


def test_v3_all_updated_acceptance_gates_pass(leakage_report: dict) -> None:
    assert leakage_report["failed_acceptance_gates"] == []
    assert leakage_report["passed"] is True
    assert leakage_report["readiness"] == "READY TO COMMIT"


@pytest.mark.parametrize("seeds", ((), (1199,), (1400,), (2000,), (20000,)))
def test_v3_leakage_audit_rejects_non_audit_and_protected_seeds(
    seeds: tuple[int, ...],
) -> None:
    with pytest.raises(ValueError, match="1200-1399"):
        audit_incident_003_v3_leakage_range(seeds)
