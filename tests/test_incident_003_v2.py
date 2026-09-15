from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from diagbench.audits.incident_003 import audit_temporal_ablation
from diagbench.generators.incident_003 import TEMPORAL_TEMPLATES, generate_incident_003
from diagbench.generators.incident_003_v2 import (
    FAMILY_ID,
    GENERATOR_VERSION,
    PROTOCOL_VERSION,
    generate_incident_003_v2,
)
from diagbench.schema import IncidentV3
from diagpriv.evaluation import cli as evaluation_cli
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.incident_families import (
    INCIDENT_003_V2_DEVELOPMENT_SEEDS,
    INCIDENT_003_V2_FAMILY,
    INCIDENT_003_V2_SEED_SELECTION_VERSION,
)
from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.prompt_v3 import PROMPT_SHA256, build_prompt_v3
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.response import RCAResponseV3
from diagpriv.evaluation.runner import (
    ProtectedSeedError,
    RawRunConfig,
    prepare_model_input,
    run_raw_experiment,
)
from diagpriv.evaluation.scoring_v3 import RCAScoreV3

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "experiments" / "incident_003_v2_raw_sol_development.toml"
RESULT_NAME = "incident_003_v2_raw_sol_development_gpt_5_6_sol_medium.jsonl"
EXPECTED_SEEDS = (1019, 1020, 1021, 1022, 1023, 1025, 1026, 1028)
EXPECTED_HASHES = {
    1019: "2fdd467c9408b66de7a370b5bf7f9877316dfbfa4204bb93ff4c250b9822f452",
    1020: "454b06bcb400c718ac4ed6a29e4fba618d7b280f2bec13c1d03198246c4ac18e",
    1021: "4d5c3f69abfd5d8eb795fbf1dd5044e4a4621d49f8457ae9778780b2dae02f29",
    1022: "2135b32e0712b9feb2744a70f182b33c784f4d7797322b0e3f901aa9b6b71fba",
    1023: "f9c14cb3c14036565bd1a026fc96fce1c33abe88e8011a7f0e5926c88960c8c4",
    1025: "6275bcc7cc6531bdefacd060655c6613b504413c2b4053b897c3b74f6f52b2bc",
    1026: "be72cf270b660c9dd857a08fe7878d9adf1405dcbd73107097371b66a23eba6b",
    1028: "1acbf564bb312397a57935dbb81d8bd7307465b6a2e6d3667f834e110e030b14",
}


def _config(seed: int) -> RawRunConfig:
    return RawRunConfig(
        experiment_id=f"incident-003-v2-offline-{seed}",
        seed=seed,
        model="offline-fixture",
        model_version="test-version",
        incident_family=INCIDENT_003_V2_FAMILY,
        manifest_schema_version="raw-rca-manifest-v9",
        reasoning_effort="medium",
        decoding_settings={"max_output_tokens": 4096},
        intended_temperature=0.0,
        temperature_omission_reason="Temperature is intentionally omitted.",
        prompt_version="raw-rca-v3",
        timestamp="2037-01-01T00:00:00+00:00",
        expected_model_input_sha256=EXPECTED_HASHES.get(seed),
    )


def _response(seed: int) -> RCAResponseV3:
    incident = generate_incident_003_v2(seed)
    oracle = incident.ground_truth_v3
    assert oracle is not None
    target = incident.metadata["target_operation_id"]
    evidence_ids = tuple(
        str(row["evidence_id"])
        for source in (
            "workflow_attempts",
            "execution_observations",
            "effect_records",
            "compensation_records",
        )
        for row in incident.structured_evidence[source]
        if row["operation_id"] == target
    )
    return RCAResponseV3(
        observed_outcome=oracle.observed_outcome,
        trigger=oracle.trigger,
        subsequent_action=oracle.subsequent_action,
        failure_mechanism=oracle.failure_mechanism,
        affected_component=oracle.affected_component,
        supporting_evidence=evidence_ids,
        explanation="Offline protocol fixture.",
        confidence=0.9,
    )


def test_v2_wraps_frozen_v1_without_mutating_v1_behavior() -> None:
    before = generate_incident_003(1019)
    v2 = generate_incident_003_v2(1019)
    after = generate_incident_003(1019)
    assert before == after
    assert before.model_view() == v2.model_view()
    assert not hasattr(before, "ground_truth_v3")
    assert before.ground_truth_v2.failure_mechanism == "incorrect_state_transition"
    assert v2.ground_truth_v2 == before.ground_truth_v2
    assert v2.ground_truth_v3 is not None
    assert v2.ground_truth_v3.failure_mechanism == "incorrect_concurrency_control"
    assert v2.incident_id == FAMILY_ID
    assert v2.metadata["generator_version"] == GENERATOR_VERSION
    assert v2.metadata["protocol_version"] == PROTOCOL_VERSION
    assert v2.metadata["construction_generator_version"] == (
        "incident-003-generator-v1"
    )
    assert IncidentV3.from_json(v2.to_json()) == v2


