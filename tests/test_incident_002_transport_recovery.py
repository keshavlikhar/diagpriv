from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.manifest import ExperimentManifest, append_manifest
from diagpriv.evaluation.providers import FakeProvider, InvocationResult
from diagpriv.evaluation.reporting import inspection_records, load_manifests
from diagpriv.evaluation.response import ParsedResponse
from diagpriv.evaluation.runner import RawRunConfig, prepare_model_input, run_raw_experiment
from diagpriv.evaluation.transport_recovery import (
    CONDITIONS, ELIGIBLE_CELLS, RECOVERY_PROTOCOL, RecoveryDefinition,
    prepare_recovery,
)

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "experiments/incident_002_transport_recovery.toml"
SEEDS = (1000, 1001, 1003, 1004, 1005, 1017)
PUBLIC_TEST_KEY = bytes(range(32))  # Public fixture only; never an experiment key.
VALID = json.dumps({
    "observed_outcome": "missing_effect", "trigger": "malformed_or_unexpected_input",
    "subsequent_action": "no_follow_on_action",
    "failure_mechanism": "validation_or_input_handling_failure",
    "affected_component": "operation_executor", "supporting_evidence": [],
    "explanation": "Offline synthetic recovery fixture.", "confidence": 0.9,
})


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def source_fixture(tmp_path: Path) -> tuple[Path, RecoveryDefinition]:
    """Synthetic sources in pytest's temporary tree; no local results required."""
    original = RecoveryDefinition.load(CONFIG)
    text = CONFIG.read_text()
    failures = {(c, s, t): error for c, s, t, error in ELIGIBLE_CELLS}
    for condition in CONDITIONS:
        source = original.data["sources"][condition]
        one_path = tmp_path / source["trial_one_path"]
        repeated_path = tmp_path / source["repeated_path"]
        for seed in SEEDS:
            baseline = run_raw_experiment(RawRunConfig(
                experiment_id=f"fixture-{condition}-{seed}-trial-1", seed=seed,
                model="gpt-5.6-sol", model_version=None,
                incident_family="incident_002_format_defect",
                manifest_schema_version="raw-rca-manifest-v6",
                reasoning_effort="medium", condition=condition,
                decoding_settings={"max_output_tokens": 4096},
                intended_temperature=0.0,
                temperature_omission_reason="Frozen fixture decoding protocol.",
                prompt_version="raw-rca-v2",
                hmac_key=PUBLIC_TEST_KEY if condition == "hmac-v1" else None,
                transformation_key_id="public-fixture" if condition == "hmac-v1" else None,
            ), FakeProvider(raw_output=VALID))
            append_manifest(one_path, baseline)
            for trial in (2, 3):
                repeated = replace(
                    baseline, manifest_schema_version="raw-rca-manifest-v7",
                    experiment_id=f"fixture-{condition}-{seed}-trial-{trial}",
                    trial_index=trial,
                )
                if (condition, seed, trial) in failures:
                    repeated = replace(repeated, score=None, response=ParsedResponse(
                        "provider_error", "",
                        error=f"OpenAI Responses API failure: {failures[condition, seed, trial]}",
                    ))
                append_manifest(repeated_path, repeated)
        text = text.replace(source["trial_one_sha256"], digest(one_path))
        text = text.replace(source["repeated_sha256"], digest(repeated_path))
    config = tmp_path / "experiments" / CONFIG.name
    config.parent.mkdir()
    config.write_text(text)
    pricing = tmp_path / "experiments/pricing/openai_gpt_5_6_sol_2026-09-10.toml"
    pricing.parent.mkdir()
    pricing.write_bytes((ROOT / pricing.relative_to(tmp_path)).read_bytes())
    return config, RecoveryDefinition.load(config)


def source_hashes(definition: RecoveryDefinition) -> dict[str, str]:
    return {
        source[f"{prefix}_path"]: digest(definition.repository_root / source[f"{prefix}_path"])
        for source in definition.data["sources"].values()
        for prefix in ("trial_one", "repeated")
    }


