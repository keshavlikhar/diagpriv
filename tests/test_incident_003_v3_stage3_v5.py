"""Offline guards for prospective Stage-3 temporal ablation under evidence v5."""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import subprocess

import pytest

from diagbench.audits.incident_003 import temporally_ablated_model_view
from diagbench.audits.incident_003_v3_leakage import audit_incident_003_v3_leakage_range
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.evidence_support_v5 import score_evidence_support_v5
from diagpriv.evaluation.incident_003_v3_evidence_v5 import (
    build_incident_003_v3_evidence_rubric_v5,
    evidence_requirement_set_sha256_v5,
)
from diagpriv.evaluation.incident_003_v3_evidence_v5_semantics import (
    Incident003V3EvidenceSemanticEvaluatorV5,
)
from diagpriv.evaluation.incident_families import (
    INCIDENT_003_V3_FAMILY,
    generate_evaluation_incident,
)
from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.response import RCAResponseV3
from diagpriv.evaluation.runner import RawRunConfig, prepare_model_input, run_raw_experiment
from diagpriv.evaluation.stage3_v5_reporting import summarize_stage3_v5
from diagpriv.transformations.provenance import (
    TEMPORAL_SEMANTICS_UNAVAILABLE,
    transformation_configuration_for_condition,
    transformation_configuration_sha256,
)

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "experiments/incident_003_v3_temporal_ablation_v1_paired_sol_development_v5.toml"
HISTORICAL = ROOT / "experiments/incident_003_v3_temporal_ablation_v1_paired_sol_development.toml"
STAGE2 = ROOT / "experiments/incident_003_v3_relative_time_v1_paired_sol_development_v5.toml"
RESULT = ROOT / "results/incident_003_v3_temporal_ablation_v1_paired_sol_development_evidence_v5_gpt_5_6_sol_medium.jsonl"
MODEL_HASHES = {
    "1319:target": "a14a79f2c923e8a674ca5f6e88c07434841eadec509a8f457d5bf2428963037e",
    "1319:temporal_twin": "ad9400cf344a34b91ed7a3f5c0125c9f1c2c9b59f5737db1f69fa5016b55b9ec",
    "1299:target": "7d3bbafc8e003908f529259c9038e5e7e67c3c31ee6790c6a995d3b20ce1146b",
    "1299:temporal_twin": "7e8b263aff8e85d5bad358992001406bcdca87a9019370dff3b51d49552f2672",
    "1387:target": "0a66accda0e5aaba981a743526914ae81f6d3f79d712e91fd5a3ea7b57a26f8c",
    "1387:temporal_twin": "674aa91310a1b9185acf6e3c4276a69eb592d31320e7253d9420b2ae5f3dfcbb",
    "1222:target": "854c91718478adfa302f187728dc4b5a356b5f366b25d7867e3aa3d770d45a4f",
    "1222:temporal_twin": "49cb4c19fcac5eb9eaf388bb914d9abb6c7b77b3720973307fa7dc511f014c07",
}
V5_HASHES = {
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
        expected_evidence_requirement_set_sha256=V5_HASHES[case_id],
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
    oracle = prepare_model_input(config).incident.ground_truth_v3
    return RCAResponseV3(
        observed_outcome=oracle.observed_outcome,
        trigger=oracle.trigger,
        subsequent_action=oracle.subsequent_action,
        failure_mechanism=mechanism or oracle.failure_mechanism,
        affected_component=oracle.affected_component,
        supporting_evidence=(),
        explanation="Synthetic offline test response.",
        confidence=0.9,
    ).to_json()


def test_v13_config_is_exactly_eight_development_cases_and_v11_v12_stay_distinct() -> None:
    definition = _definition()
    assert definition.incident_family == INCIDENT_003_V3_FAMILY
    assert definition.manifest_schema_version == "raw-rca-manifest-v13"
    assert definition.condition == "temporal-ablation-v1"
    assert definition.development_seeds == (1319, 1299, 1387, 1222)
    assert definition.query_roles == ("target", "temporal_twin")
    assert len(definition.paired_case_plan()) == 8
    assert definition.calls_per_seed == 1
    assert definition.validation_seeds == definition.held_out_seeds == ()
    assert definition.seed_scope == "development_only"
    assert definition.result_path_must_not_exist
    assert definition.provider == "openai-responses"
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
    assert PilotDefinition.load(HISTORICAL).manifest_schema_version == "raw-rca-manifest-v11"
    assert PilotDefinition.load(HISTORICAL).expected_evidence_support_version == "evidence-support-v4"
    assert PilotDefinition.load(STAGE2).manifest_schema_version == "raw-rca-manifest-v12"
    assert PilotDefinition.load(STAGE2).condition == "relative-time-v1"


def test_all_eight_frozen_inputs_and_pinned_v5_rubrics_are_independently_verified() -> None:
    definition = _definition()
    assert PilotDefinition.load(HISTORICAL).expected_model_input_sha256_by_case_id == MODEL_HASHES
    assert definition.expected_model_input_sha256_by_case_id == MODEL_HASHES
    assert definition.expected_evidence_requirement_set_sha256_by_case_id == V5_HASHES
    assert definition.expected_transformation_configuration_sha256 == (
        "fc564bb585f3f30e0482c206b061d096a49c3bc824965043f9eeb3ff12d71f7b"
    )
    assert transformation_configuration_sha256(
        transformation_configuration_for_condition("temporal-ablation-v1")
    ) == definition.expected_transformation_configuration_sha256
    for _, _, case_id in definition.paired_case_plan():
        prepared = prepare_model_input(_config(definition, case_id))
        assert hashlib.sha256(prepared.prompt.encode()).hexdigest() == MODEL_HASHES[case_id]
        assert prepared.evidence_requirement_set_sha256 == V5_HASHES[case_id]
        assert prepared.evidence_support_version == "evidence-support-v5"
        assert prepared.semantic_evaluator_version == "incident-003-v3-evidence-semantic-evaluator-v3"
        assert prepared.transformation_provenance.temporal_semantics_version == TEMPORAL_SEMANTICS_UNAVAILABLE


def test_v13_manifest_round_trip_and_ablation_scoring_are_offline() -> None:
    config = _config(_definition(), "1319:target")
    manifest = run_raw_experiment(config, FakeProvider(raw_output=_response(config)))
    assert manifest.score is not None
    assert manifest.score.exact_root_cause_correct
    assert not manifest.score.evidence_supported
    assert manifest.model_input_sha256 == MODEL_HASHES[config.case_id]
    assert manifest.evidence_requirement_set_sha256 == V5_HASHES[config.case_id]
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest
    with pytest.raises(ValueError, match="frozen Stage-3 input"):
        replace(manifest, model_input_sha256="0" * 64)
    with pytest.raises(ValueError, match="frozen Stage-3 input"):
        replace(manifest, evidence_requirement_set_sha256="0" * 64)
    with pytest.raises(ValueError, match="evidence-support-v5"):
        replace(manifest, evidence_support_version="evidence-support-v4")


def test_v13_rejects_v4_and_cross_condition_fallbacks_without_broadening_v12() -> None:
    definition = _definition()
    with pytest.raises(ValueError):
        replace(definition, expected_evidence_support_version="evidence-support-v4").validate()
    with pytest.raises(ValueError):
        replace(definition, condition="raw").validate()
    with pytest.raises(ValueError):
        replace(definition, condition="relative-time-v1").validate()
    with pytest.raises(ValueError):
        replace(PilotDefinition.load(STAGE2), condition="temporal-ablation-v1").validate()
    config = _config(definition, "1319:target")
    with pytest.raises(ValueError, match="Manifest v13"):
        prepare_model_input(replace(config, condition="raw"))
    with pytest.raises(ValueError, match="Manifest v13"):
        prepare_model_input(replace(config, condition="relative-time-v1"))
    with pytest.raises(ValueError, match="Manifest v13"):
        prepare_model_input(replace(config, expected_model_input_sha256="0" * 64))
    with pytest.raises(ValueError, match="Manifest v13"):
        prepare_model_input(replace(config, expected_evidence_requirement_set_sha256="0" * 64))
    with pytest.raises(ValueError, match="Manifest v13"):
        prepare_model_input(replace(config, seed=2000, case_id="2000:target"))
    with pytest.raises(ValueError, match="Manifest v13"):
        prepare_model_input(replace(config, seed=20000, case_id="20000:target"))


def test_older_v9_v10_pilot_loaders_remain_compatible() -> None:
    v9 = PilotDefinition.load(
        ROOT / "experiments/incident_003_v2_raw_sol_development.toml"
    )
    v10 = PilotDefinition.load(
        ROOT / "experiments/incident_003_v2_relative_time_v1_sol_development.toml"
    )
    assert v9.manifest_schema_version == "raw-rca-manifest-v9"
    assert v10.manifest_schema_version == "raw-rca-manifest-v10"
    assert v9.expected_evidence_support_version == "evidence-support-v3"
    assert v10.expected_evidence_support_version == "evidence-support-v3"


def test_selected_ablation_isomorphic_with_conflicting_oracles_and_no_v5_temporal_proof() -> None:
    seeds = (1319, 1299, 1387, 1222)
    report = audit_incident_003_v3_leakage_range(seeds)
    pairs = report["paired_queries"]
    assert report["passed"] is True
    assert pairs["ablated_query_pair_isomorphism_count"] == 4
    assert pairs["conflicting_mechanism_oracle_count"] == 4
    assert pairs["underlying_evidence_equal_count"] == 4
    target_temporal = {
        "deadline_before_original_completion",
        "compensation_after_deadline",
        "execution_compensation_overlap",
        "late_successful_original_effect",
    }
    twin_temporal = {
        "successful_execution_and_active_effect_before_deadline",
        "compensation_after_committed_success",
        "serialized_execution_before_compensation",
    }
    for seed in seeds:
        for role in ("target", "temporal_twin"):
            incident = generate_evaluation_incident(INCIDENT_003_V3_FAMILY, seed, query_role=role)
            view = temporally_ablated_model_view(incident)
            rubric = build_incident_003_v3_evidence_rubric_v5(incident)
            assert evidence_requirement_set_sha256_v5(rubric) == V5_HASHES[f"{seed}:{role}"]
            evaluator = Incident003V3EvidenceSemanticEvaluatorV5(TEMPORAL_SEMANTICS_UNAVAILABLE)
            all_ids = tuple(eid for binding in rubric.subject_bindings for eid in binding.evidence_ids)
            maximal = score_evidence_support_v5(all_ids, view, rubric, evaluator)
            assert not maximal.evidence_supported
            assert (target_temporal if role == "target" else twin_temporal) <= set(maximal.missing_essential_requirements)
            for binding in rubric.subject_bindings:
                if binding.role != "target":
                    distractor = score_evidence_support_v5(binding.evidence_ids, view, rubric, evaluator)
                    assert not distractor.evidence_supported
                    assert (target_temporal if role == "target" else twin_temporal) <= set(distractor.missing_essential_requirements)


def test_stage3_report_keeps_unavailable_and_wrong_separate() -> None:
    definition = _definition()
    first = _config(definition, "1319:target")
    twin = _config(definition, "1319:temporal_twin")
    valid = run_raw_experiment(first, FakeProvider(raw_output=_response(first)))
    parser_failure = run_raw_experiment(twin, FakeProvider(raw_output="{"))
    report = summarize_stage3_v5(definition, (valid, parser_failure))
    assert report["report_version"] == "incident-003-v3-stage3-evidence-v5-report-v1"
    assert report["planned_cases"] == 8
    assert report["attempted_calls"] == 2
    assert report["unattempted_calls"] == 6
    assert report["valid_responses"] == report["observed_denominator"] == 1
    assert report["rca"]["exact_correct"] == 1
    assert report["infrastructure"]["parser_failures"] == 1
    assert report["paired"]["observed_denominator"] == 0
    assert report["paired"]["patterns"]["1319"] == "unavailable"
    assert report["paired"]["unavailability"]["1319"] == {
        "target": "valid", "temporal_twin": "malformed_json"
    }
    assert report["paired"]["unavailability"]["1299"] == {
        "target": "unattempted", "temporal_twin": "unattempted"
    }
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_stage3_v5(definition, (valid, valid))


def test_stage3_report_patterns_are_exclusive() -> None:
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
    report = summarize_stage3_v5(definition, manifests)
    assert report["paired"]["patterns"] == {
        "1319": "correct_mechanism_flip",
        "1299": "both_concurrency",
        "1387": "both_state_transition",
        "1222": "one_or_both_other_valid_mechanism_labels",
    }
    assert report["paired"]["observed_denominator"] == 4
    assert report["attempted_calls"] == report["valid_responses"] == 8


def test_stage3_report_reversed_mechanism_flip_is_separate() -> None:
    definition = _definition()
    manifests = []
    for case_id, mechanism in (
        ("1319:target", "incorrect_state_transition"),
        ("1319:temporal_twin", "incorrect_concurrency_control"),
    ):
        config = _config(definition, case_id)
        manifests.append(run_raw_experiment(config, FakeProvider(raw_output=_response(config, mechanism))))
    report = summarize_stage3_v5(definition, manifests)
    assert report["paired"]["patterns"]["1319"] == "reversed_mechanism_flip"
    assert report["paired"]["observed_denominator"] == 1
    assert report["paired"]["mechanism_correct"] == 0


def test_stage3_result_is_ignored_and_dry_run_creates_no_artifact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ignored = subprocess.run(["git", "check-ignore", "-q", str(RESULT)], cwd=ROOT, check=False)
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(RESULT)],
        cwd=ROOT, check=False, capture_output=True,
    )
    assert ignored.returncode == 0
    assert tracked.returncode != 0
    candidate = tmp_path / "stage3-dry-run.jsonl"
    args = build_parser().parse_args([
        "run-pilot", "--config", str(CONFIG), "--results", str(candidate)
    ])
    args.handler(args)
    assert '"execution": "pending"' in capsys.readouterr().out
    assert not candidate.exists()


def test_existing_result_path_aborts_before_provider_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = tmp_path / "existing.jsonl"
    candidate.write_text("historical\n", encoding="utf-8")

    def forbidden_provider(_definition: PilotDefinition) -> None:
        raise AssertionError("Provider setup must not occur")

    monkeypatch.setattr("diagpriv.evaluation.cli._openai_provider", forbidden_provider)
    args = build_parser().parse_args([
        "run-pilot", "--config", str(CONFIG), "--results", str(candidate), "--execute"
    ])
    with pytest.raises(SystemExit, match="already exists"):
        args.handler(args)
    assert candidate.read_text(encoding="utf-8") == "historical\n"
