from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from diagbench.generators.incident_003 import (
    TEMPORAL_TEMPLATES,
    generate_incident_003,
)
from diagbench.temporal import before
from diagpriv.evaluation import cli as evaluation_cli
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.incident_families import (
    INCIDENT_003_DEVELOPMENT_SEEDS,
    INCIDENT_003_FAMILY,
    INCIDENT_003_SEED_SELECTION_VERSION,
)
from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.prompt_v2 import PROMPT_SHA256, build_prompt_v2
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.response import RCAResponseV2
from diagpriv.evaluation.runner import (
    ProtectedSeedError,
    RawRunConfig,
    prepare_model_input,
    run_raw_experiment,
)
from diagpriv.invariants import evaluate_invariants

ROOT = Path(__file__).parents[1]
CONFIG = ROOT / "experiments" / "incident_003_raw_sol_development.toml"
RESULT_PATH = (
    ROOT
    / "results"
    / "incident_003_raw_sol_development_gpt_5_6_sol_medium.jsonl"
)
PRICING_PATH = (
    ROOT / "experiments" / "pricing" / "openai_gpt_5_6_sol_2026-09-10.toml"
)
EXPECTED_SELECTION = (
    (1000, "wide_overlap", 4, True, "compensation_completes_before_original"),
    (1001, "wide_overlap", 2, True, "original_completes_before_compensation"),
    (1002, "tight_overlap", 4, False, "compensation_completes_before_original"),
    (1003, "tight_overlap", 2, False, "compensation_completes_before_original"),
    (1004, "short_overlap", 3, True, "compensation_completes_before_original"),
    (1015, "delayed_compensation", 4, False, "compensation_completes_before_original"),
    (1017, "delayed_compensation", 3, False, "original_completes_before_compensation"),
    (1018, "short_overlap", 5, True, "compensation_completes_before_original"),
)
EXPECTED_HASHES = {
    1000: "9c9ef3c804ef9204262a9e9469004289714c8fe32cf70b6f982d0ee4982b5c55",
    1001: "e6130243472f0e688c39bffbc76e4dbd932004770ca4413ae05dd4484dad3fba",
    1002: "ab2c1b87e74f973b4c1746284e2d2e2a4e31f5d9a05093271dbdd8470643a5be",
    1003: "7822bddef226d46e5991011f7f7af772aa2ea4d565541d99b76ac0011fe68184",
    1004: "2fe36fe6ac7dd4a2585dc16910683b37978903f816c36c907db26fa4144bbc9d",
    1015: "99d18bfdd30e5a012dcae97ec9d34469833ef4b243d6ab8660caf9f19e01d002",
    1017: "8e2fabbc9be83c07314ca05161b9a0e673b01bec5925933aad1f428236eb9cbf",
    1018: "0252355478316de3a15a401ae8de24bfa55802ac5a732e576582cc4cf5923458",
}


def _selection_row(seed: int) -> tuple[int, str, int, bool, str]:
    incident = generate_incident_003(seed)
    target = str(incident.metadata["target_operation_id"])
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
    completion_order = (
        "compensation_completes_before_original"
        if before(
            str(compensation["completed_at"]), str(execution["completed_at"])
        )
        else "original_completes_before_compensation"
    )
    return (
        seed,
        str(incident.metadata["temporal_template_name"]),
        int(incident.metadata["target_chronological_position"]),
        bool(incident.metadata["target_dependency_warning"]),
        completion_order,
    )


def _correct_response(seed: int) -> RCAResponseV2:
    incident = generate_incident_003(seed)
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
        explanation="Visible temporal evidence supports the selected RCA dimensions.",
        confidence=0.9,
    )


def _run_config(seed: int) -> RawRunConfig:
    return RawRunConfig(
        experiment_id=f"incident-003-offline-{seed}",
        seed=seed,
        model="offline-fixture",
        model_version="test-version",
        incident_family=INCIDENT_003_FAMILY,
        manifest_schema_version="raw-rca-manifest-v6",
        reasoning_effort="medium",
        decoding_settings={"max_output_tokens": 4096},
        intended_temperature=0.0,
        temperature_omission_reason="Temperature is intentionally omitted.",
        prompt_version="raw-rca-v2",
        timestamp="2036-01-01T00:00:00+00:00",
    )


