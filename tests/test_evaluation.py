from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from diagbench.generators.incident_001 import generate_incident_001
from diagpriv.evaluation.cli import build_parser
from diagpriv.evaluation.manifest import ExperimentManifest, append_manifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.pricing import PricingSnapshot
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
    SanitizedAPIError,
)
from diagpriv.evaluation.reporting import (
    inspection_records,
    summarize_manifests,
    summarize_path,
)
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
        reasoning_effort="medium",
        decoding_settings={"temperature": 0.0, "max_output_tokens": 4096},
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
    assert plan == tuple(range(1000, 1005))
    assert all(1000 <= seed <= 1004 for seed in plan)


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


def test_frozen_pilot_definition_is_exactly_the_development_luna_pilot() -> None:
    path = Path(__file__).parents[1] / "experiments" / "raw_pilot_v1.toml"
    definition = PilotDefinition.load(path)
    assert definition.development_seeds == tuple(range(1000, 1005))
    assert definition.validation_seeds == ()
    assert definition.held_out_seeds == ()
    assert definition.calls_per_seed == 1
    assert definition.requested_model == "gpt-5.6-luna"
    assert definition.reasoning_effort == "medium"
    assert "temperature" not in definition.decoding_settings
    assert definition.intended_temperature == 0.0
    assert definition.effective_temperature is None
    assert definition.temperature_omission_reason is not None
    assert "HTTP 400" in definition.temperature_omission_reason
    assert "does not support the temperature parameter" in (
        definition.temperature_omission_reason
    )
    assert definition.decoding_settings["max_output_tokens"] == 4096
    assert definition.prompt_sha256 == PROMPT_SHA256
    assert definition.pricing_snapshot_path.is_file()


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


