"""Aggregate raw experiment manifests into split-specific pilot summaries."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

from diagpriv.evaluation.manifest import ExperimentManifest


@dataclass(frozen=True, slots=True)
class SplitSummary:
    status: str
    runs: int
    valid_response_rate: float | None
    exact_rca_accuracy: float | None
    outcome_accuracy: float | None
    trigger_accuracy: float | None
    mechanism_accuracy: float | None
    component_accuracy: float | None
    average_evidence_precision: float | None
    average_evidence_recall: float | None
    average_evidence_f1: float | None
    parse_failures: dict[str, int]
    provider_failures: int
    rate_limits: int
    refusals: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class PilotSummary:
    development: SplitSummary
    validation: SplitSummary

    def to_dict(self) -> dict[str, object]:
        return {
            "development": self.development.to_dict(),
            "validation": self.validation.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _summarize_split(manifests: list[ExperimentManifest]) -> SplitSummary:
    if not manifests:
        return SplitSummary(
            status="pending",
            runs=0,
            valid_response_rate=None,
            exact_rca_accuracy=None,
            outcome_accuracy=None,
            trigger_accuracy=None,
            mechanism_accuracy=None,
            component_accuracy=None,
            average_evidence_precision=None,
            average_evidence_recall=None,
            average_evidence_f1=None,
            parse_failures={},
            provider_failures=0,
            rate_limits=0,
            refusals=0,
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
    return SplitSummary(
        status="complete",
        runs=run_count,
        valid_response_rate=_rate(statuses["valid"], run_count),
        exact_rca_accuracy=_rate(
            sum(score.exact_root_cause_correct for score in scores), run_count
        ),
        outcome_accuracy=_rate(sum(score.outcome_correct for score in scores), run_count),
        trigger_accuracy=_rate(sum(score.trigger_correct for score in scores), run_count),
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
    )


def summarize_manifests(manifests: Iterable[ExperimentManifest]) -> PilotSummary:
    grouped: dict[str, list[ExperimentManifest]] = {
        "development": [],
        "validation": [],
    }
    for manifest in manifests:
        if manifest.split in grouped:
            grouped[manifest.split].append(manifest)
    return PilotSummary(
        development=_summarize_split(grouped["development"]),
        validation=_summarize_split(grouped["validation"]),
    )


def summarize_path(path: Path) -> PilotSummary:
    if not path.exists():
        return summarize_manifests([])
    manifests = [
        ExperimentManifest.from_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return summarize_manifests(manifests)

