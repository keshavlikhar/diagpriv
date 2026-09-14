"""Frozen, sparse Incident 002 transport-recovery preparation (no API calls)."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
import re
import tomllib
from typing import Any, Self

from diagpriv.evaluation.incident_families import (
    INCIDENT_002_DEVELOPMENT_SEEDS, INCIDENT_002_FAMILY,
)
from diagpriv.evaluation.manifest import ExperimentManifest, RecoveryProvenance
from diagpriv.evaluation.prompt_v2 import PROMPT_SHA256
from diagpriv.evaluation.reporting import load_manifests
from diagpriv.evaluation.runner import RawRunConfig, prepare_model_input

RECOVERY_PROTOCOL = "incident-002-transport-recovery-v1"
SOURCE_CHECKPOINT = "e1bd3c125ae2042b81b5ad88d5c0093d6bd553eb"
RECOVERY_RESULT = "results/incident_002_sol_transport_recovery.jsonl"
CONDITIONS = (
    "raw", "redaction-v1", "hmac-v1", "tokenization-v1", "format-preserving-v1",
)
# This reviewed allowlist is intentionally sparse; never form a seed/trial product.
ELIGIBLE_CELLS = (
    ("redaction-v1", 1001, 3, "TimeoutError"),
    ("redaction-v1", 1003, 2, "URLError"),
    ("redaction-v1", 1003, 3, "URLError"),
    ("redaction-v1", 1004, 2, "URLError"),
    ("redaction-v1", 1004, 3, "URLError"),
    ("redaction-v1", 1005, 2, "URLError"),
    ("redaction-v1", 1005, 3, "URLError"),
    ("redaction-v1", 1017, 2, "URLError"),
    ("redaction-v1", 1017, 3, "URLError"),
    ("tokenization-v1", 1001, 2, "TimeoutError"),
)
FROZEN_SETTINGS = {
    "incident_family": INCIDENT_002_FAMILY,
    "requested_model": "gpt-5.6-sol",
    "reasoning_effort": "medium",
    "temperature": "omitted",
    "max_output_tokens": 4096,
    "prompt_version": "raw-rca-v2",
    "prompt_sha256": PROMPT_SHA256,
    "taxonomy_version": "rca-taxonomy-v2",
    "scorer_version": "raw-rca-scorer-v2",
}


def _sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


@dataclass(frozen=True, slots=True)
class RecoveryDefinition:
    repository_root: Path
    data: dict[str, Any]

    @classmethod
    def load(cls, path: Path) -> Self:
        definition = cls(path.resolve().parent.parent, tomllib.loads(path.read_text()))
        definition.validate()
        return definition

    def validate(self) -> None:
        if set(self.data) != {"recovery", "settings", "sources", "cells", "pricing"}:
            raise ValueError("Unexpected recovery configuration sections")
        expected = {
            "protocol_version": RECOVERY_PROTOCOL,
            "attempt_index": 1,
            "manifest_schema_version": "raw-rca-manifest-v8",
            "source_checkpoint": SOURCE_CHECKPOINT,
            "result_path": RECOVERY_RESULT,
            "seed_scope": "development_only",
            "validation_seeds": [],
            "held_out_seeds": [],
        }
        if self.data["recovery"] != expected or type(self.data["recovery"]["attempt_index"]) is not int:
            raise ValueError("Recovery protocol, attempt, output path or seed scope changed")
        if self.data["settings"] != FROZEN_SETTINGS:
            raise ValueError("Recovery settings differ from the frozen protocol")
        if self.data["pricing"] != {"snapshot": "pricing/openai_gpt_5_6_sol_2026-09-10.toml"}:
            raise ValueError("Recovery pricing snapshot changed")
        sources = self.data["sources"]
        if set(sources) != set(CONDITIONS):
            raise ValueError("All five source conditions must be audited")
        for condition, source in sources.items():
            slug = condition.replace("-", "_")
            if set(source) != {"repeated_path", "repeated_sha256", "trial_one_path", "trial_one_sha256"}:
                raise ValueError("Incomplete source artifact reference")
            if source["repeated_path"] != f"results/incident_002_{slug}_sol_repeated_trials_2_3.jsonl":
                raise ValueError("Unexpected repeated-trial source path")
            if source["trial_one_path"] != f"results/incident_002_{slug}_sol_development_gpt_5_6_sol_medium.jsonl":
                raise ValueError("Unexpected trial-1 source path")
            if not all(_sha256(source[key]) for key in ("repeated_sha256", "trial_one_sha256")):
                raise ValueError("Invalid source artifact SHA-256")
        cells = self.data["cells"]
        if not isinstance(cells, list) or len(cells) != 10:
            raise ValueError("Recovery requires exactly ten sparse cells")
        schedule = []
        for cell in cells:
            if set(cell) != {"condition", "seed", "trial_index", "failure_type", "model_input_sha256"}:
                raise ValueError("Unexpected recovery cell fields")
            if type(cell["seed"]) is not int or type(cell["trial_index"]) is not int:
                raise ValueError("Recovery seed and trial index must be integers")
            if not _sha256(cell["model_input_sha256"]):
                raise ValueError("Recovery cell requires a frozen model-input SHA-256")
            schedule.append((cell["condition"], cell["seed"], cell["trial_index"], cell["failure_type"]))
        if tuple(schedule) != ELIGIBLE_CELLS:
            raise ValueError("Recovery schedule differs from the ten eligible failures")

    @property
    def result_path(self) -> Path:
        return self.repository_root / RECOVERY_RESULT

    @property
    def pricing_path(self) -> Path:
        return self.repository_root / "experiments" / self.data["pricing"]["snapshot"]

    def check_result_path(self, requested: Path) -> None:
        if requested.absolute() != self.result_path.absolute():
            raise ValueError("Recovery requires its dedicated frozen result path")
        if requested.exists() or requested.is_symlink():
            raise ValueError("Recovery result already exists; no further attempt is permitted")


def _read_frozen(root: Path, source: dict[str, str], prefix: str) -> list[ExperimentManifest]:
    path = root / source[f"{prefix}_path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != source[f"{prefix}_sha256"]:
        raise ValueError(f"Frozen {prefix} source artifact SHA-256 differs")
    return load_manifests(path)


def _check_settings(manifest: ExperimentManifest, condition: str) -> None:
    for name in (
        "incident_family", "requested_model", "reasoning_effort", "prompt_version",
        "prompt_sha256", "taxonomy_version", "scorer_version",
    ):
        if getattr(manifest, name) != FROZEN_SETTINGS[name]:
            raise ValueError(f"Source protocol mismatch: {name}")
    if manifest.condition != condition or manifest.split != "development":
        raise ValueError("Source condition or split differs")
    if manifest.temperature is not None or manifest.decoding_settings != {"max_output_tokens": 4096}:
        raise ValueError("Source decoding settings differ")


def prepare_recovery(definition: RecoveryDefinition) -> tuple[tuple[RawRunConfig, ...], dict[str, object]]:
    """Audit all 60 attempts, then reconstruct only the ten eligible inputs."""
    definition.validate()
    definition.check_result_path(definition.result_path)
    originals: dict[tuple[str, int, int], ExperimentManifest] = {}
    baselines: dict[tuple[str, int], ExperimentManifest] = {}
    failures: set[tuple[str, int, int, str]] = set()
    for condition in CONDITIONS:
        source = definition.data["sources"][condition]
        repeated = _read_frozen(definition.repository_root, source, "repeated")
        trial_one = _read_frozen(definition.repository_root, source, "trial_one")
        if len(repeated) != 12 or {(m.seed, m.trial_index) for m in repeated} != {
            (seed, trial) for seed in INCIDENT_002_DEVELOPMENT_SEEDS for trial in (2, 3)
        }:
            raise ValueError("Source repeated-trial identities differ")
        if len(trial_one) != 6 or {m.seed for m in trial_one} != set(INCIDENT_002_DEVELOPMENT_SEEDS):
            raise ValueError("Source trial-1 identities differ")
        for m in trial_one:
            _check_settings(m, condition)
            if m.manifest_schema_version != "raw-rca-manifest-v6" or m.trial_index is not None:
                raise ValueError("Trial-1 source must retain historical schema v6")
            if m.response.status != "valid":
                raise ValueError("Unexpected failure in frozen trial 1")
            baselines[condition, m.seed] = m
        for m in repeated:
            _check_settings(m, condition)
            if m.manifest_schema_version != "raw-rca-manifest-v7" or m.recovery_provenance is not None:
                raise ValueError("Recovery source must be an original v7 observation")
            baseline = baselines[condition, m.seed]
            for name in (
                "model_input_sha256", "benchmark_version", "model_version_metadata",
                "intended_temperature", "temperature_omission_reason",
                "transformation_key_id", "transformation_key_fingerprint",
            ):
                if getattr(m, name) != getattr(baseline, name):
                    raise ValueError(f"Trial-1/source mismatch: {name}")
            originals[condition, m.seed, m.trial_index] = m
            if m.response.status != "valid":
                error_type = (m.response.error or "").removeprefix("OpenAI Responses API failure: ")
                if (m.response.status != "provider_error" or error_type not in {"TimeoutError", "URLError"}
                        or m.response.response is not None or m.score is not None):
                    raise ValueError("Source contains a non-eligible failure")
                failures.add((condition, m.seed, m.trial_index, error_type))
    if failures != set(ELIGIBLE_CELLS):
        raise ValueError("Observed source failures differ from the exact ten eligible cells")

    configs = []
    planned = []
    for cell in definition.data["cells"]:
        condition, seed, trial = cell["condition"], cell["seed"], cell["trial_index"]
        original = originals[condition, seed, trial]
        source = definition.data["sources"][condition]
        if cell["model_input_sha256"] != original.model_input_sha256:
            raise ValueError("Recovery cell hash differs from original failed input")
        provenance = RecoveryProvenance(
            recovery_protocol_version=RECOVERY_PROTOCOL,
            recovery_attempt_index=1,
            recovery_of_trial_index=trial,
            original_condition=condition,
            original_seed=seed,
            original_failure_type=cell["failure_type"],
            original_experiment_id=original.experiment_id,
            original_result_artifact=source["repeated_path"],
            original_result_artifact_sha256=source["repeated_sha256"],
        )
        config = RawRunConfig(
            experiment_id=f"{RECOVERY_PROTOCOL}-{condition}-development-{seed}-trial-{trial}-recovery-1",
            seed=seed, model=original.requested_model,
            model_version=original.model_version_metadata,
            incident_family=original.incident_family,
            manifest_schema_version="raw-rca-manifest-v8",
            reasoning_effort=original.reasoning_effort, condition=condition,
            decoding_settings=dict(original.decoding_settings),
            intended_temperature=original.intended_temperature,
            temperature_omission_reason=original.temperature_omission_reason,
            prompt_version=original.prompt_version,
            expected_model_input_sha256=original.model_input_sha256,
            trial_index=trial, recovery_provenance=provenance,
        )
        prepared = prepare_model_input(config)
        ordinary = prepare_model_input(replace(
            config, experiment_id=original.experiment_id,
            manifest_schema_version="raw-rca-manifest-v7", recovery_provenance=None,
        ))
        if prepared.prompt != ordinary.prompt:
            raise ValueError("Recovery metadata altered the model-visible input")
        configs.append(config)
        planned.append({
            "condition": condition, "seed": seed, "trial_index": trial,
            "experiment_id": config.experiment_id,
            "model_input_sha256": prepared.model_input_sha256,
            "matches_failed_observation": True, "matches_trial_one": True,
            "recovery_metadata_absent_from_input": True,
            "recovery_provenance": provenance.to_dict(),
        })
    return tuple(configs), {
        "execution": "pending", "analysis_role": "transport-recovery sensitivity analysis",
        "protocol_version": RECOVERY_PROTOCOL, "source_checkpoint": SOURCE_CHECKPOINT,
        "manifest_schema_version": "raw-rca-manifest-v8", "settings": FROZEN_SETTINGS,
        "source_observations_audited": 60, "source_valid_responses": 50,
        "source_transport_failures": 10, "scheduled_calls": len(configs),
        "result_path": RECOVERY_RESULT, "planned_observations": planned,
    }
