from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from diagbench.audits.incident_002 import (
    audit_incident_002_sample,
    audit_shape_ablation,
    audit_transformation_expectations,
    shape_ablated_model_view,
)
from diagbench.generators.incident_001 import generate_incident_001
from diagbench.generators.incident_002 import (
    DEFAULT_SEED,
    FAMILY_ID,
    GENERATOR_VERSION,
    SUPPORTED_GENERATION_DEFECTS,
    generate_incident_002,
)
from diagbench.schema import Incident, ModelView
from diagbench.structural import (
    STRUCTURAL_SIGNATURE_VERSION,
    SUPPORTED_STRUCTURAL_DELTAS,
    structural_defect_matches,
    structural_signature,
)
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations.format_preserving_v1 import format_preserving_incident
from diagpriv.transformations.hmac_v1 import hmac_incident
from diagpriv.transformations.redaction_v1 import redact_incident
from diagpriv.transformations.tokenization_v1 import tokenize_incident

ROOT = Path(__file__).parents[1]
FIXTURE = (
    ROOT
    / "diagbench"
    / "incidents"
    / "incident_002_format_defect"
    / "incident.json"
)
PUBLIC_TEST_KEY = bytes(range(32))
DEFECT_SEEDS = {
    "extra_separator": 1000,
    "missing_separator": 1001,
    "case_class_mismatch": 1003,
    "truncation": 1004,
    "leading_zero_loss": 1005,
    "fixed_width_mismatch": 1017,
}
PROHIBITED_VISIBLE_TERMS = {
    "malformed",
    "invalid",
    "format",
    "normalization",
    "truncation",
    "separator defect",
    "format_valid",
    "ground_truth",
    "diagnostic_invariants",
    "expected_evidence",
    "sensitive_fields",
    "latent_valid_reference",
    "defect_class",
    "component_mappings",
}


def _invariants(incident: Incident, view: ModelView) -> dict[str, object]:
    return {result.name: result for result in evaluate_invariants(incident, view)}


def _operation_references(incident: Incident) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for source in ("processing_attempts", "lookup_observations"):
        for row in incident.structured_evidence[source]:
            grouped.setdefault(str(row["operation_id"]), set()).add(
                str(row["external_reference"])
            )
    for entry in incident.log_evidence:
        operation_id = entry.attributes.get("operation_id")
        external_reference = entry.attributes.get("external_reference")
        if operation_id is not None and external_reference is not None:
            grouped.setdefault(str(operation_id), set()).add(str(external_reference))
    return grouped


def test_canonical_fixture_equals_generator_and_round_trips() -> None:
    generated = generate_incident_002(DEFAULT_SEED)
    fixture = Incident.load(FIXTURE)
    assert fixture == generated
    assert Incident.from_json(fixture.to_json()) == fixture
    assert fixture.incident_id == FAMILY_ID
    json.dumps(fixture.to_dict())


def test_generation_is_deterministic_and_domain_separated_from_incident_001() -> None:
    first = generate_incident_002(1001)
    second = generate_incident_002(1001)
    incident_001 = generate_incident_001(1001)
    assert first == second
    assert first.metadata["generator_version"] == GENERATOR_VERSION
    assert first.metadata["family_id"] != incident_001.incident_id
    assert first.metadata["generation_domain_sha256"] not in incident_001.to_json()
    assert first.model_view() != incident_001.model_view()


def test_structural_signature_v1_has_exact_ascii_semantics() -> None:
    assert STRUCTURAL_SIGNATURE_VERSION == "structural-signature-v1"
    assert set(SUPPORTED_STRUCTURAL_DELTAS) == {
        "missing_separator",
        "extra_separator",
        "truncation",
        "fixed_width_mismatch",
        "numeric_run_leading_position_deletion",
        "case_class_mismatch",
    }
    assert structural_signature("AB-1234-xY") == "UU-DDDD-lU"
    assert structural_signature("a_B/90.Z") == "l_U/DD.U"
    assert structural_signature("A 9") == "U D"
    with pytest.raises(ValueError, match="printable ASCII"):
        structural_signature("Å-12")
    with pytest.raises(ValueError, match="printable ASCII"):
        structural_signature("A\n12")


