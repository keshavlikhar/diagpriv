"""Provider-independent orchestration for one raw RCA baseline run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from diagbench.generators.incident_001 import (
    DEVELOPMENT_SEEDS,
    VALIDATION_SEEDS,
    generate_incident_001,
    seed_split,
)
from diagpriv.evaluation.manifest import ExperimentManifest, append_manifest
from diagpriv.evaluation.prompt import PROMPT_SHA256, PROMPT_VERSION, build_prompt
from diagpriv.evaluation.providers import ModelProvider, ModelRequest
from diagpriv.evaluation.response import ParsedResponse, parse_response
from diagpriv.evaluation.scoring import score_response


class ProtectedSeedError(ValueError):
    """Raised when a run would consume a protected or unassigned seed."""


@dataclass(frozen=True, slots=True)
class RawRunConfig:
    experiment_id: str
    seed: int
    model: str
    model_version: str | None
    reasoning_effort: str | None = None
    decoding_settings: dict[str, float | int | str | bool | None] = field(
        default_factory=lambda: {"temperature": 0.0}
    )
    allow_held_out: bool = False
    timestamp: str | None = None


def pilot_seed_plan(
    development_count: int = 5, validation_count: int = 0
) -> tuple[int, ...]:
    """Return a bounded pilot plan containing no held-out evaluation seeds."""
    if not 0 <= development_count <= len(DEVELOPMENT_SEEDS):
        raise ValueError("development_count is outside the development seed range")
    if not 0 <= validation_count <= len(VALIDATION_SEEDS):
        raise ValueError("validation_count is outside the validation seed range")
    development = tuple(DEVELOPMENT_SEEDS[:development_count])
    validation = tuple(VALIDATION_SEEDS[:validation_count])
    return development + validation


def run_raw_experiment(
    config: RawRunConfig,
    provider: ModelProvider,
    *,
    result_path: Path | None = None,
) -> ExperimentManifest:
    """Generate, prompt, invoke, parse, score, and optionally append one run."""
    split = seed_split(config.seed)
    if split == "evaluation" and not config.allow_held_out:
        raise ProtectedSeedError(
            "Held-out evaluation seeds require allow_held_out=True explicitly"
        )
    if split == "retired":
        raise ProtectedSeedError("Retired evaluation seeds may not be invoked")
    if split == "unassigned":
        raise ProtectedSeedError("Unassigned seeds are not permitted by the protocol")

    incident = generate_incident_001(config.seed)

    prompt = build_prompt(incident.model_view())
    invocation = provider.invoke(
        ModelRequest(
            prompt=prompt,
            model=config.model,
            model_version=config.model_version,
            decoding_settings=dict(config.decoding_settings),
            reasoning_effort=config.reasoning_effort,
        )
    )
    if invocation.status in {"provider_error", "rate_limited", "refusal"}:
        parsed = ParsedResponse(
            invocation.status,
            invocation.raw_output,
            error=invocation.error or "Unspecified provider error",
        )
    else:
        parsed = parse_response(invocation.raw_output)
    score = None if parsed.response is None else score_response(incident, parsed.response)

    manifest = ExperimentManifest(
        experiment_id=config.experiment_id,
        benchmark_version=str(incident.metadata["benchmark_version"]),
        incident_family="incident_001",
        seed=config.seed,
        split=split,
        condition="raw",
        requested_model=config.model,
        provider_returned_model=invocation.provider_returned_model,
        model_version_metadata=config.model_version,
        reasoning_effort=config.reasoning_effort,
        temperature=_temperature(config.decoding_settings.get("temperature")),
        prompt_version=PROMPT_VERSION,
        prompt_sha256=PROMPT_SHA256,
        decoding_settings=dict(config.decoding_settings),
        timestamp=config.timestamp or datetime.now(UTC).isoformat(),
        response_id=invocation.response_id,
        provider_timestamp=invocation.provider_timestamp,
        input_token_count=invocation.input_token_count,
        cached_input_token_count=invocation.cached_input_token_count,
        cache_write_input_token_count=invocation.cache_write_input_token_count,
        output_token_count=invocation.output_token_count,
        reasoning_token_count=invocation.reasoning_token_count,
        total_token_count=invocation.total_token_count,
        provider_response_status=invocation.response_status,
        provider_service_tier=invocation.service_tier,
        response=parsed,
        score=score,
    )
    if result_path is not None:
        append_manifest(result_path, manifest)
    return manifest


def _temperature(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
