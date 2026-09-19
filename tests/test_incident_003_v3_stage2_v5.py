"""Offline guards for prospective paired Stage-2 evidence-support-v5."""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import subprocess

import pytest

from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.incident_families import INCIDENT_003_V3_FAMILY
from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.response import RCAResponseV3
from diagpriv.evaluation.runner import (
    ProtectedSeedError,
    RawRunConfig,
    prepare_model_input,
    run_raw_experiment,
)
from diagpriv.evaluation.stage2_v5_reporting import summarize_stage2_v5
from diagpriv.transformations.provenance import (
    transformation_configuration_for_condition,
    transformation_configuration_sha256,
)

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "experiments/incident_003_v3_relative_time_v1_paired_sol_development_v5.toml"
HISTORICAL = ROOT / "experiments/incident_003_v3_relative_time_v1_paired_sol_development.toml"
RESULT = ROOT / "results/incident_003_v3_relative_time_v1_paired_sol_development_evidence_v5_gpt_5_6_sol_medium.jsonl"
MODEL_HASHES = {
    "1319:target": "a5bd805e6f4db8cb22c6bcdf160f82446aaa4de9900b545db75aac458063c765",
    "1319:temporal_twin": "1b83853f0f246341cfef515fbe870d703739492875bb5d11cae115461bf6c80f",
    "1299:target": "b7dc8a177cdaab04b7e1943de63337dd3ad8fbef3e62a06f8a6392388eb6a354",
    "1299:temporal_twin": "bafb78e26c66d7e9e740c3e009f118222a7c5be6d33738e56814058bd3ca724c",
    "1387:target": "976b254d1e471f073fe3265381f9de12c222055af542af7d21a9b507a24946f8",
    "1387:temporal_twin": "401a2e3e5689cb39c554c3babbc847c64e3cfdb66f8c29dbd712399c1e3ab5d6",
    "1222:target": "57134350497a57636869c19eb2938a491639d28f4f7481aa289fa6e9736193a7",
    "1222:temporal_twin": "5c90a29ed5d622b5912bda17f06f61ff997f0ef5bf35ef7e82a679167cff9bf2",
}
V5_REQUIREMENT_HASHES = {
    "1319:target": "c68aa89d9b9414a520435eea7f0830a4f7ce8e1e0b56fd09d5feaa995381593d",
    "1319:temporal_twin": "745df9f32e9768c064a61dbce43d424dfbd62c544d62cd33c7d21c2f9cf775cd",
    "1299:target": "832a09456766ee9fbdb5796327be33375190435b8db18a63b8af85587c3d2ca5",
    "1299:temporal_twin": "9576f9e5271054daeb41dc6ef8e9654b4ec7a0630dbdcbacd89010b909874794",
    "1387:target": "d5d6bee92d6db457153f8f97325ea295552b53330e8366f7fd7e0b692f415579",
    "1387:temporal_twin": "189c2295b1b7eb69ad9d0c2b6f91cec864ff17b39f0466051a803fc31cdf5c09",
    "1222:target": "6a6e4571351b6d726c65588e19f44bfd0d179ece291861b8071644a6c81c732b",
    "1222:temporal_twin": "e09c002225b8e1bc35098e56682a66c4f74ac72c6c9c6e2cc2edb3edd60484a3",
}


def _definition() -> PilotDefinition:
    return PilotDefinition.load(CONFIG)


def _config(definition: PilotDefinition, case_id: str) -> RawRunConfig:
    seed_text, role = case_id.split(":", 1)
    return RawRunConfig(
        experiment_id=f"{definition.pilot_id}-development-{case_id}-call-1",
        seed=int(seed_text),
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
        expected_model_input_sha256=MODEL_HASHES[case_id],
        expected_evidence_requirement_set_sha256=V5_REQUIREMENT_HASHES[case_id],
        expected_incident_generator_version=definition.expected_incident_generator_version,
        expected_incident_protocol_version=definition.expected_incident_protocol_version,
        expected_evidence_support_version=definition.expected_evidence_support_version,
        expected_transformation_configuration_sha256=definition.expected_transformation_configuration_sha256,
        query_role=role,
        case_id=case_id,
        expected_paired_query_protocol_version=definition.expected_paired_query_protocol_version,
        expected_anchor_allocation_version=definition.expected_anchor_allocation_version,
        expected_evidence_requirement_version=definition.expected_evidence_requirement_version,
        expected_semantic_evaluator_version=definition.expected_semantic_evaluator_version,
    )


