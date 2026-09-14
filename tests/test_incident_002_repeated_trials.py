from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess

import pytest

from diagbench.generators.incident_002 import generate_incident_002
from diagpriv.evaluation.cli import _input_preflight, build_parser
from diagpriv.evaluation.incident_families import (
    INCIDENT_002_DEVELOPMENT_SEEDS,
    INCIDENT_002_FAMILY,
    INCIDENT_002_SEED_SELECTION_VERSION,
)
from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.runner import (
    RawRunConfig,
    prepare_model_input,
    run_raw_experiment,
)
from diagpriv.transformations import hmac_key_fingerprint

ROOT = Path(__file__).parents[1]
PUBLIC_TEST_KEY = bytes(range(32))
CONDITIONS = (
    "raw",
    "redaction-v1",
    "hmac-v1",
    "tokenization-v1",
    "format-preserving-v1",
)
REPEATED_CONFIGS = {
    condition: ROOT
    / "experiments"
    / f"incident_002_{condition.replace('-', '_')}_sol_repeated_trials.toml"
    for condition in CONDITIONS
}
TRIAL_ONE_CONFIGS = {
    "raw": ROOT / "experiments" / "incident_002_raw_sol_development.toml",
    **{
        condition: ROOT
        / "experiments"
        / f"incident_002_{condition.replace('-', '_')}_sol_development.toml"
        for condition in CONDITIONS[1:]
    },
}
RESULTS = {
    condition: ROOT
    / "results"
    / f"incident_002_{condition.replace('-', '_')}_sol_repeated_trials_2_3.jsonl"
    for condition in CONDITIONS
}


def _correct_response(seed: int) -> str:
    incident = generate_incident_002(seed)
    oracle = incident.ground_truth_v2
    return json.dumps(
        {
            "observed_outcome": oracle.observed_outcome,
            "trigger": oracle.trigger,
            "subsequent_action": oracle.subsequent_action,
            "failure_mechanism": oracle.failure_mechanism,
            "affected_component": oracle.affected_component,
            "supporting_evidence": [],
            "explanation": "Offline repeated-trial schema fixture.",
            "confidence": 0.9,
        }
    )


def _trial_one_hashes(condition: str) -> dict[int, str]:
    definition = PilotDefinition.load(TRIAL_ONE_CONFIGS[condition])
    return (
        definition.matched_model_input_sha256_by_seed
        if condition == "raw"
        else definition.expected_model_input_sha256_by_seed
    )


@pytest.mark.parametrize("condition", CONDITIONS)
def test_repeated_trial_configs_freeze_only_trials_two_and_three(
    condition: str,
) -> None:
    definition = PilotDefinition.load(REPEATED_CONFIGS[condition])
    assert definition.incident_family == INCIDENT_002_FAMILY
    assert definition.manifest_schema_version == "raw-rca-manifest-v7"
    assert (
        definition.development_seed_selection_version
        == INCIDENT_002_SEED_SELECTION_VERSION
    )
    assert definition.condition == condition
    assert definition.development_seeds == INCIDENT_002_DEVELOPMENT_SEEDS
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 2
    assert definition.trial_indices == (2, 3)
    assert (
        definition.repetition_protocol_version
        == "incident-002-three-trial-development-v1"
    )
    assert definition.historical_trial_count == 1
    assert definition.target_total_trials == 3
    assert definition.requested_model == "gpt-5.6-sol"
    assert definition.reasoning_effort == "medium"
    assert definition.decoding_settings == {"max_output_tokens": 4096}
    assert definition.effective_temperature is None
    assert definition.prompt_version == "raw-rca-v2"
    assert definition.taxonomy_version == "rca-taxonomy-v2"
    assert definition.scorer_version == "raw-rca-scorer-v2"
    assert definition.expected_model_input_sha256_by_seed == _trial_one_hashes(
        condition
    )


def test_repeated_trial_configs_schedule_exactly_sixty_calls() -> None:
    definitions = [PilotDefinition.load(path) for path in REPEATED_CONFIGS.values()]
    assert sum(
        len(definition.development_seeds) * definition.calls_per_seed
        for definition in definitions
    ) == 60
    assert {
        (condition, seed, trial_index)
        for condition, definition in zip(CONDITIONS, definitions, strict=True)
        for seed in definition.development_seeds
        for trial_index in definition.trial_indices
    } == {
        (condition, seed, trial_index)
        for condition in CONDITIONS
        for seed in INCIDENT_002_DEVELOPMENT_SEEDS
        for trial_index in (2, 3)
    }


@pytest.mark.parametrize("condition", CONDITIONS)
def test_preflight_proves_trial_index_does_not_change_model_input(
    condition: str,
) -> None:
    definition = PilotDefinition.load(REPEATED_CONFIGS[condition])
    expected = _trial_one_hashes(condition)
    if condition == "hmac-v1":
        expected = {
            seed: prepare_model_input(
                RawRunConfig(
                    experiment_id=f"public-key-baseline-{seed}",
                    seed=seed,
                    model=definition.requested_model,
                    model_version=None,
                    incident_family=definition.incident_family,
                    manifest_schema_version=definition.manifest_schema_version,
                    reasoning_effort=definition.reasoning_effort,
                    condition=definition.condition,
                    decoding_settings=dict(definition.decoding_settings),
                    intended_temperature=definition.intended_temperature,
                    temperature_omission_reason=(
                        definition.temperature_omission_reason
                    ),
                    prompt_version=definition.prompt_version,
                    hmac_key=PUBLIC_TEST_KEY,
                    transformation_key_id=definition.hmac_key_id,
                    trial_index=2,
                )
            ).model_input_sha256
            for seed in definition.development_seeds
        }
        definition = replace(
            definition,
            expected_model_input_sha256_by_seed=expected,
            expected_transformation_key_fingerprint=hmac_key_fingerprint(
                PUBLIC_TEST_KEY
            ),
        )
    report = _input_preflight(
        definition,
        hmac_key=PUBLIC_TEST_KEY if condition == "hmac-v1" else None,
    )
    expected_text = {str(seed): digest for seed, digest in expected.items()}
    assert report["status"] == "verified"
    assert report["trial_indices"] == [2, 3]
    assert report["model_input_sha256_by_seed"] == expected_text
    assert report["model_input_sha256_by_trial"] == {
        "2": expected_text,
        "3": expected_text,
    }


