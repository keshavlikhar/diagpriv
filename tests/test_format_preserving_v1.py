from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import string

import pytest

from diagbench.generators.incident_001 import generate_incident_001
from diagbench.schema import ModelView, SensitiveField
from diagbench.schema.models import JSONValue
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.prompt import PROMPT_SHA256 as PROMPT_SHA256_V1
from diagpriv.evaluation.prompt_v2 import PROMPT_SHA256 as PROMPT_SHA256_V2
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.runner import RawRunConfig, run_raw_experiment
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations import TRANSFORMATION_VERSION as PACKAGE_VERSION
from diagpriv.transformations.format_preserving_v1 import (
    TRANSFORMATION_VERSION,
    _assign_pattern_values,
    _initial_rank,
    _parse_pattern,
    _render_rank,
    format_preserving_incident,
    structural_pattern,
)
from diagpriv.transformations.hmac_v1 import hmac_incident
from diagpriv.transformations.redaction_v1 import redact_incident
from diagpriv.transformations.tokenization_v1 import tokenize_incident

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "experiments" / "format_preserving_v1_development.toml"
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


def _assert_same_pattern(before: str, after: str) -> None:
    assert len(after) == len(before)
    assert structural_pattern(after) == structural_pattern(before)
    for original, pseudonym in zip(before, after, strict=True):
        if original in string.punctuation or original == " ":
            assert pseudonym == original
        elif original.isupper():
            assert pseudonym in string.ascii_uppercase
        elif original.islower():
            assert pseudonym in string.ascii_lowercase
        elif original.isdigit():
            assert pseudonym in string.digits


def test_format_preserving_v1_changes_exactly_annotated_fields() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = format_preserving_incident(incident)
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
                    assert isinstance(original_value, str)
                    assert isinstance(transformed_row[field], str)
                    assert transformed_row[field] != original_value
                    _assert_same_pattern(original_value, transformed_row[field])
                else:
                    assert transformed_row[field] == original_value

    for original_entry, transformed_entry in zip(
        original.log_evidence, transformed.log_evidence, strict=True
    ):
        for field in ("evidence_id", "timestamp", "level", "service", "message"):
            assert getattr(transformed_entry, field) == getattr(original_entry, field)
        assert original_entry.attributes.keys() == transformed_entry.attributes.keys()
        for field, original_value in original_entry.attributes.items():
            path = f"logs.{field}"
            if path in sensitive_paths:
                transformed_value = transformed_entry.attributes[field]
                assert isinstance(original_value, str)
                assert isinstance(transformed_value, str)
                assert transformed_value != original_value
                _assert_same_pattern(original_value, transformed_value)
            else:
                assert transformed_entry.attributes[field] == original_value


def test_structural_pattern_rules_cover_required_character_classes() -> None:
    assert structural_pattern("AB-123-xy") == "UU-DDD-ll"
    assert structural_pattern("000-88-3435") == "DDD-DD-DDDD"
    assert structural_pattern("a.B+9@example.invalid") == "l.U+D@lllllll.lllllll"
    assert structural_pattern("A Name (Test)") == "U Ulll (Ulll)"


def test_same_values_map_the_same_and_different_values_stay_distinct() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = format_preserving_incident(incident)
    for annotation in incident.sensitive_fields:
        before = _path_values(original, annotation.path)
        after = _path_values(transformed, annotation.path)
        mapping: dict[object, JSONValue] = {}
        for plaintext, pseudonym in zip(before, after, strict=True):
            if plaintext in mapping:
                assert mapping[plaintext] == pseudonym
            else:
                mapping[plaintext] = pseudonym
        assert len(set(after)) == len(set(before))


def test_intended_cross_source_identity_and_independent_namespaces() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = format_preserving_incident(incident)
    target_request = incident.metadata["target_request_id"]
    payment_requests = dict(
        zip(
            _path_values(original, "payments.request_id"),
            _path_values(transformed, "payments.request_id"),
            strict=True,
        )
    )
    log_requests = dict(
        zip(
            _path_values(original, "logs.request_id"),
            _path_values(transformed, "logs.request_id"),
            strict=True,
        )
    )
    assert payment_requests[target_request] == log_requests[target_request]

    payment_ids = dict(
        zip(
            _path_values(original, "payments.payment_id"),
            _path_values(transformed, "payments.payment_id"),
            strict=True,
        )
    )
    log_ids = dict(
        zip(
            _path_values(original, "logs.payment_id"),
            _path_values(transformed, "logs.payment_id"),
            strict=True,
        )
    )
    shared_plaintext = set(payment_ids).intersection(log_ids)
    assert shared_plaintext
    assert all(payment_ids[value] != log_ids[value] for value in shared_plaintext)


