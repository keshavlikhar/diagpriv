from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from diagbench.audits.incident_003 import temporally_ablated_model_view
from diagbench.audits.incident_003_v3_leakage import (
    audit_incident_003_v3_leakage_range,
)
from diagbench.generators.incident_003_v3 import generate_incident_003_v3
from diagbench.relative_time import RELATIVE_TIME_SEMANTICS_VERSION
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.evidence_support_v4 import score_evidence_support_v4
from diagpriv.evaluation.incident_003_v3_evidence import (
    build_incident_003_v3_evidence_rubric,
)
from diagpriv.evaluation.incident_003_v3_evidence_semantics import (
    Incident003V3EvidenceSemanticEvaluator,
)
from diagpriv.evaluation.incident_families import (
    INCIDENT_003_V3_FAMILY,
    INCIDENT_003_V3_QUALIFICATION_SEEDS,
    INCIDENT_003_V3_QUERY_ROLES,
    incident_003_v3_case_id,
    select_incident_003_v3_qualification_seeds,
)
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
from diagpriv.transformations.provenance import TEMPORAL_SEMANTICS_UNAVAILABLE

ROOT = Path(__file__).parents[1]
CONFIGS = {
    "raw": ROOT / "experiments/incident_003_v3_raw_paired_sol_development.toml",
    "relative-time-v1": (
        ROOT
        / "experiments/incident_003_v3_relative_time_v1_paired_sol_development.toml"
    ),
    "temporal-ablation-v1": (
        ROOT
        / "experiments/incident_003_v3_temporal_ablation_v1_paired_sol_development.toml"
    ),
}
RESULTS = {
    "raw": ROOT
    / "results/incident_003_v3_raw_paired_sol_development_gpt_5_6_sol_medium.jsonl",
    "relative-time-v1": ROOT
    / "results/incident_003_v3_relative_time_v1_paired_sol_development_gpt_5_6_sol_medium.jsonl",
    "temporal-ablation-v1": ROOT
    / "results/incident_003_v3_temporal_ablation_v1_paired_sol_development_gpt_5_6_sol_medium.jsonl",
}
SELECTION_DIGESTS = {
    1319: "01158f484f822ae5eebd6efeb12f038dfa5f8475b4d4dc48f6094e7f24f2c7d4",
    1299: "01479aadecf2a505bab788b7fb410255257af0416094e2ade4bd7787c7a17de1",
    1387: "0309d5c21954a9ea8b06358c1f4cccad9256f88daf0f0ede0444a729bd1b6966",
    1222: "04b22773b02d9c607e3ec290259ac51250268ce373cde8a2ef9a47b336d5b447",
}


def _run_config(definition: PilotDefinition, case_id: str) -> RawRunConfig:
    seed_text, query_role = case_id.split(":", maxsplit=1)
    return RawRunConfig(
        experiment_id=f"offline-{definition.condition}-{case_id}",
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
        expected_model_input_sha256=(
            definition.expected_model_input_sha256_by_case_id[case_id]
        ),
        expected_evidence_requirement_set_sha256=(
            definition.expected_evidence_requirement_set_sha256_by_case_id[case_id]
        ),
        expected_incident_generator_version=(
            definition.expected_incident_generator_version
        ),
        expected_incident_protocol_version=(
            definition.expected_incident_protocol_version
        ),
        expected_evidence_support_version=(
            definition.expected_evidence_support_version
        ),
        expected_transformation_configuration_sha256=(
            definition.expected_transformation_configuration_sha256
        ),
        query_role=query_role,  # type: ignore[arg-type]
        case_id=case_id,
        expected_paired_query_protocol_version=(
            definition.expected_paired_query_protocol_version
        ),
        expected_anchor_allocation_version=(
            definition.expected_anchor_allocation_version
        ),
        expected_evidence_requirement_version=(
            definition.expected_evidence_requirement_version
        ),
        expected_semantic_evaluator_version=(
            definition.expected_semantic_evaluator_version
        ),
    )


