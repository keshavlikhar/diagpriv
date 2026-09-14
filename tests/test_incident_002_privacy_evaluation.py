from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

from diagbench.generators.incident_002 import generate_incident_002
from diagpriv.evaluation.cli import _input_preflight, build_parser
from diagpriv.evaluation.incident_families import (
    INCIDENT_002_DEVELOPMENT_SEEDS,
    INCIDENT_002_FAMILY,
    INCIDENT_002_SEED_SELECTION_VERSION,
)
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.runner import (
    RawRunConfig,
    prepare_model_input,
    run_raw_experiment,
)
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations import hmac_key_fingerprint

ROOT = Path(__file__).parents[1]
PUBLIC_TEST_KEY = bytes(range(32))
PROMPT_SHA256 = "744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d"
HMAC_KEY_ID = "hmac-v1-synthetic-experiment-key-001"
HMAC_KEY_FINGERPRINT = (
    "fd04c65f6329f9e8c42b392ea8b9253a6c88da58e6f3858a322228bee907997d"
)
TEMPERATURE_REASON = (
    "Temperature is omitted to preserve the decoding protocol used by the "
    "matched GPT-5.6 Sol raw-development baseline."
)

CONFIGS = {
    condition: ROOT
    / "experiments"
    / f"incident_002_{condition.replace('-', '_')}_sol_development.toml"
    for condition in (
        "redaction-v1",
        "hmac-v1",
        "tokenization-v1",
        "format-preserving-v1",
    )
}
RESULTS = {
    condition: ROOT
    / "results"
    / (
        f"incident_002_{condition.replace('-', '_')}_sol_development_"
        "gpt_5_6_sol_medium.jsonl"
    )
    for condition in CONFIGS
}
EXPECTED_HASHES = {
    "redaction-v1": {
        1000: "4ead5fc58caffefe3da1f87c77f41f92524e3f513e2eca8c4bde25cdd8bbb3a2",
        1001: "10e655bd365b063109c269e9ae0e54020e1958072b7bba91ee67d503fec0155e",
        1003: "10eddbe3ea2f86c6fe57f218f3df329a8c19872f955423c8aeae3609e11a34d8",
        1004: "a23e5deb3ba1935af72874bf595fc87e388d0d8f29d5cc3fbbab67409d629193",
        1005: "3d66f5311dc08b9c59e9d67ac1a1b15441824d4ed81d966150f02ec9117826f0",
        1017: "33eab7a6961ad57b109e7ff73b2e2342c005cc44b465992b90e973ca8d8645e4",
    },
    "hmac-v1": {
        1000: "94813c0294fd973f6248ae442c0f0ab048b017a86801afbc6a3e9a2f188a212c",
        1001: "eba2604433893e22d8cf10ff17c447c88715e4d8b4b916dbc228b5b0e6c7a746",
        1003: "c7803f059390fcf8ab4fc0c77386e60f4dd9509c661c367dd2c97509e7367de5",
        1004: "d43e37d02604517c53ae641b3ed4267558614175b722ccd22c4273b3430f8f80",
        1005: "5260a58dafd1a8c9114bc0c9f8d954486f4cc1869dd74dcc62d355b3aa506b20",
        1017: "64c301cac97a0c1deb182e5f854c256b795eb433d13ac56e7999a8f39d055ffd",
    },
    "tokenization-v1": {
        1000: "66a3b9aa3b4a7fa3af2bff66d8361d9fdb9fc3f09b3cf7130b8b264133fd1cb0",
        1001: "6bb0c75d95dbc0eb34da6b92c0968af818e2ffdf3365dcc2e2a37926a94e228c",
        1003: "bd440ccc4fa06b5b21ba3411c84f90e468fb7f38aead1d54d8d4dff4a1e4a48c",
        1004: "df838a3a2edfece1f69f188e12a28f636e9d58a51d5905a50f0f65daa1f1c345",
        1005: "a765a7e0b31080cb3f501c04d48e0f8f5bee307b21b31adc86789668d4b706f6",
        1017: "dc1e58d27ab0fa405e68404df4cdd6518424688c8decbb691c9d59da6a8bda01",
    },
    "format-preserving-v1": {
        1000: "76cd30855d3e1b0d68da9591e3c77eb0936ca229122fb6b8e850a1566f77e53a",
        1001: "b7f553459d8a840b5a789c625315fe4e1aee4c4c709169c10cdc7937522f05b0",
        1003: "de629ae11487212d73385ec08d4dc5e1a46d16c8ad5f9d3adeb226e07d71e86b",
        1004: "f0b7182216c5e7b2811ac94ed155374b05535464782cd08ef821f829aab44e4b",
        1005: "3c8d8d9446021144d3b637a708d5e37f7072fa87a8e6c36e0f929c3c64886e3d",
        1017: "e61aa72f7251084bb84826412c0ab49ab7fdc5f5e447b9002988b69cd54dd331",
    },
}

