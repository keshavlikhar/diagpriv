from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from diagbench.generators.incident_001 import generate_incident_001
from diagbench.generators.incident_002 import (
    SUPPORTED_GENERATION_DEFECTS,
    generate_incident_002,
)
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.incident_families import (
    INCIDENT_002_DEVELOPMENT_SEEDS,
    INCIDENT_002_FAMILY,
    INCIDENT_002_SEED_SELECTION_VERSION,
)
from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.prompt_v2 import PROMPT_SHA256
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.response import RCAResponseV2
from diagpriv.evaluation.runner import (
    ProtectedSeedError,
    RawRunConfig,
    run_raw_experiment,
)

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "experiments" / "incident_002_raw_development.toml"
RESULT_PATH = ROOT / "results" / "incident_002_raw_development_gpt_5_6_luna_medium.jsonl"
EXPECTED_SELECTION = (
    (1000, "extra_separator", "hyphenated_mixed_b", "extra_separator"),
    (1001, "missing_separator", "hyphenated_mixed_b", "missing_separator"),
    (1003, "case_class_mismatch", "underscored_mixed", "case_class_mismatch"),
    (1004, "truncation", "slashed_mixed", "truncation"),
    (
        1005,
        "leading_zero_loss",
        "slashed_mixed",
        "numeric_run_leading_position_deletion",
    ),
    (1017, "fixed_width_mismatch", "slashed_mixed", "fixed_width_mismatch"),
)


def _correct_response(seed: int) -> RCAResponseV2:
    incident = generate_incident_002(seed)
    oracle = incident.ground_truth_v2
    evidence_ids = tuple(
        sorted(
            {
                str(reference.selector["evidence_id"])
                for expected in incident.expected_evidence
                for reference in expected.references
            }
        )
    )
    return RCAResponseV2(
        observed_outcome=oracle.observed_outcome,
        trigger=oracle.trigger,
        subsequent_action=oracle.subsequent_action,
        failure_mechanism=oracle.failure_mechanism,
        affected_component=oracle.affected_component,
        supporting_evidence=evidence_ids,
        explanation="Visible evidence supports the five selected RCA dimensions.",
        confidence=0.9,
    )


def _run_config(seed: int, *, schema: str = "raw-rca-manifest-v6") -> RawRunConfig:
    return RawRunConfig(
        experiment_id=f"incident-002-offline-{seed}",
        seed=seed,
        model="offline-fixture",
        model_version="test-version",
        incident_family=INCIDENT_002_FAMILY,
        manifest_schema_version=schema,
        reasoning_effort="medium",
        decoding_settings={"max_output_tokens": 4096},
        intended_temperature=0.0,
        temperature_omission_reason="Provider rejects temperature for this model.",
        prompt_version="raw-rca-v2",
        timestamp="2032-01-01T00:00:00+00:00",
    )


def test_first_occurrence_selection_is_exact_and_stops_at_six_classes() -> None:
    selected: list[tuple[int, str, str, str]] = []
    seen: set[str] = set()
    seed = 1000
    while len(seen) < len(SUPPORTED_GENERATION_DEFECTS):
        incident = generate_incident_002(seed)
        defect = str(incident.metadata["defect_class"])
        if defect not in seen:
            seen.add(defect)
            selected.append(
                (
                    seed,
                    defect,
                    str(incident.metadata["structural_template_name"]),
                    str(incident.metadata["observable_structural_delta"]),
                )
            )
        seed += 1

    assert tuple(selected) == EXPECTED_SELECTION
    assert tuple(item[0] for item in selected) == INCIDENT_002_DEVELOPMENT_SEEDS
    assert seed == 1018
    assert seen == set(SUPPORTED_GENERATION_DEFECTS)


def test_incident_002_pilot_is_exactly_the_frozen_raw_development_scope() -> None:
    definition = PilotDefinition.load(CONFIG)
    assert definition.pilot_id == "incident-002-raw-development-v1"
    assert definition.incident_family == INCIDENT_002_FAMILY
    assert definition.manifest_schema_version == "raw-rca-manifest-v6"
    assert (
        definition.development_seed_selection_version
        == INCIDENT_002_SEED_SELECTION_VERSION
    )
    assert definition.seed_scope == "development_only"
    assert definition.development_seeds == INCIDENT_002_DEVELOPMENT_SEEDS
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.condition == "raw"
    assert definition.requested_model == "gpt-5.6-luna"
    assert definition.reasoning_effort == "medium"
    assert "temperature" not in definition.decoding_settings
    assert definition.intended_temperature == 0.0
    assert definition.effective_temperature is None
    assert definition.prompt_version == "raw-rca-v2"
    assert definition.prompt_sha256 == PROMPT_SHA256
    assert definition.taxonomy_version == "rca-taxonomy-v2"
    assert definition.scorer_version == "raw-rca-scorer-v2"


@pytest.mark.parametrize(
    ("original", "changed", "message"),
    [
        (
            "development_seeds = [1000, 1001, 1003, 1004, 1005, 1017]",
            "development_seeds = [1000, 1001, 1002, 1003, 1004, 1005]",
            "non-development seed|frozen development seeds",
        ),
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
            'seed_scope = "development_only"',
            'seed_scope = "development_and_validation"',
            "Incident 002 pilot must be development-only",
        ),
        (
            'incident_family = "incident_002_format_defect"',
            'incident_family = "incident_001"',
            "seed-selection metadata is valid only for Incident 002",
        ),
        (
            'manifest_schema_version = "raw-rca-manifest-v6"',
            'manifest_schema_version = "raw-rca-manifest-v5"',
            "Incident 002 pilot requires manifest schema v6",
        ),
    ],
)
def test_incident_002_config_rejects_any_scope_change(
    tmp_path: Path, original: str, changed: str, message: str
) -> None:
    path = tmp_path / "invalid.toml"
    path.write_text(
        CONFIG.read_text(encoding="utf-8").replace(original, changed),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=message):
        PilotDefinition.load(path)