def test_plaintext_and_mapping_table_do_not_leak() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = format_preserving_incident(incident)
    sensitive_plaintext = {
        value
        for annotation in incident.sensitive_fields
        for value in _path_values(original, annotation.path)
    }
    assert sensitive_plaintext.isdisjoint(
        set(_all_scalar_values(transformed.to_dict()))
    )
    serialized = transformed.to_json()
    assert all(str(value) not in serialized for value in sensitive_plaintext)
    assert "mapping_table" not in serialized
    assert "plaintext_to_pseudonym" not in serialized


def test_repeated_transformation_is_deterministic_and_order_independent() -> None:
    incident = generate_incident_001(1001)
    first = format_preserving_incident(incident)
    second = format_preserving_incident(incident)
    reordered = replace(
        incident,
        structured_evidence={
            source: list(reversed(rows))
            for source, rows in incident.structured_evidence.items()
        },
        log_evidence=tuple(reversed(incident.log_evidence)),
        sensitive_fields=tuple(reversed(incident.sensitive_fields)),
    )
    reordered_result = format_preserving_incident(reordered)
    assert first == second
    assert _normalized_view(first) == _normalized_view(reordered_result)


def test_small_domain_collision_resolution_skips_blocked_candidate() -> None:
    namespace = "path:test.value"
    pattern = _parse_pattern("0")
    first_candidate = _render_rank(
        pattern, _initial_rank(namespace, pattern, "0", 10)
    )
    used = {first_candidate}
    mapping = _assign_pattern_values(
        namespace=namespace,
        pattern=pattern,
        values={"0"},
        forbidden={"0"},
        used=used,
    )
    assert mapping["0"] != first_candidate
    assert mapping["0"] != "0"
    assert len(mapping["0"]) == 1
    assert mapping["0"].isdigit()


def test_format_preserving_v1_fails_closed_when_output_domain_is_exhausted() -> None:
    incident = generate_incident_001(1001)
    evidence = deepcopy(incident.structured_evidence)
    evidence["customers"][0]["name"] = "-"
    changed = replace(incident, structured_evidence=evidence)
    with pytest.raises(ValueError, match="output domain is too small"):
        format_preserving_incident(changed)