STRUCTURAL = {
    "healthy_identifier_pattern_consistency",
    "target_identifier_pattern_anomaly",
    "target_identifier_defect_signature",
    "target_identifier_length_delta",
}
LINKAGE = {
    "target_identifier_cross_source_identity",
    "control_identifier_cross_source_identity",
    "target_and_control_identifier_distinctness",
}
OPERATIONAL = {
    "target_lookup_miss_state",
    "control_lookup_success_state",
    "control_effect_presence",
    "target_event_order",
    "target_effect_absence",
}


def _run_config(
    definition: PilotDefinition,
    seed: int,
    *,
    hmac_key: bytes | None = None,
    expected_hash: bool = True,
) -> RawRunConfig:
    return RawRunConfig(
        experiment_id=f"offline-{definition.condition}-{seed}",
        seed=seed,
        model=definition.requested_model,
        model_version=None,
        incident_family=definition.incident_family,
        manifest_schema_version=definition.manifest_schema_version,
        reasoning_effort=definition.reasoning_effort,
        condition=definition.condition,
        decoding_settings=dict(definition.decoding_settings),
        intended_temperature=definition.intended_temperature,
        temperature_omission_reason=definition.temperature_omission_reason,
        prompt_version=definition.prompt_version,
        hmac_key=hmac_key,
        transformation_key_id=definition.hmac_key_id,
        expected_model_input_sha256=(
            definition.expected_model_input_sha256_by_seed[seed]
            if expected_hash
            else None
        ),
        expected_transformation_key_fingerprint=(
            definition.expected_transformation_key_fingerprint
            if expected_hash
            else None
        ),
    )


@pytest.mark.parametrize("condition", tuple(CONFIGS))
def test_privacy_configs_freeze_the_complete_matched_protocol(condition: str) -> None:
    definition = PilotDefinition.load(CONFIGS[condition])
    assert definition.incident_family == INCIDENT_002_FAMILY
    assert definition.manifest_schema_version == "raw-rca-manifest-v6"
    assert (
        definition.development_seed_selection_version
        == INCIDENT_002_SEED_SELECTION_VERSION
    )
    assert definition.condition == condition
    assert definition.development_seeds == INCIDENT_002_DEVELOPMENT_SEEDS
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.requested_model == "gpt-5.6-sol"
    assert definition.reasoning_effort == "medium"
    assert definition.decoding_settings == {"max_output_tokens": 4096}
    assert definition.intended_temperature == 0.0
    assert definition.effective_temperature is None
    assert definition.temperature_omission_reason == TEMPERATURE_REASON
    assert definition.prompt_version == "raw-rca-v2"
    assert definition.prompt_sha256 == PROMPT_SHA256
    assert definition.taxonomy_version == "rca-taxonomy-v2"
    assert definition.scorer_version == "raw-rca-scorer-v2"
    assert definition.expected_model_input_sha256_by_seed == EXPECTED_HASHES[condition]


def test_hmac_config_records_only_established_nonsecret_key_provenance() -> None:
    definition = PilotDefinition.load(CONFIGS["hmac-v1"])
    text = CONFIGS["hmac-v1"].read_text(encoding="utf-8")
    assert definition.hmac_key_environment_variable == "DIAGPRIV_HMAC_KEY_HEX"
    assert definition.hmac_key_id == HMAC_KEY_ID
    assert definition.expected_transformation_key_fingerprint == HMAC_KEY_FINGERPRINT
    assert PUBLIC_TEST_KEY.hex() not in text
    assert "OPENAI_API_KEY=" not in text
    assert "DIAGPRIV_HMAC_KEY_HEX=" not in text


@pytest.mark.parametrize(
    "condition",
    ("redaction-v1", "tokenization-v1", "format-preserving-v1"),
)
@pytest.mark.parametrize("seed", INCIDENT_002_DEVELOPMENT_SEEDS)
def test_nonsecret_transformed_model_inputs_match_frozen_hashes(
    condition: str, seed: int
) -> None:
    definition = PilotDefinition.load(CONFIGS[condition])
    prepared = prepare_model_input(_run_config(definition, seed))
    assert prepared.model_input_sha256 == EXPECTED_HASHES[condition][seed]


