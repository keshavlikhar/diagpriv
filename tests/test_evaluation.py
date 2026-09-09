from __future__ import annotations

import json
from pathlib import Path

import pytest

from diagbench.generators.incident_001 import generate_incident_001
from diagpriv.evaluation.manifest import ExperimentManifest, append_manifest
from diagpriv.evaluation.prompt import PROMPT_VERSION, build_prompt, prompt_template
from diagpriv.evaluation.providers import FakeProvider
from diagpriv.evaluation.response import RCAResponse, parse_response
from diagpriv.evaluation.runner import (
    ProtectedSeedError,
    RawRunConfig,
    pilot_seed_plan,
    run_raw_experiment,
)
from diagpriv.evaluation.scoring import score_response


def _expected_ids(seed: int = 1001) -> tuple[str, ...]:
    incident = generate_incident_001(seed)
    return tuple(
        sorted(
            {
                str(reference.selector["evidence_id"])
                for expected in incident.expected_evidence
                for reference in expected.references
            }
        )
    )


def _correct_response(seed: int = 1001, *, visible_component: bool = False) -> RCAResponse:
    incident = generate_incident_001(seed)
    component = (
        incident.component_mappings[0].visible_names[0]
        if visible_component
        else incident.ground_truth.affected_component
    )
    return RCAResponse(
        observed_outcome="duplicate_payment",
        trigger="retry_after_timeout",
        failure_mechanism="missing_or_ineffective_idempotency",
        affected_component=component,
        supporting_evidence=_expected_ids(seed),
        explanation="One request was received twice around a timeout and produced two writes.",
        confidence=0.93,
    )


def _config(seed: int, experiment_id: str = "raw-test-001") -> RawRunConfig:
    return RawRunConfig(
        experiment_id=experiment_id,
        seed=seed,
        model="offline-fixture",
        model_version="1",
        decoding_settings={"temperature": 0.0},
        timestamp="2032-01-01T00:00:00+00:00",
    )


def test_structured_rca_response_json_round_trip() -> None:
    response = _correct_response()
    assert RCAResponse.from_json(response.to_json()) == response
    json.dumps(response.to_dict())


def test_correct_rca_gets_full_component_and_evidence_score() -> None:
    score = score_response(generate_incident_001(1001), _correct_response())
    assert score.outcome_correct
    assert score.trigger_correct
    assert score.failure_mechanism_correct
    assert score.affected_component_correct
    assert score.exact_root_cause_correct
    assert score.evidence_precision == 1.0
    assert score.evidence_recall == 1.0
    assert score.evidence_f1 == 1.0
    assert score.overall_correct


def test_wrong_trigger_loses_only_trigger_credit() -> None:
    response = _correct_response()
    response = RCAResponse.from_dict(
        {**response.to_dict(), "trigger": "scheduled_reprocessing"}
    )
    score = score_response(generate_incident_001(1001), response)
    assert not score.trigger_correct
    assert score.outcome_correct
    assert score.failure_mechanism_correct
    assert score.affected_component_correct
    assert not score.exact_root_cause_correct


def test_wrong_mechanism_loses_only_mechanism_credit() -> None:
    response = _correct_response()
    response = RCAResponse.from_dict(
        {**response.to_dict(), "failure_mechanism": "database_corruption"}
    )
    score = score_response(generate_incident_001(1001), response)
    assert not score.failure_mechanism_correct
    assert score.outcome_correct
    assert score.trigger_correct
    assert score.affected_component_correct
    assert not score.exact_root_cause_correct


def test_visible_component_alias_maps_to_canonical_component() -> None:
    incident = generate_incident_001(1001)
    response = _correct_response(visible_component=True)
    assert response.affected_component in {
        entry.service for entry in incident.model_view().log_evidence
    }
    assert score_response(incident, response).affected_component_correct


def test_incorrect_component_is_rejected() -> None:
    response = _correct_response()
    response = RCAResponse.from_dict(
        {**response.to_dict(), "affected_component": "email-sender"}
    )
    score = score_response(generate_incident_001(1001), response)
    assert not score.affected_component_correct
    assert not score.exact_root_cause_correct


def test_nonexistent_evidence_ids_are_explicitly_scored() -> None:
    response = _correct_response()
    response = RCAResponse.from_dict(
        {
            **response.to_dict(),
            "supporting_evidence": [*_expected_ids(), "SYN-EVD-00000000"],
        }
    )
    score = score_response(generate_incident_001(1001), response)
    assert score.evidence_recall == 1.0
    assert score.evidence_precision < 1.0
    assert score.unknown_evidence_ids == ("SYN-EVD-00000000",)
    assert not score.evidence_supported
    assert not score.overall_correct


