from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from diagbench.generators.incident_001 import generate_incident_001
from diagpriv.evaluation.manifest import ExperimentManifest, append_manifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.prompt import (
    PROMPT_SHA256,
    PROMPT_VERSION,
    build_prompt,
    prompt_template,
)
from diagpriv.evaluation.providers import (
    FakeProvider,
    InvocationResult,
    ModelRequest,
    OpenAIResponsesProvider,
)
from diagpriv.evaluation.reporting import summarize_manifests, summarize_path
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
        run_raw_experiment(_config(20_000), FakeProvider())
    assert not generated


def test_retired_evaluation_seed_is_never_invokable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = False

    def fail_if_generated(seed: int):
        nonlocal generated
        generated = True
        raise AssertionError(f"Retired seed {seed} was consumed")

    monkeypatch.setattr(
        "diagpriv.evaluation.runner.generate_incident_001", fail_if_generated
    )
    with pytest.raises(ProtectedSeedError, match="Retired"):
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
    assert PROMPT_SHA256 == "0c06c1ec6d72ca08927a367aaf873d7bea2b34c6210ceb74824263dd7f2bd9cd"
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


def test_frozen_prompt_hash_detects_unversioned_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changed_prompt = tmp_path / "changed-prompt.txt"
    changed_prompt.write_text(prompt_template() + "changed\n", encoding="utf-8")
    monkeypatch.setattr("diagpriv.evaluation.prompt.PROMPT_PATH", changed_prompt)
    with pytest.raises(ValueError, match="Prompt hash mismatch"):
        prompt_template()


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


def test_frozen_pilot_definition_has_only_development_and_validation_seeds() -> None:
    path = Path(__file__).parents[1] / "experiments" / "raw_pilot_v1.toml"
    definition = PilotDefinition.load(path)
    assert definition.development_seeds == tuple(range(1000, 1005))
    assert definition.validation_seeds == tuple(range(2000, 2010))
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.decoding_settings["temperature"] == 0.0
    assert definition.prompt_sha256 == PROMPT_SHA256


def test_pilot_definition_rejects_new_held_out_seed_without_generating_it(
    tmp_path: Path,
) -> None:
    source = Path(__file__).parents[1] / "experiments" / "raw_pilot_v1.toml"
    changed = source.read_text(encoding="utf-8").replace(
        "held_out_seeds = []", "held_out_seeds = [20000]"
    )
    path = tmp_path / "invalid-pilot.toml"
    path.write_text(changed, encoding="utf-8")
    with pytest.raises(ValueError, match="must not contain held-out"):
        PilotDefinition.load(path)


def test_empty_pilot_summary_is_pending(tmp_path: Path) -> None:
    summary = summarize_path(tmp_path / "not-created.jsonl")
    for split in (summary.development, summary.validation):
        assert split.status == "pending"
        assert split.runs == 0
        assert split.valid_response_rate is None
        assert split.exact_rca_accuracy is None


def test_pilot_summary_separates_development_and_validation() -> None:
    development = run_raw_experiment(
        _config(1001, "summary-dev"),
        FakeProvider(raw_output=_correct_response(1001).to_json()),
    )
    validation = run_raw_experiment(
        _config(2001, "summary-validation"),
        FakeProvider(raw_output="{bad json"),
    )
    summary = summarize_manifests((development, validation))
    assert summary.development.runs == 1
    assert summary.development.exact_rca_accuracy == 1.0
    assert summary.validation.runs == 1
    assert summary.validation.valid_response_rate == 0.0
    assert summary.validation.parse_failures == {"malformed_json": 1}


def test_openai_provider_requires_environment_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIResponsesProvider()
    result = provider.invoke(ModelRequest("prompt", "model", "version", {}))
    assert result.status == "provider_error"
    assert result.error == "Missing environment variable: OPENAI_API_KEY"


def test_openai_provider_extracts_output_without_exposing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "test-secret-not-for-storage"
    monkeypatch.setenv("OPENAI_API_KEY", secret)
    output = _correct_response().to_json()
    captured_body: dict[str, object] = {}

    class FakeHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            payload = {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": output}],
                    }
                ],
            }
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen(request, timeout: float):
        captured_body.update(json.loads(request.data.decode("utf-8")))
        assert timeout == 120.0
        return FakeHTTPResponse()

    monkeypatch.setattr("diagpriv.evaluation.providers.urlopen", fake_urlopen)
    provider = OpenAIResponsesProvider()
    manifest = run_raw_experiment(_config(1001, "openai-adapter-test"), provider)
    assert manifest.response.status == "valid"
    assert captured_body["model"] == "offline-fixture"
    assert captured_body["store"] is False
    assert captured_body["temperature"] == 0.0
    assert "Operational evidence:" in str(captured_body["input"])
    assert secret not in manifest.to_json()


def test_openai_rate_limit_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")

    def rate_limited(request, timeout: float):
        raise HTTPError(request.full_url, 429, "rate limit", {}, None)

    monkeypatch.setattr("diagpriv.evaluation.providers.urlopen", rate_limited)
    result = OpenAIResponsesProvider().invoke(
        ModelRequest("prompt", "model", "version", {})
    )
    assert result.status == "rate_limited"
    assert result.error == "OpenAI Responses API rate limit (HTTP 429)"


def test_rate_limit_is_recorded_in_manifest_and_summary() -> None:
    class RateLimitedProvider:
        def invoke(self, request: ModelRequest) -> InvocationResult:
            return InvocationResult("rate_limited", error="rate limited")

    manifest = run_raw_experiment(_config(1001, "rate-limited-run"), RateLimitedProvider())
    assert manifest.response.status == "rate_limited"
    assert manifest.response.error == "rate limited"
    assert manifest.score is None
    summary = summarize_manifests((manifest,))
    assert summary.development.provider_failures == 0
    assert summary.development.rate_limits == 1