def test_frozen_schedule_is_exactly_ten_sparse_failures() -> None:
    definition = RecoveryDefinition.load(CONFIG)
    cells = definition.data["cells"]
    assert tuple((c["condition"], c["seed"], c["trial_index"], c["failure_type"]) for c in cells) == ELIGIBLE_CELLS
    assert len(cells) == 10
    assert {c["trial_index"] for c in cells} == {2, 3}
    assert sum(c["condition"] == "redaction-v1" for c in cells) == 9
    assert sum(c["condition"] == "tokenization-v1" for c in cells) == 1
    assert "results/*" in (ROOT / ".gitignore").read_text()


@pytest.mark.parametrize("change", [
    "valid_seed", "extra_cell", "missing_cell", "duplicate_cell", "validation",
    "held_out", "trial_four", "attempt_two", "attempt_bool", "seed_bool",
    "temperature", "model", "family", "condition", "scope", "extra_section",
])
def test_invalid_schedule_is_rejected_before_generation(change: str, monkeypatch: pytest.MonkeyPatch) -> None:
    definition = RecoveryDefinition.load(CONFIG)
    data = deepcopy(definition.data)
    if change == "valid_seed": data["cells"][0]["seed"] = 1000
    elif change == "extra_cell": data["cells"].append(data["cells"][0])
    elif change == "missing_cell": data["cells"].pop()
    elif change == "duplicate_cell": data["cells"][1] = data["cells"][0]
    elif change == "validation": data["cells"][0]["seed"] = 2000
    elif change == "held_out": data["cells"][0]["seed"] = 20000
    elif change == "trial_four": data["cells"][0]["trial_index"] = 4
    elif change == "attempt_two": data["recovery"]["attempt_index"] = 2
    elif change == "attempt_bool": data["recovery"]["attempt_index"] = True
    elif change == "seed_bool": data["cells"][0]["seed"] = True
    elif change == "temperature": data["settings"]["temperature"] = 0.0
    elif change == "model": data["settings"]["requested_model"] = "other-model"
    elif change == "family": data["settings"]["incident_family"] = "incident_001_duplicate_payment"
    elif change == "condition": data["cells"][0]["condition"] = "raw"
    elif change == "scope": data["recovery"]["validation_seeds"] = [2000]
    elif change == "extra_section": data["decoding"] = {"temperature": 0}
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid schedule must fail before generation")
    monkeypatch.setattr("diagpriv.evaluation.transport_recovery.prepare_model_input", forbidden)
    with pytest.raises(ValueError):
        prepare_recovery(replace(definition, data=data))


def test_preflight_matches_both_frozen_sources_without_mutating_them(source_fixture) -> None:
    _, definition = source_fixture
    before = source_hashes(definition)
    plan, report = prepare_recovery(definition)
    assert len(plan) == report["scheduled_calls"] == 10
    assert report["source_observations_audited"] == 60
    assert report["source_valid_responses"] == 50
    assert report["source_transport_failures"] == 10
    for config, item in zip(plan, report["planned_observations"], strict=True):
        assert item["matches_failed_observation"] and item["matches_trial_one"]
        assert item["recovery_metadata_absent_from_input"]
        prepared = prepare_model_input(config)
        ordinary = prepare_model_input(replace(config, recovery_provenance=None))
        assert prepared.prompt == ordinary.prompt
        assert RECOVERY_PROTOCOL not in prepared.prompt
        assert config.experiment_id not in prepared.prompt
        assert config.recovery_provenance.original_experiment_id not in prepared.prompt
        assert "recovery_provenance" not in prepared.model_view.to_dict()
    assert source_hashes(definition) == before
    assert not definition.result_path.exists()


