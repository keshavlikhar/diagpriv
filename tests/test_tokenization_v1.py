from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import re

import pytest

from diagbench.generators.incident_001 import generate_incident_001
from diagbench.schema import ModelView
from diagbench.schema.models import JSONValue
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.prompt import PROMPT_SHA256 as PROMPT_SHA256_V1
from diagpriv.evaluation.prompt_v2 import PROMPT_SHA256 as PROMPT_SHA256_V2
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.runner import RawRunConfig, run_raw_experiment
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations import TRANSFORMATION_VERSION as PACKAGE_VERSION
from diagpriv.transformations.hmac_v1 import hmac_incident
from diagpriv.transformations.redaction_v1 import redact_incident
from diagpriv.transformations.tokenization_v1 import (
    TRANSFORMATION_VERSION,
    tokenize_incident,
)

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "experiments" / "tokenization_v1_development.toml"
PUBLIC_TEST_KEY = bytes(range(32))


def _path_values(model_view: ModelView, path: str) -> tuple[JSONValue, ...]:
    source, field = path.split(".", maxsplit=1)
    if source != "logs":
        return tuple(row[field] for row in model_view.structured_evidence[source])
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
            item for nested in value.values() for item in _all_scalar_values(nested)
        )
    if isinstance(value, list):
        return tuple(item for nested in value for item in _all_scalar_values(nested))
    return (value,)


def _normalized_view(model_view: ModelView) -> dict[str, JSONValue]:
    data = deepcopy(model_view.to_dict())
    structured = data["structured_evidence"]
    assert isinstance(structured, dict)
    for rows in structured.values():
        assert isinstance(rows, list)
        rows.sort(key=lambda row: row["evidence_id"] if isinstance(row, dict) else "")
    logs = data["log_evidence"]
    assert isinstance(logs, list)
    logs.sort(key=lambda entry: entry["evidence_id"] if isinstance(entry, dict) else "")
    return data


def test_tokenization_v1_changes_exactly_annotated_fields() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = tokenize_incident(incident)
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
                    assert transformed_row[field] != original_value
                    assert str(transformed_row[field]).startswith("TOK_")
                else:
                    assert transformed_row[field] == original_value

    for original_entry, transformed_entry in zip(
        original.log_evidence, transformed.log_evidence, strict=True
    ):
        for field in ("evidence_id", "timestamp", "level", "service", "message"):
            path = f"logs.{field}"
            transformed_value = getattr(transformed_entry, field)
            if path in sensitive_paths:
                assert transformed_value != getattr(original_entry, field)
                assert str(transformed_value).startswith("TOK_")
            else:
                assert transformed_value == getattr(original_entry, field)
        assert original_entry.attributes.keys() == transformed_entry.attributes.keys()
        for field, original_value in original_entry.attributes.items():
            path = f"logs.{field}"
            if path in sensitive_paths:
                assert transformed_entry.attributes[field] != original_value
                assert str(transformed_entry.attributes[field]).startswith("TOK_")
            else:
                assert transformed_entry.attributes[field] == original_value


def test_tokenization_v1_fixed_seed_assignment_vector() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = tokenize_incident(incident)
    target_request = incident.metadata["target_request_id"]
    target_rows = [
        (before, after)
        for before, after in zip(
            original.structured_evidence["payments"],
            transformed.structured_evidence["payments"],
            strict=True,
        )
        if before["request_id"] == target_request
    ]

    assert [row[1]["request_id"] for row in target_rows] == [
        "TOK_REQ_000005",
        "TOK_REQ_000005",
    ]
    assert [row[1]["payment_id"] for row in target_rows] == [
        "TOK_PAY_PAYMENTS_000008",
        "TOK_PAY_PAYMENTS_000006",
    ]
    assert {row[1]["customer_id"] for row in target_rows} == {"TOK_CUST_000003"}
    assert {row[1]["account_id"] for row in target_rows} == {"TOK_ACCT_000002"}


def test_same_values_map_to_same_token_and_different_values_stay_distinct() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = tokenize_incident(incident)

    for annotation in incident.sensitive_fields:
        before = _path_values(original, annotation.path)
        after = _path_values(transformed, annotation.path)
        mapping: dict[object, JSONValue] = {}
        for plaintext, token in zip(before, after, strict=True):
            if plaintext in mapping:
                assert mapping[plaintext] == token
            else:
                mapping[plaintext] = token
        assert len(set(after)) == len(set(before))

    assert len(set(_path_values(original, "payments.request_id"))) < len(
        _path_values(original, "payments.request_id")
    )
    payment_ids = _path_values(transformed, "payments.payment_id")
    assert len(set(payment_ids)) == len(payment_ids)


