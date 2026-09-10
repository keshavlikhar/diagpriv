"""Aggregate and inspect raw experiment manifests without hiding individual runs."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pricing import PricingSnapshot


@dataclass(frozen=True, slots=True)
class SplitSummary:
    status: str
    runs: int
    valid_response_rate: float | None
    exact_rca_accuracy: float | None
    outcome_accuracy: float | None
    trigger_accuracy: float | None
    subsequent_action_accuracy: float | None
    mechanism_accuracy: float | None
    component_accuracy: float | None
    average_evidence_precision: float | None
    average_evidence_recall: float | None
    average_evidence_f1: float | None
    parse_failures: dict[str, int]
    provider_failures: int
    rate_limits: int
    refusals: int
    total_input_tokens: int
    total_cached_input_tokens: int
    total_cache_write_input_tokens: int
    total_output_tokens: int
    total_reasoning_tokens: int | None
    total_tokens: int
    token_usage_available_runs: int
    reasoning_usage_available_runs: int
    pricing_snapshot_id: str | None
    estimated_api_cost_usd: float | None
    estimated_average_cost_per_incident_usd: float | None
    costed_runs: int
    uncosted_runs: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PilotSummary:
    pricing_snapshot: dict[str, object] | None
    development: SplitSummary
    validation: SplitSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "pricing_snapshot": self.pricing_snapshot,
            "development": self.development.to_dict(),
            "validation": self.validation.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _summarize_split(
    manifests: list[ExperimentManifest], pricing: PricingSnapshot | None
) -> SplitSummary:
    pricing_id = None if pricing is None else pricing.pricing_snapshot_id
    if not manifests:
        return SplitSummary(
            status="pending",
            runs=0,
            valid_response_rate=None,
            exact_rca_accuracy=None,
            outcome_accuracy=None,
            trigger_accuracy=None,
            subsequent_action_accuracy=None,
            mechanism_accuracy=None,
            component_accuracy=None,
            average_evidence_precision=None,
            average_evidence_recall=None,
            average_evidence_f1=None,
            parse_failures={},
            provider_failures=0,
            rate_limits=0,
            refusals=0,
            total_input_tokens=0,
            total_cached_input_tokens=0,
            total_cache_write_input_tokens=0,
            total_output_tokens=0,
            total_reasoning_tokens=None,
            total_tokens=0,
            token_usage_available_runs=0,
            reasoning_usage_available_runs=0,
            pricing_snapshot_id=pricing_id,
            estimated_api_cost_usd=0.0 if pricing is not None else None,
            estimated_average_cost_per_incident_usd=None,
            costed_runs=0,
            uncosted_runs=0,
        )

    statuses = Counter(item.response.status for item in manifests)
    scores = [item.score for item in manifests if item.score is not None]
    parse_statuses = {
        "malformed_json",
        "missing_fields",
        "invalid_schema",
        "unknown_category",
        "empty_response",
    }
    parse_failures = {
        status: statuses[status] for status in sorted(parse_statuses) if statuses[status]
    }
    run_count = len(manifests)
    costs = (
        []
        if pricing is None
        else [
            cost
            for item in manifests
            if (cost := pricing.estimate_usd(item)) is not None
        ]
    )
    cost_total = sum(costs) if costs else None
    v2_split = all(
        item.scorer_version == "raw-rca-scorer-v2" for item in manifests
    )
    return SplitSummary(
        status="complete",
        runs=run_count,
        valid_response_rate=_rate(statuses["valid"], run_count),
        exact_rca_accuracy=_rate(
            sum(score.exact_root_cause_correct for score in scores), run_count
        ),
        outcome_accuracy=_rate(sum(score.outcome_correct for score in scores), run_count),
        trigger_accuracy=_rate(sum(score.trigger_correct for score in scores), run_count),
        subsequent_action_accuracy=(
            _rate(
                sum(
                    score.subsequent_action_correct
                    for score in scores
                    if hasattr(score, "subsequent_action_correct")
                ),
                run_count,
            )
            if v2_split
            else None
        ),
        mechanism_accuracy=_rate(
            sum(score.failure_mechanism_correct for score in scores), run_count
        ),
        component_accuracy=_rate(
            sum(score.affected_component_correct for score in scores), run_count
        ),
        average_evidence_precision=_average(
            [score.evidence_precision for score in scores]
        ),
        average_evidence_recall=_average([score.evidence_recall for score in scores]),
        average_evidence_f1=_average([score.evidence_f1 for score in scores]),
        parse_failures=parse_failures,
        provider_failures=statuses["provider_error"],
        rate_limits=statuses["rate_limited"],
        refusals=statuses["refusal"],
        total_input_tokens=sum(item.input_token_count or 0 for item in manifests),
        total_cached_input_tokens=sum(
            item.cached_input_token_count or 0 for item in manifests
        ),
        total_cache_write_input_tokens=sum(
            item.cache_write_input_token_count or 0 for item in manifests
        ),
        total_output_tokens=sum(item.output_token_count or 0 for item in manifests),
        total_reasoning_tokens=(
            sum(item.reasoning_token_count or 0 for item in manifests)
            if any(item.reasoning_token_count is not None for item in manifests)
            else None
        ),
        total_tokens=sum(item.total_token_count or 0 for item in manifests),
        token_usage_available_runs=sum(
            item.total_token_count is not None for item in manifests
        ),
        reasoning_usage_available_runs=sum(
            item.reasoning_token_count is not None for item in manifests
        ),
        pricing_snapshot_id=pricing_id,
        estimated_api_cost_usd=cost_total,
        estimated_average_cost_per_incident_usd=(
            cost_total / run_count
            if cost_total is not None and len(costs) == run_count
            else None
        ),
        costed_runs=len(costs),
        uncosted_runs=run_count - len(costs) if pricing is not None else run_count,
    )


def summarize_manifests(
    manifests: Iterable[ExperimentManifest], pricing: PricingSnapshot | None = None
) -> PilotSummary:
    grouped: dict[str, list[ExperimentManifest]] = {
        "development": [],
        "validation": [],
    }
    for manifest in manifests:
        if manifest.split in grouped:
            grouped[manifest.split].append(manifest)
    return PilotSummary(
        pricing_snapshot=None if pricing is None else pricing.to_dict(),
        development=_summarize_split(grouped["development"], pricing),
        validation=_summarize_split(grouped["validation"], pricing),
    )


def load_manifests(path: Path) -> list[ExperimentManifest]:
    if not path.exists():
        return []
    return [
        ExperimentManifest.from_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize_path(
    path: Path, pricing: PricingSnapshot | None = None
) -> PilotSummary:
    return summarize_manifests(load_manifests(path), pricing)


def inspection_records(path: Path) -> list[dict[str, object]]:
    """Expose raw output, structured response, scores, failures, and usage per run."""
    records: list[dict[str, object]] = []
    for manifest in load_manifests(path):
        score = manifest.to_dict()["score"]
        score_data = score if isinstance(score, dict) else {}
        structured = manifest.response.response
        records.append(
            {
                "experiment_id": manifest.experiment_id,
                "manifest_schema_version": manifest.manifest_schema_version,
                "incident_family": manifest.incident_family,
                "seed": manifest.seed,
                "split": manifest.split,
                "condition": manifest.condition,
                "requested_model": manifest.requested_model,
                "provider_returned_model": manifest.provider_returned_model,
                "model_version_metadata": manifest.model_version_metadata,
                "reasoning_effort": manifest.reasoning_effort,
                "temperature": manifest.temperature,
                "intended_temperature": manifest.intended_temperature,
                "temperature_omission_reason": manifest.temperature_omission_reason,
                "prompt_version": manifest.prompt_version,
                "prompt_sha256": manifest.prompt_sha256,
                **(
                    {"model_input_sha256": manifest.model_input_sha256}
                    if manifest.model_input_sha256 is not None
                    else {}
                ),
                "taxonomy_version": manifest.taxonomy_version,
                "scorer_version": manifest.scorer_version,
                **(
                    {"transformation_key_id": manifest.transformation_key_id}
                    if manifest.transformation_key_id is not None
                    else {}
                ),
                **(
                    {
                        "transformation_key_fingerprint": (
                            manifest.transformation_key_fingerprint
                        )
                    }
                    if manifest.transformation_key_fingerprint is not None
                    else {}
                ),
                "response_id": manifest.response_id,
                "provider_timestamp": manifest.provider_timestamp,
                "provider_response_status": manifest.provider_response_status,
                "provider_service_tier": manifest.provider_service_tier,
                "sanitized_api_error": (
                    None
                    if manifest.sanitized_api_error is None
                    else manifest.sanitized_api_error.to_dict()
                ),
                "parse_status": manifest.response.status,
                "failure": manifest.response.error,
                "raw_model_response": manifest.response.raw_output,
                "structured_response": (
                    None if structured is None else structured.to_dict()
                ),
                "supporting_evidence_ids": (
                    [] if structured is None else list(structured.supporting_evidence)
                ),
                "rca_score": score_data.get("rca"),
                "evidence_score": score_data.get("evidence"),
                "token_usage": {
                    "input": manifest.input_token_count,
                    "cached_input": manifest.cached_input_token_count,
                    "cache_write_input": manifest.cache_write_input_token_count,
                    "output": manifest.output_token_count,
                    "reasoning": manifest.reasoning_token_count,
                    "total": manifest.total_token_count,
                },
            }
        )
    return records


def inspection_json(path: Path) -> str:
    return json.dumps({"runs": inspection_records(path)}, indent=2, sort_keys=True) + "\n"
