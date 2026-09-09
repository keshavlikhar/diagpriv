"""Versioned pricing metadata kept separate from scientific scoring."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import tomllib
from typing import Self

from diagpriv.evaluation.manifest import ExperimentManifest


@dataclass(frozen=True, slots=True)
class PricingSnapshot:
    pricing_snapshot_id: str
    provider: str
    requested_model: str
    effective_date: str
    currency: str
    unit_tokens: int
    input_usd_per_unit: float
    cached_input_usd_per_unit: float
    cache_write_input_usd_per_unit: float
    output_usd_per_unit: float
    output_token_count_includes_reasoning: bool
    long_context_threshold_input_tokens: int
    long_context_input_multiplier: float
    long_context_output_multiplier: float
    source: str

    @classmethod
    def load(cls, path: Path) -> Self:
        data = tomllib.loads(path.read_text(encoding="utf-8"))["pricing"]
        snapshot = cls(**data)
        snapshot.validate()
        return snapshot

    def validate(self) -> None:
        if self.currency != "USD":
            raise ValueError("Only USD pricing snapshots are supported")
        if self.unit_tokens <= 0:
            raise ValueError("Pricing unit_tokens must be positive")
        if self.long_context_threshold_input_tokens <= 0:
            raise ValueError("Long-context threshold must be positive")
        if any(
            rate < 0
            for rate in (
                self.input_usd_per_unit,
                self.cached_input_usd_per_unit,
                self.cache_write_input_usd_per_unit,
                self.output_usd_per_unit,
            )
        ):
            raise ValueError("Pricing rates must not be negative")
        if (
            self.long_context_input_multiplier <= 0
            or self.long_context_output_multiplier <= 0
        ):
            raise ValueError("Long-context pricing multipliers must be positive")
        if not self.output_token_count_includes_reasoning:
            raise ValueError(
                "Cost logic assumes output_token_count already includes reasoning tokens"
            )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def estimate_usd(self, manifest: ExperimentManifest) -> float | None:
        """Estimate one run without changing or participating in RCA scoring."""
        if manifest.requested_model != self.requested_model:
            return None
        if (
            manifest.provider_returned_model is not None
            and not manifest.provider_returned_model.startswith(self.requested_model)
        ):
            return None
        if manifest.input_token_count is None or manifest.output_token_count is None:
            return None
        cached = manifest.cached_input_token_count or 0
        cache_write = manifest.cache_write_input_token_count or 0
        uncached = max(manifest.input_token_count - cached - cache_write, 0)
        long_context = (
            manifest.input_token_count > self.long_context_threshold_input_tokens
        )
        input_multiplier = (
            self.long_context_input_multiplier if long_context else 1.0
        )
        output_multiplier = (
            self.long_context_output_multiplier if long_context else 1.0
        )
        input_cost = (
            uncached * self.input_usd_per_unit
            + cached * self.cached_input_usd_per_unit
            + cache_write * self.cache_write_input_usd_per_unit
        ) / self.unit_tokens * input_multiplier
        output_cost = (
            manifest.output_token_count * self.output_usd_per_unit
        ) / self.unit_tokens * output_multiplier
        return input_cost + output_cost