def test_run_pilot_requires_execute_before_provider_calls(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = Path(__file__).parents[1] / "experiments" / "raw_pilot_v1.toml"
    results = tmp_path / "must-not-exist.jsonl"
    parser = build_parser()
    args = parser.parse_args(
        [
            "run-pilot",
            "--config",
            str(config),
            "--results",
            str(results),
        ]
    )
    args.handler(args)
    assert json.loads(capsys.readouterr().out)["execution"] == "pending"
    assert not results.exists()


def test_run_diagnostic_dry_run_is_one_development_seed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = Path(__file__).parents[1] / "experiments" / "raw_pilot_v1.toml"
    results = tmp_path / "must-not-exist.jsonl"
    parser = build_parser()
    args = parser.parse_args(
        [
            "run-diagnostic",
            "--config",
            str(config),
            "--results",
            str(results),
            "--experiment-id",
            "diagnostic-development-1000-call-1",
            "--seed",
            "1000",
        ]
    )
    args.handler(args)
    pending = json.loads(capsys.readouterr().out)
    assert pending["execution"] == "pending"
    assert pending["seed"] == 1000
    assert pending["split"] == "development"
    assert not results.exists()


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
    development_payload = summary.to_dict()["development"]
    assert isinstance(development_payload, dict)
    assert "average_essential_requirement_coverage" not in development_payload
    assert "wrong_subject_citation_count" not in development_payload


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
                "id": "resp_test_001",
                "created_at": 1_968_163_200,
                "model": "gpt-5.6-luna-2026-08-31",
                "service_tier": "default",
                "status": "completed",
                "usage": {
                    "input_tokens": 800,
                    "input_tokens_details": {
                        "cached_tokens": 200,
                        "cache_write_tokens": 100,
                    },
                    "output_tokens": 120,
                    "output_tokens_details": {"reasoning_tokens": 40},
                    "total_tokens": 920,
                },
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
    assert captured_body["service_tier"] == "default"
    assert captured_body["temperature"] == 0.0
    assert captured_body["max_output_tokens"] == 4096
    assert captured_body["reasoning"] == {"effort": "medium"}
    assert "Operational evidence:" in str(captured_body["input"])
    assert manifest.requested_model == "offline-fixture"
    assert manifest.provider_returned_model == "gpt-5.6-luna-2026-08-31"
    assert manifest.model_version_metadata == "1"
    assert manifest.reasoning_effort == "medium"
    assert manifest.temperature == 0.0
    assert manifest.response_id == "resp_test_001"
    assert manifest.provider_timestamp == 1_968_163_200
    assert manifest.input_token_count == 800
    assert manifest.cached_input_token_count == 200
    assert manifest.cache_write_input_token_count == 100
    assert manifest.output_token_count == 120
    assert manifest.reasoning_token_count == 40
    assert manifest.total_token_count == 920
    assert manifest.provider_response_status == "completed"
    assert manifest.provider_service_tier == "default"
    manifest_data = manifest.to_dict()
    assert manifest_data["response_status"] == "completed"
    assert manifest_data["score"]["rca"]["exact_root_cause_correct"] is True
    assert manifest_data["score"]["evidence"]["evidence_f1"] == 1.0
    assert secret not in manifest.to_json()


def test_luna_pilot_omits_temperature_and_records_protocol_correction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")
    definition = PilotDefinition.load(
        Path(__file__).parents[1] / "experiments" / "raw_pilot_v1.toml"
    )
    captured_body: dict[str, object] = {}

    class FakeHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "id": "resp_temperature_omitted",
                    "model": "gpt-5.6-luna",
                    "status": "completed",
                    "output": [],
                }
            ).encode("utf-8")

    def fake_urlopen(request, timeout: float):
        captured_body.update(json.loads(request.data.decode("utf-8")))
        return FakeHTTPResponse()

    monkeypatch.setattr("diagpriv.evaluation.providers.urlopen", fake_urlopen)
    manifest = run_raw_experiment(
        RawRunConfig(
            experiment_id="luna-temperature-correction-test",
            seed=1000,
            model=definition.requested_model,
            model_version=None,
            reasoning_effort=definition.reasoning_effort,
            decoding_settings=dict(definition.decoding_settings),
            intended_temperature=definition.intended_temperature,
            temperature_omission_reason=definition.temperature_omission_reason,
            timestamp="2032-01-01T00:00:00+00:00",
        ),
        OpenAIResponsesProvider(),
    )
    assert "temperature" not in captured_body
    assert captured_body["model"] == "gpt-5.6-luna"
    assert captured_body["reasoning"] == {"effort": "medium"}
    assert manifest.temperature is None
    assert manifest.intended_temperature == 0.0
    assert manifest.temperature_omission_reason == (
        definition.temperature_omission_reason
    )
    assert manifest.to_dict()["temperature"] is None


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
    assert result.sanitized_api_error == SanitizedAPIError(
        http_status=429,
        error_type=None,
        error_code=None,
        parameter_name=None,
        message="OpenAI Responses API rate limit (HTTP 429)",
        request_id=None,
    )


def test_openai_http_error_is_allowlisted_sanitized_and_persisted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secret = "sk-test-secret-123456789"
    monkeypatch.setenv("OPENAI_API_KEY", secret)

    def invalid_request(request, timeout: float):
        body = json.dumps(
            {
                "error": {
                    "message": (
                        "Unsupported value; Authorization: Bearer leaked-token "
                        f"and key {secret}"
                    ),
                    "type": "invalid_request_error",
                    "param": "temperature",
                    "code": "unsupported_value",
                    "unapproved_detail": "must not be persisted",
                },
                "unapproved_top_level": "must not be persisted either",
            }
        ).encode("utf-8")
        raise HTTPError(
            request.full_url,
            400,
            "Bad Request",
            {
                "x-request-id": "req_safe_123",
                "Authorization": f"Bearer {secret}",
                "set-cookie": "credential=not-safe",
            },
            BytesIO(body),
        )

    monkeypatch.setattr("diagpriv.evaluation.providers.urlopen", invalid_request)
    manifest = run_raw_experiment(
        _config(1000, "sanitized-http-error"), OpenAIResponsesProvider()
    )
    assert manifest.response.status == "provider_error"
    assert manifest.sanitized_api_error == SanitizedAPIError(
        http_status=400,
        error_type="invalid_request_error",
        error_code="unsupported_value",
        parameter_name="temperature",
        message="Unsupported value; [REDACTED] and key [REDACTED]",
        request_id="req_safe_123",
    )
    serialized = manifest.to_json()
    assert ExperimentManifest.from_json(serialized) == manifest
    assert secret not in serialized
    assert "leaked-token" not in serialized
    assert "Authorization" not in serialized
    assert "set-cookie" not in serialized
    assert "unapproved_detail" not in serialized
    assert "unapproved_top_level" not in serialized
    results = tmp_path / "sanitized-error.jsonl"
    append_manifest(results, manifest)
    assert inspection_records(results)[0]["sanitized_api_error"] == (
        manifest.sanitized_api_error.to_dict()
    )


