"""Append-only experiment manifests for reproducible RCA runs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal, Self

from diagpriv.evaluation.providers import SanitizedAPIError
from diagpriv.evaluation.response import ParsedResponse
from diagpriv.evaluation.scoring import RCAScore
from diagpriv.evaluation.scoring_v2 import RCAScoreV2


@dataclass(frozen=True, slots=True)
class ExperimentManifest:
    experiment_id: str
    benchmark_version: str
    incident_family: str
    seed: int
    split: str
    condition: Literal["raw", "redaction-v1", "hmac-v1"]
    requested_model: str
    provider_returned_model: str | None
    model_version_metadata: str | None
    reasoning_effort: str | None
    temperature: float | None
    intended_temperature: float | None
    temperature_omission_reason: str | None
    prompt_version: str
    prompt_sha256: str
    taxonomy_version: str
    scorer_version: str
    transformation_key_id: str | None
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
    sanitized_api_error: SanitizedAPIError | None
    response: ParsedResponse
    score: RCAScore | RCAScoreV2 | None

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "manifest_schema_version": "raw-rca-manifest-v5",
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
            "intended_temperature": self.intended_temperature,
            "temperature_omission_reason": self.temperature_omission_reason,
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
            "taxonomy_version": self.taxonomy_version,
            "scorer_version": self.scorer_version,
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
            "sanitized_api_error": (
                None
                if self.sanitized_api_error is None
                else self.sanitized_api_error.to_dict()
            ),
            "response": self.response.to_dict(),
            "score": _score_to_dict(self.score),
        }
        if self.transformation_key_id is not None:
            data["transformation_key_id"] = self.transformation_key_id
        return data

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        prompt_version = data["prompt_version"]
        taxonomy_version = data.get(
            "taxonomy_version",
            "rca-taxonomy-v2"
            if prompt_version == "raw-rca-v2"
            else "rca-taxonomy-v1",
        )
        scorer_version = data.get(
            "scorer_version",
            "raw-rca-scorer-v2"
            if prompt_version == "raw-rca-v2"
            else "raw-rca-scorer-v1",
        )
        score = _score_from_dict(data.get("score"), scorer_version=scorer_version)
        sanitized_error_data = data.get("sanitized_api_error")
        if sanitized_error_data is not None and not isinstance(
            sanitized_error_data, dict
        ):
            raise ValueError("Manifest sanitized API error must be an object or null")
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
            intended_temperature=data.get("intended_temperature"),
            temperature_omission_reason=data.get("temperature_omission_reason"),
            prompt_version=prompt_version,
            prompt_sha256=data["prompt_sha256"],
            taxonomy_version=taxonomy_version,
            scorer_version=scorer_version,
            transformation_key_id=data.get("transformation_key_id"),
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
            sanitized_api_error=(
                None
                if sanitized_error_data is None
                else SanitizedAPIError.from_dict(sanitized_error_data)
            ),
            response=ParsedResponse.from_dict(
                data["response"], prompt_version=prompt_version
            ),
            score=score,
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Experiment manifest must be a JSON object")
        return cls.from_dict(data)


def _score_to_dict(
    score: RCAScore | RCAScoreV2 | None,
) -> dict[str, object] | None:
    if score is None:
        return None
    data = score.to_dict()
    rca_fields = [
        "outcome_correct",
        "trigger_correct",
        "failure_mechanism_correct",
        "affected_component_correct",
        "exact_root_cause_correct",
    ]
    if isinstance(score, RCAScoreV2):
        rca_fields.insert(2, "subsequent_action_correct")
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


def _score_from_dict(
    data: object, *, scorer_version: str
) -> RCAScore | RCAScoreV2 | None:
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError("Manifest score must be an object or null")
    score_class = RCAScoreV2 if scorer_version == "raw-rca-scorer-v2" else RCAScore
    if "rca" not in data:
        return score_class.from_dict(data)
    rca = data.get("rca")
    evidence = data.get("evidence")
    if not isinstance(rca, dict) or not isinstance(evidence, dict):
        raise ValueError("Manifest RCA and evidence scores must be objects")
    return score_class.from_dict(
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