@pytest.mark.parametrize("seed", range(1000, 1005))
def test_format_preserving_v1_has_expected_invariant_profile(seed: int) -> None:
    incident = generate_incident_001(seed)
    results = {
        result.name: (result.preserved, result.status)
        for result in evaluate_invariants(
            incident, format_preserving_incident(incident)
        )
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


def test_model_view_and_runner_persist_no_oracle_plaintext_or_mapping(tmp_path: Path) -> None:
    incident = generate_incident_001(1001)
    provider = FakeProvider(raw_output="{}")
    result_path = tmp_path / "format-preserving-results.jsonl"
    config = RawRunConfig(
        experiment_id="format-preserving-v1-offline-test",
        seed=1001,
        model="offline-fixture",
        model_version="1",
        reasoning_effort="medium",
        condition="format-preserving-v1",
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
    assert all("mapping_table" not in output for output in outputs)
    assert manifest.condition == "format-preserving-v1"
    assert manifest.transformation_key_id is None
    assert manifest.transformation_key_fingerprint is None
    transformed = format_preserving_incident(incident)
    assert set(transformed.to_dict()) == {
        "troubleshooting_question",
        "structured_evidence",
        "log_evidence",
    }
    assert ModelView.from_json(transformed.to_json()) == transformed


def test_fail_closed_for_missing_duplicate_unsupported_and_ambiguous_annotations() -> None:
    incident = generate_incident_001(1001)
    missing = replace(
        incident,
        sensitive_fields=(
            replace(incident.sensitive_fields[0], path="customers.missing"),
            *incident.sensitive_fields[1:],
        ),
    )
    with pytest.raises(ValueError, match="absent"):
        format_preserving_incident(missing)

    duplicate = replace(
        incident,
        sensitive_fields=(*incident.sensitive_fields, incident.sensitive_fields[0]),
    )
    with pytest.raises(ValueError, match="Duplicate"):
        format_preserving_incident(duplicate)

    unsupported = replace(
        incident,
        sensitive_fields=(
            replace(incident.sensitive_fields[0], policy="encrypt_somehow"),
            *incident.sensitive_fields[1:],
        ),
    )
    with pytest.raises(ValueError, match="Unsupported"):
        format_preserving_incident(unsupported)

    ambiguous_annotation = SensitiveField(
        path="customers.name",
        classification="direct:identifier",
        policy="remove_or_pseudonymize",
        rationale="test fixture",
    )
    ambiguous = replace(
        incident,
        sensitive_fields=(ambiguous_annotation, *incident.sensitive_fields[1:]),
    )
    with pytest.raises(ValueError, match="Ambiguous"):
        format_preserving_incident(ambiguous)


@pytest.mark.parametrize("value", [["secret"], {"secret": "value"}, 42, True, None])
def test_fail_closed_for_composite_or_unsupported_scalar_values(value: JSONValue) -> None:
    incident = generate_incident_001(1001)
    evidence = deepcopy(incident.structured_evidence)
    evidence["customers"][0]["name"] = value
    changed = replace(incident, structured_evidence=evidence)
    expected = "composite" if isinstance(value, (list, dict)) else "string scalars"
    with pytest.raises((TypeError, ValueError), match=expected):
        format_preserving_incident(changed)


def test_existing_protocols_remain_unchanged() -> None:
    incident = generate_incident_001(1001)
    raw_before = incident.model_view()
    redaction_before = redact_incident(incident)
    hmac_before = hmac_incident(incident, key=PUBLIC_TEST_KEY)
    tokenization_before = tokenize_incident(incident)
    format_preserving_incident(incident)
    assert incident.model_view() == raw_before
    assert redact_incident(incident) == redaction_before
    assert hmac_incident(incident, key=PUBLIC_TEST_KEY) == hmac_before
    assert tokenize_incident(incident) == tokenization_before
    assert PACKAGE_VERSION == "redaction-v1"
    assert PROMPT_SHA256_V1 == (
        "0c06c1ec6d72ca08927a367aaf873d7bea2b34c6210ceb74824263dd7f2bd9cd"
    )
    assert PROMPT_SHA256_V2 == (
        "744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d"
    )


def test_development_config_is_exact_and_safe() -> None:
    definition = PilotDefinition.load(CONFIG)
    assert TRANSFORMATION_VERSION == "format-preserving-v1"
    assert definition.pilot_id == "format-preserving-v1-development"
    assert definition.condition == "format-preserving-v1"
    assert definition.seed_scope == "development_only"
    assert definition.development_seeds == tuple(range(1000, 1005))
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.requested_model == "gpt-5.6-luna"
    assert definition.reasoning_effort == "medium"
    assert "temperature" not in definition.decoding_settings
    assert definition.prompt_version == "raw-rca-v2"
    assert definition.prompt_sha256 == PROMPT_SHA256_V2
    assert definition.taxonomy_version == "rca-taxonomy-v2"
    assert definition.scorer_version == "raw-rca-scorer-v2"


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
def test_config_rejects_validation_held_out_and_mislabeled_seeds(
    tmp_path: Path, original: str, changed: str, message: str
) -> None:
    path = tmp_path / "invalid-format-preserving.toml"
    path.write_text(
        CONFIG.read_text(encoding="utf-8").replace(original, changed),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=message):
        PilotDefinition.load(path)


def test_command_is_pending_without_execute(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    results = tmp_path / "must-not-exist.jsonl"
    args = build_parser().parse_args(
        ["run-pilot", "--config", str(CONFIG), "--results", str(results)]
    )
    args.handler(args)
    pending = json.loads(capsys.readouterr().out)
    assert pending["execution"] == "pending"
    assert pending["pilot"]["condition"] == "format-preserving-v1"
    assert pending["pilot"]["development_seeds"] == list(range(1000, 1005))
    assert pending["pilot"]["validation_seeds"] == []
    assert pending["pilot"]["held_out_seeds"] == []
    assert not results.exists()