def _response(seed: int, query_role: str) -> RCAResponseV3:
    incident = generate_incident_003_v3(seed, query_role)  # type: ignore[arg-type]
    oracle = incident.ground_truth_v3
    rubric = build_incident_003_v3_evidence_rubric(incident)
    citations = tuple(
        evidence_id
        for binding in rubric.subject_bindings
        for evidence_id in binding.evidence_ids
    )
    return RCAResponseV3(
        observed_outcome=oracle.observed_outcome,
        trigger=oracle.trigger,
        subsequent_action=oracle.subsequent_action,
        failure_mechanism=oracle.failure_mechanism,
        affected_component=oracle.affected_component,
        supporting_evidence=citations,
        explanation="Offline paired-query fixture.",
        confidence=0.9,
    )


def test_seed_selection_is_content_independent_and_exact() -> None:
    digests = {
        seed: hashlib.sha256(
            f"incident-003-v3-paired-qualification-v1|{seed}".encode("ascii")
        ).hexdigest()
        for seed in range(1200, 1400)
    }
    selected = tuple(sorted(digests, key=digests.get)[:4])
    assert selected == INCIDENT_003_V3_QUALIFICATION_SEEDS
    assert selected == select_incident_003_v3_qualification_seeds()
    assert {seed: digests[seed] for seed in selected} == SELECTION_DIGESTS


@pytest.mark.parametrize("condition", tuple(CONFIGS))
def test_paired_configs_are_isolated_and_preregister_eight_cases(
    condition: str,
) -> None:
    definition = PilotDefinition.load(CONFIGS[condition])
    assert definition.incident_family == INCIDENT_003_V3_FAMILY
    assert definition.manifest_schema_version == "raw-rca-manifest-v11"
    assert definition.condition == condition
    assert definition.development_seeds == INCIDENT_003_V3_QUALIFICATION_SEEDS
    assert definition.query_roles == INCIDENT_003_V3_QUERY_ROLES
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    plan = definition.paired_case_plan()
    assert len(plan) == 8
    assert len({case_id for _, _, case_id in plan}) == 8
    assert {
        case_id for _, _, case_id in plan
    } == set(definition.expected_model_input_sha256_by_case_id)
    assert not RESULTS[condition].exists()


def test_target_and_twin_share_exact_evidence_and_neutral_question_template() -> None:
    for seed in INCIDENT_003_V3_QUALIFICATION_SEEDS:
        target = generate_incident_003_v3(seed, "target")
        twin = generate_incident_003_v3(seed, "temporal_twin")
        target_view = target.model_view()
        twin_view = twin.model_view()
        assert target_view.structured_evidence == twin_view.structured_evidence
        assert target_view.log_evidence == twin_view.log_evidence
        target_id = str(target.metadata["queried_operation_id"])
        twin_id = str(twin.metadata["queried_operation_id"])
        assert target_view.troubleshooting_question.replace(
            target_id, "<queried_operation_id>"
        ) == twin_view.troubleshooting_question.replace(
            twin_id, "<queried_operation_id>"
        )
        assert target.ground_truth_v3.failure_mechanism == (
            "incorrect_concurrency_control"
        )
        assert twin.ground_truth_v3.failure_mechanism == (
            "incorrect_state_transition"
        )


@pytest.mark.parametrize("condition", tuple(CONFIGS))
def test_prepared_inputs_and_rubrics_match_frozen_case_hashes(condition: str) -> None:
    definition = PilotDefinition.load(CONFIGS[condition])
    for _, _, case_id in definition.paired_case_plan():
        prepared = prepare_model_input(_run_config(definition, case_id))
        assert prepared.case_id == case_id
        assert prepared.model_input_sha256 == (
            definition.expected_model_input_sha256_by_case_id[case_id]
        )
        assert prepared.evidence_requirement_set_sha256 == (
            definition.expected_evidence_requirement_set_sha256_by_case_id[case_id]
        )
        assert prepared.semantic_evaluator_version == (
            "incident-003-v3-evidence-semantic-evaluator-v2"
        )
        assert prepared.transformation_provenance is not None
        assert prepared.transformation_provenance.transformation_version == (
            "incident-003-temporal-ablation-v1"
            if condition == "temporal-ablation-v1"
            else condition
        )


def test_rubric_hash_is_transformation_independent_for_each_case() -> None:
    definitions = [PilotDefinition.load(path) for path in CONFIGS.values()]
    for case_id in definitions[0].expected_evidence_requirement_set_sha256_by_case_id:
        assert len(
            {
                definition.expected_evidence_requirement_set_sha256_by_case_id[
                    case_id
                ]
                for definition in definitions
            }
        ) == 1


def test_complete_citations_support_raw_and_relative_but_not_ablation() -> None:
    semantics = {
        "raw": TEMPORAL_SEMANTICS_VERSION,
        "relative-time-v1": RELATIVE_TIME_SEMANTICS_VERSION,
        "temporal-ablation-v1": TEMPORAL_SEMANTICS_UNAVAILABLE,
    }
    for condition, config_path in CONFIGS.items():
        definition = PilotDefinition.load(config_path)
        for _, _, case_id in definition.paired_case_plan():
            prepared = prepare_model_input(_run_config(definition, case_id))
            assert prepared.evidence_rubric is not None
            citations = tuple(
                evidence_id
                for binding in prepared.evidence_rubric.subject_bindings
                for evidence_id in binding.evidence_ids
            )
            score = score_evidence_support_v4(
                citations,
                prepared.model_view,
                prepared.evidence_rubric,
                Incident003V3EvidenceSemanticEvaluator(semantics[condition]),
            )
            assert score.evidence_supported is (condition != "temporal-ablation-v1")
            if condition == "temporal-ablation-v1":
                assert score.missing_essential_requirements


def test_selected_ablation_pairs_are_isomorphic_and_oracles_conflict() -> None:
    report = audit_incident_003_v3_leakage_range(
        INCIDENT_003_V3_QUALIFICATION_SEEDS
    )
    pairs = report["paired_queries"]
    assert pairs["ablated_query_pair_isomorphism_count"] == 4
    assert pairs["conflicting_mechanism_oracle_count"] == 4
    assert pairs["underlying_evidence_equal_count"] == 4
    assert report["passed"] is True


def test_manifest_v11_round_trip_persists_unambiguous_pair_identity() -> None:
    definition = PilotDefinition.load(CONFIGS["raw"])
    case_id = "1319:temporal_twin"
    response = _response(1319, "temporal_twin")
    manifest = run_raw_experiment(
        _run_config(definition, case_id),
        FakeProvider(raw_output=response.to_json()),
    )
    assert manifest.seed == 1319
    assert manifest.construction_seed == 1319
    assert manifest.query_role == "temporal_twin"
    assert manifest.case_id == case_id
    assert manifest.paired_query_protocol_version == (
        "incident-003-v3-paired-query-v1"
    )
    assert manifest.evidence_requirement_version == (
        "incident-003-v3-evidence-requirements-v2"
    )
    assert manifest.semantic_evaluator_version == (
        "incident-003-v3-evidence-semantic-evaluator-v2"
    )
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest


def test_v11_rejects_role_or_case_mismatch_before_provider_invocation() -> None:
    definition = PilotDefinition.load(CONFIGS["raw"])
    provider = FakeProvider(raw_output=_response(1319, "target").to_json())
    with pytest.raises(ValueError, match="case ID"):
        run_raw_experiment(
            replace(_run_config(definition, "1319:target"), case_id="1319:temporal_twin"),
            provider,
        )
    assert provider.requests == []


@pytest.mark.parametrize("seed", [1199, 1200, 1320, 1399, 2000, 20000])
def test_nonselected_and_protected_seeds_fail_before_generation(
    seed: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    definition = PilotDefinition.load(CONFIGS["raw"])
    generated = False

    def fail_if_generated(candidate: int, query_role: str):
        nonlocal generated
        generated = True
        raise AssertionError((candidate, query_role))

    monkeypatch.setattr(
        "diagpriv.evaluation.incident_families.generate_incident_003_v3",
        fail_if_generated,
    )
    config = replace(
        _run_config(definition, "1319:target"),
        seed=seed,
        case_id=incident_003_v3_case_id(seed, "target"),
    )
    with pytest.raises(ProtectedSeedError):
        prepare_model_input(config)
    assert generated is False


@pytest.mark.parametrize("condition", tuple(CONFIGS))
def test_dry_run_reports_eight_cases_and_never_initializes_provider(
    condition: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = tmp_path / RESULTS[condition].name

    def fail_if_started(*args, **kwargs):
        raise AssertionError((args, kwargs))

    monkeypatch.setattr("diagpriv.evaluation.cli._openai_provider", fail_if_started)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(CONFIGS[condition]),
            "--results",
            str(result),
        ]
    )
    args.handler(args)
    output = json.loads(capsys.readouterr().out)
    assert output["execution"] == "pending"
    assert output["scheduled_calls"] == 8
    assert len(output["input_preflight"]["case_ids"]) == 8
    assert not result.exists()