def test_tokenization_preserves_intended_cross_source_identity() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = tokenize_incident(incident)
    grouped: dict[tuple[str, str, object], set[JSONValue]] = {}
    sources: dict[tuple[str, str, object], set[str]] = {}

    for annotation in incident.sensitive_fields:
        if annotation.policy != "consistent_pseudonym":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        for plaintext, token in zip(
            _path_values(original, annotation.path),
            _path_values(transformed, annotation.path),
            strict=True,
        ):
            identity = (annotation.classification, field, plaintext)
            grouped.setdefault(identity, set()).add(token)
            sources.setdefault(identity, set()).add(source)

    cross_source = [
        identity for identity, source_set in sources.items() if len(source_set) > 1
    ]
    assert cross_source
    assert all(len(grouped[identity]) == 1 for identity in cross_source)


def test_independent_paths_use_distinct_visible_token_namespaces() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = tokenize_incident(incident)
    payment_pairs = dict(
        zip(
            _path_values(original, "payments.payment_id"),
            _path_values(transformed, "payments.payment_id"),
            strict=True,
        )
    )
    log_pairs = dict(
        zip(
            _path_values(original, "logs.payment_id"),
            _path_values(transformed, "logs.payment_id"),
            strict=True,
        )
    )
    shared_plaintext = set(payment_pairs).intersection(log_pairs)
    assert shared_plaintext
    assert all(payment_pairs[value] != log_pairs[value] for value in shared_plaintext)
    assert all(str(token).startswith("TOK_PAY_PAYMENTS_") for token in payment_pairs.values())
    assert all(str(token).startswith("TOK_PAY_LOGS_") for token in log_pairs.values())


def test_tokens_are_short_synthetic_ordinals_not_hmac_or_original_format() -> None:
    incident = generate_incident_001(1001)
    transformed = tokenize_incident(incident)
    token_values = {
        value
        for annotation in incident.sensitive_fields
        for value in _path_values(transformed, annotation.path)
    }
    assert token_values
    assert all(isinstance(value, str) for value in token_values)
    assert all(re.fullmatch(r"TOK_[A-Z0-9_]+_[0-9]{6}", value) for value in token_values)
    assert all("HMAC1_" not in value and "SYN-" not in value for value in token_values)


def test_tokenization_leaks_no_sensitive_plaintext() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = tokenize_incident(incident)
    sensitive_plaintext = {
        value
        for annotation in incident.sensitive_fields
        for value in _path_values(original, annotation.path)
    }
    transformed_values = set(_all_scalar_values(transformed.to_dict()))
    assert sensitive_plaintext
    assert sensitive_plaintext.isdisjoint(transformed_values)
    serialized = transformed.to_json()
    assert all(
        str(value) not in serialized
        for value in sensitive_plaintext
        if isinstance(value, str)
    )


def test_tokenization_is_repeatable_and_independent_of_input_order() -> None:
    incident = generate_incident_001(1001)
    first = tokenize_incident(incident)
    second = tokenize_incident(incident)
    reordered = replace(
        incident,
        structured_evidence={
            source: list(reversed(rows))
            for source, rows in incident.structured_evidence.items()
        },
        log_evidence=tuple(reversed(incident.log_evidence)),
        sensitive_fields=tuple(reversed(incident.sensitive_fields)),
    )
    reordered_result = tokenize_incident(reordered)
    assert first == second
    assert _normalized_view(first) == _normalized_view(reordered_result)


@pytest.mark.parametrize("seed", range(1000, 1005))
def test_tokenization_v1_has_expected_incident_001_invariant_profile(seed: int) -> None:
    incident = generate_incident_001(seed)
    results = {
        result.name: (result.preserved, result.status)
        for result in evaluate_invariants(incident, tokenize_incident(incident))
    }
    expected_non_preservation = {
        "literal_customer_identity",
        "literal_account_identity",
    }
    assert set(results) == {
        invariant.name for invariant in incident.diagnostic_invariants
    }
    assert all(preserved for preserved, _ in results.values())
    assert {
        name for name, (_, status) in results.items() if status == "genuine_preservation"
    } == set(results).difference(expected_non_preservation)
    assert {
        name
        for name, (_, status) in results.items()
        if status == "expected_non_preservation"
    } == expected_non_preservation


