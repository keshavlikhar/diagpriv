from __future__ import annotations

import json
from pathlib import Path

import pytest

from diagbench.generators.incident_001 import generate_incident_001
from diagbench.schema import ModelView
from diagbench.schema.models import JSONValue
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.runner import RawRunConfig, run_raw_experiment
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations.redaction_v1 import (
    TRANSFORMATION_VERSION,
    redact_incident,
    redaction_placeholder,
)

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "experiments" / "redaction_v1_development.toml"


def _path_values(model_view: ModelView, path: str) -> tuple[JSONValue, ...]:
    source, field = path.split(".", maxsplit=1)
    if source != "logs":
        return tuple(
            row[field] for row in model_view.structured_evidence[source]
        )
    values: list[JSONValue] = []
    for entry in model_view.log_evidence:
        data = entry.to_dict()
        if field in data:
            values.append(data[field])
        elif field in entry.attributes:
            values.append(entry.attributes[field])
    return tuple(values)


def _all_scalar_values(value: JSONValue) -> tuple[JSONValue, ...]:
    if isinstance(value, dict):
        return tuple(
            item
            for nested in value.values()
            for item in _all_scalar_values(nested)
        )
    if isinstance(value, list):
        return tuple(item for nested in value for item in _all_scalar_values(nested))
    return (value,)


def test_redaction_v1_changes_exactly_annotated_fields() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = redact_incident(incident)
    sensitive_paths = {annotation.path for annotation in incident.sensitive_fields}

    assert original.troubleshooting_question == transformed.troubleshooting_question
    assert original.structured_evidence.keys() == transformed.structured_evidence.keys()
    for source, original_rows in original.structured_evidence.items():
        transformed_rows = transformed.structured_evidence[source]
        assert len(original_rows) == len(transformed_rows)
        for original_row, transformed_row in zip(
            original_rows, transformed_rows, strict=True
        ):
            assert original_row.keys() == transformed_row.keys()
            for field, original_value in original_row.items():
                path = f"{source}.{field}"
                if path in sensitive_paths:
                    assert transformed_row[field] == f"[REDACTED:{path}]"
                else:
                    assert transformed_row[field] == original_value

    assert len(original.log_evidence) == len(transformed.log_evidence)
    for original_entry, transformed_entry in zip(
        original.log_evidence, transformed.log_evidence, strict=True
    ):
        for field in ("evidence_id", "timestamp", "level", "service", "message"):
            path = f"logs.{field}"
            transformed_value = getattr(transformed_entry, field)
            if path in sensitive_paths:
                assert transformed_value == f"[REDACTED:{path}]"
            else:
                assert transformed_value == getattr(original_entry, field)
        assert original_entry.attributes.keys() == transformed_entry.attributes.keys()
        for field, original_value in original_entry.attributes.items():
            path = f"logs.{field}"
            if path in sensitive_paths:
                assert transformed_entry.attributes[field] == f"[REDACTED:{path}]"
            else:
                assert transformed_entry.attributes[field] == original_value


def test_redaction_v1_leaks_no_original_sensitive_plaintext() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = redact_incident(incident)
    sensitive_plaintext = {
        value
        for annotation in incident.sensitive_fields
        for value in _path_values(original, annotation.path)
        if isinstance(value, str)
    }
    transformed_values = set(_all_scalar_values(transformed.to_dict()))
    assert sensitive_plaintext
    assert sensitive_plaintext.isdisjoint(transformed_values)


def test_redaction_v1_is_many_to_one_and_not_cross_source_linkable() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = redact_incident(incident)

    assert len(set(_path_values(original, "payments.request_id"))) > 1
    assert set(_path_values(transformed, "payments.request_id")) == {
        "[REDACTED:payments.request_id]"
    }
    assert set(_path_values(transformed, "logs.request_id")) == {
        "[REDACTED:logs.request_id]"
    }
    assert _path_values(transformed, "payments.request_id")[0] != _path_values(
        transformed, "logs.request_id"
    )[0]
    assert len(set(_path_values(original, "payments.payment_id"))) > 1
    assert set(_path_values(transformed, "payments.payment_id")) == {
        "[REDACTED:payments.payment_id]"
    }


@pytest.mark.parametrize("seed", range(1000, 1005))
def test_redaction_v1_has_expected_incident_001_invariant_profile(seed: int) -> None:
    incident = generate_incident_001(seed)
    results = {
        result.name: (result.preserved, result.status)
        for result in evaluate_invariants(incident, redact_incident(incident))
    }
    assert results == {
        "target_request_equality": (True, "degenerate_all_to_one"),
        "target_request_cross_source_identity": (False, "broken"),
        "unrelated_request_inequality": (False, "broken"),
        "target_payment_distinctness": (False, "broken"),
        "target_event_order": (True, "genuine_preservation"),
        "target_success_state": (True, "genuine_preservation"),
        "target_customer_equality": (True, "degenerate_all_to_one"),
        "target_account_equality": (True, "degenerate_all_to_one"),
        "target_amount_equality": (True, "genuine_preservation"),
        "payment_row_cardinality": (True, "genuine_preservation"),
        "exact_rearrival_interval": (True, "genuine_preservation"),
        "literal_customer_identity": (True, "expected_non_preservation"),
        "literal_account_identity": (True, "expected_non_preservation"),
    }