def test_manifest_v8_round_trip_and_v7_remain_distinct(source_fixture) -> None:
    _, definition = source_fixture
    plan, _ = prepare_recovery(definition)
    config = plan[0]
    provider = FakeProvider(raw_output=VALID)
    manifest = run_raw_experiment(config, provider)
    assert manifest.trial_index == manifest.recovery_provenance.recovery_of_trial_index == 3
    assert manifest.recovery_provenance.recovery_attempt_index == 1
    assert manifest.model_input_sha256 == config.expected_model_input_sha256
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest
    ordinary = replace(manifest, manifest_schema_version="raw-rca-manifest-v7", recovery_provenance=None)
    assert "recovery_provenance" not in ordinary.to_dict()
    assert ExperimentManifest.from_json(ordinary.to_json()) == ordinary
    assert provider.requests[0].prompt == prepare_model_input(replace(config, recovery_provenance=None)).prompt


@pytest.mark.parametrize("change", ["missing", "v7", "trial", "seed", "condition"])
def test_mismatched_recovery_identity_fails_before_invocation(source_fixture, change: str) -> None:
    _, definition = source_fixture
    plan, _ = prepare_recovery(definition)
    config = plan[0]
    if change == "missing": config = replace(config, recovery_provenance=None)
    elif change == "v7": config = replace(config, manifest_schema_version="raw-rca-manifest-v7")
    elif change == "trial": config = replace(config, trial_index=2)
    elif change == "seed": config = replace(config, seed=1000)
    elif change == "condition": config = replace(config, condition="raw")
    provider = FakeProvider(raw_output=VALID)
    with pytest.raises(ValueError): run_raw_experiment(config, provider)
    assert provider.requests == []


