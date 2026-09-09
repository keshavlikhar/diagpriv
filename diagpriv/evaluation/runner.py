"""Provider-independent orchestration for one RCA experiment run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from diagbench.generators.incident_001 import (
    DEVELOPMENT_SEEDS,
    VALIDATION_SEEDS,
    generate_incident_001,
    seed_split,
)
from diagpriv.evaluation.manifest import ExperimentManifest, append_manifest
from diagpriv.evaluation.prompt import (
    PROMPT_SHA256 as PROMPT_SHA256_V1,
    PROMPT_VERSION as PROMPT_VERSION_V1,
    build_prompt,
)
from diagpriv.evaluation.prompt_v2 import (
    PROMPT_SHA256 as PROMPT_SHA256_V2,
    PROMPT_VERSION as PROMPT_VERSION_V2,
    build_prompt_v2,
)
from diagpriv.evaluation.providers import ModelProvider, ModelRequest
from diagpriv.evaluation.response import (
    ParsedResponse,
    parse_response,
    parse_response_v2,
)
from diagpriv.evaluation.scoring import score_response
from diagpriv.evaluation.scoring_v2 import SCORER_VERSION as SCORER_VERSION_V2
from diagpriv.evaluation.scoring_v2 import score_response_v2
from diagpriv.evaluation.taxonomy_v2 import TAXONOMY_VERSION as TAXONOMY_VERSION_V2
from diagpriv.transformations import (
    hmac_incident,
    hmac_key_fingerprint,
    redact_incident,
    tokenize_incident,
)

SCORER_VERSION_V1 = "raw-rca-scorer-v1"
TAXONOMY_VERSION_V1 = "rca-taxonomy-v1"


class ProtectedSeedError(ValueError):
    """Raised when a run would consume a protected or unassigned seed."""


@dataclass(frozen=True, slots=True)
class RawRunConfig:
    experiment_id: str
    seed: int
    model: str
    model_version: str | None
    reasoning_effort: str | None = None
    condition: Literal[
        "raw", "redaction-v1", "hmac-v1", "tokenization-v1"
    ] = "raw"
    decoding_settings: dict[str, float | int | str | bool | None] = field(
        default_factory=lambda: {"temperature": 0.0}
    )
    intended_temperature: float | None = None
    temperature_omission_reason: str | None = None
    prompt_version: str = PROMPT_VERSION_V1
    allow_held_out: bool = False
    timestamp: str | None = None
    hmac_key: bytes | None = field(default=None, repr=False, compare=False)
    transformation_key_id: str | None = None


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

    if config.prompt_version == PROMPT_VERSION_V1:
        prompt_builder = build_prompt
        response_parser = parse_response
        prompt_sha256 = PROMPT_SHA256_V1
        taxonomy_version = TAXONOMY_VERSION_V1
        scorer_version = SCORER_VERSION_V1
    elif config.prompt_version == PROMPT_VERSION_V2:
        prompt_builder = build_prompt_v2
        response_parser = parse_response_v2
        prompt_sha256 = PROMPT_SHA256_V2
        taxonomy_version = TAXONOMY_VERSION_V2
        scorer_version = SCORER_VERSION_V2
    else:
        raise ValueError(f"Unsupported raw RCA prompt version: {config.prompt_version}")

    incident = generate_incident_001(config.seed)
    transformation_key_fingerprint: str | None = None
    if config.condition == "raw":
        model_view = incident.model_view()
    elif config.condition == "redaction-v1":
        model_view = redact_incident(incident)
    elif config.condition == "hmac-v1":
        if config.hmac_key is None:
            raise ValueError("hmac-v1 requires an external HMAC key")
        if not config.transformation_key_id:
            raise ValueError("hmac-v1 requires a non-secret experimental key ID")
        transformation_key_fingerprint = hmac_key_fingerprint(config.hmac_key)
        model_view = hmac_incident(incident, key=config.hmac_key)
    elif config.condition == "tokenization-v1":
        model_view = tokenize_incident(incident)
    else:
        raise ValueError(f"Unsupported evaluation condition: {config.condition}")

    prompt = prompt_builder(model_view)
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
        parsed = response_parser(invocation.raw_output)
    if parsed.response is None:
        score = None
    elif config.prompt_version == PROMPT_VERSION_V2:
        score = score_response_v2(incident, parsed.response)
    else:
        score = score_response(incident, parsed.response)

    manifest = ExperimentManifest(
        experiment_id=config.experiment_id,
        benchmark_version=str(incident.metadata["benchmark_version"]),
        incident_family="incident_001",
        seed=config.seed,
        split=split,
        condition=config.condition,
        requested_model=config.model,
        provider_returned_model=invocation.provider_returned_model,
        model_version_metadata=config.model_version,
        reasoning_effort=config.reasoning_effort,
        temperature=_temperature(config.decoding_settings.get("temperature")),
        intended_temperature=config.intended_temperature,
        temperature_omission_reason=config.temperature_omission_reason,
        prompt_version=config.prompt_version,
        prompt_sha256=prompt_sha256,
        taxonomy_version=taxonomy_version,
        scorer_version=scorer_version,
        transformation_key_id=config.transformation_key_id,
        transformation_key_fingerprint=transformation_key_fingerprint,
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
        sanitized_api_error=invocation.sanitized_api_error,
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
