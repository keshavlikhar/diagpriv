from __future__ import annotations

import base64
import json
from pathlib import Path

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
from diagpriv.transformations.hmac_v1 import (
    HMAC_KEY_ENVIRONMENT_VARIABLE,
    TRANSFORMATION_VERSION,
    hmac_incident,
    hmac_token,
    parse_hmac_key_hex,
)
from diagpriv.transformations.redaction_v1 import redact_incident

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "experiments" / "hmac_v1_development.toml"
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


def test_hmac_v1_changes_exactly_annotated_fields() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = hmac_incident(incident, key=PUBLIC_TEST_KEY)
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
                    assert str(transformed_row[field]).startswith("HMAC1_")
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
                assert str(transformed_value).startswith("HMAC1_")
            else:
                assert transformed_value == getattr(original_entry, field)
        assert original_entry.attributes.keys() == transformed_entry.attributes.keys()
        for field, original_value in original_entry.attributes.items():
            path = f"logs.{field}"
            if path in sensitive_paths:
                assert transformed_entry.attributes[field] != original_value
                assert str(transformed_entry.attributes[field]).startswith("HMAC1_")
            else:
                assert transformed_entry.attributes[field] == original_value


def test_hmac_v1_preserves_deterministic_equality_within_namespaces() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = hmac_incident(incident, key=PUBLIC_TEST_KEY)

    for annotation in incident.sensitive_fields:
        before = _path_values(original, annotation.path)
        after = _path_values(transformed, annotation.path)
        mapping: dict[object, JSONValue] = {}
        for plaintext, pseudonym in zip(before, after, strict=True):
            if plaintext in mapping:
                assert mapping[plaintext] == pseudonym
            else:
                mapping[plaintext] = pseudonym

    assert len(set(_path_values(original, "payments.request_id"))) < len(
        _path_values(original, "payments.request_id")
    )


def test_hmac_v1_preserves_inequality_with_negligible_collision_risk() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = hmac_incident(incident, key=PUBLIC_TEST_KEY)

    for annotation in incident.sensitive_fields:
        before = _path_values(original, annotation.path)
        after = _path_values(transformed, annotation.path)
        assert len(set(after)) == len(set(before))

    payment_ids = _path_values(transformed, "payments.payment_id")
    assert len(set(payment_ids)) == len(payment_ids)


def test_hmac_v1_preserves_intended_cross_source_identity() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = hmac_incident(incident, key=PUBLIC_TEST_KEY)

    grouped: dict[tuple[str, str, object], set[JSONValue]] = {}
    sources: dict[tuple[str, str, object], set[str]] = {}
    for annotation in incident.sensitive_fields:
        if annotation.policy != "consistent_pseudonym":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        for plaintext, pseudonym in zip(
            _path_values(original, annotation.path),
            _path_values(transformed, annotation.path),
            strict=True,
        ):
            identity = (annotation.classification, field, plaintext)
            grouped.setdefault(identity, set()).add(pseudonym)
            sources.setdefault(identity, set()).add(source)

    cross_source_identities = [
        identity for identity, identity_sources in sources.items() if len(identity_sources) > 1
    ]
    assert cross_source_identities
    assert all(len(grouped[identity]) == 1 for identity in cross_source_identities)

    target_request = incident.metadata["target_request_id"]
    payment_pairs = dict(
        zip(
            _path_values(original, "payments.request_id"),
            _path_values(transformed, "payments.request_id"),
            strict=True,
        )
    )
    log_pairs = dict(
        zip(
            _path_values(original, "logs.request_id"),
            _path_values(transformed, "logs.request_id"),
            strict=True,
        )
    )
    assert payment_pairs[target_request] == log_pairs[target_request]


def test_independent_policy_uses_source_qualified_namespaces() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = hmac_incident(incident, key=PUBLIC_TEST_KEY)
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


def test_hmac_v1_leaks_no_sensitive_plaintext() -> None:
    incident = generate_incident_001(1001)
    original = incident.model_view()
    transformed = hmac_incident(incident, key=PUBLIC_TEST_KEY)
    sensitive_plaintext = {
        value
        for annotation in incident.sensitive_fields
        for value in _path_values(original, annotation.path)
    }
    transformed_values = set(_all_scalar_values(transformed.to_dict()))
    assert sensitive_plaintext
    assert sensitive_plaintext.isdisjoint(transformed_values)
    serialized = transformed.to_json()
    assert all(str(value) not in serialized for value in sensitive_plaintext)


def test_hmac_v1_is_reproducible_with_same_key_and_changes_with_key() -> None:
    incident = generate_incident_001(1001)
    first = hmac_incident(incident, key=PUBLIC_TEST_KEY)
    second = hmac_incident(incident, key=PUBLIC_TEST_KEY)
    different = hmac_incident(incident, key=bytes(reversed(range(32))))
    assert first == second
    assert first != different


def test_hmac_v1_public_test_vector_and_fixed_nonformat_token() -> None:
    token = hmac_token(
        "SYN-REQ-23555431",
        key=PUBLIC_TEST_KEY,
        namespace="shared:operational_identifier:request_id",
    )
    assert token == "HMAC1_1oEsGYTJYIhjCMvAmBcsVKK4nOspCZ5ggDWJWKvEP_U"
    assert len(token) == 49
    assert "SYN-REQ" not in token