def test_fresh_seed_selection_is_exact_and_stops_at_1028() -> None:
    selected: list[int] = []
    counts = {name: 0 for name in TEMPORAL_TEMPLATES}
    seed = 1019
    while any(count < 2 for count in counts.values()):
        template = str(generate_incident_003_v2(seed).metadata["temporal_template_name"])
        if counts[template] < 2:
            selected.append(seed)
            counts[template] += 1
        seed += 1
    assert tuple(selected) == EXPECTED_SEEDS
    assert tuple(selected) == INCIDENT_003_V2_DEVELOPMENT_SEEDS
    assert set(counts.values()) == {2}
    assert seed == 1029


def test_v2_preserves_the_reviewed_temporal_ablation() -> None:
    for seed in EXPECTED_SEEDS:
        report = audit_temporal_ablation(generate_incident_003_v2(seed))
        assert report["passed"] is True
        assert report["timestamp_ablation_classification"] == (
            "unavailable_not_preserved"
        )


def test_v3_config_is_development_only_and_version_locked() -> None:
    definition = PilotDefinition.load(CONFIG)
    assert definition.incident_family == INCIDENT_003_V2_FAMILY
    assert definition.development_seed_selection_version == (
        INCIDENT_003_V2_SEED_SELECTION_VERSION
    )
    assert definition.manifest_schema_version == "raw-rca-manifest-v9"
    assert definition.development_seeds == EXPECTED_SEEDS
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.condition == "raw"
    assert definition.prompt_version == "raw-rca-v3"
    assert definition.prompt_sha256 == PROMPT_SHA256
    assert definition.taxonomy_version == "rca-taxonomy-v3"
    assert definition.scorer_version == "raw-rca-scorer-v3"
    assert definition.expected_model_input_sha256_by_seed == EXPECTED_HASHES


@pytest.mark.parametrize("seed", [1000, 1018, 1024, 1027, 1029, 1999, 2000, 20000])
def test_v3_runner_rejects_nonfrozen_seeds_before_generation(
    seed: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    generated = False

    def fail_if_generated(candidate: int):
        nonlocal generated
        generated = True
        raise AssertionError(f"Unapproved seed {candidate} was generated")

    monkeypatch.setattr(
        "diagpriv.evaluation.incident_families.generate_incident_003_v2",
        fail_if_generated,
    )
    with pytest.raises(ProtectedSeedError):
        prepare_model_input(_config(seed))
    assert generated is False


def test_v3_manifest_round_trip_versions_semantic_score() -> None:
    seed = 1019
    provider = FakeProvider(raw_output=_response(seed).to_json())
    manifest = run_raw_experiment(_config(seed), provider)
    assert manifest.manifest_schema_version == "raw-rca-manifest-v9"
    assert manifest.prompt_version == "raw-rca-v3"
    assert manifest.taxonomy_version == "rca-taxonomy-v3"
    assert manifest.scorer_version == "raw-rca-scorer-v3"
    assert manifest.evidence_support_version == "evidence-support-v3"
    assert manifest.model_input_sha256 == EXPECTED_HASHES[seed]
    assert isinstance(manifest.score, RCAScoreV3)
    assert manifest.score.overall_correct is True
    restored = ExperimentManifest.from_json(manifest.to_json())
    assert restored == manifest


def test_v3_hashes_exact_rendered_model_input_and_excludes_hidden_data() -> None:
    for seed in EXPECTED_SEEDS:
        incident = generate_incident_003_v2(seed)
        prompt = build_prompt_v3(incident.model_view())
        assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == EXPECTED_HASHES[seed]
        for forbidden in (
            "ground_truth_v3",
            "diagnostic_invariants",
            "expected_evidence",
            "sensitive_fields",
            "target_operation_id",
            "temporal_template_name",
            "construction_generator_version",
        ):
            assert forbidden not in prompt


def test_v3_dry_run_preflights_without_provider_or_result(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = tmp_path / RESULT_NAME

    def provider_must_not_be_configured(definition: PilotDefinition):
        raise AssertionError(f"Provider configured during dry run: {definition.pilot_id}")

    monkeypatch.setattr(evaluation_cli, "_openai_provider", provider_must_not_be_configured)
    args = build_parser().parse_args(
        ["run-pilot", "--config", str(CONFIG), "--results", str(result)]
    )
    args.handler(args)
    payload = json.loads(capsys.readouterr().out)
    assert payload["execution"] == "pending"
    assert payload["scheduled_calls"] == 8
    assert payload["pilot"]["validation_seeds"] == []
    assert payload["pilot"]["held_out_seeds"] == []
    assert payload["input_preflight"]["model_input_sha256_by_seed"] == {
        str(seed): digest for seed, digest in EXPECTED_HASHES.items()
    }
    assert result.exists() is False