@pytest.mark.parametrize(
    ("defect", "target"),
    [
        ("missing_separator", "AB1234-xY"),
        ("extra_separator", "AB--1234-xY"),
        ("truncation", "AB-1234-x"),
        ("fixed_width_mismatch", "A-1234-xY"),
        ("numeric_run_leading_position_deletion", "AB-234-xY"),
        ("case_class_mismatch", "aB-1234-xY"),
    ],
)
def test_each_supported_defect_is_derived_from_visible_signatures(
    defect: str, target: str
) -> None:
    controls = ("AB-0234-xY", "QZ-0876-aM", "LM-0123-bN")
    assert structural_defect_matches(controls, target, defect)


def test_fixed_width_insertion_is_supported() -> None:
    controls = ("AB-1234-xY", "QZ-9876-aM", "LM-4123-bN")
    assert structural_defect_matches(
        controls, "ABB-1234-xY", "fixed_width_mismatch"
    )


@pytest.mark.parametrize("defect", SUPPORTED_GENERATION_DEFECTS)
def test_generator_reaches_every_approved_defect_and_visible_delta_matches(
    defect: str,
) -> None:
    incident = generate_incident_002(DEFECT_SEEDS[defect])
    assert incident.metadata["defect_class"] == defect
    expected_delta = (
        "numeric_run_leading_position_deletion"
        if defect == "leading_zero_loss"
        else defect
    )
    assert incident.metadata["observable_structural_delta"] == expected_delta
    invariant = next(
        item
        for item in incident.diagnostic_invariants
        if item.name == "target_identifier_defect_signature"
    )
    assert invariant.expected == expected_delta
    result = _invariants(incident, incident.model_view())[
        "target_identifier_defect_signature"
    ]
    assert result.preserved is True
    assert result.status == "genuine_preservation"


@pytest.mark.parametrize("defect", SUPPORTED_GENERATION_DEFECTS)
def test_length_delta_is_conditional_on_length_changing_defects(defect: str) -> None:
    incident = generate_incident_002(DEFECT_SEEDS[defect])
    names = {invariant.name for invariant in incident.diagnostic_invariants}
    if defect == "case_class_mismatch":
        assert "target_identifier_length_delta" not in names
    else:
        assert "target_identifier_length_delta" in names
        result = _invariants(incident, incident.model_view())[
            "target_identifier_length_delta"
        ]
        assert result.preserved is True


def test_defect_invariant_is_not_self_certified_by_hidden_metadata() -> None:
    incident = generate_incident_002(1001)
    data = incident.model_view().to_dict()
    target_id = incident.metadata["target_operation_id"]
    control_id = incident.metadata["control_operation_ids"][0]
    rows = data["structured_evidence"]["processing_attempts"]
    target = next(row for row in rows if row["operation_id"] == target_id)
    control = next(row for row in rows if row["operation_id"] == control_id)
    target["external_reference"] = control["external_reference"]
    changed_view = ModelView.from_dict(data)
    result = _invariants(incident, changed_view)[
        "target_identifier_defect_signature"
    ]
    assert incident.metadata["defect_class"] == "missing_separator"
    assert result.preserved is False


def test_hidden_leading_zero_cause_cannot_satisfy_observable_delta_predicate() -> None:
    incident = generate_incident_002(1005)
    assert incident.metadata["defect_class"] == "leading_zero_loss"
    assert (
        incident.metadata["observable_structural_delta"]
        == "numeric_run_leading_position_deletion"
    )
    invariant = next(
        item
        for item in incident.diagnostic_invariants
        if item.name == "target_identifier_defect_signature"
    )
    values = tuple(str(incident.resolve_reference(item)) for item in invariant.operands)
    assert structural_defect_matches(values[1:], values[0], "leading_zero_loss") is False
    hidden_claim = replace(invariant, expected="leading_zero_loss")
    changed = replace(
        incident,
        diagnostic_invariants=tuple(
            hidden_claim if item.name == hidden_claim.name else item
            for item in incident.diagnostic_invariants
        ),
    )
    assert _invariants(changed, changed.model_view())[
        "target_identifier_defect_signature"
    ].preserved is False


