"""Versioned, validated configuration for the first raw RCA pilot."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import tomllib
from typing import Any, Literal, Self

from diagpriv.evaluation.incident_families import (
    INCIDENT_001_FAMILY,
    INCIDENT_002_DEVELOPMENT_SEEDS,
    INCIDENT_002_FAMILY,
    INCIDENT_002_SEED_SELECTION_VERSION,
    INCIDENT_003_DEVELOPMENT_SEEDS,
    INCIDENT_003_FAMILY,
    INCIDENT_003_SEED_SELECTION_VERSION,
    INCIDENT_003_V2_DEVELOPMENT_SEEDS,
    INCIDENT_003_V2_FAMILY,
    INCIDENT_003_V2_SEED_SELECTION_VERSION,
    INCIDENT_003_V3_FAMILY,
    INCIDENT_003_V3_QUALIFICATION_SEEDS,
    INCIDENT_003_V3_QUERY_ROLES,
    INCIDENT_003_V3_SEED_SELECTION_VERSION,
    SUPPORTED_INCIDENT_FAMILIES,
    evaluation_seed_split,
    generate_evaluation_incident,
    incident_003_v3_case_id,
)
from diagpriv.evaluation.prompt import (
    PROMPT_SHA256 as PROMPT_SHA256_V1,
    PROMPT_VERSION as PROMPT_VERSION_V1,
)
from diagpriv.evaluation.prompt_v2 import (
    PROMPT_SHA256 as PROMPT_SHA256_V2,
    PROMPT_VERSION as PROMPT_VERSION_V2,
    build_prompt_v2,
)
from diagpriv.evaluation.prompt_v3 import (
    PROMPT_SHA256 as PROMPT_SHA256_V3,
    PROMPT_VERSION as PROMPT_VERSION_V3,
)
from diagpriv.evaluation.evidence_support_v3 import (
    EVIDENCE_SUPPORT_VERSION as EVIDENCE_SUPPORT_VERSION_V3,
)
from diagpriv.evaluation.evidence_support_v4 import (
    EVIDENCE_SUPPORT_VERSION as EVIDENCE_SUPPORT_VERSION_V4,
)
from diagpriv.transformations.provenance import (
    transformation_configuration_for_condition,
    transformation_configuration_sha256,
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
    PROMPT_VERSION_V3: (
        PROMPT_SHA256_V3,
        "rca-taxonomy-v3",
        "raw-rca-scorer-v3",
    ),
}

SeedScope = Literal["development_and_validation", "development_only", "validation_only"]


@dataclass(frozen=True, slots=True)
class PilotDefinition:
    pilot_id: str
    provider: str
    incident_family: str
    manifest_schema_version: str
    development_seed_selection_version: str | None
    condition: Literal[
        "raw",
        "redaction-v1",
        "hmac-v1",
        "tokenization-v1",
        "format-preserving-v1",
        "relative-time-v1",
        "temporal-ablation-v1",
    ]
    prompt_version: str
    prompt_sha256: str
    taxonomy_version: str
    scorer_version: str
    seed_scope: SeedScope
    development_seeds: tuple[int, ...]
    validation_seeds: tuple[int, ...]
    held_out_seeds: tuple[int, ...]
    calls_per_seed: int
    result_path_must_not_exist: bool
    trial_indices: tuple[int, ...]
    repetition_protocol_version: str | None
    historical_trial_count: int | None
    target_total_trials: int | None
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
    transformation_version: str | None
    transformation_semantics_version: str | None
    transformation_anchor_rule: str | None
    transformation_precision: str | None
    transformation_representation: str | None
    transformation_annotation_classification: str | None
    transformation_scope_policy: str | None
    matched_input_baseline_pilot_id: str | None
    matched_input_baseline_result_sha256: str | None
    matched_model_input_sha256_by_seed: dict[int, str]
    expected_model_input_sha256_by_seed: dict[int, str]
    expected_evidence_requirement_set_sha256_by_seed: dict[int, str]
    expected_incident_generator_version: str | None
    expected_incident_protocol_version: str | None
    expected_evidence_support_version: str | None
    expected_transformation_key_fingerprint: str | None
    expected_transformation_configuration_sha256: str | None
    query_roles: tuple[str, ...]
    expected_model_input_sha256_by_case_id: dict[str, str]
    expected_evidence_requirement_set_sha256_by_case_id: dict[str, str]
    expected_paired_query_protocol_version: str | None
    expected_anchor_allocation_version: str | None
    expected_evidence_requirement_version: str | None
    expected_semantic_evaluator_version: str | None

    @classmethod
    def load(cls, path: Path) -> Self:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        pilot = data["pilot"]
        model = data["model"]
        pricing = data["pricing"]
        transformation = data.get("transformation", {})
        matched_input = data.get("matched_input", {})
        input_provenance = data.get("input_provenance", {})
        incident_protocol = data.get("incident_protocol", {})
        if not isinstance(transformation, dict):
            raise ValueError("transformation must be a table")
        if not isinstance(matched_input, dict):
            raise ValueError("matched_input must be a table")
        if not isinstance(input_provenance, dict):
            raise ValueError("input_provenance must be a table")
        if not isinstance(incident_protocol, dict):
            raise ValueError("incident_protocol must be a table")
        matched_hashes = matched_input.get("model_input_sha256_by_seed", {})
        if not isinstance(matched_hashes, dict):
            raise ValueError("matched input hashes must be a table")
        expected_hashes = input_provenance.get(
            "model_input_sha256_by_seed", {}
        )
        if not isinstance(expected_hashes, dict):
            raise ValueError("Input-provenance hashes must be a table")
        expected_rubric_hashes = input_provenance.get(
            "evidence_requirement_set_sha256_by_seed", {}
        )
        if not isinstance(expected_rubric_hashes, dict):
            raise ValueError("Evidence requirement-set hashes must be a table")
        expected_case_hashes = input_provenance.get(
            "model_input_sha256_by_case_id", {}
        )
        if not isinstance(expected_case_hashes, dict):
            raise ValueError("Case input-provenance hashes must be a table")
        expected_case_rubric_hashes = input_provenance.get(
            "evidence_requirement_set_sha256_by_case_id", {}
        )
        if not isinstance(expected_case_rubric_hashes, dict):
            raise ValueError("Case evidence requirement-set hashes must be a table")
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
            incident_family=pilot.get("incident_family", INCIDENT_001_FAMILY),
            manifest_schema_version=pilot.get(
                "manifest_schema_version", "raw-rca-manifest-v5"
            ),
            development_seed_selection_version=pilot.get(
                "development_seed_selection_version"
            ),
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
            result_path_must_not_exist=pilot.get(
                "result_path_must_not_exist", False
            ),
            trial_indices=tuple(pilot.get("trial_indices", ())),
            repetition_protocol_version=pilot.get("repetition_protocol_version"),
            historical_trial_count=pilot.get("historical_trial_count"),
            target_total_trials=pilot.get("target_total_trials"),
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
            transformation_version=transformation.get("transformation_version"),
            transformation_semantics_version=transformation.get(
                "temporal_semantics_version"
            ),
            transformation_anchor_rule=transformation.get("anchor_rule"),
            transformation_precision=transformation.get("precision"),
            transformation_representation=transformation.get("representation"),
            transformation_annotation_classification=transformation.get(
                "annotation_classification"
            ),
            transformation_scope_policy=transformation.get("scope_policy"),
            matched_input_baseline_pilot_id=matched_input.get(
                "baseline_pilot_id"
            ),
            matched_input_baseline_result_sha256=matched_input.get(
                "baseline_result_sha256"
            ),
            matched_model_input_sha256_by_seed={
                int(seed): digest for seed, digest in matched_hashes.items()
            },
            expected_model_input_sha256_by_seed={
                int(seed): digest for seed, digest in expected_hashes.items()
            },
            expected_evidence_requirement_set_sha256_by_seed={
                int(seed): digest for seed, digest in expected_rubric_hashes.items()
            },
            expected_incident_generator_version=incident_protocol.get(
                "generator_version"
            ),
            expected_incident_protocol_version=incident_protocol.get(
                "protocol_version"
            ),
            expected_evidence_support_version=incident_protocol.get(
                "evidence_protocol_version"
            ),
            expected_transformation_key_fingerprint=input_provenance.get(
                "transformation_key_fingerprint"
            ),
            expected_transformation_configuration_sha256=input_provenance.get(
                "transformation_configuration_sha256"
            ),
            query_roles=tuple(pilot.get("query_roles", ())),
            expected_model_input_sha256_by_case_id={
                str(case_id): digest
                for case_id, digest in expected_case_hashes.items()
            },
            expected_evidence_requirement_set_sha256_by_case_id={
                str(case_id): digest
                for case_id, digest in expected_case_rubric_hashes.items()
            },
            expected_paired_query_protocol_version=incident_protocol.get(
                "paired_query_protocol_version"
            ),
            expected_anchor_allocation_version=incident_protocol.get(
                "anchor_allocation_version"
            ),
            expected_evidence_requirement_version=incident_protocol.get(
                "evidence_requirement_version"
            ),
            expected_semantic_evaluator_version=incident_protocol.get(
                "semantic_evaluator_version"
            ),
        )
        definition.validate()
        return definition

    def validate(self) -> None:
        if self.incident_family not in SUPPORTED_INCIDENT_FAMILIES:
            raise ValueError(f"Unsupported incident family: {self.incident_family}")
        if self.manifest_schema_version not in {
            "raw-rca-manifest-v5",
            "raw-rca-manifest-v6",
            "raw-rca-manifest-v7",
            "raw-rca-manifest-v9",
            "raw-rca-manifest-v10",
            "raw-rca-manifest-v11",
        }:
            raise ValueError(
                f"Unsupported manifest schema: {self.manifest_schema_version}"
            )
        if self.condition not in {
            "raw",
            "redaction-v1",
            "hmac-v1",
            "tokenization-v1",
            "format-preserving-v1",
            "relative-time-v1",
            "temporal-ablation-v1",
        }:
            raise ValueError(f"Unsupported pilot condition: {self.condition}")
        if self.condition == "hmac-v1":
            if not self.hmac_key_environment_variable:
                raise ValueError("hmac-v1 requires a key environment variable name")
            if not self.hmac_key_id:
                raise ValueError("hmac-v1 requires a non-secret experimental key ID")
        elif self.hmac_key_environment_variable is not None or self.hmac_key_id is not None:
            raise ValueError("HMAC key configuration is valid only for hmac-v1")
        transformation_configuration = {
            "transformation_version": self.transformation_version,
            "temporal_semantics_version": self.transformation_semantics_version,
            "anchor_rule": self.transformation_anchor_rule,
            "precision": self.transformation_precision,
            "representation": self.transformation_representation,
            "annotation_classification": (
                self.transformation_annotation_classification
            ),
            "scope_policy": self.transformation_scope_policy,
        }
        configured_values = tuple(transformation_configuration.values())
        if self.manifest_schema_version in {
            "raw-rca-manifest-v10",
            "raw-rca-manifest-v11",
        }:
            expected_configuration = transformation_configuration_for_condition(
                self.condition
            )
            if transformation_configuration != expected_configuration:
                raise ValueError(
                    "Manifest v10 requires the frozen transformation configuration"
                )
            actual_hash = transformation_configuration_sha256(
                expected_configuration
            )
            if self.expected_transformation_configuration_sha256 != actual_hash:
                raise ValueError("Transformation configuration SHA-256 mismatch")
        elif self.condition in {"relative-time-v1", "temporal-ablation-v1"}:
            raise ValueError(f"{self.condition} requires manifest schema v10")
        elif any(value is not None for value in configured_values):
            raise ValueError(
                "Transformation configuration fields require manifest schema v10"
            )
        elif self.expected_transformation_configuration_sha256 is not None:
            raise ValueError(
                "Transformation configuration SHA-256 requires manifest schema v10"
            )
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
        if not isinstance(self.result_path_must_not_exist, bool):
            raise ValueError("result_path_must_not_exist must be a boolean")
        if self.manifest_schema_version == "raw-rca-manifest-v7":
            if not self.repetition_protocol_version:
                raise ValueError(
                    "Manifest schema v7 requires a repetition protocol version"
                )
            if (
                isinstance(self.historical_trial_count, bool)
                or not isinstance(self.historical_trial_count, int)
                or self.historical_trial_count < 1
                or isinstance(self.target_total_trials, bool)
                or not isinstance(self.target_total_trials, int)
                or self.target_total_trials <= self.historical_trial_count
            ):
                raise ValueError(
                    "Manifest schema v7 requires valid historical and target trial counts"
                )
            expected_indices = tuple(
                range(self.historical_trial_count + 1, self.target_total_trials + 1)
            )
            if self.trial_indices != expected_indices:
                raise ValueError(
                    "Trial indices must continue consecutively after historical trials"
                )
            if len(self.trial_indices) != self.calls_per_seed:
                raise ValueError(
                    "Manifest schema v7 requires one trial index per call"
                )
            if (
                any(
                    isinstance(index, bool)
                    or not isinstance(index, int)
                    or index < 1
                    for index in self.trial_indices
                )
                or len(set(self.trial_indices)) != len(self.trial_indices)
                or tuple(sorted(self.trial_indices)) != self.trial_indices
            ):
                raise ValueError(
                    "Manifest schema v7 trial indices must be unique positive "
                    "integers in ascending order"
                )
        elif any(
            value is not None
            for value in (
                self.repetition_protocol_version,
                self.historical_trial_count,
                self.target_total_trials,
            )
        ) or self.trial_indices:
            raise ValueError("Repeated-trial metadata requires manifest schema v7")
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
        if any(
            evaluation_seed_split(self.incident_family, seed) != "development"
            for seed in self.development_seeds
        ):
            raise ValueError("Pilot development_seeds contains a non-development seed")
        if any(
            evaluation_seed_split(self.incident_family, seed) != "validation"
            for seed in self.validation_seeds
        ):
            raise ValueError("Pilot validation_seeds contains a non-validation seed")
        if len(set((*self.development_seeds, *self.validation_seeds))) != len(
            self.development_seeds
        ) + len(self.validation_seeds):
            raise ValueError("Pilot seed lists must not overlap")
        if self.incident_family == INCIDENT_002_FAMILY:
            if self.seed_scope != "development_only":
                raise ValueError("Incident 002 pilot must be development-only")
            if self.development_seeds != INCIDENT_002_DEVELOPMENT_SEEDS:
                raise ValueError(
                    "Incident 002 pilot must use exactly the frozen development seeds"
                )
            if (
                self.development_seed_selection_version
                != INCIDENT_002_SEED_SELECTION_VERSION
            ):
                raise ValueError(
                    "Incident 002 pilot requires the frozen seed-selection version"
                )
            if self.manifest_schema_version not in {
                "raw-rca-manifest-v6",
                "raw-rca-manifest-v7",
            }:
                raise ValueError("Incident 002 pilot requires manifest schema v6 or v7")
        elif self.incident_family == INCIDENT_003_FAMILY:
            if self.seed_scope != "development_only":
                raise ValueError("Incident 003 pilot must be development-only")
            if self.development_seeds != INCIDENT_003_DEVELOPMENT_SEEDS:
                raise ValueError(
                    "Incident 003 pilot must use exactly the frozen development seeds"
                )
            if (
                self.development_seed_selection_version
                != INCIDENT_003_SEED_SELECTION_VERSION
            ):
                raise ValueError(
                    "Incident 003 pilot requires the frozen seed-selection version"
                )
            if self.manifest_schema_version != "raw-rca-manifest-v6":
                raise ValueError("Incident 003 pilot requires manifest schema v6")
            if not self.result_path_must_not_exist:
                raise ValueError(
                    "Incident 003 pilot requires a previously absent result path"
                )
        elif self.incident_family == INCIDENT_003_V2_FAMILY:
            if self.seed_scope != "development_only":
                raise ValueError("Incident 003 v2 pilot must be development-only")
            if self.development_seeds != INCIDENT_003_V2_DEVELOPMENT_SEEDS:
                raise ValueError(
                    "Incident 003 v2 pilot must use exactly the frozen fresh "
                    "development seeds"
                )
            if (
                self.development_seed_selection_version
                != INCIDENT_003_V2_SEED_SELECTION_VERSION
            ):
                raise ValueError(
                    "Incident 003 v2 pilot requires the frozen fresh "
                    "seed-selection version"
                )
            expected_schema = (
                "raw-rca-manifest-v9"
                if self.condition == "raw"
                else "raw-rca-manifest-v10"
            )
            if self.manifest_schema_version != expected_schema:
                raise ValueError(
                    f"Incident 003 v2 {self.condition} pilot requires "
                    f"manifest schema {expected_schema.removeprefix('raw-rca-manifest-')}"
                )
            expected_evidence_version = (
                EVIDENCE_SUPPORT_VERSION_V4
                if self.condition
                in {
                    "temporal-ablation-v1",
                    "redaction-v1",
                    "hmac-v1",
                    "tokenization-v1",
                    "format-preserving-v1",
                }
                else EVIDENCE_SUPPORT_VERSION_V3
            )
            if (
                self.expected_incident_generator_version
                != "incident-003-generator-v2"
                or self.expected_incident_protocol_version
                != "incident-003-temporal-protocol-v2"
                or self.expected_evidence_support_version
                != expected_evidence_version
            ):
                raise ValueError(
                    "Incident 003 v2 pilot requires frozen incident/evidence versions"
                )
            if self.prompt_version != PROMPT_VERSION_V3:
                raise ValueError("Incident 003 v2 pilot requires raw-rca-v3")
            if self.condition not in {
                "raw",
                "relative-time-v1",
                "temporal-ablation-v1",
                "redaction-v1",
                "hmac-v1",
                "tokenization-v1",
                "format-preserving-v1",
            }:
                raise ValueError(
                    "Incident 003 v2 does not support the configured condition"
                )
            if not self.result_path_must_not_exist:
                raise ValueError(
                    "Incident 003 v2 pilot requires a previously absent result path"
                )
        elif self.incident_family == INCIDENT_003_V3_FAMILY:
            if self.seed_scope != "development_only":
                raise ValueError("Incident 003 v3 pilot must be development-only")
            if self.development_seeds != INCIDENT_003_V3_QUALIFICATION_SEEDS:
                raise ValueError(
                    "Incident 003 v3 pilot must use exactly the frozen "
                    "qualification seeds"
                )
            if (
                self.development_seed_selection_version
                != INCIDENT_003_V3_SEED_SELECTION_VERSION
            ):
                raise ValueError(
                    "Incident 003 v3 pilot requires the frozen seed-selection rule"
                )
            if self.query_roles != INCIDENT_003_V3_QUERY_ROLES:
                raise ValueError(
                    "Incident 003 v3 pilot requires both frozen query roles"
                )
            if self.manifest_schema_version != "raw-rca-manifest-v11":
                raise ValueError("Incident 003 v3 paired pilot requires manifest v11")
            if self.prompt_version != PROMPT_VERSION_V3:
                raise ValueError("Incident 003 v3 pilot requires raw-rca-v3")
            if self.condition not in {
                "raw",
                "relative-time-v1",
                "temporal-ablation-v1",
            }:
                raise ValueError(
                    "Incident 003 v3 qualification supports only its three "
                    "preregistered conditions"
                )
            expected_versions = (
                "incident-003-generator-v3",
                "incident-003-temporal-protocol-v3",
                EVIDENCE_SUPPORT_VERSION_V4,
                "incident-003-v3-paired-query-v1",
                "incident-003-v3-role-neutral-anchor-allocation-v1",
                "incident-003-v3-evidence-requirements-v2",
                "incident-003-v3-evidence-semantic-evaluator-v2",
            )
            actual_versions = (
                self.expected_incident_generator_version,
                self.expected_incident_protocol_version,
                self.expected_evidence_support_version,
                self.expected_paired_query_protocol_version,
                self.expected_anchor_allocation_version,
                self.expected_evidence_requirement_version,
                self.expected_semantic_evaluator_version,
            )
            if actual_versions != expected_versions:
                raise ValueError(
                    "Incident 003 v3 pilot requires frozen paired protocol versions"
                )
            if self.calls_per_seed != 1:
                raise ValueError(
                    "Incident 003 v3 qualification requires one call per paired case"
                )
            if not self.result_path_must_not_exist:
                raise ValueError(
                    "Incident 003 v3 pilot requires a previously absent result path"
                )
        elif self.development_seed_selection_version is not None:
            if (
                self.development_seed_selection_version
                == INCIDENT_002_SEED_SELECTION_VERSION
            ):
                raise ValueError(
                    "Incident 002 seed-selection metadata is valid only for Incident 002"
                )
            if (
                self.development_seed_selection_version
                == INCIDENT_003_SEED_SELECTION_VERSION
            ):
                raise ValueError(
                    "Incident 003 seed-selection metadata is valid only for Incident 003"
                )
            if (
                self.development_seed_selection_version
                == INCIDENT_003_V2_SEED_SELECTION_VERSION
            ):
                raise ValueError(
                    "Incident 003 v2 seed-selection metadata is valid only for "
                    "Incident 003 v2"
                )
            if (
                self.development_seed_selection_version
                == INCIDENT_003_V3_SEED_SELECTION_VERSION
            ):
                raise ValueError(
                    "Incident 003 v3 seed-selection metadata is valid only for "
                    "Incident 003 v3"
                )
            raise ValueError("Unknown family-specific seed-selection metadata")
        if self.incident_family != INCIDENT_003_V3_FAMILY and (
            self.query_roles
            or self.expected_model_input_sha256_by_case_id
            or self.expected_evidence_requirement_set_sha256_by_case_id
            or any(
                value is not None
                for value in (
                    self.expected_paired_query_protocol_version,
                    self.expected_anchor_allocation_version,
                    self.expected_evidence_requirement_version,
                    self.expected_semantic_evaluator_version,
                )
            )
        ):
            raise ValueError(
                "Paired-query configuration is valid only for Incident 003 v3"
            )
        self._validate_matched_inputs()
        self._validate_input_provenance()
        if not self.pricing_snapshot_path.is_file():
            raise ValueError("Pilot pricing snapshot does not exist")

    def _validate_matched_inputs(self) -> None:
        metadata = (
            self.matched_input_baseline_pilot_id,
            self.matched_input_baseline_result_sha256,
            self.matched_model_input_sha256_by_seed,
        )
        if not any(metadata):
            return
        if not all(metadata):
            raise ValueError("Matched-input metadata must be complete")
        if self.condition != "raw" or self.prompt_version != PROMPT_VERSION_V2:
            raise ValueError("Matched-input verification currently requires raw-rca-v2")
        baseline_digest = self.matched_input_baseline_result_sha256
        if not isinstance(baseline_digest, str) or not _is_sha256(baseline_digest):
            raise ValueError("Matched-input baseline result SHA-256 is invalid")
        configured_seeds = (*self.development_seeds, *self.validation_seeds)
        if set(self.matched_model_input_sha256_by_seed) != set(configured_seeds):
            raise ValueError("Matched-input hashes must cover exactly the pilot seeds")
        for seed in configured_seeds:
            expected = self.matched_model_input_sha256_by_seed[seed]
            if not isinstance(expected, str) or not _is_sha256(expected):
                raise ValueError(f"Matched-input SHA-256 is invalid for seed {seed}")
            incident = generate_evaluation_incident(self.incident_family, seed)
            prompt = build_prompt_v2(incident.model_view())
            actual = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            if actual != expected:
                raise ValueError(
                    f"Matched model input differs from baseline for seed {seed}"
                )

    def _validate_input_provenance(self) -> None:
        hashes = self.expected_model_input_sha256_by_seed
        rubric_hashes = self.expected_evidence_requirement_set_sha256_by_seed
        fingerprint = self.expected_transformation_key_fingerprint
        if self.incident_family == INCIDENT_003_V3_FAMILY:
            if hashes or rubric_hashes:
                raise ValueError(
                    "Incident 003 v3 provenance must be keyed by paired case ID"
                )
            expected_case_ids = {
                incident_003_v3_case_id(seed, role)  # type: ignore[arg-type]
                for seed in self.development_seeds
                for role in self.query_roles
            }
            case_hashes = self.expected_model_input_sha256_by_case_id
            case_rubric_hashes = (
                self.expected_evidence_requirement_set_sha256_by_case_id
            )
            if set(case_hashes) != expected_case_ids:
                raise ValueError(
                    "Model-input hashes must cover exactly the paired case IDs"
                )
            if set(case_rubric_hashes) != expected_case_ids:
                raise ValueError(
                    "Evidence requirement hashes must cover exactly the paired case IDs"
                )
            for label, values in (
                ("Model-input", case_hashes),
                ("Evidence requirement-set", case_rubric_hashes),
            ):
                for case_id, digest in values.items():
                    if not isinstance(digest, str) or not _is_sha256(digest):
                        raise ValueError(f"{label} SHA-256 is invalid for {case_id}")
            if fingerprint is not None:
                raise ValueError(
                    "Incident 003 v3 qualification does not use HMAC provenance"
                )
            return
        if not hashes and not rubric_hashes and fingerprint is None:
            return
        if not hashes:
            raise ValueError("Input provenance requires model-input hashes")
        configured_seeds = (*self.development_seeds, *self.validation_seeds)
        if set(hashes) != set(configured_seeds):
            raise ValueError(
                "Input-provenance hashes must cover exactly the pilot seeds"
            )
        for seed, digest in hashes.items():
            if not isinstance(digest, str) or not _is_sha256(digest):
                raise ValueError(
                    f"Input-provenance SHA-256 is invalid for seed {seed}"
                )
        if self.manifest_schema_version in {
            "raw-rca-manifest-v9",
            "raw-rca-manifest-v10",
        }:
            if set(rubric_hashes) != set(configured_seeds):
                raise ValueError(
                    "Evidence requirement-set hashes must cover exactly the pilot seeds"
                )
            for seed, digest in rubric_hashes.items():
                if not isinstance(digest, str) or not _is_sha256(digest):
                    raise ValueError(
                        f"Evidence requirement-set SHA-256 is invalid for seed {seed}"
                    )
        elif rubric_hashes:
            raise ValueError(
                "Evidence requirement-set hashes require manifest schema v9 or v10"
            )
        if self.condition == "hmac-v1":
            if not isinstance(fingerprint, str) or not _is_sha256(fingerprint):
                raise ValueError(
                    "HMAC input provenance requires a valid key fingerprint"
                )
        elif fingerprint is not None:
            raise ValueError(
                "Transformation-key fingerprint is valid only for hmac-v1"
            )

    def paired_case_plan(self) -> tuple[tuple[int, str, str], ...]:
        """Return stable seed/role/case identities without seed-only deduplication."""
        if self.incident_family != INCIDENT_003_V3_FAMILY:
            return ()
        return tuple(
            (seed, role, incident_003_v3_case_id(seed, role))  # type: ignore[arg-type]
            for seed in self.development_seeds
            for role in self.query_roles
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "pilot_id": self.pilot_id,
            "provider": self.provider,
            "incident_family": self.incident_family,
            "manifest_schema_version": self.manifest_schema_version,
            "development_seed_selection_version": (
                self.development_seed_selection_version
            ),
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
            **(
                {"query_roles": list(self.query_roles)}
                if self.query_roles
                else {}
            ),
            **(
                {"result_path_must_not_exist": True}
                if self.result_path_must_not_exist
                else {}
            ),
            **(
                {"trial_indices": list(self.trial_indices)}
                if self.trial_indices
                else {}
            ),
            **(
                {
                    "repetition_protocol_version": self.repetition_protocol_version,
                    "historical_trial_count": self.historical_trial_count,
                    "target_total_trials": self.target_total_trials,
                }
                if self.repetition_protocol_version is not None
                else {}
            ),
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
        if self.expected_incident_generator_version is not None:
            data["incident_protocol"] = {
                "generator_version": self.expected_incident_generator_version,
                "protocol_version": self.expected_incident_protocol_version,
                "evidence_protocol_version": self.expected_evidence_support_version,
                **(
                    {
                        "paired_query_protocol_version": (
                            self.expected_paired_query_protocol_version
                        ),
                        "anchor_allocation_version": (
                            self.expected_anchor_allocation_version
                        ),
                        "evidence_requirement_version": (
                            self.expected_evidence_requirement_version
                        ),
                        "semantic_evaluator_version": (
                            self.expected_semantic_evaluator_version
                        ),
                    }
                    if self.expected_paired_query_protocol_version is not None
                    else {}
                ),
            }
        if self.manifest_schema_version in {
            "raw-rca-manifest-v10",
            "raw-rca-manifest-v11",
        }:
            transformation: dict[str, object] = {
                "transformation_version": self.transformation_version,
                "temporal_semantics_version": (
                    self.transformation_semantics_version
                ),
                "anchor_rule": self.transformation_anchor_rule,
                "precision": self.transformation_precision,
                "representation": self.transformation_representation,
                "annotation_classification": (
                    self.transformation_annotation_classification
                ),
                "scope_policy": self.transformation_scope_policy,
            }
            if self.condition == "hmac-v1":
                transformation.update(
                    {
                        "key_environment_variable": (
                            self.hmac_key_environment_variable
                        ),
                        "key_id": self.hmac_key_id,
                    }
                )
            data["transformation"] = transformation
        elif self.condition == "hmac-v1":
            data["transformation"] = {
                "version": "hmac-v1",
                "key_environment_variable": self.hmac_key_environment_variable,
                "key_id": self.hmac_key_id,
            }
        if self.matched_input_baseline_pilot_id is not None:
            data["matched_input"] = {
                "baseline_pilot_id": self.matched_input_baseline_pilot_id,
                "baseline_result_sha256": (
                    self.matched_input_baseline_result_sha256
                ),
                "model_input_sha256_by_seed": {
                    str(seed): digest
                    for seed, digest in sorted(
                        self.matched_model_input_sha256_by_seed.items()
                    )
                },
            }
        if self.expected_model_input_sha256_by_seed:
            input_provenance: dict[str, object] = {
                "model_input_sha256_by_seed": {
                    str(seed): digest
                    for seed, digest in sorted(
                        self.expected_model_input_sha256_by_seed.items()
                    )
                }
            }
            if self.expected_transformation_key_fingerprint is not None:
                input_provenance["transformation_key_fingerprint"] = (
                    self.expected_transformation_key_fingerprint
                )
            if self.expected_transformation_configuration_sha256 is not None:
                input_provenance["transformation_configuration_sha256"] = (
                    self.expected_transformation_configuration_sha256
                )
            if self.expected_evidence_requirement_set_sha256_by_seed:
                input_provenance["evidence_requirement_set_sha256_by_seed"] = {
                    str(seed): digest
                    for seed, digest in sorted(
                        self.expected_evidence_requirement_set_sha256_by_seed.items()
                    )
                }
            data["input_provenance"] = input_provenance
        elif self.expected_model_input_sha256_by_case_id:
            data["input_provenance"] = {
                "transformation_configuration_sha256": (
                    self.expected_transformation_configuration_sha256
                ),
                "model_input_sha256_by_case_id": dict(
                    sorted(self.expected_model_input_sha256_by_case_id.items())
                ),
                "evidence_requirement_set_sha256_by_case_id": dict(
                    sorted(
                        self.expected_evidence_requirement_set_sha256_by_case_id.items()
                    )
                ),
            }
        return data


def _optional_temperature(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )
