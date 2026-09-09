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
    model: str
    model_version: str
    prompt_version: str
    prompt_sha256: str
    decoding_settings: dict[str, float | int | str | bool | None]
    timestamp: str
    response: ParsedResponse
    score: RCAScore | None

    def to_dict(self) -> dict[str, object]:
        return {
            "experiment_id": self.experiment_id,
            "benchmark_version": self.benchmark_version,
            "incident_family": self.incident_family,
            "seed": self.seed,
            "split": self.split,
            "condition": self.condition,
            "model": self.model,
            "model_version": self.model_version,
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
            "decoding_settings": self.decoding_settings,
            "timestamp": self.timestamp,
            "response": self.response.to_dict(),
            "score": None if self.score is None else self.score.to_dict(),
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        score = data.get("score")
        return cls(
            experiment_id=data["experiment_id"],
            benchmark_version=data["benchmark_version"],
            incident_family=data["incident_family"],
            seed=data["seed"],
            split=data["split"],
            condition=data["condition"],
            model=data["model"],
            model_version=data["model_version"],
            prompt_version=data["prompt_version"],
            prompt_sha256=data["prompt_sha256"],
            decoding_settings=data["decoding_settings"],
            timestamp=data["timestamp"],
            response=ParsedResponse.from_dict(data["response"]),
            score=None if score is None else RCAScore.from_dict(score),
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Experiment manifest must be a JSON object")
        return cls.from_dict(data)


def append_manifest(path: Path, manifest: ExperimentManifest) -> None:
    """Append one unique run; never overwrite or silently duplicate a run ID."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and json.loads(line).get("experiment_id") == manifest.experiment_id:
                raise ValueError(f"Experiment already recorded: {manifest.experiment_id}")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(manifest.to_json(indent=None))