@pytest.mark.parametrize("change", ["hash", "extra_failure", "now_valid", "parser_failure", "settings", "input_hash"])
def test_changed_source_stops_preflight(source_fixture, change: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _, definition = source_fixture
    data = deepcopy(definition.data)
    source = data["sources"]["redaction-v1"]
    path = definition.repository_root / source["repeated_path"]
    rows = load_manifests(path)
    if change == "hash":
        path.write_text(path.read_text() + "\n")
    else:
        index = next(i for i, m in enumerate(rows) if m.seed == 1001 and m.trial_index == 3)
        if change == "extra_failure":
            rows[0] = replace(rows[0], score=None, response=ParsedResponse("provider_error", "", error="OpenAI Responses API failure: URLError"))
        elif change == "now_valid": rows[index] = replace(rows[index], response=rows[0].response, score=rows[0].score)
        elif change == "parser_failure": rows[index] = replace(rows[index], response=ParsedResponse("malformed_json", "bad JSON"))
        elif change == "settings": rows[index] = replace(rows[index], reasoning_effort="high")
        elif change == "input_hash": rows[index] = replace(rows[index], model_input_sha256="0" * 64)
        path.write_text("".join(m.to_json(indent=None) for m in rows))
        source["repeated_sha256"] = digest(path)
    def forbidden(*args, **kwargs):
        raise AssertionError("Source validation must precede incident generation")
    monkeypatch.setattr("diagpriv.evaluation.transport_recovery.prepare_model_input", forbidden)
    with pytest.raises(ValueError): prepare_recovery(replace(definition, data=data))


def test_reconstruction_mismatch_stops_preflight(source_fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    _, definition = source_fixture
    def changed(config):
        return prepare_model_input(replace(config, expected_model_input_sha256="0" * 64))
    monkeypatch.setattr("diagpriv.evaluation.transport_recovery.prepare_model_input", changed)
    with pytest.raises(ValueError, match="differs from frozen provenance"):
        prepare_recovery(definition)


def test_dry_run_enumerates_ten_before_provider_setup(source_fixture, monkeypatch, capsys) -> None:
    config_path, definition = source_fixture
    def forbidden(): raise AssertionError("Dry run must not set up a provider")
    monkeypatch.setattr("diagpriv.evaluation.cli.OpenAIResponsesProvider", forbidden)
    args = build_parser().parse_args(["run-recovery", "--config", str(config_path), "--results", str(definition.result_path)])
    args.handler(args)
    output = json.loads(capsys.readouterr().out)
    assert output["execution"] == "pending"
    assert output["scheduled_calls"] == len(output["planned_observations"]) == 10
    assert not definition.result_path.exists()


def test_sparse_execution_preserves_every_outcome_and_disallows_second_launch(source_fixture, monkeypatch, capsys) -> None:
    config_path, definition = source_fixture
    before = source_hashes(definition)
    wrong = json.loads(VALID)
    wrong["trigger"] = "resource_exhaustion"
    outcomes = [
        InvocationResult("success", raw_output=json.dumps(wrong)),
        InvocationResult("provider_error", error="Offline transport failure"),
        InvocationResult("success", raw_output="malformed"),
        InvocationResult("refusal", raw_output="Offline refusal"),
        InvocationResult("rate_limited", error="Offline rate limit"),
    ] + [InvocationResult("success", raw_output=VALID)] * 5
    class Provider:
        is_configured = True
        requests = []
        def invoke(self, request):
            self.requests.append(request)
            return outcomes[len(self.requests) - 1]
    provider = Provider()
    monkeypatch.setattr("diagpriv.evaluation.cli.OpenAIResponsesProvider", lambda: provider)
    args = build_parser().parse_args(["run-recovery", "--config", str(config_path), "--results", str(definition.result_path), "--execute"])
    args.handler(args)
    records = load_manifests(definition.result_path)
    assert len(records) == len(provider.requests) == 10
    assert [(r.condition, r.seed, r.trial_index) for r in records] == [cell[:3] for cell in ELIGIBLE_CELLS]
    assert [r.response.status for r in records[:5]] == ["valid", "provider_error", "malformed_json", "refusal", "rate_limited"]
    assert not records[0].score.trigger_correct
    assert all(r.recovery_provenance.recovery_attempt_index == 1 for r in records)
    assert all("recovery_provenance" in r for r in inspection_records(definition.result_path))
    assert json.loads(capsys.readouterr().out)["analysis_role"] == "transport-recovery sensitivity analysis"
    with pytest.raises(ValueError, match="already exists"): args.handler(args)
    assert len(provider.requests) == 10
    assert source_hashes(definition) == before


@pytest.mark.parametrize("abort_on", [1, 2])
def test_runner_abort_leaves_reservation_and_never_resumes(source_fixture, monkeypatch, abort_on: int) -> None:
    config_path, definition = source_fixture
    class Provider:
        is_configured = True
        calls = 0
        def invoke(self, request):
            self.calls += 1
            if self.calls == abort_on: raise RuntimeError("Offline runner abort")
            return InvocationResult("success", raw_output=VALID)
    provider = Provider()
    monkeypatch.setattr("diagpriv.evaluation.cli.OpenAIResponsesProvider", lambda: provider)
    args = build_parser().parse_args(["run-recovery", "--config", str(config_path), "--results", str(definition.result_path), "--execute"])
    with pytest.raises(RuntimeError, match="runner abort"): args.handler(args)
    assert definition.result_path.exists()
    assert len(load_manifests(definition.result_path)) == abort_on - 1
    with pytest.raises(ValueError, match="already exists"): args.handler(args)
    assert provider.calls == abort_on


def test_alternate_result_path_cannot_bypass_single_attempt(source_fixture, monkeypatch) -> None:
    config_path, definition = source_fixture
    def forbidden(): raise AssertionError("Provider setup must not occur")
    monkeypatch.setattr("diagpriv.evaluation.cli.OpenAIResponsesProvider", forbidden)
    args = build_parser().parse_args(["run-recovery", "--config", str(config_path), "--results", str(definition.result_path.with_name("alternate.jsonl")), "--execute"])
    with pytest.raises(ValueError, match="dedicated frozen result path"): args.handler(args)


def test_v8_provenance_rejects_second_attempt(source_fixture) -> None:
    _, definition = source_fixture
    plan, _ = prepare_recovery(definition)
    with pytest.raises(ValueError, match="attempt index 1"):
        replace(plan[0].recovery_provenance, recovery_attempt_index=2)