def test_manifest_v7_records_trial_identity_without_changing_v6() -> None:
    seed = 1000
    common = dict(
        experiment_id="repeated-trial-offline",
        seed=seed,
        model="offline-fixture",
        model_version=None,
        incident_family=INCIDENT_002_FAMILY,
        reasoning_effort="medium",
        condition="raw",
        decoding_settings={"max_output_tokens": 4096},
        intended_temperature=0.0,
        temperature_omission_reason="Frozen protocol omission.",
        prompt_version="raw-rca-v2",
    )
    provider = FakeProvider(raw_output=_correct_response(seed))
    v7 = run_raw_experiment(
        RawRunConfig(
            **common,
            manifest_schema_version="raw-rca-manifest-v7",
            trial_index=2,
        ),
        provider,
    )
    assert v7.trial_index == 2
    assert v7.to_dict()["trial_index"] == 2
    assert ExperimentManifest.from_json(v7.to_json()) == v7
    with pytest.raises(ValueError, match="requires a positive trial_index"):
        replace(v7, trial_index=None)
    provider_without_trial = FakeProvider(raw_output=_correct_response(seed))
    with pytest.raises(ValueError, match="requires a positive trial_index"):
        run_raw_experiment(
            RawRunConfig(**common, manifest_schema_version="raw-rca-manifest-v7"),
            provider_without_trial,
        )
    assert provider_without_trial.requests == []

    v6 = run_raw_experiment(
        RawRunConfig(**common, manifest_schema_version="raw-rca-manifest-v6"),
        FakeProvider(raw_output=_correct_response(seed)),
    )
    assert v6.trial_index is None
    assert "trial_index" not in v6.to_dict()
    assert ExperimentManifest.from_json(v6.to_json()) == v6
    with pytest.raises(ValueError, match="only in manifest schema v7"):
        replace(v6, trial_index=1)


@pytest.mark.parametrize("condition", CONDITIONS)
def test_repeated_trial_config_rejects_scope_or_trial_changes(
    condition: str, tmp_path: Path
) -> None:
    source = REPEATED_CONFIGS[condition].read_text(encoding="utf-8")
    changes = (
        ("trial_indices = [2, 3]", "trial_indices = [1, 2]"),
        ("calls_per_seed = 2", "calls_per_seed = 3"),
        ("validation_seeds = []", "validation_seeds = [2000]"),
        ("held_out_seeds = []", "held_out_seeds = [20000]"),
    )
    for index, (original, changed) in enumerate(changes):
        path = tmp_path / f"invalid-{condition}-{index}.toml"
        path.write_text(source.replace(original, changed), encoding="utf-8")
        with pytest.raises(ValueError):
            PilotDefinition.load(path)


@pytest.mark.parametrize(
    "condition",
    ("raw", "redaction-v1", "tokenization-v1", "format-preserving-v1"),
)
def test_repeated_trial_dry_run_is_nonexecuting_and_reports_twelve_calls(
    condition: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = tmp_path / RESULTS[condition].name
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(REPEATED_CONFIGS[condition]),
            "--results",
            str(result),
        ]
    )
    args.handler(args)
    output = json.loads(capsys.readouterr().out)
    assert output["execution"] == "pending"
    assert output["scheduled_calls"] == 12
    assert output["pilot"]["trial_indices"] == [2, 3]
    assert output["input_preflight"]["trial_indices"] == [2, 3]
    assert not result.exists()


def test_repeated_trial_execution_refuses_an_existing_result_before_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = tmp_path / "already-exists.jsonl"
    result.write_text("historical observation\n", encoding="utf-8")
    provider_started = False

    def fail_if_started(definition: PilotDefinition) -> tuple[FakeProvider, None]:
        nonlocal provider_started
        provider_started = True
        raise AssertionError(definition.pilot_id)

    monkeypatch.setattr("diagpriv.evaluation.cli._openai_provider", fail_if_started)
    args = build_parser().parse_args(
        [
            "run-pilot",
            "--config",
            str(REPEATED_CONFIGS["raw"]),
            "--results",
            str(result),
            "--execute",
        ]
    )
    with pytest.raises(SystemExit, match="already exists"):
        args.handler(args)
    assert provider_started is False


def test_repeated_trial_result_paths_are_ignored_and_untracked() -> None:
    assert "results/*" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert all(path.relative_to(ROOT).parts[0] == "results" for path in RESULTS.values())
    for path in RESULTS.values():
        assert subprocess.run(
            ["git", "check-ignore", "-q", str(path)], cwd=ROOT, check=False
        ).returncode == 0
        assert not subprocess.check_output(
            ["git", "ls-files", "--", str(path)], cwd=ROOT
        ).strip()