def test_existing_result_blocks_execution_before_provider_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = tmp_path / "existing.jsonl"
    result.write_text("historical observation\n", encoding="utf-8")
    provider_started = False

    def fail_if_started(*args, **kwargs):
        nonlocal provider_started
        provider_started = True
        raise AssertionError((args, kwargs))

    monkeypatch.setattr("diagpriv.evaluation.cli._openai_provider", fail_if_started)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(CONFIGS["raw"]),
            "--results",
            str(result),
            "--execute",
        ]
    )
    with pytest.raises(SystemExit, match="already exists"):
        args.handler(args)
    assert provider_started is False


def test_input_hash_mismatch_fails_closed_before_provider_setup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    changed = tmp_path / "hash-mismatch.toml"
    changed.write_text(
        CONFIGS["raw"].read_text(encoding="utf-8").replace(
            "a8929b46726e39b9718c61e3d3f1f83ddf8ad464c5a0e02e1d58f529a26120ba",
            "0" * 64,
        ).replace(
            'snapshot = "pricing/openai_gpt_5_6_sol_2026-09-10.toml"',
            f'snapshot = "{ROOT / "experiments/pricing/openai_gpt_5_6_sol_2026-09-10.toml"}"',
        ),
        encoding="utf-8",
    )
    provider_started = False

    def fail_if_started(*args, **kwargs):
        nonlocal provider_started
        provider_started = True
        raise AssertionError((args, kwargs))

    monkeypatch.setattr("diagpriv.evaluation.cli._openai_provider", fail_if_started)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(changed),
            "--results",
            str(tmp_path / "never-created.jsonl"),
            "--execute",
        ]
    )
    with pytest.raises(ValueError, match="differs from frozen provenance"):
        args.handler(args)
    assert provider_started is False


def test_condition_cannot_silently_fall_back_to_raw(tmp_path: Path) -> None:
    changed = tmp_path / "condition-mismatch.toml"
    changed.write_text(
        CONFIGS["raw"].read_text(encoding="utf-8").replace(
            'condition = "raw"', 'condition = "relative-time-v1"', 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="frozen transformation configuration"):
        PilotDefinition.load(changed)


def test_result_paths_are_unique_ignored_untracked_and_absent() -> None:
    assert len(set(RESULTS.values())) == 3
    for path in RESULTS.values():
        assert not path.exists()
        assert subprocess.run(
            ["git", "check-ignore", "-q", str(path)], cwd=ROOT, check=False
        ).returncode == 0
        assert not subprocess.check_output(
            ["git", "ls-files", "--", str(path)], cwd=ROOT
        ).strip()


def test_historical_manifest_v10_does_not_gain_paired_fields() -> None:
    historical = PilotDefinition.load(
        ROOT / "experiments/incident_003_v2_relative_time_v1_sol_development.toml"
    )
    prepared = prepare_model_input(
        RawRunConfig(
            experiment_id="historical-v10-reader",
            seed=1019,
            model="offline",
            model_version=None,
            incident_family=historical.incident_family,
            manifest_schema_version=historical.manifest_schema_version,
            condition=historical.condition,
            decoding_settings=dict(historical.decoding_settings),
            prompt_version=historical.prompt_version,
            expected_model_input_sha256=(
                historical.expected_model_input_sha256_by_seed[1019]
            ),
            expected_evidence_requirement_set_sha256=(
                historical.expected_evidence_requirement_set_sha256_by_seed[1019]
            ),
            expected_incident_generator_version=(
                historical.expected_incident_generator_version
            ),
            expected_incident_protocol_version=(
                historical.expected_incident_protocol_version
            ),
            expected_evidence_support_version=(
                historical.expected_evidence_support_version
            ),
            expected_transformation_configuration_sha256=(
                historical.expected_transformation_configuration_sha256
            ),
        )
    )
    assert prepared.query_role is None
    assert prepared.case_id is None