def test_incident_002_runner_routes_only_to_incident_002(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def incident_001_must_not_run(seed: int):
        raise AssertionError(f"Incident 001 was routed for seed {seed}")

    monkeypatch.setattr(
        "diagpriv.evaluation.incident_families.generate_incident_001",
        incident_001_must_not_run,
    )
    seed = INCIDENT_002_DEVELOPMENT_SEEDS[0]
    provider = FakeProvider(raw_output=_correct_response(seed).to_json())
    manifest = run_raw_experiment(_run_config(seed), provider)
    incident = generate_incident_002(seed)
    assert manifest.incident_family == INCIDENT_002_FAMILY
    assert manifest.benchmark_version == incident.metadata["benchmark_version"]
    assert manifest.score is not None
    assert manifest.score.exact_root_cause_correct is True
    assert incident.model_view().to_json().strip() in provider.requests[0].prompt
    assert generate_incident_001(seed).troubleshooting_question not in (
        provider.requests[0].prompt
    )


@pytest.mark.parametrize("seed", [1002, 2000, 2999, 10_000, 20_000, 20_999])
def test_incident_002_runner_rejects_non_frozen_seeds_before_generation(
    seed: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    generated = False

    def fail_if_generated(candidate: int):
        nonlocal generated
        generated = True
        raise AssertionError(f"Protected seed {candidate} was generated")

    monkeypatch.setattr(
        "diagpriv.evaluation.incident_families.generate_incident_002",
        fail_if_generated,
    )
    with pytest.raises(ProtectedSeedError):
        run_raw_experiment(_run_config(seed), FakeProvider())
    assert generated is False


def test_manifest_v6_hashes_exact_provider_input_without_oracle_data() -> None:
    seed = 1001
    incident = generate_incident_002(seed)
    provider = FakeProvider(raw_output=_correct_response(seed).to_json())
    manifest = run_raw_experiment(_run_config(seed), provider)
    prompt = provider.requests[0].prompt
    expected_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    assert manifest.manifest_schema_version == "raw-rca-manifest-v6"
    assert manifest.model_input_sha256 == expected_hash
    assert manifest.to_dict()["model_input_sha256"] == expected_hash
    assert incident.ground_truth_v2.explanation not in prompt
    for forbidden in (
        "ground_truth",
        "diagnostic_invariants",
        "expected_evidence",
        "sensitive_fields",
        "defect_class",
        "latent_valid_reference",
    ):
        assert forbidden not in prompt
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest


def test_manifest_v6_hash_varies_with_rendered_model_view() -> None:
    manifests = []
    for seed in INCIDENT_002_DEVELOPMENT_SEEDS[:2]:
        manifests.append(
            run_raw_experiment(
                _run_config(seed),
                FakeProvider(raw_output=_correct_response(seed).to_json()),
            )
        )
    assert manifests[0].prompt_sha256 == manifests[1].prompt_sha256 == PROMPT_SHA256
    assert manifests[0].model_input_sha256 != manifests[1].model_input_sha256


def test_manifest_v5_behavior_remains_without_model_input_hash() -> None:
    seed = 1001
    manifest = run_raw_experiment(
        replace(
            _run_config(seed, schema="raw-rca-manifest-v5"),
            incident_family="incident_001",
        ),
        FakeProvider(raw_output="{}"),
    )
    assert manifest.manifest_schema_version == "raw-rca-manifest-v5"
    assert manifest.model_input_sha256 is None
    assert "model_input_sha256" not in manifest.to_dict()
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest


def test_manifest_v6_requires_a_valid_model_input_hash() -> None:
    seed = 1001
    manifest = run_raw_experiment(
        _run_config(seed), FakeProvider(raw_output=_correct_response(seed).to_json())
    )
    with pytest.raises(ValueError, match="requires model_input_sha256"):
        replace(manifest, model_input_sha256=None)
    with pytest.raises(ValueError, match="requires model_input_sha256"):
        replace(manifest, model_input_sha256="not-a-sha256")


def test_dry_run_requires_execute_and_creates_no_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = tmp_path / RESULT_PATH.name
    args = build_parser().parse_args(
        ["run-pilot", "--config", str(CONFIG), "--results", str(result)]
    )
    args.handler(args)
    pending = json.loads(capsys.readouterr().out)
    assert pending["execution"] == "pending"
    assert pending["pilot"]["incident_family"] == INCIDENT_002_FAMILY
    assert pending["pilot"]["development_seeds"] == list(
        INCIDENT_002_DEVELOPMENT_SEEDS
    )
    assert pending["pilot"]["validation_seeds"] == []
    assert pending["pilot"]["held_out_seeds"] == []
    assert result.exists() is False


def test_proposed_result_path_is_covered_by_git_ignore_policy() -> None:
    assert "results/*" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert RESULT_PATH.relative_to(ROOT).parts[0] == "results"