def test_exact_oracle_and_component_ownership_are_hidden() -> None:
    incident = generate_incident_002(1001)
    assert incident.ground_truth_v2.to_dict() == {
        "observed_outcome": "missing_effect",
        "trigger": "malformed_or_unexpected_input",
        "subsequent_action": "no_follow_on_action",
        "failure_mechanism": "validation_or_input_handling_failure",
        "affected_component": "operation_executor",
        "logical_operation_repeated": False,
        "explanation": (
            "The executor did not validate or normalize a structurally unexpected "
            "external reference before exact lookup; the miss created no effect."
        ),
    }
    mappings = {item.canonical_role: item.visible_names for item in incident.component_mappings}
    assert mappings["operation_executor"] == (incident.metadata["executor_alias"],)
    assert mappings["request_ingress"] == (incident.metadata["intake_alias"],)
    serialized = incident.model_view().to_json().lower()
    assert all(term not in serialized for term in PROHIBITED_VISIBLE_TERMS)
    assert set(incident.model_view().structured_evidence) == {
        "processing_attempts",
        "lookup_observations",
        "effect_records",
        "dependency_health",
    }
    assert set(incident.model_view().to_dict()) == {
        "troubleshooting_question",
        "structured_evidence",
        "log_evidence",
    }


def test_question_and_logs_are_cause_neutral() -> None:
    incident = generate_incident_002(1001)
    question = incident.troubleshooting_question.lower()
    messages = " ".join(entry.message.lower() for entry in incident.log_evidence)
    for term in (
        "malformed",
        "invalid",
        "format",
        "normalization",
        "truncation",
        "separator defect",
    ):
        assert term not in question
        assert term not in messages
    assert "format_valid" not in incident.model_view().to_json()


def test_intake_is_opaque_and_executor_owns_exact_lookup() -> None:
    incident = generate_incident_002(1001)
    intake_alias = incident.metadata["intake_alias"]
    executor_alias = incident.metadata["executor_alias"]
    intake_messages = [
        entry.message.lower()
        for entry in incident.log_evidence
        if entry.service == intake_alias
    ]
    assert any("accepted" in message for message in intake_messages)
    assert any("queued" in message for message in intake_messages)
    assert all(
        "external_reference" not in entry.attributes
        for entry in incident.log_evidence
        if entry.service == intake_alias
    )
    assert {
        row["executor_alias"]
        for row in incident.structured_evidence["lookup_observations"]
    } == {executor_alias}
    assert {
        row["match_mode"]
        for row in incident.structured_evidence["lookup_observations"]
    } == {"exact"}


def test_sensitive_fields_are_exactly_external_references_and_cross_source_link() -> None:
    incident = generate_incident_002(1001)
    assert {item.path for item in incident.sensitive_fields} == {
        "processing_attempts.external_reference",
        "lookup_observations.external_reference",
        "logs.external_reference",
    }
    assert all(item.policy == "consistent_pseudonym" for item in incident.sensitive_fields)
    assert all(len(values) == 1 for values in _operation_references(incident).values())


def test_required_invariant_set_and_necessity_classification() -> None:
    incident = generate_incident_002(1001)
    by_name = {item.name: item for item in incident.diagnostic_invariants}
    essential = {
        "healthy_identifier_pattern_consistency",
        "target_identifier_pattern_anomaly",
        "target_identifier_defect_signature",
        "target_identifier_length_delta",
        "target_identifier_cross_source_identity",
        "control_identifier_cross_source_identity",
        "target_lookup_miss_state",
        "control_lookup_success_state",
        "control_effect_presence",
        "target_event_order",
        "target_effect_absence",
        "target_and_control_identifier_distinctness",
    }
    supportive = {
        "controls_bracket_target",
        "shared_executor_role",
        "dependency_remained_available",
        "latency_control_lookup_success",
        "benign_miss_recovery",
        "benign_miss_recovery_order",
        "target_no_follow_on_lookup",
        "effect_record_cardinality",
    }
    discardable = {"literal_external_reference_identity"}
    assert {name for name, item in by_name.items() if item.necessity == "essential"} == essential
    assert {name for name, item in by_name.items() if item.necessity == "supportive"} == supportive
    assert {name for name, item in by_name.items() if item.necessity == "discardable"} == discardable


@pytest.mark.parametrize("seed", range(1000, 1010))
def test_all_non_discardable_invariants_hold_in_raw_generation(seed: int) -> None:
    incident = generate_incident_002(seed)
    results = evaluate_invariants(incident, incident.model_view())
    assert all(result.preserved for result in results if result.necessity != "discardable")
    assert all(
        result.status == "genuine_preservation"
        for result in results
        if result.necessity != "discardable"
    )