def test_hmac_preflight_verifies_key_fingerprint_and_hash_without_persisting_key() -> None:
    definition = PilotDefinition.load(CONFIGS["hmac-v1"])
    baseline = prepare_model_input(
        _run_config(definition, 1000, hmac_key=PUBLIC_TEST_KEY, expected_hash=False)
    )
    verified = prepare_model_input(
        replace(
            _run_config(
                definition,
                1000,
                hmac_key=PUBLIC_TEST_KEY,
                expected_hash=False,
            ),
            expected_model_input_sha256=baseline.model_input_sha256,
            expected_transformation_key_fingerprint=hmac_key_fingerprint(
                PUBLIC_TEST_KEY
            ),
        )
    )
    assert verified.model_input_sha256 == baseline.model_input_sha256
    assert verified.transformation_key_fingerprint == hmac_key_fingerprint(
        PUBLIC_TEST_KEY
    )
    assert PUBLIC_TEST_KEY.hex() not in repr(verified)


def test_hmac_cli_preflight_reports_only_nonsecret_provenance() -> None:
    definition = PilotDefinition.load(CONFIGS["hmac-v1"])
    hashes = {
        seed: prepare_model_input(
            _run_config(
                definition,
                seed,
                hmac_key=PUBLIC_TEST_KEY,
                expected_hash=False,
            )
        ).model_input_sha256
        for seed in INCIDENT_002_DEVELOPMENT_SEEDS
    }
    adjusted = replace(
        definition,
        expected_model_input_sha256_by_seed=hashes,
        expected_transformation_key_fingerprint=hmac_key_fingerprint(
            PUBLIC_TEST_KEY
        ),
    )
    report = _input_preflight(adjusted, hmac_key=PUBLIC_TEST_KEY)
    assert report["status"] == "verified"
    assert report["model_input_sha256_by_seed"] == {
        str(seed): digest for seed, digest in hashes.items()
    }
    assert report["transformation_key_id"] == HMAC_KEY_ID
    assert report["transformation_key_fingerprint"] == hmac_key_fingerprint(
        PUBLIC_TEST_KEY
    )
    assert PUBLIC_TEST_KEY.hex() not in json.dumps(report)


def test_input_provenance_mismatch_stops_before_provider_invocation() -> None:
    definition = PilotDefinition.load(CONFIGS["redaction-v1"])
    provider = FakeProvider()
    with pytest.raises(ValueError, match="differs from frozen provenance"):
        run_raw_experiment(
            replace(
                _run_config(definition, 1000),
                expected_model_input_sha256="0" * 64,
            ),
            provider,
        )
    assert provider.requests == []


@pytest.mark.parametrize("condition", tuple(CONFIGS))
@pytest.mark.parametrize("seed", INCIDENT_002_DEVELOPMENT_SEEDS)
def test_transformed_prompts_exclude_plaintext_and_hidden_research_metadata(
    condition: str, seed: int
) -> None:
    definition = PilotDefinition.load(CONFIGS[condition])
    prepared = prepare_model_input(
        _run_config(
            definition,
            seed,
            hmac_key=PUBLIC_TEST_KEY if condition == "hmac-v1" else None,
            expected_hash=condition != "hmac-v1",
        )
    )
    incident = generate_incident_002(seed)
    plaintext = {
        str(row["external_reference"])
        for source in ("processing_attempts", "lookup_observations")
        for row in incident.structured_evidence[source]
    }
    plaintext.update(
        str(entry.attributes["external_reference"])
        for entry in incident.log_evidence
        if "external_reference" in entry.attributes
    )
    assert all(value not in prepared.prompt for value in plaintext)
    assert str(incident.metadata["latent_valid_reference"]) not in prepared.prompt
    for marker in (
        "ground_truth",
        "diagnostic_invariants",
        "expected_evidence",
        "sensitive_fields",
        "defect_class",
        "observable_structural_delta",
        "latent_valid_reference",
        "component_mappings",
    ):
        assert marker not in prepared.prompt
    assert PUBLIC_TEST_KEY.hex() not in prepared.prompt


