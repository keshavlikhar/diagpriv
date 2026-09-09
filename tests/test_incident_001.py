from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re

from diagbench.generators.incident_001 import (
    DEFAULT_SEED,
    generate_incident_001,
    seed_split,
)
from diagbench.schema import Incident, ModelView

FIXTURE = (
    Path(__file__).parents[1]
    / "diagbench"
    / "incidents"
    / "incident_001_duplicate_payment"
    / "incident.json"
)
NEUTRAL_ID = re.compile(r"SYN-(?:CUST|ACCT|PAY|REQ|EVD|TRN)-\d{8}")
PROHIBITED_MODEL_PHRASES = {
    "duplicate",
    "idempotency",
    "idempotent",
    "retry",
    "normal",
    "reference",
    "missing_or_ineffective_idempotency",
}


def _request_groups(incident: Incident) -> dict[object, list[dict[str, object]]]:
    groups: dict[object, list[dict[str, object]]] = {}
    for payment in incident.structured_evidence["payments"]:
        groups.setdefault(payment["request_id"], []).append(payment)
    return groups


def _assert_declared_relation(incident: Incident, invariant_index: int) -> None:
    invariant = incident.diagnostic_invariants[invariant_index]
    values = [incident.resolve_reference(item) for item in invariant.operands]
    if invariant.relation == "equal":
        assert len(set(values)) == 1
        if invariant.expected is not True:
            assert values[0] == invariant.expected
    elif invariant.relation == "not_equal":
        assert len(values) == 2 and values[0] != values[1]
    elif invariant.relation == "all_distinct":
        assert len(values) == len(set(values))
    elif invariant.relation == "ordered_before":
        timestamps = [
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            for value in values
        ]
        assert timestamps == sorted(timestamps)
        assert len(timestamps) == len(set(timestamps))
    elif invariant.relation == "row_count":
        assert len(values) == invariant.expected
    elif invariant.relation == "interval_seconds":
        first, second = (
            datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            for value in values
        )
        assert (second - first).total_seconds() == invariant.expected
    elif invariant.relation == "preserve_literal":
        assert invariant.expected is False
    else:
        raise AssertionError(f"Unhandled relation: {invariant.relation}")


def test_canonical_incident_loads_and_round_trips() -> None:
    original = Incident.load(FIXTURE)
    restored = Incident.from_json(original.to_json())
    assert restored == original
    assert original.incident_id == "incident_001_duplicate_payment"
    assert set(original.to_dict()) == set(Incident.__dataclass_fields__)
    json.dumps(original.to_dict())


def test_structured_ground_truth_round_trips_through_json() -> None:
    incident = generate_incident_001(DEFAULT_SEED)
    restored = Incident.from_json(incident.to_json())
    assert restored.ground_truth == incident.ground_truth
    assert restored.ground_truth.to_dict() == {
        "outcome": "duplicate_payment",
        "trigger": "retry_after_timeout",
        "failure_mechanism": "missing_or_ineffective_idempotency",
        "affected_component": "payment_worker",
        "logical_operation_repeated": True,
        "explanation": (
            "A caller repeated one logical request after a response timeout, and "
            "the payment worker persisted both arrivals as separate payments."
        ),
    }


def test_model_view_has_only_model_visible_sections() -> None:
    view = generate_incident_001(DEFAULT_SEED).model_view()
    assert set(view.to_dict()) == {
        "troubleshooting_question",
        "structured_evidence",
        "log_evidence",
    }
    assert ModelView.from_json(view.to_json()) == view


def test_model_view_contains_no_oracle_annotations() -> None:
    incident = generate_incident_001(DEFAULT_SEED)
    serialized = incident.model_view().to_json().lower()
    forbidden = {
        "ground_truth",
        "expected_evidence",
        "diagnostic_invariants",
        "sensitive_fields",
        '"policy"',
        '"rationale"',
        '"necessity"',
        '"description"',
    }
    assert all(item not in serialized for item in forbidden)
    assert all(
        invariant.description.lower() not in serialized
        for invariant in incident.diagnostic_invariants
    )
    assert all(
        expected.description.lower() not in serialized
        for expected in incident.expected_evidence
    )
    assert all(
        field.policy.lower() not in serialized
        and field.rationale.lower() not in serialized
        for field in incident.sensitive_fields
    )
    hidden_root_cause_values = {
        incident.ground_truth.outcome,
        incident.ground_truth.trigger,
        incident.ground_truth.failure_mechanism,
        incident.ground_truth.affected_component,
        incident.ground_truth.explanation,
    }
    assert all(
        value is None or value.lower() not in serialized
        for value in hidden_root_cause_values
    )


def test_model_view_contains_no_diagnosis_bearing_labels_or_phrases() -> None:
    serialized = generate_incident_001(DEFAULT_SEED).model_view().to_json().lower()
    assert "incident_001" not in serialized
    assert all(phrase not in serialized for phrase in PROHIBITED_MODEL_PHRASES)


def test_all_model_visible_identifiers_are_neutral() -> None:
    view = generate_incident_001(DEFAULT_SEED).model_view()
    identifiers: list[str] = []
    for rows in view.structured_evidence.values():
        for row in rows:
            identifiers.extend(
                str(value) for field, value in row.items() if field.endswith("_id")
            )
    for log in view.log_evidence:
        identifiers.append(log.evidence_id)
        identifiers.extend(
            str(value)
            for field, value in log.attributes.items()
            if field.endswith("_id")
        )
    assert identifiers
    assert all(NEUTRAL_ID.fullmatch(identifier) for identifier in identifiers)


def test_model_visible_logs_avoid_answer_bearing_language() -> None:
    messages = " ".join(
        entry.message.lower()
        for entry in generate_incident_001(DEFAULT_SEED).model_view().log_evidence
    )
    assert all(phrase not in messages for phrase in PROHIBITED_MODEL_PHRASES)


def test_model_view_is_a_defensive_copy() -> None:
    incident = generate_incident_001(DEFAULT_SEED)
    view = incident.model_view()
    original = incident.structured_evidence["customers"][0]["name"]
    view.structured_evidence["customers"][0]["name"] = "changed"
    assert incident.structured_evidence["customers"][0]["name"] == original


def test_all_evidence_references_resolve_to_one_element() -> None:
    incident = generate_incident_001(DEFAULT_SEED)
    for invariant in incident.diagnostic_invariants:
        for reference in invariant.operands:
            incident.resolve_reference(reference)
    for expected in incident.expected_evidence:
        for reference in expected.references:
            incident.resolve_reference(reference)


def test_sensitive_field_declarations_reference_visible_fields() -> None:
    incident = generate_incident_001(DEFAULT_SEED)
    fields: set[str] = set()
    for source, rows in incident.structured_evidence.items():
        for row in rows:
            fields.update(f"{source}.{field}" for field in row)
    for entry in incident.log_evidence:
        fields.update(
            {
                "logs.evidence_id",
                "logs.timestamp",
                "logs.level",
                "logs.service",
                "logs.message",
            }
        )
        fields.update(f"logs.{field}" for field in entry.attributes)
    assert all(item.path in fields for item in incident.sensitive_fields)


def test_declared_invariant_relationships_hold() -> None:
    incident = generate_incident_001(DEFAULT_SEED)
    for index in range(len(incident.diagnostic_invariants)):
        _assert_declared_relation(incident, index)


def test_relevant_request_equality_and_unrelated_request_inequality_exist() -> None:
    incident = generate_incident_001(DEFAULT_SEED)
    by_name = {item.name: item for item in incident.diagnostic_invariants}
    target = by_name["target_request_equality"]
    assert len({incident.resolve_reference(item) for item in target.operands}) == 1
    unrelated = by_name["unrelated_request_inequality"]
    values = [incident.resolve_reference(item) for item in unrelated.operands]
    assert len(values) == len(set(values))