@pytest.mark.parametrize("seed", range(1000, 1010))
def test_distractors_prevent_lookup_latency_dependency_and_position_shortcuts(seed: int) -> None:
    incident = generate_incident_002(seed)
    controls = set(incident.metadata["control_operation_ids"])
    target = incident.metadata["target_operation_id"]
    attempts = incident.structured_evidence["processing_attempts"]
    assert len(controls) >= 5
    assert {row["executor_alias"] for row in attempts} == {
        incident.metadata["executor_alias"]
    }
    miss_operations = {
        row["operation_id"]
        for row in incident.structured_evidence["lookup_observations"]
        if row["lookup_result"] == "no_match"
    }
    assert target in miss_operations
    assert len(miss_operations) == 2
    latency = incident.metadata["latency_control_operation_id"]
    assert any(
        row["operation_id"] == latency
        and row["lookup_result"] == "match"
        and row["latency_ms"] >= 650
        for row in incident.structured_evidence["lookup_observations"]
    )
    recovery = incident.metadata["recovery_control_operation_id"]
    recovery_results = {
        row["lookup_result"]
        for row in incident.structured_evidence["lookup_observations"]
        if row["operation_id"] == recovery
    }
    assert recovery_results == {"no_match", "match"}
    assert all(
        row["availability_state"] == "available"
        for row in incident.structured_evidence["dependency_health"]
    )
    assert any(
        row["warning"] != "none"
        for row in incident.structured_evidence["dependency_health"]
    )


def test_target_position_templates_aliases_and_defects_vary() -> None:
    incidents = tuple(generate_incident_002(seed) for seed in range(1000, 1100))
    assert len({item.metadata["target_chronological_position"] for item in incidents}) > 1
    assert len({item.metadata["structural_template_name"] for item in incidents}) == 5
    assert {item.metadata["defect_class"] for item in incidents} == set(
        SUPPORTED_GENERATION_DEFECTS
    )
    assert len({item.metadata["executor_alias"] for item in incidents}) > 1
    assert len({item.metadata["dependency_alias"] for item in incidents}) > 1


def test_evidence_ids_are_unique_and_all_oracle_references_are_well_formed() -> None:
    incident = generate_incident_002(1001)
    evidence_ids = [
        str(row["evidence_id"])
        for rows in incident.structured_evidence.values()
        for row in rows
    ] + [entry.evidence_id for entry in incident.log_evidence]
    assert len(evidence_ids) == len(set(evidence_ids))
    for invariant in incident.diagnostic_invariants:
        if invariant.relation == "match_count":
            continue
        for reference in invariant.operands:
            incident.resolve_reference(reference)
    for expected in incident.expected_evidence:
        for reference in expected.references:
            incident.resolve_reference(reference)


def test_pattern_collapse_is_reported_separately_from_predicate_truth() -> None:
    incident = generate_incident_002(1001)
    raw = _invariants(incident, incident.model_view())[
        "healthy_identifier_pattern_consistency"
    ]
    redacted = _invariants(incident, redact_incident(incident))[
        "healthy_identifier_pattern_consistency"
    ]
    tokenized = _invariants(incident, tokenize_incident(incident))[
        "healthy_identifier_pattern_consistency"
    ]
    formatted = _invariants(incident, format_preserving_incident(incident))[
        "healthy_identifier_pattern_consistency"
    ]
    assert (raw.preserved, raw.status) == (True, "genuine_preservation")
    assert (redacted.preserved, redacted.status) == (
        True,
        "degenerate_pattern_collapse",
    )
    assert (tokenized.preserved, tokenized.status) == (
        True,
        "degenerate_pattern_collapse",
    )
    assert (formatted.preserved, formatted.status) == (
        True,
        "genuine_preservation",
    )


@pytest.mark.parametrize("seed", tuple(DEFECT_SEEDS.values()))
def test_transformation_expectation_matrix(seed: int) -> None:
    report = audit_transformation_expectations(
        generate_incident_002(seed), hmac_key=PUBLIC_TEST_KEY
    )
    assert all(item["expectation_met"] is True for item in report.values())
    assert report["raw"]["structural_evidence_available"] is True
    assert report["redaction-v1"]["relationships_preserved"] is False
    assert report["hmac-v1"]["relationships_preserved"] is True
    assert report["tokenization-v1"]["structural_evidence_available"] is False
    assert report["format-preserving-v1"]["structural_evidence_available"] is True


