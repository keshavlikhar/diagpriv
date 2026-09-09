"""Versioned, validated configuration for the first raw RCA pilot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any, Literal, Self

from diagbench.generators.incident_001 import seed_split
from diagpriv.evaluation.prompt import (
    PROMPT_SHA256 as PROMPT_SHA256_V1,
    PROMPT_VERSION as PROMPT_VERSION_V1,
)
from diagpriv.evaluation.prompt_v2 import (
    PROMPT_SHA256 as PROMPT_SHA256_V2,
    PROMPT_VERSION as PROMPT_VERSION_V2,
)

FROZEN_PROTOCOLS = {
    PROMPT_VERSION_V1: (
        PROMPT_SHA256_V1,
        "rca-taxonomy-v1",
        "raw-rca-scorer-v1",
    ),
    PROMPT_VERSION_V2: (
        PROMPT_SHA256_V2,
        "rca-taxonomy-v2",
        "raw-rca-scorer-v2",
    ),
}

SeedScope = Literal["development_and_validation", "development_only", "validation_only"]


@dataclass(frozen=True, slots=True)
class PilotDefinition:
    pilot_id: str
    provider: str
    condition: Literal["raw", "redaction-v1", "hmac-v1"]
    prompt_version: str
    prompt_sha256: str
    taxonomy_version: str
    scorer_version: str
    seed_scope: SeedScope
    development_seeds: tuple[int, ...]
    validation_seeds: tuple[int, ...]
    held_out_seeds: tuple[int, ...]
    calls_per_seed: int
    requested_model: str
    model_version_metadata_environment_variable: str | None
    reasoning_effort: str
    decoding_settings: dict[str, float | int | str | bool | None]
    intended_temperature: float | None
    effective_temperature: float | None
    temperature_omission_reason: str | None
    pricing_snapshot_path: Path
    hmac_key_environment_variable: str | None
    hmac_key_id: str | None

    @classmethod
    def load(cls, path: Path) -> Self:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        pilot = data["pilot"]
        model = data["model"]
        pricing = data["pricing"]
        transformation = data.get("transformation", {})
        if not isinstance(transformation, dict):
            raise ValueError("transformation must be a table")
        protocol = FROZEN_PROTOCOLS.get(pilot["prompt_version"])
        default_taxonomy = None if protocol is None else protocol[1]
        default_scorer = None if protocol is None else protocol[2]
        temperature_correction = data.get("temperature_protocol_correction")
        intended_temperature = None
        effective_temperature = _optional_temperature(
            data.get("decoding", {}).get("temperature")
        )
        temperature_omission_reason = None
        if temperature_correction is not None:
            if not isinstance(temperature_correction, dict):
                raise ValueError("temperature_protocol_correction must be a table")
            intended_temperature = _optional_temperature(
                temperature_correction.get("intended")
            )
            if temperature_correction.get("effective") != "omitted":
                raise ValueError("Corrected temperature must be marked omitted")
            effective_temperature = None
            temperature_omission_reason = temperature_correction.get(
                "omission_reason"
            )
        definition = cls(
            pilot_id=pilot["pilot_id"],
            provider=pilot["provider"],
            condition=pilot["condition"],
            prompt_version=pilot["prompt_version"],
            prompt_sha256=pilot["prompt_sha256"],
            taxonomy_version=pilot.get("taxonomy_version", default_taxonomy),
            scorer_version=pilot.get("scorer_version", default_scorer),
            seed_scope=pilot.get("seed_scope", "development_and_validation"),
            development_seeds=tuple(pilot["development_seeds"]),
            validation_seeds=tuple(pilot["validation_seeds"]),
            held_out_seeds=tuple(pilot["held_out_seeds"]),
            calls_per_seed=pilot["calls_per_seed"],
            requested_model=model["requested_model"],
            model_version_metadata_environment_variable=model.get(
                "version_metadata_environment_variable"
            ),
            reasoning_effort=model["reasoning_effort"],
            decoding_settings=dict(data["decoding"]),
            intended_temperature=intended_temperature,
            effective_temperature=effective_temperature,
            temperature_omission_reason=temperature_omission_reason,
            pricing_snapshot_path=path.parent / pricing["snapshot"],
            hmac_key_environment_variable=transformation.get(
                "key_environment_variable"
            ),
            hmac_key_id=transformation.get("key_id"),
        )
        definition.validate()
        return definition

    def validate(self) -> None:
        if self.condition not in {"raw", "redaction-v1", "hmac-v1"}:
            raise ValueError(f"Unsupported pilot condition: {self.condition}")
        if self.condition == "hmac-v1":
            if not self.hmac_key_environment_variable:
                raise ValueError("hmac-v1 requires a key environment variable name")
            if not self.hmac_key_id:
                raise ValueError("hmac-v1 requires a non-secret experimental key ID")
        elif self.hmac_key_environment_variable is not None or self.hmac_key_id is not None:
            raise ValueError("HMAC key configuration is valid only for hmac-v1")
        if FROZEN_PROTOCOLS.get(self.prompt_version) != (
            self.prompt_sha256,
            self.taxonomy_version,
            self.scorer_version,
        ):
            raise ValueError(
                "Pilot prompt, hash, taxonomy, and scorer do not match a frozen protocol"
            )
        if self.calls_per_seed < 1:
            raise ValueError("calls_per_seed must be positive")
        if self.effective_temperature != _optional_temperature(
            self.decoding_settings.get("temperature")
        ):
            raise ValueError("Effective temperature does not match decoding settings")
        if self.intended_temperature is not None:
            if "temperature" in self.decoding_settings:
                raise ValueError("Corrected temperature must be omitted from decoding")
            if not self.temperature_omission_reason:
                raise ValueError("Corrected temperature requires an omission reason")
        if self.seed_scope not in {
            "development_and_validation",
            "development_only",
            "validation_only",
        }:
            raise ValueError(f"Unsupported pilot seed scope: {self.seed_scope}")
        if self.held_out_seeds:
            raise ValueError("Pilot must not contain held-out seeds")
        if self.seed_scope == "development_only" and self.validation_seeds:
            raise ValueError("Development-only pilot cannot contain validation seeds")
        if self.seed_scope == "validation_only" and self.development_seeds:
            raise ValueError("Validation-only pilot cannot contain development seeds")
        if self.seed_scope == "validation_only" and not self.validation_seeds:
            raise ValueError("Validation-only pilot must contain validation seeds")
        if any(seed_split(seed) != "development" for seed in self.development_seeds):
            raise ValueError("Pilot development_seeds contains a non-development seed")
        if any(seed_split(seed) != "validation" for seed in self.validation_seeds):
            raise ValueError("Pilot validation_seeds contains a non-validation seed")
        if len(set((*self.development_seeds, *self.validation_seeds))) != len(
            self.development_seeds
        ) + len(self.validation_seeds):
            raise ValueError("Pilot seed lists must not overlap")
        if not self.pricing_snapshot_path.is_file():
            raise ValueError("Pilot pricing snapshot does not exist")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "pilot_id": self.pilot_id,
            "provider": self.provider,
            "condition": self.condition,
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
            "taxonomy_version": self.taxonomy_version,
            "scorer_version": self.scorer_version,
            "seed_scope": self.seed_scope,
            "development_seeds": list(self.development_seeds),
            "validation_seeds": list(self.validation_seeds),
            "held_out_seeds": list(self.held_out_seeds),
            "calls_per_seed": self.calls_per_seed,
            "requested_model": self.requested_model,
            "model_version_metadata_environment_variable": (
                self.model_version_metadata_environment_variable
            ),
            "reasoning_effort": self.reasoning_effort,
            "decoding_settings": self.decoding_settings,
            "temperature": {
                "intended": self.intended_temperature,
                "effective": self.effective_temperature,
                "request_parameter": (
                    "omitted" if self.intended_temperature is not None else "configured"
                ),
                "omission_reason": self.temperature_omission_reason,
            },
            "pricing_snapshot_path": str(self.pricing_snapshot_path),
        }
        if self.condition == "hmac-v1":
            data["transformation"] = {
                "version": "hmac-v1",
                "key_environment_variable": self.hmac_key_environment_variable,
                "key_id": self.hmac_key_id,
            }
        return data


def _optional_temperature(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