def test_exactly_one_causal_repeated_operation_exists() -> None:
    incident = generate_incident_001(DEFAULT_SEED)
    repeated_groups = [rows for rows in _request_groups(incident).values() if len(rows) > 1]
    assert len(repeated_groups) == 1
    assert len(repeated_groups[0]) == 2
    assert {row["status"] for row in repeated_groups[0]} == {"succeeded"}
    assert len({row["payment_id"] for row in repeated_groups[0]}) == 2
    assert len({row["amount"] for row in repeated_groups[0]}) == 1


def test_distractors_do_not_satisfy_the_complete_causal_pattern() -> None:
    incident = generate_incident_001(DEFAULT_SEED)
    target_request = incident.metadata["target_request_id"]
    groups = _request_groups(incident)
    assert all(
        len(rows) == 1 for request, rows in groups.items() if request != target_request
    )

    receipt_counts: dict[object, int] = {}
    receive_messages = {"Inbound operation accepted", "Operation received"}
    for entry in incident.log_evidence:
        request_id = entry.attributes.get("request_id")
        if request_id is not None and entry.message in receive_messages:
            receipt_counts[request_id] = receipt_counts.get(request_id, 0) + 1
    benign_repeated_receipts = [
        request
        for request, count in receipt_counts.items()
        if count > 1 and request != target_request
    ]
    assert benign_repeated_receipts
    assert all(len(groups[request]) == 1 for request in benign_repeated_receipts)


def test_all_identities_are_clearly_fictional() -> None:
    incident = generate_incident_001(DEFAULT_SEED)
    assert incident.metadata["synthetic"] is True
    assert "fictional" in str(incident.metadata["fictionality_notice"]).lower()
    for customer in incident.structured_evidence["customers"]:
        assert "Fictional" in str(customer["name"])
        assert str(customer["email"]).endswith("@example.invalid")
        assert str(customer["ssn"]).startswith("000-")


def test_same_seed_is_deterministic_and_matches_fixture() -> None:
    generated = generate_incident_001(DEFAULT_SEED).to_json()
    assert generated == generate_incident_001(DEFAULT_SEED).to_json()
    assert generated == FIXTURE.read_text(encoding="utf-8")


def test_different_seeds_vary_more_than_identifiers() -> None:
    first_view = generate_incident_001(1001).model_view()
    second_view = generate_incident_001(1002).model_view()
    differences = {
        "customer_count": len(first_view.structured_evidence["customers"])
        != len(second_view.structured_evidence["customers"]),
        "payment_count": len(first_view.structured_evidence["payments"])
        != len(second_view.structured_evidence["payments"]),
        "names": sorted(
            row["name"] for row in first_view.structured_evidence["customers"]
        )
        != sorted(row["name"] for row in second_view.structured_evidence["customers"]),
        "amounts": sorted(
            row["amount"] for row in first_view.structured_evidence["payments"]
        )
        != sorted(row["amount"] for row in second_view.structured_evidence["payments"]),
        "timestamps": [entry.timestamp for entry in first_view.log_evidence]
        != [entry.timestamp for entry in second_view.log_evidence],
        "services": {entry.service for entry in first_view.log_evidence}
        != {entry.service for entry in second_view.log_evidence},
        "messages": [entry.message for entry in first_view.log_evidence]
        != [entry.message for entry in second_view.log_evidence],
    }
    assert sum(differences.values()) >= 4


def test_different_seeds_preserve_structured_root_cause() -> None:
    assert generate_incident_001(1001).ground_truth == generate_incident_001(
        1002
    ).ground_truth


def test_seed_splits_are_explicit_and_nonoverlapping() -> None:
    assert seed_split(1001) == "development"
    assert seed_split(2001) == "validation"
    assert seed_split(10_001) == "evaluation"
    assert seed_split(42) == "unassigned"