def test_malformed_output_produces_recorded_parse_failure() -> None:
    provider = FakeProvider(raw_output="{not valid json")
    manifest = run_raw_experiment(_config(1001), provider)
    assert manifest.response.status == "malformed_json"
    assert manifest.response.raw_output == "{not valid json"
    assert manifest.score is None


@pytest.mark.parametrize(
    ("raw_output", "expected_status"),
    [
        ("", "empty_response"),
        ("I cannot assist with this request.", "refusal"),
        ('{"observed_outcome": "duplicate_payment"}', "missing_fields"),
        (_correct_response().to_json().replace("duplicate_payment", "unknown_outcome"), "unknown_category"),
    ],
)
def test_structured_response_failures_are_preserved(
    raw_output: str, expected_status: str
) -> None:
    result = parse_response(raw_output)
    assert result.status == expected_status
    assert result.raw_output == raw_output


def test_provider_error_is_recorded() -> None:
    manifest = run_raw_experiment(
        _config(1001), FakeProvider(error="offline provider unavailable")
    )
    assert manifest.response.status == "provider_error"
    assert manifest.response.error == "offline provider unavailable"
    assert manifest.score is None


@pytest.mark.parametrize("seed", [1001, 2001])
def test_development_and_validation_seeds_run_normally(seed: int) -> None:
    provider = FakeProvider(raw_output=_correct_response(seed).to_json())
    manifest = run_raw_experiment(_config(seed, f"raw-{seed}"), provider)
    assert manifest.split in {"development", "validation"}
    assert manifest.score is not None
    assert manifest.score.exact_root_cause_correct


def test_held_out_evaluation_seed_requires_override_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = False

    def fail_if_generated(seed: int):
        nonlocal generated
        generated = True
        raise AssertionError(f"Held-out seed {seed} was consumed")

    monkeypatch.setattr(
        "diagpriv.evaluation.runner.generate_incident_001", fail_if_generated
    )
    with pytest.raises(ProtectedSeedError, match="allow_held_out"):
        run_raw_experiment(_config(10_000), FakeProvider())
    assert not generated


def test_default_pilot_plan_contains_no_held_out_seeds() -> None:
    plan = pilot_seed_plan()
    assert plan == (*range(1000, 1005), *range(2000, 2010))
    assert all(seed < 3000 for seed in plan)


def test_provider_receives_model_view_and_no_oracle_fields() -> None:
    incident = generate_incident_001(1001)
    provider = FakeProvider(raw_output=_correct_response().to_json())
    run_raw_experiment(_config(1001), provider)
    assert len(provider.requests) == 1
    prompt = provider.requests[0].prompt
    assert incident.model_view().to_json().strip() in prompt
    assert incident.ground_truth.outcome not in prompt
    assert incident.ground_truth.trigger not in prompt
    assert incident.ground_truth.failure_mechanism not in prompt
    assert "ground_truth" not in prompt
    assert "expected_evidence" not in prompt
    assert "diagnostic_invariants" not in prompt
    assert "sensitive_fields" not in prompt
    assert all(item.description not in prompt for item in incident.expected_evidence)
    assert all(item.description not in prompt for item in incident.diagnostic_invariants)


def test_versioned_prompt_avoids_excluded_research_context() -> None:
    template = prompt_template().lower()
    assert PROMPT_VERSION == "raw-rca-v1"
    for forbidden in (
        "diagpriv",
        "privacy",
        "masking",
        "diagnostic invariant",
        "expected evidence",
        "benchmark family",
        "duplicate_payment",
        "retry_after_timeout",
        "missing_or_ineffective_idempotency",
    ):
        assert forbidden not in template


def test_manifest_round_trip_and_append_only_persistence(tmp_path: Path) -> None:
    provider = FakeProvider(raw_output=_correct_response().to_json())
    manifest = run_raw_experiment(_config(1001), provider)
    assert ExperimentManifest.from_json(manifest.to_json()) == manifest

    path = tmp_path / "raw-results.jsonl"
    append_manifest(path, manifest)
    first_contents = path.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="already recorded"):
        append_manifest(path, manifest)
    assert path.read_text(encoding="utf-8") == first_contents
