"""Append-only experiment manifests for reproducible raw-baseline runs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal, Self

from diagpriv.evaluation.response import ParsedResponse
from diagpriv.evaluation.scoring import RCAScore


@dataclass(frozen=True, slots=True)
class ExperimentManifest:
    experiment_id: str
    benchmark_version: str
    incident_family: str
    seed: int
    split: str
    condition: Literal["raw"]
    requested_model: str
    provider_returned_model: str | None
    model_version_metadata: str | None
    reasoning_effort: str | None
    temperature: float | None
    prompt_version: str
    prompt_sha256: str
    decoding_settings: dict[str, float | int | str | bool | None]
    timestamp: str
    response_id: str | None
    provider_timestamp: int | float | str | None
    input_token_count: int | None
    cached_input_token_count: int | None
    cache_write_input_token_count: int | None
    output_token_count: int | None
    reasoning_token_count: int | None
    total_token_count: int | None
    provider_response_status: str | None
    provider_service_tier: str | None
    response: ParsedResponse
    score: RCAScore | None

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_schema_version": "raw-rca-manifest-v2",
            "experiment_id": self.experiment_id,
            "benchmark_version": self.benchmark_version,
            "incident_family": self.incident_family,
            "seed": self.seed,
            "split": self.split,
            "condition": self.condition,
            "requested_model": self.requested_model,
            "provider_returned_model": self.provider_returned_model,
            "model_version_metadata": self.model_version_metadata,
            "reasoning_effort": self.reasoning_effort,
            "temperature": self.temperature,
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
            "decoding_settings": self.decoding_settings,
            "timestamp": self.timestamp,
            "response_id": self.response_id,
            "provider_timestamp": self.provider_timestamp,
            "input_token_count": self.input_token_count,
            "cached_input_token_count": self.cached_input_token_count,
            "cache_write_input_token_count": self.cache_write_input_token_count,
            "output_token_count": self.output_token_count,
            "reasoning_token_count": self.reasoning_token_count,
            "total_token_count": self.total_token_count,
            "response_status": self.provider_response_status,
            "provider_service_tier": self.provider_service_tier,
            "response": self.response.to_dict(),
            "score": _score_to_dict(self.score),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        score = _score_from_dict(data.get("score"))
        requested_model = data.get("requested_model", data.get("model"))
        model_version = data.get("model_version_metadata", data.get("model_version"))
        return cls(
            experiment_id=data["experiment_id"],
            benchmark_version=data["benchmark_version"],
            incident_family=data["incident_family"],
            seed=data["seed"],
            split=data["split"],
            condition=data["condition"],
            requested_model=requested_model,
            provider_returned_model=data.get("provider_returned_model"),
            model_version_metadata=model_version,
            reasoning_effort=data.get("reasoning_effort"),
            temperature=data.get(
                "temperature", data.get("decoding_settings", {}).get("temperature")
            ),
            prompt_version=data["prompt_version"],
            prompt_sha256=data["prompt_sha256"],
            decoding_settings=data["decoding_settings"],
            timestamp=data["timestamp"],
            response_id=data.get("response_id"),
            provider_timestamp=data.get("provider_timestamp"),
            input_token_count=data.get("input_token_count"),
            cached_input_token_count=data.get("cached_input_token_count"),
            cache_write_input_token_count=data.get("cache_write_input_token_count"),
            output_token_count=data.get("output_token_count"),
            reasoning_token_count=data.get("reasoning_token_count"),
            total_token_count=data.get("total_token_count"),
            provider_response_status=data.get(
                "response_status", data.get("provider_response_status")
            ),
            provider_service_tier=data.get("provider_service_tier"),
            response=ParsedResponse.from_dict(data["response"]),
            score=score,
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Experiment manifest must be a JSON object")
        return cls.from_dict(data)


def _score_to_dict(score: RCAScore | None) -> dict[str, object] | None:
    if score is None:
        return None
    data = score.to_dict()
    rca_fields = (
        "outcome_correct",
        "trigger_correct",
        "failure_mechanism_correct",
        "affected_component_correct",
        "exact_root_cause_correct",
    )
    evidence_fields = (
        "evidence_precision",
        "evidence_recall",
        "evidence_f1",
        "evidence_supported",
        "valid_evidence_ids",
        "matched_evidence_ids",
        "unknown_evidence_ids",
        "expected_evidence_ids",
    )
    return {
        "rca": {field: data[field] for field in rca_fields},
        "evidence": {field: data[field] for field in evidence_fields},
        "overall_correct": data["overall_correct"],
    }


def _score_from_dict(data: object) -> RCAScore | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("Manifest score must be an object or null")
    if "rca" not in data:
        return RCAScore.from_dict(data)
    rca = data.get("rca")
    evidence = data.get("evidence")
    if not isinstance(rca, dict) or not isinstance(evidence, dict):
        raise ValueError("Manifest RCA and evidence scores must be objects")
    return RCAScore.from_dict(
        {**rca, **evidence, "overall_correct": data["overall_correct"]}
    )


def append_manifest(path: Path, manifest: ExperimentManifest) -> None:
    """Append one unique run; never overwrite or silently duplicate a run ID."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and json.loads(line).get("experiment_id") == manifest.experiment_id:
                raise ValueError(f"Experiment already recorded: {manifest.experiment_id}")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(manifest.to_json(indent=None))