@pytest.mark.parametrize("seed", range(1000, 1005))
def test_hmac_v1_has_expected_incident_001_invariant_profile(seed: int) -> None:
    incident = generate_incident_001(seed)
    results = {
        result.name: (result.preserved, result.status)
        for result in evaluate_invariants(
            incident, hmac_incident(incident, key=PUBLIC_TEST_KEY)
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


def test_hmac_model_view_excludes_oracle_and_privacy_metadata() -> None:
    incident = generate_incident_001(1001)
    transformed = hmac_incident(incident, key=PUBLIC_TEST_KEY)
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


def test_hmac_key_never_enters_prompt_manifest_result_or_repr(tmp_path: Path) -> None:
    incident = generate_incident_001(1001)
    provider = FakeProvider(raw_output="{}")
    result_path = tmp_path / "hmac-results.jsonl"
    config = RawRunConfig(
        experiment_id="hmac-v1-offline-test",
        seed=1001,
        model="offline-fixture",
        model_version="1",
        reasoning_effort="medium",
        condition="hmac-v1",
        decoding_settings={"max_output_tokens": 4096},
        prompt_version="raw-rca-v2",
        timestamp="2032-01-01T00:00:00+00:00",
        hmac_key=PUBLIC_TEST_KEY,
        transformation_key_id="public-test-key-only",
    )
    manifest = run_raw_experiment(config, provider, result_path=result_path)
    secret_representations = {
        PUBLIC_TEST_KEY.hex(),
        base64.b64encode(PUBLIC_TEST_KEY).decode("ascii"),
        repr(PUBLIC_TEST_KEY),
    }
    serialized_outputs = (
        provider.requests[0].prompt,
        manifest.to_json(),
        result_path.read_text(encoding="utf-8"),
        repr(config),
    )
    assert all(
        secret not in output
        for secret in secret_representations
        for output in serialized_outputs
    )
    assert "HMAC1_" in provider.requests[0].prompt
    assert manifest.transformation_key_id == "public-test-key-only"
    assert manifest.to_dict()["transformation_key_id"] == "public-test-key-only"
    for annotation in incident.sensitive_fields:
        for value in _path_values(incident.model_view(), annotation.path):
            assert str(value) not in provider.requests[0].prompt


@pytest.mark.parametrize(
    ("key", "key_id", "message"),
    [
        (None, "public-test-key-only", "requires an external HMAC key"),
        (PUBLIC_TEST_KEY, None, "requires a non-secret experimental key ID"),
    ],
)
def test_hmac_runner_requires_external_key_metadata_before_provider_invocation(
    key: bytes | None, key_id: str | None, message: str
) -> None:
    provider = FakeProvider(raw_output="{}")
    with pytest.raises(ValueError, match=message):
        run_raw_experiment(
            RawRunConfig(
                experiment_id="hmac-v1-missing-key",
                seed=1001,
                model="offline-fixture",
                model_version="1",
                condition="hmac-v1",
                decoding_settings={"max_output_tokens": 4096},
                prompt_version="raw-rca-v2",
                hmac_key=key,
                transformation_key_id=key_id,
            ),
            provider,
        )
    assert provider.requests == []


@pytest.mark.parametrize("invalid", ["", "not-hex", "00" * 31, "00" * 33])
def test_hmac_key_parser_rejects_invalid_values_without_echoing_them(
    invalid: str,
) -> None:
    with pytest.raises(ValueError) as caught:
        parse_hmac_key_hex(invalid)
    if invalid:
        assert invalid not in str(caught.value)


def test_hmac_v1_development_config_is_exact_safe_and_secret_free() -> None:
    definition = PilotDefinition.load(CONFIG)
    text = CONFIG.read_text(encoding="utf-8")
    assert TRANSFORMATION_VERSION == "hmac-v1"
    assert definition.pilot_id == "hmac-v1-development"
    assert definition.condition == "hmac-v1"
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
    assert definition.hmac_key_environment_variable == HMAC_KEY_ENVIRONMENT_VARIABLE
    assert definition.hmac_key_id == "hmac-v1-synthetic-experiment-key-001"
    assert PUBLIC_TEST_KEY.hex() not in text
    assert "PASTE_KEY_HERE" not in text


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
def test_hmac_v1_config_rejects_nondevelopment_seeds(
    tmp_path: Path, original: str, changed: str, message: str
) -> None:
    path = tmp_path / "invalid-hmac.toml"
    path.write_text(
        CONFIG.read_text(encoding="utf-8").replace(original, changed),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=message):
        PilotDefinition.load(path)


def test_hmac_v1_command_is_pending_without_key_or_execute(
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
    assert pending["pilot"]["condition"] == "hmac-v1"
    assert pending["pilot"]["development_seeds"] == list(range(1000, 1005))
    assert pending["pilot"]["validation_seeds"] == []
    assert pending["pilot"]["held_out_seeds"] == []
    assert pending["pilot"]["transformation"] == {
        "version": "hmac-v1",
        "key_environment_variable": HMAC_KEY_ENVIRONMENT_VARIABLE,
        "key_id": "hmac-v1-synthetic-experiment-key-001",
    }
    assert not results.exists()


def test_hmac_addition_leaves_raw_and_redaction_v1_behavior_unchanged() -> None:
    incident = generate_incident_001(1001)
    raw_before = incident.model_view()
    redaction_before = redact_incident(incident)
    hmac_incident(incident, key=PUBLIC_TEST_KEY)
    assert incident.model_view() == raw_before
    assert redact_incident(incident) == redaction_before
    assert PACKAGE_VERSION == "redaction-v1"
    assert PROMPT_SHA256_V1 == (
        "0c06c1ec6d72ca08927a367aaf873d7bea2b34c6210ceb74824263dd7f2bd9cd"
    )
    assert PROMPT_SHA256_V2 == (
        "744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d"
    )
