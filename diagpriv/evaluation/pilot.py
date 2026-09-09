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

FROZEN_PROMPT_HASHES = {
    PROMPT_VERSION_V1: PROMPT_SHA256_V1,
    PROMPT_VERSION_V2: PROMPT_SHA256_V2,
}


@dataclass(frozen=True, slots=True)
class PilotDefinition:
    pilot_id: str
    provider: str
    condition: Literal["raw"]
    prompt_version: str
    prompt_sha256: str
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

    @classmethod
    def load(cls, path: Path) -> Self:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        pilot = data["pilot"]
        model = data["model"]
        pricing = data["pricing"]
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
        )
        definition.validate()
        return definition

    def validate(self) -> None:
        if self.condition != "raw":
            raise ValueError("The v0.1 pilot supports only the raw condition")
        if FROZEN_PROMPT_HASHES.get(self.prompt_version) != self.prompt_sha256:
            raise ValueError("Pilot prompt version or hash does not match frozen raw prompt")
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
        if self.held_out_seeds:
            raise ValueError("The first pilot must not contain held-out seeds")
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
        return {
            "pilot_id": self.pilot_id,
            "provider": self.provider,
            "condition": self.condition,
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
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


def _optional_temperature(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