def test_transformations_remove_plaintext_and_do_not_mutate_raw_or_prior_family() -> None:
    incident = generate_incident_002(1001)
    original = incident.model_view()
    prior = generate_incident_001(1001)
    prior_json = prior.to_json()
    transformed = (
        redact_incident(incident),
        hmac_incident(incident, key=PUBLIC_TEST_KEY),
        tokenize_incident(incident),
        format_preserving_incident(incident),
    )
    plaintext = {
        str(row["external_reference"])
        for source in ("processing_attempts", "lookup_observations")
        for row in incident.structured_evidence[source]
    }
    assert all(
        value not in view.to_json()
        for view in transformed
        for value in plaintext
    )
    assert incident.model_view() == original
    assert generate_incident_001(1001).to_json() == prior_json


@pytest.mark.parametrize("seed", range(1000, 1010))
def test_shape_ablation_removes_unique_structural_cause_clue(seed: int) -> None:
    incident = generate_incident_002(seed)
    report = audit_shape_ablation(incident)
    assert report["passed"] is True
    assert report["target_was_unique_structural_outlier"] is True
    assert report["all_external_references_share_one_ablated_signature"] is True
    assert report["lookup_miss_operation_count"] == 2
    assert report["format_cause_mechanically_unique_after_ablation"] is False
    ablated = shape_ablated_model_view(incident)
    assert ablated.troubleshooting_question == incident.troubleshooting_question
    assert {
        structural_signature(str(row["external_reference"]))
        for row in ablated.structured_evidence["processing_attempts"]
    } == {"UUU_DDDDDD"}
    raw = incident.model_view().to_dict()
    changed = ablated.to_dict()
    for source in ("processing_attempts", "lookup_observations"):
        for before, after in zip(
            raw["structured_evidence"][source],
            changed["structured_evidence"][source],
            strict=True,
        ):
            assert {
                key: value for key, value in before.items() if key != "external_reference"
            } == {
                key: value for key, value in after.items() if key != "external_reference"
            }


def test_construction_audit_covers_substantial_development_sample() -> None:
    report = audit_incident_002_sample(range(1000, 1200))
    assert report["sample_size"] == 200
    assert all(check["passed"] is True for check in report["checks"].values())
    assert set(report["defect_counts"]) == set(SUPPORTED_GENERATION_DEFECTS)
    assert set(report["observable_delta_counts"]) == set(SUPPORTED_STRUCTURAL_DELTAS)
    assert len(report["template_counts"]) == 5
    assert report["defects_vary"] is True
    assert report["templates_vary"] is True
    assert report["target_positions_vary"] is True
    assert report["row_order_varies"] is True
    assert report["aliases_vary"] is True
    assert report["messages_vary"] is True


@pytest.mark.parametrize("seed", [999, 2000, 2999, 10_000, 20_000, 20_999])
def test_incident_002_rejects_non_development_seeds_before_generation(seed: int) -> None:
    with pytest.raises(ValueError, match="development-only"):
        generate_incident_002(seed)


def test_match_count_handles_zero_rows_without_weakening_reference_resolution() -> None:
    incident = generate_incident_002(1001)
    target_absence = next(
        item
        for item in incident.diagnostic_invariants
        if item.name == "target_effect_absence"
    )
    assert target_absence.relation == "match_count"
    result = _invariants(incident, incident.model_view())["target_effect_absence"]
    assert result.preserved is True
    with pytest.raises(ValueError, match="found 0 matches"):
        incident.resolve_reference(target_absence.operands[0])


def test_model_view_remains_a_defensive_copy() -> None:
    incident = generate_incident_002(1001)
    view = incident.model_view()
    view.structured_evidence["processing_attempts"][0]["final_state"] = "changed"
    assert incident.structured_evidence["processing_attempts"][0]["final_state"] != "changed"


def test_changing_hidden_defect_label_does_not_change_model_view() -> None:
    incident = generate_incident_002(1001)
    metadata = dict(incident.metadata)
    metadata["defect_class"] = "case_class_mismatch"
    changed = replace(incident, metadata=metadata)
    assert changed.model_view() == incident.model_view()