@pytest.mark.parametrize("condition", tuple(CONFIGS))
@pytest.mark.parametrize("seed", INCIDENT_002_DEVELOPMENT_SEEDS)
def test_offline_invariant_matrix_matches_preregistered_expectations(
    condition: str, seed: int
) -> None:
    definition = PilotDefinition.load(CONFIGS[condition])
    prepared = prepare_model_input(
        _run_config(
            definition,
            seed,
            hmac_key=PUBLIC_TEST_KEY if condition == "hmac-v1" else None,
            expected_hash=condition != "hmac-v1",
        )
    )
    results = {
        result.name: result.status
        for result in evaluate_invariants(prepared.incident, prepared.model_view)
    }
    assert all(results[name] == "genuine_preservation" for name in OPERATIONAL)
    assert (
        results["literal_external_reference_identity"]
        == "expected_non_preservation"
    )
    if condition == "redaction-v1":
        assert results["healthy_identifier_pattern_consistency"] == (
            "degenerate_pattern_collapse"
        )
        assert all(results[name] == "broken" for name in STRUCTURAL - {
            "healthy_identifier_pattern_consistency",
            "target_identifier_length_delta",
        })
        assert all(results[name] == "broken" for name in LINKAGE)
    elif condition == "hmac-v1":
        assert all(results[name] == "broken" for name in STRUCTURAL - {
            "target_identifier_length_delta"
        })
        assert all(results[name] == "genuine_preservation" for name in LINKAGE)
    elif condition == "tokenization-v1":
        assert results["healthy_identifier_pattern_consistency"] == (
            "degenerate_pattern_collapse"
        )
        assert all(results[name] == "broken" for name in STRUCTURAL - {
            "healthy_identifier_pattern_consistency",
            "target_identifier_length_delta",
        })
        assert all(results[name] == "genuine_preservation" for name in LINKAGE)
    else:
        assert all(results[name] == "genuine_preservation" for name in STRUCTURAL - {
            "target_identifier_length_delta"
        })
        assert all(results[name] == "genuine_preservation" for name in LINKAGE)

    if seed == 1003:
        assert "target_identifier_length_delta" not in results
    elif condition == "format-preserving-v1":
        assert results["target_identifier_length_delta"] == "genuine_preservation"
    else:
        assert results["target_identifier_length_delta"] == "broken"


@pytest.mark.parametrize("condition", tuple(CONFIGS))
def test_privacy_config_rejects_validation_held_out_and_seed_changes(
    condition: str, tmp_path: Path
) -> None:
    source = CONFIGS[condition].read_text(encoding="utf-8")
    changes = (
        ("validation_seeds = []", "validation_seeds = [2000]"),
        ("held_out_seeds = []", "held_out_seeds = [20000]"),
        (
            "development_seeds = [1000, 1001, 1003, 1004, 1005, 1017]",
            "development_seeds = [1000, 1001, 1002, 1003, 1004, 1005]",
        ),
    )
    for index, (original, changed) in enumerate(changes):
        path = tmp_path / f"invalid-{index}.toml"
        path.write_text(source.replace(original, changed), encoding="utf-8")
        with pytest.raises(ValueError):
            PilotDefinition.load(path)


@pytest.mark.parametrize(
    "condition",
    ("redaction-v1", "tokenization-v1", "format-preserving-v1"),
)
def test_dry_run_verifies_all_inputs_without_creating_a_result(
    condition: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = tmp_path / RESULTS[condition].name
    args = build_parser().parse_args(
        ["run-pilot", "--config", str(CONFIGS[condition]), "--results", str(result)]
    )
    args.handler(args)
    output = json.loads(capsys.readouterr().out)
    assert output["execution"] == "pending"
    assert output["input_preflight"]["status"] == "verified"
    assert output["input_preflight"]["model_input_sha256_by_seed"] == {
        str(seed): digest for seed, digest in EXPECTED_HASHES[condition].items()
    }
    assert not result.exists()


def test_result_paths_are_ignored_and_no_result_is_required_for_preparation() -> None:
    assert "results/*" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert all(path.relative_to(ROOT).parts[0] == "results" for path in RESULTS.values())


def test_frozen_raw_sol_config_keeps_its_historical_provenance_semantics() -> None:
    raw = PilotDefinition.load(
        ROOT / "experiments" / "incident_002_raw_sol_development.toml"
    )
    assert raw.condition == "raw"
    assert raw.expected_model_input_sha256_by_seed == {}
    assert raw.expected_transformation_key_fingerprint is None
    assert raw.matched_model_input_sha256_by_seed
