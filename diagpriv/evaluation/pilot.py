"""Versioned, validated configuration for the first raw RCA pilot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any, Literal, Self

from diagbench.generators.incident_001 import seed_split
from diagpriv.evaluation.prompt import PROMPT_SHA256, PROMPT_VERSION


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
    model_environment_variable: str
    model_version_environment_variable: str
    decoding_settings: dict[str, float | int | str | bool | None]

    @classmethod
    def load(cls, path: Path) -> Self:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        pilot = data["pilot"]
        model = data["model"]
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
            model_environment_variable=model["name_environment_variable"],
            model_version_environment_variable=model[
                "version_environment_variable"
            ],
            decoding_settings=dict(data["decoding"]),
        )
        definition.validate()
        return definition

    def validate(self) -> None:
        if self.condition != "raw":
            raise ValueError("The v0.1 pilot supports only the raw condition")
        if self.prompt_version != PROMPT_VERSION or self.prompt_sha256 != PROMPT_SHA256:
            raise ValueError("Pilot prompt version or hash does not match frozen raw prompt")
        if self.calls_per_seed < 1:
            raise ValueError("calls_per_seed must be positive")
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
            "model_environment_variable": self.model_environment_variable,
            "model_version_environment_variable": self.model_version_environment_variable,
            "decoding_settings": self.decoding_settings,
        }

