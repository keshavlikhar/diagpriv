"""Synthetic measurement tests and a deterministic development artifact check."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from diagbench.generators.incident_001 import generate_incident_001
from diagbench.generators.incident_002 import generate_incident_002
from diagbench.schema import LogEntry, ModelView, SensitiveField
from diagpriv.privacy.exposure import (
    ANALYSIS_VERSION,
    SecretExposureError,
    analyze_model_views,
    build_development_report,
    render_development_report,
)
from diagpriv.transformations import (
    format_preserving_incident,
    hmac_incident,
    redact_incident,
    tokenize_incident,
)
from diagpriv.transformations.hmac_v1 import hmac_token


def _view(
    rows: list[dict[str, object]], *,
    question: str = "Investigate.",
    logs: tuple[LogEntry, ...] = (),
) -> ModelView:
    return ModelView(question, {"records": rows}, logs)


def _annotation(field: str = "entity_id", classification: str = "identifier") -> tuple[SensitiveField, ...]:
    return (SensitiveField(f"records.{field}", classification, "consistent_pseudonym", "synthetic"),)


def _fraction(vector: dict[str, object], key: str) -> float | None:
    return vector["metrics"][key]["fraction"]  # type: ignore[index]


def test_direct_literal_includes_entire_visible_view_not_only_aligned_field() -> None:
    raw = _view([{"evidence_id": "e1", "entity_id": "SYN-ENTITY-123"}])
    token = _view([{"evidence_id": "e1", "entity_id": "TOK_ENTITY_000001"}])
    assert _fraction(analyze_model_views(raw, token, _annotation()), "protected_literal_exposure") == 0
    leaked_question = _view(
        [{"evidence_id": "e1", "entity_id": "TOK_ENTITY_000001"}],
        question="Investigate SYN-ENTITY-123.",
    )
    assert _fraction(analyze_model_views(raw, leaked_question, _annotation()), "protected_literal_exposure") == 1


def test_all_to_one_collapse_is_not_faithful_equality_or_frequency() -> None:
    raw = _view([
        {"evidence_id": "e1", "entity_id": "SYN-A"},
        {"evidence_id": "e2", "entity_id": "SYN-A"},
        {"evidence_id": "e3", "entity_id": "SYN-B"},
    ])
    redacted = _view([
        {"evidence_id": key, "entity_id": "[REDACTED:records.entity_id]"}
        for key in ("e1", "e2", "e3")
    ])
    vector = analyze_model_views(raw, redacted, _annotation())
    assert _fraction(vector, "equal_pair_preservation") == 1
    assert _fraction(vector, "unequal_pair_separation") == 0
    assert _fraction(vector, "multiplicity_histogram_preservation") == 0
    assert _fraction(vector, "distinct_entity_count_preservation") == 0
    assert _fraction(vector, "sensitive_field_presence_preservation") == 1
    assert vector["format_categories"] == {"redacted_placeholder": 3}


def test_cross_source_linkage_uses_visible_values_and_typed_identity() -> None:
    log = lambda value: LogEntry("l1", "2039-01-01T00:00:00Z", "INFO", "svc", "seen", {"entity_id": value})
    raw = _view([{"evidence_id": "e1", "entity_id": "SYN-A"}], logs=(log("SYN-A"),))
    annotations = _annotation() + (
        SensitiveField("logs.entity_id", "identifier", "consistent_pseudonym", "synthetic"),
    )
    linked = _view([{"evidence_id": "e1", "entity_id": "TOK_1"}], logs=(log("TOK_1"),))
    unlinked = _view([{"evidence_id": "e1", "entity_id": "TOK_1"}], logs=(log("TOK_2"),))
    assert _fraction(analyze_model_views(raw, linked, annotations), "cross_source_equal_pair_preservation") == 1
    assert _fraction(analyze_model_views(raw, unlinked, annotations), "cross_source_equal_pair_preservation") == 0


def test_format_shape_and_cardinality_are_separate() -> None:
    raw = _view([
        {"evidence_id": "e1", "entity_id": "AB-012"},
        {"evidence_id": "e2", "entity_id": "CD-345"},
    ])
    shaped = _view([
        {"evidence_id": "e1", "entity_id": "EF-678"},
        {"evidence_id": "e2", "entity_id": "GH-901"},
    ])
    vector = analyze_model_views(raw, shaped, _annotation())
    assert _fraction(vector, "format_shape_preservation") == 1
    assert _fraction(vector, "direct_non_temporal_literal_exposure") == 0
    assert vector["format_categories"] == {"changed_same_shape": 2}
    removed = _view([{"evidence_id": "e1"}])
    vector = analyze_model_views(raw, removed, _annotation())
    assert _fraction(vector, "record_count_preservation") == 0.5
    assert _fraction(vector, "sensitive_field_presence_preservation") == 0


def test_absolute_time_relative_order_and_interval_are_independent() -> None:
    def logs(values: tuple[str, str, str]) -> tuple[LogEntry, ...]:
        return tuple(
            LogEntry(f"l{index}", value, "INFO", "svc", "event", {})
            for index, value in enumerate(values)
        )
    raw = _view([], logs=logs((
        "2039-01-01T00:00:00.000Z", "2039-01-01T00:00:01.000Z",
        "2039-01-01T00:00:03.000Z",
    )))
    relative = _view([], logs=logs(("T+0ms", "T+1000ms", "T+3000ms")))
    ablated = _view([], logs=logs(("slot-1", "slot-2", "slot-3")))
    raw_vector = analyze_model_views(raw, raw, ())
    relative_vector = analyze_model_views(raw, relative, ())
    ablated_vector = analyze_model_views(raw, ablated, ())
    assert _fraction(raw_vector, "absolute_timestamp_exposure") == 1
    assert _fraction(relative_vector, "absolute_timestamp_exposure") == 0
    assert _fraction(relative_vector, "temporal_pair_evaluability") == 1
    assert _fraction(relative_vector, "temporal_order_preservation") == 1
    assert _fraction(relative_vector, "temporal_interval_preservation") == 1
    assert _fraction(ablated_vector, "temporal_pair_evaluability") == 0
    assert _fraction(ablated_vector, "temporal_order_preservation") == 0
    assert _fraction(ablated_vector, "temporal_interval_preservation") == 0


def test_empty_denominators_are_not_applicable_not_zero_exposure() -> None:
    view = _view([{"evidence_id": "e1", "entity_id": "ONE"}])
    vector = analyze_model_views(view, view, _annotation())
    assert vector["metrics"]["equal_pair_preservation"] == {
        "numerator": 0, "denominator": 0, "fraction": None, "status": "not_applicable"
    }
    assert vector["metrics"]["secret_literal_exposure"]["status"] == "not_applicable"


def test_typed_identity_distinguishes_string_and_numeric_values() -> None:
    raw = _view([
        {"evidence_id": "e1", "entity_id": "1"},
        {"evidence_id": "e2", "entity_id": 1},
    ])
    vector = analyze_model_views(raw, raw, _annotation())
    assert vector["metrics"]["equal_pair_preservation"]["status"] == "not_applicable"
    assert _fraction(vector, "unequal_pair_separation") == 1


def test_secret_literal_exposure_fails_closed_without_echoing_value() -> None:
    secret = "SYNTHETIC-NONCREDENTIAL-SECRET-123"
    raw = _view([{"evidence_id": "e1", "api_token": secret}])
    annotation = (SensitiveField("records.api_token", "secret", "never_release", "synthetic"),)
    leaked = _view([{"evidence_id": "e1", "api_token": "[REDACTED]"}], question=f"Value: {secret}")
    with pytest.raises(SecretExposureError) as captured:
        analyze_model_views(raw, leaked, annotation)
    assert secret not in str(captured.value)
    safe = _view([{"evidence_id": "e1", "api_token": "[REDACTED]"}])
    assert _fraction(analyze_model_views(raw, safe, annotation), "secret_literal_exposure") == 0


def test_existing_scalar_transformations_are_measured_not_redefined() -> None:
    incident = generate_incident_001(1000)
    raw = incident.model_view()
    synthetic_key = hashlib.sha256(b"public-test-only-privacy-exposure-key").digest()
    redacted = analyze_model_views(raw, redact_incident(incident), incident.sensitive_fields)
    hmac = analyze_model_views(raw, hmac_incident(incident, key=synthetic_key), incident.sensitive_fields)
    token = analyze_model_views(raw, tokenize_incident(incident), incident.sensitive_fields)
    shaped = analyze_model_views(raw, format_preserving_incident(incident), incident.sensitive_fields)
    assert _fraction(redacted, "direct_non_temporal_literal_exposure") == 0
    assert _fraction(hmac, "direct_non_temporal_literal_exposure") == 0
    assert _fraction(token, "direct_non_temporal_literal_exposure") == 0
    assert _fraction(shaped, "direct_non_temporal_literal_exposure") == 0
    assert _fraction(shaped, "format_shape_preservation") == 1
    assert _fraction(hmac, "format_shape_preservation") == 0
    assert _fraction(token, "format_shape_preservation") == 0
    assert _fraction(hmac, "unequal_pair_separation") == 1
    assert _fraction(token, "unequal_pair_separation") == 1


def test_hmac_same_namespace_and_key_relinks_synthetic_identity_across_incidents() -> None:
    key = hashlib.sha256(b"public-test-only-cross-incident-key").digest()
    one = hmac_token("SYNTHETIC-REUSED-ID", key=key, namespace="shared:identifier:entity_id")
    two = hmac_token("SYNTHETIC-REUSED-ID", key=key, namespace="shared:identifier:entity_id")
    independent = hmac_token("SYNTHETIC-REUSED-ID", key=key, namespace="path:other.entity_id")
    assert one == two
    assert one != independent


def test_incident_002_reference_shape_is_measured_from_released_view() -> None:
    incident = generate_incident_002(1000)
    raw = incident.model_view()
    token = analyze_model_views(raw, tokenize_incident(incident), incident.sensitive_fields)
    shaped = analyze_model_views(raw, format_preserving_incident(incident), incident.sensitive_fields)
    assert _fraction(token, "format_shape_preservation") == 0
    assert _fraction(shaped, "format_shape_preservation") == 1
    assert _fraction(shaped, "cross_source_equal_pair_preservation") == 1


def test_development_regeneration_is_byte_deterministic_and_matches_artifact() -> None:
    first = render_development_report()
    second = render_development_report()
    artifact = Path(__file__).parents[1] / "docs/data/privacy_exposure_development_v1.json"
    assert first == second == artifact.read_bytes()
    report = build_development_report()
    assert report["analysis_version"] == ANALYSIS_VERSION
    assert report["incident_003_role_vectors_equal"] is True
    assert len(report["cases"]) == 79
    assert len(report["summary"]) == 13
    summaries = {
        (entry["incident_family"], entry["condition"]): entry
        for entry in report["summary"]
    }
    family = "incident_003_temporal_compensation_v3"
    relative = summaries[(family, "relative-time-v1")]["metrics"]
    ablated = summaries[(family, "temporal-ablation-v1")]["metrics"]
    assert relative["absolute_timestamp_exposure"]["numerator"] == 0
    assert relative["temporal_interval_preservation"]["fraction"] == 1
    assert ablated["temporal_pair_evaluability"]["fraction"] == 0
    assert ablated["temporal_interval_preservation"]["fraction"] == 0
    scalar = summaries[("incident_001_duplicate_payment", "hmac-v1")]["metrics"]
    assert scalar["direct_non_temporal_literal_exposure"]["fraction"] == 0
    assert scalar["protected_literal_not_visible"]["fraction"] == 1
    raw_literal = generate_incident_001(1000).structured_evidence["customers"][0]["customer_id"]
    assert isinstance(raw_literal, str)
    assert raw_literal.encode() not in first
    reference = generate_incident_002(1000).structured_evidence["processing_attempts"][0]["external_reference"]
    assert isinstance(reference, str)
    assert reference.encode() not in first
    assert b"DIAGPRIV_HMAC_KEY_HEX" not in first
