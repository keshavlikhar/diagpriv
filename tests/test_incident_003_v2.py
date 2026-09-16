from __future__ import annotations

from dataclasses import replace
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
    target_completion_order_variant,
)
from diagbench.schema import IncidentV3
from diagpriv.evaluation import cli as evaluation_cli
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.incident_families import (
    INCIDENT_003_V2_DEVELOPMENT_SEEDS,
    INCIDENT_003_V2_FAMILY,
    INCIDENT_003_V2_SEED_SELECTION_VERSION,
)
from diagpriv.evaluation.incident_003_v2_evidence import (
    build_incident_003_v2_evidence_rubric,
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
EXPECTED_RUBRIC_HASHES = {
    1019: "c01d15e2f8ea4e857b324f803769b1fe9eaff30434a9a64d16a6d10b8766c0db",
    1020: "d8f4d67988180b0692f4a1e3f12c8d97e02489fe986c3f62ce17400da04f1377",
    1021: "e8d55010bc62f36f9982ce0bfe96b89995c3990ce99a4cbb5088dae96117feac",
    1022: "f0eb6ca56f15e43421c6168467179898f51098a7ddb22852dd037bb9d0649c64",
    1023: "5703cbb60e3db5220fa73e6a12231332f2cdb2c1714845f1981268789ddc1f60",
    1025: "03348ab34228647752a384c8e01be7d4af74607a140aa16c65cc1d9dac7399b5",
    1026: "d67a92a6bccdb6891bfb3f437a68abc42a1f36719776a15d9a5a7be65cc45a9b",
    1028: "2524b8e23b63f739dc555a16600f54e44d5e942207b80fdf7291ab021cb89d26",
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
        expected_evidence_requirement_set_sha256=EXPECTED_RUBRIC_HASHES.get(seed),
        expected_incident_generator_version=GENERATOR_VERSION,
        expected_incident_protocol_version=PROTOCOL_VERSION,
        expected_evidence_support_version="evidence-support-v3",
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
    assert (
        definition.expected_evidence_requirement_set_sha256_by_seed
        == EXPECTED_RUBRIC_HASHES
    )
    assert definition.expected_incident_generator_version == GENERATOR_VERSION
    assert definition.expected_incident_protocol_version == PROTOCOL_VERSION
    assert definition.expected_evidence_support_version == "evidence-support-v3"


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
    assert manifest.incident_generator_version == GENERATOR_VERSION
    assert manifest.incident_protocol_version == PROTOCOL_VERSION
    assert manifest.evidence_requirement_set_sha256 == EXPECTED_RUBRIC_HASHES[seed]
    assert isinstance(manifest.score, RCAScoreV3)
    assert manifest.score.overall_correct is True
    restored = ExperimentManifest.from_json(manifest.to_json())
    assert restored == manifest

    for field in (
        "incident_generator_version",
        "incident_protocol_version",
        "evidence_requirement_set_sha256",
    ):
        with pytest.raises(ValueError):
            replace(manifest, **{field: None})


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
    assert payload["input_preflight"][
        "evidence_requirement_set_sha256_by_seed"
    ] == {str(seed): digest for seed, digest in EXPECTED_RUBRIC_HASHES.items()}
    assert result.exists() is False


@pytest.mark.parametrize(
    ("frozen_hash", "message"),
    [
        (
            EXPECTED_HASHES[1019],
            "Prepared model input differs from frozen provenance for seed 1019",
        ),
        (
            EXPECTED_RUBRIC_HASHES[1019],
            "Prepared evidence requirement set differs from frozen provenance for seed 1019",
        ),
    ],
)
def test_v3_input_and_rubric_hash_mismatch_stop_before_provider_setup(
    frozen_hash: str,
    message: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pricing = ROOT / "experiments" / "pricing" / "openai_gpt_5_6_sol_2026-09-10.toml"
    changed = CONFIG.read_text(encoding="utf-8").replace(frozen_hash, "0" * 64)
    changed = changed.replace(
        'snapshot = "pricing/openai_gpt_5_6_sol_2026-09-10.toml"',
        f'snapshot = "{pricing}"',
    )
    changed_config = tmp_path / "changed.toml"
    changed_config.write_text(changed, encoding="utf-8")
    provider_configured = False

    def provider_must_not_be_configured(definition: PilotDefinition):
        nonlocal provider_configured
        provider_configured = True
        raise AssertionError(definition.pilot_id)

    monkeypatch.setattr(evaluation_cli, "_openai_provider", provider_must_not_be_configured)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(changed_config),
            "--results",
            str(tmp_path / "result.jsonl"),
            "--execute",
        ]
    )
    with pytest.raises(ValueError, match=message):
        args.handler(args)
    assert provider_configured is False


def test_v3_invalid_rubric_stops_before_provider_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incident = generate_incident_003_v2(1019)
    rubric = build_incident_003_v2_evidence_rubric(incident)
    first_requirement = rubric.requirements[0]
    first_path = first_requirement.acceptable_paths[0]
    invalid_rubric = replace(
        rubric,
        requirements=(
            replace(
                first_requirement,
                acceptable_paths=(
                    replace(
                        first_path,
                        evidence_ids=(*first_path.evidence_ids, "NOT-AN-EVIDENCE-ID"),
                        minimum_group_requirement=len(first_path.evidence_ids) + 1,
                    ),
                ),
            ),
            *rubric.requirements[1:],
        ),
    )
    monkeypatch.setattr(
        "diagpriv.evaluation.runner.build_evidence_rubric_v3",
        lambda _: invalid_rubric,
    )
    pricing = ROOT / "experiments" / "pricing" / "openai_gpt_5_6_sol_2026-09-10.toml"
    changed = CONFIG.read_text(encoding="utf-8").replace(
        'snapshot = "pricing/openai_gpt_5_6_sol_2026-09-10.toml"',
        f'snapshot = "{pricing}"',
    )
    changed_config = tmp_path / "invalid-rubric.toml"
    changed_config.write_text(changed, encoding="utf-8")
    provider_configured = False

    def provider_must_not_be_configured(definition: PilotDefinition):
        nonlocal provider_configured
        provider_configured = True
        raise AssertionError(definition.pilot_id)

    monkeypatch.setattr(evaluation_cli, "_openai_provider", provider_must_not_be_configured)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(changed_config),
            "--results",
            str(tmp_path / "result.jsonl"),
            "--execute",
        ]
    )
    with pytest.raises(ValueError, match="nonexistent evidence"):
        args.handler(args)
    assert provider_configured is False


def test_seed_1021_completion_equality_is_reporting_only() -> None:
    incident = generate_incident_003_v2(1021)
    target = incident.metadata["target_operation_id"]
    execution = next(
        row
        for row in incident.structured_evidence["execution_observations"]
        if row["operation_id"] == target
    )
    compensation = next(
        row
        for row in incident.structured_evidence["compensation_records"]
        if row["operation_id"] == target
    )
    assert execution["completed_at"] == compensation["completed_at"]
    assert target_completion_order_variant(incident) == "equal"
    assert incident.metadata["target_completion_order_variant"] == "equal"
    report = audit_temporal_ablation(incident)
    assert report["pre_ablation_target_temporal_profile"][
        "execution_compensation_overlap"
    ] == "true"
    assert report["passed"] is True