def test_first_two_per_template_selection_is_exact_and_stops_immediately() -> None:
    selected: list[tuple[int, str, int, bool, str]] = []
    counts = {name: 0 for name in TEMPORAL_TEMPLATES}
    seed = 1000
    while any(count < 2 for count in counts.values()):
        row = _selection_row(seed)
        template = row[1]
        if counts[template] < 2:
            selected.append(row)
            counts[template] += 1
        seed += 1
    assert tuple(selected) == EXPECTED_SELECTION
    assert tuple(row[0] for row in selected) == INCIDENT_003_DEVELOPMENT_SEEDS
    assert set(counts.values()) == {2}
    assert seed == 1019


def test_incident_003_raw_config_is_exactly_the_approved_scope() -> None:
    definition = PilotDefinition.load(CONFIG)
    assert definition.pilot_id == "incident-003-raw-sol-development-v1"
    assert definition.provider == "openai-responses"
    assert definition.incident_family == INCIDENT_003_FAMILY
    assert definition.manifest_schema_version == "raw-rca-manifest-v6"
    assert (
        definition.development_seed_selection_version
        == INCIDENT_003_SEED_SELECTION_VERSION
    )
    assert definition.condition == "raw"
    assert definition.seed_scope == "development_only"
    assert definition.development_seeds == INCIDENT_003_DEVELOPMENT_SEEDS
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.result_path_must_not_exist is True
    assert definition.requested_model == "gpt-5.6-sol"
    assert definition.reasoning_effort == "medium"
    assert definition.decoding_settings == {"max_output_tokens": 4096}
    assert "temperature" not in definition.decoding_settings
    assert definition.intended_temperature == 0.0
    assert definition.effective_temperature is None
    assert definition.prompt_version == "raw-rca-v2"
    assert definition.prompt_sha256 == PROMPT_SHA256
    assert definition.taxonomy_version == "rca-taxonomy-v2"
    assert definition.scorer_version == "raw-rca-scorer-v2"
    assert definition.expected_model_input_sha256_by_seed == EXPECTED_HASHES


@pytest.mark.parametrize(
    ("original", "changed", "message"),
    [
        (
            "development_seeds = [1000, 1001, 1002, 1003, 1004, 1015, 1017, 1018]",
            "development_seeds = [1000, 1001, 1002, 1003, 1004, 1015, 1017, 1019]",
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
            "Incident 003 pilot must be development-only",
        ),
        (
            'incident_family = "incident_003_temporal_compensation"',
            'incident_family = "incident_001"',
            "seed-selection metadata is valid only for Incident 003",
        ),
        (
            'manifest_schema_version = "raw-rca-manifest-v6"',
            'manifest_schema_version = "raw-rca-manifest-v5"',
            "Incident 003 pilot requires manifest schema v6",
        ),
        (
            "result_path_must_not_exist = true",
            "result_path_must_not_exist = false",
            "requires a previously absent result path",
        ),
    ],
)
def test_incident_003_config_rejects_scope_or_provenance_changes(
    tmp_path: Path, original: str, changed: str, message: str
) -> None:
    path = tmp_path / "invalid.toml"
    path.write_text(
        CONFIG.read_text(encoding="utf-8").replace(original, changed),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=message):
        PilotDefinition.load(path)


