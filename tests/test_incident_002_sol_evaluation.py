from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from diagbench.generators.incident_002 import generate_incident_002
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.incident_families import (
    INCIDENT_002_DEVELOPMENT_SEEDS,
    INCIDENT_002_FAMILY,
    INCIDENT_002_SEED_SELECTION_VERSION,
)
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.pricing import PricingSnapshot
from diagpriv.evaluation.prompt_v2 import PROMPT_SHA256, build_prompt_v2

ROOT = Path(__file__).parents[1]
LUNA_CONFIG = ROOT / "experiments" / "incident_002_raw_development.toml"
SOL_CONFIG = ROOT / "experiments" / "incident_002_raw_sol_development.toml"
SOL_PRICING = (
    ROOT / "experiments" / "pricing" / "openai_gpt_5_6_sol_2026-09-10.toml"
)
SOL_RESULT_PATH = (
    ROOT
    / "results"
    / "incident_002_raw_sol_development_gpt_5_6_sol_medium.jsonl"
)


def test_sol_qualification_config_is_exactly_the_approved_scope() -> None:
    definition = PilotDefinition.load(SOL_CONFIG)
    assert definition.pilot_id == "incident-002-raw-sol-development-v1"
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
    assert definition.requested_model == "gpt-5.6-sol"
    assert definition.reasoning_effort == "medium"
    assert "temperature" not in definition.decoding_settings
    assert definition.intended_temperature == 0.0
    assert definition.effective_temperature is None
    assert definition.prompt_version == "raw-rca-v2"
    assert definition.prompt_sha256 == PROMPT_SHA256
    assert definition.taxonomy_version == "rca-taxonomy-v2"
    assert definition.scorer_version == "raw-rca-scorer-v2"


def test_sol_and_luna_have_identical_substantive_protocol_except_model() -> None:
    luna = PilotDefinition.load(LUNA_CONFIG)
    sol = PilotDefinition.load(SOL_CONFIG)
    for field in (
        "provider",
        "incident_family",
        "manifest_schema_version",
        "development_seed_selection_version",
        "condition",
        "prompt_version",
        "prompt_sha256",
        "taxonomy_version",
        "scorer_version",
        "seed_scope",
        "development_seeds",
        "validation_seeds",
        "held_out_seeds",
        "calls_per_seed",
        "model_version_metadata_environment_variable",
        "reasoning_effort",
        "decoding_settings",
        "intended_temperature",
        "effective_temperature",
    ):
        assert getattr(sol, field) == getattr(luna, field), field
    assert luna.requested_model == "gpt-5.6-luna"
    assert sol.requested_model == "gpt-5.6-sol"
    assert sol.temperature_omission_reason == (
        "Temperature is omitted to preserve the decoding protocol used by the "
        "matched GPT-5.6 Luna raw-development baseline; no claim is made that "
        "GPT-5.6 Sol rejects the parameter."
    )
    assert sol.temperature_omission_reason != luna.temperature_omission_reason


def test_sol_matched_input_hashes_equal_frozen_luna_observations() -> None:
    definition = PilotDefinition.load(SOL_CONFIG)
    assert definition.matched_input_baseline_pilot_id == (
        "incident-002-raw-development-v1"
    )
    assert definition.matched_input_baseline_result_sha256 == (
        "43004a011443fd2b2ca1789e4ce57198484b8cad01e50f80b240679148d6b425"
    )
    assert set(definition.matched_model_input_sha256_by_seed) == set(
        INCIDENT_002_DEVELOPMENT_SEEDS
    )
    for seed in INCIDENT_002_DEVELOPMENT_SEEDS:
        prompt = build_prompt_v2(generate_incident_002(seed).model_view())
        actual = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        assert definition.matched_model_input_sha256_by_seed[seed] == actual


def test_sol_config_fails_closed_if_a_matched_input_hash_changes(
    tmp_path: Path,
) -> None:
    changed = SOL_CONFIG.read_text(encoding="utf-8").replace(
        "68962f980e6db9ff4d5cf2e6aa0b340aa9a7b00a850d74efea96a741eb72f180",
        "0" * 64,
    )
    path = tmp_path / "mismatched-sol.toml"
    path.write_text(changed, encoding="utf-8")
    with pytest.raises(ValueError, match="differs from baseline for seed 1000"):
        PilotDefinition.load(path)


def test_sol_pricing_snapshot_is_separate_from_scientific_scoring() -> None:
    pricing = PricingSnapshot.load(SOL_PRICING)
    assert pricing.pricing_snapshot_id == "openai-gpt-5.6-sol-2026-09-10"
    assert pricing.requested_model == "gpt-5.6-sol"
    assert pricing.input_usd_per_unit == 4.0
    assert pricing.cached_input_usd_per_unit == 0.4
    assert pricing.cache_write_input_usd_per_unit == 5.0
    assert pricing.output_usd_per_unit == 20.0
    assert pricing.source == (
        "https://developers.openai.com/api/docs/models/gpt-5.6-sol"
    )


def test_sol_dry_run_requires_execute_and_creates_no_result(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    result = tmp_path / SOL_RESULT_PATH.name
    args = build_parser().parse_args(
        ["run-pilot", "--config", str(SOL_CONFIG), "--results", str(result)]
    )
    args.handler(args)
    pending = json.loads(capsys.readouterr().out)
    assert pending["execution"] == "pending"
    assert pending["pilot"]["requested_model"] == "gpt-5.6-sol"
    assert pending["pilot"]["development_seeds"] == list(
        INCIDENT_002_DEVELOPMENT_SEEDS
    )
    assert pending["pilot"]["validation_seeds"] == []
    assert pending["pilot"]["held_out_seeds"] == []
    assert pending["pilot"]["matched_input"]["baseline_pilot_id"] == (
        "incident-002-raw-development-v1"
    )
    assert result.exists() is False


def test_sol_result_path_is_covered_by_git_ignore_policy() -> None:
    assert "results/*" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert SOL_RESULT_PATH.relative_to(ROOT).parts[0] == "results"