def _response(config: RawRunConfig, mechanism: str | None = None) -> str:
    prepared = prepare_model_input(config)
    oracle = prepared.incident.ground_truth_v3
    assert prepared.evidence_rubric is not None
    citations = tuple(dict.fromkeys(
        evidence_id
        for requirement in prepared.evidence_rubric.requirements
        if requirement.kind == "essential"
        for path in requirement.acceptable_paths
        if dict(path.semantic_parameters)["modality"] == "logs"
        for evidence_id in path.evidence_ids
    ))
    return RCAResponseV3(
        observed_outcome=oracle.observed_outcome,
        trigger=oracle.trigger,
        subsequent_action=oracle.subsequent_action,
        failure_mechanism=mechanism or oracle.failure_mechanism,
        affected_component=oracle.affected_component,
        supporting_evidence=citations,
        explanation="Synthetic offline test response.",
        confidence=0.9,
    ).to_json()


def test_stage2_v12_is_exactly_eight_development_cases_with_frozen_settings() -> None:
    definition = _definition()
    historical = PilotDefinition.load(HISTORICAL)
    assert definition.incident_family == INCIDENT_003_V3_FAMILY
    assert definition.manifest_schema_version == "raw-rca-manifest-v12"
    assert historical.manifest_schema_version == "raw-rca-manifest-v11"
    assert historical.expected_evidence_support_version == "evidence-support-v4"
    assert definition.condition == "relative-time-v1"
    assert definition.development_seeds == (1319, 1299, 1387, 1222)
    assert definition.query_roles == ("target", "temporal_twin")
    assert definition.calls_per_seed == 1
    assert definition.validation_seeds == definition.held_out_seeds == ()
    assert len(definition.paired_case_plan()) == 8
    assert definition.requested_model == "gpt-5.6-sol"
    assert definition.reasoning_effort == "medium"
    assert definition.decoding_settings == {"max_output_tokens": 4096}
    assert definition.intended_temperature == 0.0
    assert definition.effective_temperature is None
    assert definition.prompt_version == "raw-rca-v3"
    assert definition.prompt_sha256 == "a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139"
    assert definition.taxonomy_version == "rca-taxonomy-v3"
    assert definition.scorer_version == "raw-rca-scorer-v3"
    assert definition.expected_evidence_support_version == "evidence-support-v5"
    assert definition.expected_evidence_requirement_version == "incident-003-v3-evidence-requirements-v3"
    assert definition.expected_semantic_evaluator_version == "incident-003-v3-evidence-semantic-evaluator-v3"
    assert definition.expected_incident_generator_version == "incident-003-generator-v3"
    assert definition.expected_incident_protocol_version == "incident-003-temporal-protocol-v3"
    assert definition.result_path_must_not_exist


def test_all_eight_inputs_match_preexisting_v11_hashes_and_new_pinned_v5_rubrics() -> None:
    definition = _definition()
    historical = PilotDefinition.load(HISTORICAL)
    assert historical.expected_model_input_sha256_by_case_id == MODEL_HASHES
    assert definition.expected_model_input_sha256_by_case_id == MODEL_HASHES
    assert definition.expected_evidence_requirement_set_sha256_by_case_id == V5_REQUIREMENT_HASHES
    assert definition.expected_transformation_configuration_sha256 == (
        "cf91779e926974db44fcc71422a31d12b6271c88711322c9151968dbd4c01660"
    )
    assert transformation_configuration_sha256(
        transformation_configuration_for_condition("relative-time-v1")
    ) == definition.expected_transformation_configuration_sha256
    for _, _, case_id in definition.paired_case_plan():
        prepared = prepare_model_input(_config(definition, case_id))
        assert hashlib.sha256(prepared.prompt.encode("utf-8")).hexdigest() == MODEL_HASHES[case_id]
        assert prepared.evidence_requirement_set_sha256 == V5_REQUIREMENT_HASHES[case_id]
        assert prepared.evidence_support_version == "evidence-support-v5"
        assert prepared.semantic_evaluator_version == "incident-003-v3-evidence-semantic-evaluator-v3"
        assert prepared.transformation_provenance.temporal_semantics_version == "relative-time-semantics-v1"


def test_v12_manifest_round_trip_and_v5_scoring_are_offline() -> None:
    definition = _definition()
    config = _config(definition, "1319:temporal_twin")
    manifest = run_raw_experiment(config, FakeProvider(raw_output=_response(config)))
    assert manifest.score is not None
    assert manifest.score.exact_root_cause_correct
    assert manifest.score.evidence_supported
    assert manifest.score.selected_evidence_paths
    assert manifest.model_input_sha256 == MODEL_HASHES[config.case_id]
    assert manifest.evidence_requirement_set_sha256 == V5_REQUIREMENT_HASHES[config.case_id]
    assert manifest.transformation_provenance.transformation_configuration_sha256 == definition.expected_transformation_configuration_sha256
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest


def test_v12_and_v11_reject_cross_version_evidence_protocols() -> None:
    definition = _definition()
    config = _config(definition, "1319:target")
    manifest = run_raw_experiment(config, FakeProvider(raw_output=_response(config)))
    with pytest.raises(ValueError, match="requires one of"):
        replace(manifest, evidence_support_version="evidence-support-v4")
    old = PilotDefinition.load(HISTORICAL)
    with pytest.raises(ValueError, match="frozen paired protocol versions"):
        replace(old, expected_evidence_support_version="evidence-support-v5").validate()
    assert old.manifest_schema_version == "raw-rca-manifest-v11"
    for filename, version in (
        ("incident_003_v2_raw_sol_development.toml", "raw-rca-manifest-v9"),
        ("incident_003_v2_relative_time_v1_sol_development.toml", "raw-rca-manifest-v10"),
    ):
        assert PilotDefinition.load(ROOT / "experiments" / filename).manifest_schema_version == version


@pytest.mark.parametrize("change", (
    {"case_id": "1319:target"},
    {"query_role": "target"},
    {"seed": 2000},
    {"seed": 20000},
    {"condition": "raw"},
    {"expected_evidence_support_version": "evidence-support-v4"},
    {"expected_evidence_requirement_set_sha256": "0" * 64},
    {"expected_model_input_sha256": "0" * 64},
))
def test_stage2_v12_fails_closed_before_any_provider_setup(change: dict[str, object]) -> None:
    config = _config(_definition(), "1319:temporal_twin")
    with pytest.raises((ValueError, ProtectedSeedError)):
        prepare_model_input(replace(config, **change))


def test_v12_manifest_rejects_inconsistent_paired_and_transformation_provenance() -> None:
    config = _config(_definition(), "1319:target")
    manifest = run_raw_experiment(config, FakeProvider(raw_output=_response(config)))
    for change in (
        {"case_id": "1319:temporal_twin"},
        {"construction_seed": 1299},
        {"semantic_evaluator_version": "incident-003-v3-evidence-semantic-evaluator-v2"},
        {"condition": "raw"},
        {"transformation_provenance": None},
    ):
        with pytest.raises(ValueError):
            replace(manifest, **change)


def test_paired_report_preserves_unavailable_and_unattempted_denominators() -> None:
    definition = _definition()
    first = _config(definition, "1319:target")
    twin = _config(definition, "1319:temporal_twin")
    valid = run_raw_experiment(first, FakeProvider(raw_output=_response(first)))
    parser_failure = run_raw_experiment(twin, FakeProvider(raw_output="{"))
    report = summarize_stage2_v5(definition, (valid, parser_failure))
    assert report["planned_cases"] == 8
    assert report["attempted_calls"] == 2
    assert report["valid_responses"] == report["observed_denominator"] == 1
    assert report["rca"]["exact_correct"] == 1
    assert report["infrastructure"]["parser_failures"] == 1
    assert report["paired"]["observed_denominator"] == 0
    assert report["paired"]["patterns"]["1319"] == "unavailable"
    assert report["paired"]["patterns"]["1299"] == "unavailable"
    assert report["paired"]["unavailability"]["1319"] == {
        "target": "valid", "temporal_twin": "malformed_json"
    }
    assert report["paired"]["unavailability"]["1299"] == {
        "target": "unattempted", "temporal_twin": "unattempted"
    }
    assert report["evidence_v5"]["supported_count"] == 1
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_stage2_v5(definition, (valid, valid))


def test_paired_report_pattern_categories_are_exclusive() -> None:
    definition = _definition()
    requested = {
        1319: ("incorrect_concurrency_control", "incorrect_state_transition"),
        1299: ("incorrect_concurrency_control", "incorrect_concurrency_control"),
        1387: ("incorrect_state_transition", "incorrect_state_transition"),
        1222: ("incorrect_retry_policy", "incorrect_state_transition"),
    }
    manifests = []
    for seed, role, case_id in definition.paired_case_plan():
        config = _config(definition, case_id)
        label = requested[seed][0 if role == "target" else 1]
        manifests.append(run_raw_experiment(config, FakeProvider(raw_output=_response(config, label))))
    report = summarize_stage2_v5(definition, manifests)
    assert report["paired"]["patterns"] == {
        "1319": "correct_mechanism_flip",
        "1299": "both_concurrency",
        "1387": "both_state_transition",
        "1222": "one_or_both_other_valid_mechanism_labels",
    }
    assert report["paired"]["observed_denominator"] == 4
    assert report["attempted_calls"] == report["valid_responses"] == 8


def test_stage2_result_is_ignored_and_dry_run_creates_no_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", str(RESULT)], cwd=ROOT, check=False
    )
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(RESULT)],
        cwd=ROOT, check=False, capture_output=True,
    )
    assert ignored.returncode == 0
    assert tracked.returncode != 0
    candidate = tmp_path / "stage2-dry-run.jsonl"
    args = build_parser().parse_args([
        "run-pilot", "--config", str(CONFIG), "--results", str(candidate)
    ])
    args.handler(args)
    assert '"execution": "pending"' in capsys.readouterr().out
    assert not candidate.exists()