def test_invariant_status_keeps_exact_predicate_separate_from_interpretation() -> None:
    incident = generate_incident_001(1001)
    results = {
        result.name: result
        for result in evaluate_invariants(incident, redact_incident(incident))
    }
    assert results["target_request_equality"].preserved is True
    assert results["target_request_equality"].status == "degenerate_all_to_one"
    assert results["target_event_order"].preserved is True
    assert results["target_event_order"].status == "genuine_preservation"
    assert results["target_request_cross_source_identity"].preserved is False
    assert results["target_request_cross_source_identity"].status == "broken"
    assert results["literal_customer_identity"].preserved is True
    assert (
        results["literal_customer_identity"].status
        == "expected_non_preservation"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("sensitive text", "[REDACTED:source.field]"),
        (42, 0),
        (42.5, 0.0),
        (True, False),
        (None, None),
        (["sensitive"], []),
        ({"sensitive": "value"}, {}),
    ],
)
def test_redaction_v1_placeholder_rules_are_generic_and_type_appropriate(
    value: JSONValue, expected: JSONValue
) -> None:
    assert redaction_placeholder("source.field", value) == expected


def test_redacted_model_view_contains_no_oracle_or_privacy_annotations() -> None:
    incident = generate_incident_001(1001)
    transformed = redact_incident(incident)
    serialized = transformed.to_json().lower()
    assert set(transformed.to_dict()) == {
        "troubleshooting_question",
        "structured_evidence",
        "log_evidence",
    }
    for forbidden in (
        "ground_truth",
        "expected_evidence",
        "diagnostic_invariants",
        "sensitive_fields",
        "classification",
        "policy",
        "rationale",
        "oracle",
    ):
        assert forbidden not in serialized
    assert ModelView.from_json(transformed.to_json()) == transformed


def test_redaction_v1_runner_sends_only_transformed_model_view() -> None:
    incident = generate_incident_001(1001)
    provider = FakeProvider(raw_output="{}")
    manifest = run_raw_experiment(
        RawRunConfig(
            experiment_id="redaction-v1-offline-test",
            seed=1001,
            model="offline-fixture",
            model_version="1",
            reasoning_effort="medium",
            condition="redaction-v1",
            decoding_settings={"max_output_tokens": 4096},
            prompt_version="raw-rca-v2",
            timestamp="2032-01-01T00:00:00+00:00",
        ),
        provider,
    )
    assert manifest.condition == "redaction-v1"
    assert manifest.response.status == "missing_fields"
    assert len(provider.requests) == 1
    prompt = provider.requests[0].prompt
    assert "[REDACTED:payments.request_id]" in prompt
    assert "[REDACTED:logs.request_id]" in prompt
    for annotation in incident.sensitive_fields:
        for value in _path_values(incident.model_view(), annotation.path):
            if isinstance(value, str):
                assert value not in prompt


def test_redaction_v1_development_config_is_exact_and_safe() -> None:
    definition = PilotDefinition.load(CONFIG)
    assert TRANSFORMATION_VERSION == "redaction-v1"
    assert definition.pilot_id == "redaction-v1-development"
    assert definition.condition == "redaction-v1"
    assert definition.seed_scope == "development_only"
    assert definition.development_seeds == tuple(range(1000, 1005))
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.prompt_version == "raw-rca-v2"
    assert definition.taxonomy_version == "rca-taxonomy-v2"
    assert definition.scorer_version == "raw-rca-scorer-v2"
    assert definition.requested_model == "gpt-5.6-luna"
    assert definition.reasoning_effort == "medium"
    assert "temperature" not in definition.decoding_settings


@pytest.mark.parametrize(
    ("original", "changed", "message"),
    [
        (
            "validation_seeds = []",
            "validation_seeds = [2000]",
            "Development-only pilot cannot contain validation seeds",
        ),
        (
            "held_out_seeds = []",
            "held_out_seeds = [20000]",
            "must not contain held-out seeds",
        ),
    ],
)
def test_redaction_v1_config_rejects_nondevelopment_seeds(
    tmp_path: Path, original: str, changed: str, message: str
) -> None:
    path = tmp_path / "invalid-redaction.toml"
    path.write_text(
        CONFIG.read_text(encoding="utf-8").replace(original, changed),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=message):
        PilotDefinition.load(path)


def test_redaction_v1_command_is_pending_without_execute(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    results = tmp_path / "must-not-exist.jsonl"
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(CONFIG),
            "--results",
            str(results),
        ]
    )
    args.handler(args)
    pending = json.loads(capsys.readouterr().out)
    assert pending["execution"] == "pending"
    assert pending["pilot"]["condition"] == "redaction-v1"
    assert pending["pilot"]["development_seeds"] == list(range(1000, 1005))
    assert pending["pilot"]["validation_seeds"] == []
    assert pending["pilot"]["held_out_seeds"] == []
    assert not results.exists()
