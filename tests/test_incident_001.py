from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from diagbench.generators.incident_001 import DEFAULT_SEED, generate_incident_001
from diagbench.schema import Incident

FIXTURE = (
    Path(__file__).parents[1]
    / "diagbench"
    / "incidents"
    / "incident_001_duplicate_payment"
    / "incident.json"
)


def _valid_evidence_references(incident: Incident) -> set[str]:
    references: set[str] = set()
    for source, rows in incident.structured_evidence.items():
        for row in rows:
            references.update(f"{source}.{field}" for field in row)
    for log in incident.log_evidence:
        references.update({"logs.timestamp", "logs.level", "logs.service", "logs.message"})
        references.update(f"logs.{field}" for field in log.attributes)
    return references


def test_incident_loads_successfully() -> None:
    incident = Incident.load(FIXTURE)
    assert incident.incident_id == "incident_001_duplicate_payment"


def test_schema_round_trip_and_required_fields() -> None:
    original = Incident.load(FIXTURE)
    restored = Incident.from_json(original.to_json())
    assert restored == original
    assert set(original.to_dict()) == set(Incident.__dataclass_fields__)
    json.dumps(original.to_dict())


def test_sensitive_fields_reference_valid_fields() -> None:
    incident = Incident.load(FIXTURE)
    valid = _valid_evidence_references(incident)
    assert incident.sensitive_fields
    assert all(field.path in valid for field in incident.sensitive_fields)


def test_invariants_reference_valid_evidence() -> None:
    incident = Incident.load(FIXTURE)
    valid = _valid_evidence_references(incident)
    assert incident.diagnostic_invariants
    for invariant in incident.diagnostic_invariants:
        assert invariant.fields
        assert set(invariant.fields) <= valid


def test_all_identities_are_clearly_fictional() -> None:
    incident = Incident.load(FIXTURE)
    assert incident.metadata["synthetic"] is True
    assert "fictional" in str(incident.metadata["fictionality_notice"]).lower()
    for customer in incident.structured_evidence["customers"]:
        assert "Fictional" in str(customer["name"])
        assert str(customer["email"]).endswith("@example.invalid")
        assert str(customer["ssn"]).startswith("000-")
        assert str(customer["customer_id"]).startswith("SYN-")
    for account in incident.structured_evidence["accounts"]:
        assert str(account["account_id"]).startswith("SYN-")
    for source in incident.structured_evidence.values():
        for row in source:
            for field, value in row.items():
                if field.endswith("_id"):
                    assert str(value).startswith("SYN-")
    for entry in incident.log_evidence:
        for field, value in entry.attributes.items():
            if field.endswith("_id"):
                assert str(value).startswith("SYN-")


def test_expected_duplicate_payment_relationship_exists() -> None:
    incident = Incident.load(FIXTURE)
    payments = incident.structured_evidence["payments"]
    groups: dict[tuple[object, ...], list[dict[str, object]]] = {}
    for payment in payments:
        key = (
            payment["customer_id"],
            payment["account_id"],
            payment["request_id"],
            payment["amount"],
            payment["status"],
        )
        groups.setdefault(key, []).append(payment)
    duplicates = [rows for rows in groups.values() if len(rows) == 2]
    assert len(duplicates) == 1
    first, second = duplicates[0]
    first_at = datetime.fromisoformat(str(first["created_at"]).replace("Z", "+00:00"))
    second_at = datetime.fromisoformat(str(second["created_at"]).replace("Z", "+00:00"))
    assert (second_at - first_at).total_seconds() == 2.767
    related_logs = [
        entry
        for entry in incident.log_evidence
        if entry.attributes.get("request_id") == first["request_id"]
    ]
    assert any("retry" in entry.message.lower() for entry in related_logs)
    assert sum(entry.attributes.get("idempotency_check") is False for entry in related_logs) == 2


def test_generation_is_deterministic_for_same_seed() -> None:
    assert generate_incident_001(DEFAULT_SEED).to_json() == generate_incident_001(
        DEFAULT_SEED
    ).to_json()
    assert generate_incident_001(DEFAULT_SEED).to_json() == FIXTURE.read_text(
        encoding="utf-8"
    )


def test_different_seeds_change_synthetic_identifiers() -> None:
    assert generate_incident_001(1).to_json() != generate_incident_001(2).to_json()