def test_tokenized_model_view_excludes_oracle_privacy_and_mapping_metadata() -> None:
    transformed = tokenize_incident(generate_incident_001(1001))
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
        "mapping_table",
        "plaintext_to_token",
    ):
        assert forbidden not in serialized
    assert ModelView.from_json(transformed.to_json()) == transformed


def test_runner_persists_no_plaintext_or_mapping_table(tmp_path: Path) -> None:
    incident = generate_incident_001(1001)
    provider = FakeProvider(raw_output="{}")
    result_path = tmp_path / "tokenization-results.jsonl"
    config = RawRunConfig(
        experiment_id="tokenization-v1-offline-test",
        seed=1001,
        model="offline-fixture",
        model_version="1",
        reasoning_effort="medium",
        condition="tokenization-v1",
        decoding_settings={"max_output_tokens": 4096},
        prompt_version="raw-rca-v2",
        timestamp="2032-01-01T00:00:00+00:00",
    )
    manifest = run_raw_experiment(config, provider, result_path=result_path)
    outputs = (
        provider.requests[0].prompt,
        manifest.to_json(),
        result_path.read_text(encoding="utf-8"),
        repr(config),
        repr(manifest),
    )
    sensitive_plaintext = {
        str(value)
        for annotation in incident.sensitive_fields
        for value in _path_values(incident.model_view(), annotation.path)
    }
    assert all(
        plaintext not in output
        for plaintext in sensitive_plaintext
        for output in outputs
    )
    assert "TOK_REQ_" in provider.requests[0].prompt
    assert all("mapping_table" not in output for output in outputs)
    assert manifest.condition == "tokenization-v1"
    assert manifest.transformation_key_id is None
    assert manifest.transformation_key_fingerprint is None


def test_existing_transformation_protocols_remain_unchanged() -> None:
    incident = generate_incident_001(1001)
    raw_before = incident.model_view()
    redaction_before = redact_incident(incident)
    hmac_before = hmac_incident(incident, key=PUBLIC_TEST_KEY)
    tokenize_incident(incident)
    assert incident.model_view() == raw_before
    assert redact_incident(incident) == redaction_before
    assert hmac_incident(incident, key=PUBLIC_TEST_KEY) == hmac_before
    assert PACKAGE_VERSION == "redaction-v1"
    assert PROMPT_SHA256_V1 == (
        "0c06c1ec6d72ca08927a367aaf873d7bea2b34c6210ceb74824263dd7f2bd9cd"
    )
    assert PROMPT_SHA256_V2 == (
        "744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d"
    )


def test_tokenization_v1_development_config_is_exact_and_safe() -> None:
    definition = PilotDefinition.load(CONFIG)
    assert TRANSFORMATION_VERSION == "tokenization-v1"
    assert definition.pilot_id == "tokenization-v1-development"
    assert definition.condition == "tokenization-v1"
    assert definition.seed_scope == "development_only"
    assert definition.development_seeds == tuple(range(1000, 1005))
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.prompt_version == "raw-rca-v2"
    assert definition.prompt_sha256 == PROMPT_SHA256_V2
    assert definition.taxonomy_version == "rca-taxonomy-v2"
    assert definition.scorer_version == "raw-rca-scorer-v2"
    assert definition.requested_model == "gpt-5.6-luna"
    assert definition.reasoning_effort == "medium"
    assert "temperature" not in definition.decoding_settings
    assert definition.hmac_key_environment_variable is None
    assert definition.hmac_key_id is None


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
        (
            "development_seeds = [1000, 1001, 1002, 1003, 1004]",
            "development_seeds = [1000, 1001, 1002, 1003, 2000]",
            "development_seeds contains a non-development seed",
        ),
    ],
)
def test_tokenization_v1_config_rejects_protected_or_mislabeled_seeds(
    tmp_path: Path, original: str, changed: str, message: str
) -> None:
    path = tmp_path / "invalid-tokenization.toml"
    path.write_text(
        CONFIG.read_text(encoding="utf-8").replace(original, changed),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=message):
        PilotDefinition.load(path)


def test_tokenization_command_is_pending_without_execute(
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
    assert pending["pilot"]["condition"] == "tokenization-v1"
    assert pending["pilot"]["development_seeds"] == list(range(1000, 1005))
    assert pending["pilot"]["validation_seeds"] == []
    assert pending["pilot"]["held_out_seeds"] == []
    assert not results.exists()