def test_incident_003_runner_routes_only_to_incident_003(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def older_family_must_not_run(seed: int):
        raise AssertionError(f"An older incident family was routed for seed {seed}")

    monkeypatch.setattr(
        "diagpriv.evaluation.incident_families.generate_incident_001",
        older_family_must_not_run,
    )
    monkeypatch.setattr(
        "diagpriv.evaluation.incident_families.generate_incident_002",
        older_family_must_not_run,
    )
    seed = INCIDENT_003_DEVELOPMENT_SEEDS[0]
    provider = FakeProvider(raw_output=_correct_response(seed).to_json())
    manifest = run_raw_experiment(_run_config(seed), provider)
    incident = generate_incident_003(seed)
    assert manifest.incident_family == INCIDENT_003_FAMILY
    assert manifest.benchmark_version == "diagbench-v0.4"
    assert manifest.score is not None
    assert manifest.score.exact_root_cause_correct is True
    assert incident.model_view().to_json().strip() in provider.requests[0].prompt


@pytest.mark.parametrize(
    "seed", [999, 1005, 1019, 1999, 2000, 2999, 10_000, 20_000, 20_999]
)
def test_incident_003_runner_rejects_every_non_frozen_seed_before_generation(
    seed: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    generated = False

    def fail_if_generated(candidate: int):
        nonlocal generated
        generated = True
        raise AssertionError(f"Unapproved seed {candidate} was generated")

    monkeypatch.setattr(
        "diagpriv.evaluation.incident_families.generate_incident_003",
        fail_if_generated,
    )
    with pytest.raises(ProtectedSeedError):
        prepare_model_input(_run_config(seed))
    assert generated is False


def test_all_frozen_inputs_have_exact_hashes_and_exclude_hidden_data() -> None:
    definition = PilotDefinition.load(CONFIG)
    for seed in INCIDENT_003_DEVELOPMENT_SEEDS:
        incident = generate_incident_003(seed)
        prompt = build_prompt_v2(incident.model_view())
        actual = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        assert actual == EXPECTED_HASHES[seed]
        assert definition.expected_model_input_sha256_by_seed[seed] == actual
        for forbidden in (
            "ground_truth",
            "diagnostic_invariants",
            "expected_evidence",
            "sensitive_fields",
            "temporal_template_name",
            "target_operation_id",
            "healthy_control_operation_ids",
        ):
            assert forbidden not in prompt


def test_manifest_v6_records_exact_incident_003_provider_input() -> None:
    seed = INCIDENT_003_DEVELOPMENT_SEEDS[0]
    provider = FakeProvider(raw_output=_correct_response(seed).to_json())
    manifest = run_raw_experiment(_run_config(seed), provider)
    expected = hashlib.sha256(provider.requests[0].prompt.encode("utf-8")).hexdigest()
    assert manifest.manifest_schema_version == "raw-rca-manifest-v6"
    assert manifest.prompt_sha256 == PROMPT_SHA256
    assert manifest.model_input_sha256 == expected == EXPECTED_HASHES[seed]
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest


def test_raw_temporal_preflight_holds_for_every_frozen_seed() -> None:
    required = {
        "target_deadline_precedes_original_completion",
        "target_compensation_after_deadline",
        "target_compensation_precedes_original_completion",
        "target_execution_compensation_overlap",
        "target_success_after_compensation_start",
        "target_inconsistent_state",
        "control_completion_precedes_deadline",
        "control_no_compensation",
        "benign_slow_control_succeeds_before_deadline",
        "legitimate_compensation_event_order",
        "legitimate_compensation_terminal_state",
        "legitimate_compensation_effect_absence",
    }
    for seed in INCIDENT_003_DEVELOPMENT_SEEDS:
        incident = generate_incident_003(seed)
        results = {
            result.name: result
            for result in evaluate_invariants(incident, incident.model_view())
        }
        assert required.issubset(results)
        assert all(results[name].preserved for name in required)


def test_dry_run_verifies_eight_hashes_without_provider_or_result(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = tmp_path / RESULT_PATH.name

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
    assert payload["pilot"]["development_seeds"] == list(
        INCIDENT_003_DEVELOPMENT_SEEDS
    )
    assert payload["pilot"]["validation_seeds"] == []
    assert payload["pilot"]["held_out_seeds"] == []
    assert payload["input_preflight"]["status"] == "verified"
    assert payload["input_preflight"]["model_input_sha256_by_seed"] == {
        str(seed): digest for seed, digest in EXPECTED_HASHES.items()
    }
    assert result.exists() is False


def test_hash_mismatch_stops_execute_before_provider_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changed = CONFIG.read_text(encoding="utf-8").replace(
        EXPECTED_HASHES[1000], "0" * 64
    )
    changed = changed.replace(
        'snapshot = "pricing/openai_gpt_5_6_sol_2026-09-10.toml"',
        f'snapshot = "{PRICING_PATH}"',
    )
    changed_config = tmp_path / "changed-input.toml"
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
    with pytest.raises(ValueError, match="differs from frozen provenance for seed 1000"):
        args.handler(args)
    assert provider_configured is False


def test_existing_result_path_stops_before_provider_setup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = tmp_path / "already-exists.jsonl"
    result.write_text("historical\n", encoding="utf-8")
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
            str(CONFIG),
            "--results",
            str(result),
            "--execute",
        ]
    )
    with pytest.raises(SystemExit, match="result path already exists"):
        args.handler(args)
    assert provider_configured is False
    assert result.read_text(encoding="utf-8") == "historical\n"


def test_result_path_is_ignored_and_not_created_during_preparation() -> None:
    assert "results/*" in (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert RESULT_PATH.relative_to(ROOT).parts[0] == "results"
    assert not RESULT_PATH.exists()