def test_openai_structured_refusal_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-secret")

    class FakeHTTPResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(
                {
                    "id": "resp_refusal",
                    "status": "completed",
                    "output": [
                        {
                            "type": "message",
                            "content": [
                                {
                                    "type": "refusal",
                                    "refusal": "Unable to provide this response.",
                                }
                            ],
                        }
                    ],
                }
            ).encode("utf-8")

    monkeypatch.setattr(
        "diagpriv.evaluation.providers.urlopen",
        lambda request, timeout: FakeHTTPResponse(),
    )
    manifest = run_raw_experiment(_config(1001, "refusal"), OpenAIResponsesProvider())
    assert manifest.response.status == "refusal"
    assert manifest.response.raw_output == "Unable to provide this response."
    assert manifest.response.error == "Provider refused the task"
    assert manifest.response_id == "resp_refusal"


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


def test_versioned_pricing_estimates_cost_outside_scoring() -> None:
    root = Path(__file__).parents[1]
    pricing = PricingSnapshot.load(
        root / "experiments" / "pricing" / "openai_gpt_5_6_luna_2026-07-30.toml"
    )

    class UsageProvider:
        def invoke(self, request: ModelRequest) -> InvocationResult:
            return InvocationResult(
                "success",
                raw_output=_correct_response(1000).to_json(),
                provider_returned_model="gpt-5.6-luna",
                response_id="resp_usage",
                provider_timestamp=1_968_163_200,
                input_token_count=100,
                cached_input_token_count=20,
                cache_write_input_token_count=10,
                output_token_count=50,
                reasoning_token_count=30,
                total_token_count=150,
                response_status="completed",
            )

    manifest = run_raw_experiment(
        RawRunConfig(
            experiment_id="luna-cost-test",
            seed=1000,
            model="gpt-5.6-luna",
            model_version=None,
            reasoning_effort="medium",
            decoding_settings={"temperature": 0.0},
            timestamp="2032-01-01T00:00:00+00:00",
        ),
        UsageProvider(),
    )
    summary = summarize_manifests((manifest,), pricing)
    development = summary.development
    assert development.total_input_tokens == 100
    assert development.total_output_tokens == 50
    assert development.total_reasoning_tokens == 30
    assert development.total_tokens == 150
    assert development.costed_runs == 1
    assert development.uncosted_runs == 0
    assert development.estimated_api_cost_usd == pytest.approx(0.0000769)
    assert development.estimated_average_cost_per_incident_usd == pytest.approx(
        0.0000769
    )
    assert manifest.score is not None
    assert manifest.score.exact_root_cause_correct


def test_inspection_exposes_every_raw_response_and_individual_score(
    tmp_path: Path,
) -> None:
    path = tmp_path / "five-results.jsonl"
    for seed in range(1000, 1005):
        manifest = run_raw_experiment(
            _config(seed, f"inspect-{seed}"),
            FakeProvider(raw_output=_correct_response(seed).to_json()),
        )
        append_manifest(path, manifest)

    records = inspection_records(path)
    assert [record["seed"] for record in records] == list(range(1000, 1005))
    assert all(record["raw_model_response"] for record in records)
    assert all(record["structured_response"] for record in records)
    assert all(record["supporting_evidence_ids"] for record in records)
    assert all(record["rca_score"] is not None for record in records)
    assert all(record["evidence_score"] is not None for record in records)
