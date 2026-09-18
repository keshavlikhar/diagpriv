"""Provider-independent orchestration for one RCA experiment run."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Literal

from diagbench.schema import Incident, ModelView
from diagbench.audits.incident_003 import temporally_ablated_model_view
from diagbench.generators.incident_001 import (
    DEVELOPMENT_SEEDS,
    VALIDATION_SEEDS,
    generate_incident_001,  # compatibility hook for frozen seed-guard tests
)
from diagbench.generators.incident_003_v3 import (
    ANCHOR_ALLOCATION_VERSION as INCIDENT_003_V3_ANCHOR_ALLOCATION_VERSION,
)
from diagpriv.evaluation.incident_families import (
    INCIDENT_001_FAMILY,
    INCIDENT_002_DEVELOPMENT_SEEDS,
    INCIDENT_002_FAMILY,
    INCIDENT_003_DEVELOPMENT_SEEDS,
    INCIDENT_003_FAMILY,
    INCIDENT_003_V2_DEVELOPMENT_SEEDS,
    INCIDENT_003_V2_FAMILY,
    INCIDENT_003_V3_QUALIFICATION_SEEDS,
    INCIDENT_003_V3_FAMILY,
    INCIDENT_003_V3_QUERY_ROLES,
    evaluation_seed_split,
    generate_evaluation_incident,
    incident_003_v3_case_id,
)
from diagpriv.evaluation.evidence_protocols import (
    build_evidence_rubric_v3,
    build_evidence_semantic_evaluator_v4,
)
from diagpriv.evaluation.evidence_support_v3 import (
    EVIDENCE_SUPPORT_VERSION as EVIDENCE_SUPPORT_VERSION_V3,
    EvidenceRubricV3,
    evidence_requirement_set_sha256_v3,
    validate_evidence_rubric_v3,
)
from diagpriv.evaluation.evidence_support_v4 import (
    EVIDENCE_SUPPORT_VERSION as EVIDENCE_SUPPORT_VERSION_V4,
    EvidenceSemanticEvaluatorV4,
)
from diagpriv.evaluation.incident_003_v3_evidence import (
    REQUIREMENT_CONSTRUCTOR_VERSION as INCIDENT_003_V3_REQUIREMENT_VERSION,
)
from diagpriv.evaluation.incident_003_v3_evidence_semantics import (
    EVIDENCE_SEMANTIC_EVALUATOR_VERSION as INCIDENT_003_V3_SEMANTIC_EVALUATOR_VERSION,
)
from diagpriv.evaluation.manifest import (
    ExperimentManifest,
    RecoveryProvenance,
    TransformationProvenance,
    append_manifest,
    validate_recovery_identity,
)
from diagpriv.evaluation.prompt import (
    PROMPT_SHA256 as PROMPT_SHA256_V1,
    PROMPT_VERSION as PROMPT_VERSION_V1,
    build_prompt,
)
from diagpriv.evaluation.prompt_v2 import (
    PROMPT_SHA256 as PROMPT_SHA256_V2,
    PROMPT_VERSION as PROMPT_VERSION_V2,
    build_prompt_v2,
)
from diagpriv.evaluation.prompt_v3 import (
    PROMPT_SHA256 as PROMPT_SHA256_V3,
    PROMPT_VERSION as PROMPT_VERSION_V3,
    build_prompt_v3,
)
from diagpriv.evaluation.providers import ModelProvider, ModelRequest
from diagpriv.evaluation.response import (
    ParsedResponse,
    parse_response,
    parse_response_v2,
    parse_response_v3,
)
from diagpriv.evaluation.scoring import score_response
from diagpriv.evaluation.scoring_v2 import SCORER_VERSION as SCORER_VERSION_V2
from diagpriv.evaluation.scoring_v2 import score_response_v2
from diagpriv.evaluation.scoring_v3 import SCORER_VERSION as SCORER_VERSION_V3
from diagpriv.evaluation.scoring_v3 import score_response_v3
from diagpriv.evaluation.taxonomy_v2 import TAXONOMY_VERSION as TAXONOMY_VERSION_V2
from diagpriv.evaluation.taxonomy_v3 import TAXONOMY_VERSION as TAXONOMY_VERSION_V3
from diagpriv.transformations import (
    format_preserving_incident,
    hmac_incident,
    hmac_key_fingerprint,
    redact_incident,
    relative_time_incident,
    tokenize_incident,
)
from diagpriv.transformations.provenance import (
    transformation_configuration_for_condition,
)

SCORER_VERSION_V1 = "raw-rca-scorer-v1"
TAXONOMY_VERSION_V1 = "rca-taxonomy-v1"

_INCIDENT_003_V2_DESTRUCTIVE_CONDITIONS = {
    "temporal-ablation-v1",
    "redaction-v1",
    "hmac-v1",
    "tokenization-v1",
    "format-preserving-v1",
}


class ProtectedSeedError(ValueError):
    """Raised when a run would consume a protected or unassigned seed."""


@dataclass(frozen=True, slots=True)
class RawRunConfig:
    experiment_id: str
    seed: int
    model: str
    model_version: str | None
    incident_family: str = INCIDENT_001_FAMILY
    manifest_schema_version: str = "raw-rca-manifest-v5"
    reasoning_effort: str | None = None
    condition: Literal[
        "raw",
        "redaction-v1",
        "hmac-v1",
        "tokenization-v1",
        "format-preserving-v1",
        "relative-time-v1",
        "temporal-ablation-v1",
    ] = "raw"
    decoding_settings: dict[str, float | int | str | bool | None] = field(
        default_factory=lambda: {"temperature": 0.0}
    )
    intended_temperature: float | None = None
    temperature_omission_reason: str | None = None
    prompt_version: str = PROMPT_VERSION_V1
    allow_held_out: bool = False
    timestamp: str | None = None
    hmac_key: bytes | None = field(default=None, repr=False, compare=False)
    transformation_key_id: str | None = None
    expected_model_input_sha256: str | None = None
    expected_evidence_requirement_set_sha256: str | None = None
    expected_incident_generator_version: str | None = None
    expected_incident_protocol_version: str | None = None
    expected_evidence_support_version: str | None = None
    expected_transformation_key_fingerprint: str | None = None
    expected_transformation_configuration_sha256: str | None = None
    trial_index: int | None = None
    recovery_provenance: RecoveryProvenance | None = None
    query_role: Literal["target", "temporal_twin"] | None = None
    case_id: str | None = None
    expected_paired_query_protocol_version: str | None = None
    expected_anchor_allocation_version: str | None = None
    expected_evidence_requirement_version: str | None = None
    expected_semantic_evaluator_version: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedModelInput:
    """Exact provider input and non-secret provenance prepared without a call."""

    split: str
    incident: Incident
    model_view: ModelView
    prompt: str
    prompt_sha256: str
    taxonomy_version: str
    scorer_version: str
    model_input_sha256: str
    evidence_rubric: EvidenceRubricV3 | None
    evidence_semantic_evaluator: EvidenceSemanticEvaluatorV4 | None
    evidence_requirement_set_sha256: str | None
    incident_generator_version: str
    incident_protocol_version: str
    evidence_support_version: str | None
    transformation_key_fingerprint: str | None
    transformation_provenance: TransformationProvenance | None
    query_role: Literal["target", "temporal_twin"] | None
    case_id: str | None
    paired_query_protocol_version: str | None
    anchor_allocation_version: str | None
    evidence_requirement_version: str | None
    semantic_evaluator_version: str | None


def pilot_seed_plan(
    development_count: int = 5, validation_count: int = 0
) -> tuple[int, ...]:
    """Return a bounded pilot plan containing no held-out evaluation seeds."""
    if not 0 <= development_count <= len(DEVELOPMENT_SEEDS):
        raise ValueError("development_count is outside the development seed range")
    if not 0 <= validation_count <= len(VALIDATION_SEEDS):
        raise ValueError("validation_count is outside the validation seed range")
    development = tuple(DEVELOPMENT_SEEDS[:development_count])
    validation = tuple(VALIDATION_SEEDS[:validation_count])
    return development + validation


def run_raw_experiment(
    config: RawRunConfig,
    provider: ModelProvider,
    *,
    result_path: Path | None = None,
) -> ExperimentManifest:
    """Generate, prompt, invoke, parse, score, and optionally append one run."""
    if config.manifest_schema_version in {"raw-rca-manifest-v7", "raw-rca-manifest-v8"}:
        if (
            isinstance(config.trial_index, bool)
            or not isinstance(config.trial_index, int)
            or config.trial_index < 1
        ):
            if config.manifest_schema_version == "raw-rca-manifest-v8":
                raise ValueError("Manifest schema v8 requires a positive trial_index")
            raise ValueError("Manifest schema v7 requires a positive trial_index")
    elif config.trial_index is not None:
        raise ValueError("trial_index is valid only in manifest schema v7")
    validate_recovery_identity(
        config.manifest_schema_version,
        config.trial_index,
        config.seed,
        config.condition,
        config.recovery_provenance,
    )
    prepared = prepare_model_input(config)
    response_parser = {
        PROMPT_VERSION_V1: parse_response,
        PROMPT_VERSION_V2: parse_response_v2,
        PROMPT_VERSION_V3: parse_response_v3,
    }[config.prompt_version]
    invocation = provider.invoke(
        ModelRequest(
            prompt=prepared.prompt,
            model=config.model,
            model_version=config.model_version,
            decoding_settings=dict(config.decoding_settings),
            reasoning_effort=config.reasoning_effort,
        )
    )
    if invocation.status in {"provider_error", "rate_limited", "refusal"}:
        parsed = ParsedResponse(
            invocation.status,
            invocation.raw_output,
            error=invocation.error or "Unspecified provider error",
        )
    else:
        parsed = response_parser(invocation.raw_output)
    if parsed.response is None:
        score = None
    elif config.prompt_version == PROMPT_VERSION_V2:
        score = score_response_v2(prepared.incident, parsed.response)
    elif config.prompt_version == PROMPT_VERSION_V3:
        if prepared.evidence_rubric is None:
            raise ValueError("raw-rca-v3 requires a preregistered evidence rubric")
        score = score_response_v3(
            prepared.incident,
            parsed.response,
            prepared.evidence_rubric,
            evidence_support_version=prepared.evidence_support_version
            or EVIDENCE_SUPPORT_VERSION_V3,
            model_view=prepared.model_view,
            semantic_evaluator=prepared.evidence_semantic_evaluator,
        )
    else:
        score = score_response(prepared.incident, parsed.response)

    manifest = ExperimentManifest(
        manifest_schema_version=config.manifest_schema_version,
        experiment_id=config.experiment_id,
        benchmark_version=str(prepared.incident.metadata["benchmark_version"]),
        incident_family=config.incident_family,
        seed=config.seed,
        split=prepared.split,
        condition=config.condition,
        requested_model=config.model,
        provider_returned_model=invocation.provider_returned_model,
        model_version_metadata=config.model_version,
        reasoning_effort=config.reasoning_effort,
        temperature=_temperature(config.decoding_settings.get("temperature")),
        intended_temperature=config.intended_temperature,
        temperature_omission_reason=config.temperature_omission_reason,
        prompt_version=config.prompt_version,
        prompt_sha256=prepared.prompt_sha256,
        taxonomy_version=prepared.taxonomy_version,
        scorer_version=prepared.scorer_version,
        transformation_key_id=config.transformation_key_id,
        transformation_key_fingerprint=(
            prepared.transformation_key_fingerprint
        ),
        decoding_settings=dict(config.decoding_settings),
        timestamp=config.timestamp or datetime.now(UTC).isoformat(),
        response_id=invocation.response_id,
        provider_timestamp=invocation.provider_timestamp,
        input_token_count=invocation.input_token_count,
        cached_input_token_count=invocation.cached_input_token_count,
        cache_write_input_token_count=invocation.cache_write_input_token_count,
        output_token_count=invocation.output_token_count,
        reasoning_token_count=invocation.reasoning_token_count,
        total_token_count=invocation.total_token_count,
        provider_response_status=invocation.response_status,
        provider_service_tier=invocation.service_tier,
        sanitized_api_error=invocation.sanitized_api_error,
        response=parsed,
        score=score,
        model_input_sha256=(
            prepared.model_input_sha256
            if config.manifest_schema_version
            in {
                "raw-rca-manifest-v6",
                "raw-rca-manifest-v7",
                "raw-rca-manifest-v8",
                "raw-rca-manifest-v9",
                "raw-rca-manifest-v10",
                "raw-rca-manifest-v11",
            }
            else None
        ),
        trial_index=config.trial_index,
        recovery_provenance=config.recovery_provenance,
        evidence_support_version=(
            prepared.evidence_support_version
            if config.manifest_schema_version
            in {"raw-rca-manifest-v9", "raw-rca-manifest-v10", "raw-rca-manifest-v11"}
            else None
        ),
        incident_generator_version=(
            prepared.incident_generator_version
            if config.manifest_schema_version
            in {"raw-rca-manifest-v9", "raw-rca-manifest-v10", "raw-rca-manifest-v11"}
            else None
        ),
        incident_protocol_version=(
            prepared.incident_protocol_version
            if config.manifest_schema_version
            in {"raw-rca-manifest-v9", "raw-rca-manifest-v10", "raw-rca-manifest-v11"}
            else None
        ),
        evidence_requirement_set_sha256=(
            prepared.evidence_requirement_set_sha256
            if config.manifest_schema_version
            in {"raw-rca-manifest-v9", "raw-rca-manifest-v10", "raw-rca-manifest-v11"}
            else None
        ),
        transformation_provenance=prepared.transformation_provenance,
        construction_seed=(
            config.seed
            if config.manifest_schema_version == "raw-rca-manifest-v11"
            else None
        ),
        query_role=(
            prepared.query_role
            if config.manifest_schema_version == "raw-rca-manifest-v11"
            else None
        ),
        case_id=(
            prepared.case_id
            if config.manifest_schema_version == "raw-rca-manifest-v11"
            else None
        ),
        paired_query_protocol_version=(
            prepared.paired_query_protocol_version
            if config.manifest_schema_version == "raw-rca-manifest-v11"
            else None
        ),
        anchor_allocation_version=(
            prepared.anchor_allocation_version
            if config.manifest_schema_version == "raw-rca-manifest-v11"
            else None
        ),
        evidence_requirement_version=(
            prepared.evidence_requirement_version
            if config.manifest_schema_version == "raw-rca-manifest-v11"
            else None
        ),
        semantic_evaluator_version=(
            prepared.semantic_evaluator_version
            if config.manifest_schema_version == "raw-rca-manifest-v11"
            else None
        ),
    )
    if result_path is not None:
        append_manifest(result_path, manifest)
    return manifest


def prepare_model_input(config: RawRunConfig) -> PreparedModelInput:
    """Construct and verify the exact model-visible input without invoking a model."""
    split = evaluation_seed_split(config.incident_family, config.seed)
    if split == "evaluation" and not config.allow_held_out:
        raise ProtectedSeedError(
            "Held-out evaluation seeds require allow_held_out=True explicitly"
        )
    if split == "retired":
        raise ProtectedSeedError("Retired evaluation seeds may not be invoked")
    if split == "unassigned":
        raise ProtectedSeedError("Unassigned seeds are not permitted by the protocol")
    if (
        config.incident_family == INCIDENT_002_FAMILY
        and config.seed not in INCIDENT_002_DEVELOPMENT_SEEDS
    ):
        raise ProtectedSeedError(
            "Incident 002 evaluation is restricted to its frozen development seeds"
        )
    if (
        config.incident_family == INCIDENT_003_FAMILY
        and config.seed not in INCIDENT_003_DEVELOPMENT_SEEDS
    ):
        raise ProtectedSeedError(
            "Incident 003 evaluation is restricted to its frozen development seeds"
        )
    if (
        config.incident_family == INCIDENT_003_V2_FAMILY
        and config.seed not in INCIDENT_003_V2_DEVELOPMENT_SEEDS
    ):
        raise ProtectedSeedError(
            "Incident 003 v2 evaluation is restricted to its frozen development seeds"
        )
    if config.incident_family == INCIDENT_003_V3_FAMILY:
        if config.seed not in INCIDENT_003_V3_QUALIFICATION_SEEDS:
            raise ProtectedSeedError(
                "Incident 003 v3 evaluation is restricted to the frozen "
                "qualification seeds"
            )
        if config.manifest_schema_version != "raw-rca-manifest-v11":
            raise ValueError("Incident 003 v3 paired evaluation requires manifest v11")
        if config.query_role not in INCIDENT_003_V3_QUERY_ROLES:
            raise ValueError("Incident 003 v3 requires an explicit query role")
        expected_case_id = incident_003_v3_case_id(config.seed, config.query_role)
        if config.case_id != expected_case_id:
            raise ValueError("Incident 003 v3 case ID does not match seed and role")
    elif config.query_role is not None or config.case_id is not None:
        raise ValueError("Paired query identity is valid only for Incident 003 v3")

    if (
        config.prompt_version == PROMPT_VERSION_V3
        and config.incident_family
        not in {INCIDENT_003_V2_FAMILY, INCIDENT_003_V3_FAMILY}
    ):
        raise ValueError("raw-rca-v3 currently requires Incident 003 v2 or v3")
    if (
        config.incident_family in {INCIDENT_003_V2_FAMILY, INCIDENT_003_V3_FAMILY}
        and config.prompt_version != PROMPT_VERSION_V3
    ):
        raise ValueError("Incident 003 v2 and v3 require raw-rca-v3")
    if config.prompt_version == PROMPT_VERSION_V3 and (
        config.expected_evidence_requirement_set_sha256 is None
        or config.expected_incident_generator_version is None
        or config.expected_incident_protocol_version is None
        or config.expected_evidence_support_version is None
    ):
        raise ValueError(
            "raw-rca-v3 requires frozen rubric and incident-version provenance"
        )
    if config.incident_family == INCIDENT_003_V2_FAMILY:
        expected_evidence_version = (
            EVIDENCE_SUPPORT_VERSION_V4
            if config.condition in _INCIDENT_003_V2_DESTRUCTIVE_CONDITIONS
            else EVIDENCE_SUPPORT_VERSION_V3
        )
        if config.expected_evidence_support_version != expected_evidence_version:
            raise ValueError(
                f"Incident 003 v2 {config.condition} requires "
                f"{expected_evidence_version}"
            )
    if config.incident_family == INCIDENT_003_V3_FAMILY:
        if config.expected_evidence_support_version != EVIDENCE_SUPPORT_VERSION_V4:
            raise ValueError("Incident 003 v3 requires evidence-support-v4")
        expected_paired_versions = {
            "paired_query_protocol_version": "incident-003-v3-paired-query-v1",
            "anchor_allocation_version": INCIDENT_003_V3_ANCHOR_ALLOCATION_VERSION,
            "evidence_requirement_version": INCIDENT_003_V3_REQUIREMENT_VERSION,
            "semantic_evaluator_version": (
                INCIDENT_003_V3_SEMANTIC_EVALUATOR_VERSION
            ),
        }
        actual_paired_versions = {
            "paired_query_protocol_version": (
                config.expected_paired_query_protocol_version
            ),
            "anchor_allocation_version": config.expected_anchor_allocation_version,
            "evidence_requirement_version": (
                config.expected_evidence_requirement_version
            ),
            "semantic_evaluator_version": (
                config.expected_semantic_evaluator_version
            ),
        }
        if actual_paired_versions != expected_paired_versions:
            raise ValueError(
                "Incident 003 v3 paired/evidence dispatch provenance mismatch"
            )

    transformation_provenance = _prepare_transformation_provenance(config)

    if config.prompt_version == PROMPT_VERSION_V1:
        prompt_builder = build_prompt
        prompt_sha256 = PROMPT_SHA256_V1
        taxonomy_version = TAXONOMY_VERSION_V1
        scorer_version = SCORER_VERSION_V1
    elif config.prompt_version == PROMPT_VERSION_V2:
        prompt_builder = build_prompt_v2
        prompt_sha256 = PROMPT_SHA256_V2
        taxonomy_version = TAXONOMY_VERSION_V2
        scorer_version = SCORER_VERSION_V2
    elif config.prompt_version == PROMPT_VERSION_V3:
        prompt_builder = build_prompt_v3
        prompt_sha256 = PROMPT_SHA256_V3
        taxonomy_version = TAXONOMY_VERSION_V3
        scorer_version = SCORER_VERSION_V3
    else:
        raise ValueError(f"Unsupported raw RCA prompt version: {config.prompt_version}")

    incident = generate_evaluation_incident(
        config.incident_family,
        config.seed,
        query_role=config.query_role,
    )
    # These fields are mandatory for the v9/v3 protocol, but older incident
    # families and historical manifest schemas never promised them.  Keep the
    # legacy preparation path tolerant while the v3 checks below fail closed.
    incident_generator_version = str(incident.metadata.get("generator_version", ""))
    incident_protocol_version = str(incident.metadata.get("protocol_version", ""))
    if (
        config.expected_incident_generator_version is not None
        and incident_generator_version != config.expected_incident_generator_version
    ):
        raise ValueError("Incident generator version differs from frozen provenance")
    if (
        config.expected_incident_protocol_version is not None
        and incident_protocol_version != config.expected_incident_protocol_version
    ):
        raise ValueError("Incident protocol version differs from frozen provenance")
    paired_query_protocol_version: str | None = None
    anchor_allocation_version: str | None = None
    evidence_requirement_version: str | None = None
    semantic_evaluator_version: str | None = None
    if config.incident_family == INCIDENT_003_V3_FAMILY:
        paired_query_protocol_version = str(incident.metadata["query_case_version"])
        anchor_allocation_version = str(
            incident.metadata["anchor_allocation_version"]
        )
        evidence_requirement_version = INCIDENT_003_V3_REQUIREMENT_VERSION
        semantic_evaluator_version = INCIDENT_003_V3_SEMANTIC_EVALUATOR_VERSION
        if (
            paired_query_protocol_version
            != config.expected_paired_query_protocol_version
            or anchor_allocation_version
            != config.expected_anchor_allocation_version
        ):
            raise ValueError(
                "Generated paired-query provenance differs from frozen protocol"
            )
    transformation_key_fingerprint: str | None = None
    if config.condition == "raw":
        model_view = incident.model_view()
    elif config.condition == "redaction-v1":
        model_view = redact_incident(incident)
    elif config.condition == "hmac-v1":
        if config.hmac_key is None:
            raise ValueError("hmac-v1 requires an external HMAC key")
        if not config.transformation_key_id:
            raise ValueError("hmac-v1 requires a non-secret experimental key ID")
        transformation_key_fingerprint = hmac_key_fingerprint(config.hmac_key)
        model_view = hmac_incident(incident, key=config.hmac_key)
    elif config.condition == "tokenization-v1":
        model_view = tokenize_incident(incident)
    elif config.condition == "format-preserving-v1":
        model_view = format_preserving_incident(incident)
    elif config.condition == "relative-time-v1":
        if config.incident_family not in {
            INCIDENT_003_V2_FAMILY,
            INCIDENT_003_V3_FAMILY,
        }:
            raise ValueError("relative-time-v1 currently supports Incident 003 only")
        model_view = relative_time_incident(incident)
    elif config.condition == "temporal-ablation-v1":
        if config.incident_family not in {
            INCIDENT_003_V2_FAMILY,
            INCIDENT_003_V3_FAMILY,
        }:
            raise ValueError(
                "temporal-ablation-v1 currently supports Incident 003 only"
            )
        model_view = temporally_ablated_model_view(incident)
    else:
        raise ValueError(f"Unsupported evaluation condition: {config.condition}")

    if (
        config.expected_transformation_key_fingerprint is not None
        and transformation_key_fingerprint
        != config.expected_transformation_key_fingerprint
    ):
        raise ValueError(
            "HMAC key fingerprint differs from frozen input provenance"
        )

    prompt = prompt_builder(model_view)
    model_input_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    evidence_rubric: EvidenceRubricV3 | None = None
    evidence_semantic_evaluator: EvidenceSemanticEvaluatorV4 | None = None
    evidence_requirement_set_sha256: str | None = None
    evidence_support_version: str | None = None
    if config.prompt_version == PROMPT_VERSION_V3:
        evidence_rubric = build_evidence_rubric_v3(incident)
        validate_evidence_rubric_v3(model_view, evidence_rubric)
        expected_incident_evidence_lineage = (
            EVIDENCE_SUPPORT_VERSION_V4
            if config.incident_family == INCIDENT_003_V3_FAMILY
            else EVIDENCE_SUPPORT_VERSION_V3
        )
        if incident.metadata.get("evidence_support_version") != (
            expected_incident_evidence_lineage
        ):
            raise ValueError(
                "Incident evidence rubric lineage differs from frozen provenance"
            )
        evidence_support_version = config.expected_evidence_support_version
        if evidence_support_version not in {
            EVIDENCE_SUPPORT_VERSION_V3,
            EVIDENCE_SUPPORT_VERSION_V4,
        }:
            raise ValueError("Unsupported evidence protocol version")
        if evidence_support_version == EVIDENCE_SUPPORT_VERSION_V4:
            temporal_semantics_version = (
                transformation_provenance.temporal_semantics_version
                if transformation_provenance is not None
                else str(incident.metadata["temporal_semantics_version"])
            )
            evidence_semantic_evaluator = build_evidence_semantic_evaluator_v4(
                incident, temporal_semantics_version
            )
            if (
                config.expected_semantic_evaluator_version is not None
                and evidence_semantic_evaluator.version
                != config.expected_semantic_evaluator_version
            ):
                raise ValueError(
                    "Evidence semantic evaluator differs from frozen provenance"
                )
        evidence_requirement_set_sha256 = evidence_requirement_set_sha256_v3(
            evidence_rubric
        )
    if (
        config.expected_model_input_sha256 is not None
        and model_input_sha256 != config.expected_model_input_sha256
    ):
        raise ValueError(
            f"Prepared model input differs from frozen provenance for seed "
            f"{config.seed}"
        )
    if (
        config.expected_evidence_requirement_set_sha256 is not None
        and evidence_requirement_set_sha256
        != config.expected_evidence_requirement_set_sha256
    ):
        raise ValueError(
            "Prepared evidence requirement set differs from frozen provenance "
            f"for seed {config.seed}"
        )
    return PreparedModelInput(
        split=split,
        incident=incident,
        model_view=model_view,
        prompt=prompt,
        prompt_sha256=prompt_sha256,
        taxonomy_version=taxonomy_version,
        scorer_version=scorer_version,
        transformation_key_fingerprint=transformation_key_fingerprint,
        model_input_sha256=model_input_sha256,
        evidence_rubric=evidence_rubric,
        evidence_semantic_evaluator=evidence_semantic_evaluator,
        evidence_requirement_set_sha256=evidence_requirement_set_sha256,
        incident_generator_version=incident_generator_version,
        incident_protocol_version=incident_protocol_version,
        evidence_support_version=evidence_support_version,
        transformation_provenance=transformation_provenance,
        query_role=config.query_role,
        case_id=config.case_id,
        paired_query_protocol_version=paired_query_protocol_version,
        anchor_allocation_version=anchor_allocation_version,
        evidence_requirement_version=evidence_requirement_version,
        semantic_evaluator_version=semantic_evaluator_version,
    )


def _prepare_transformation_provenance(
    config: RawRunConfig,
) -> TransformationProvenance | None:
    if config.manifest_schema_version not in {
        "raw-rca-manifest-v10",
        "raw-rca-manifest-v11",
    }:
        if config.expected_transformation_configuration_sha256 is not None:
            raise ValueError(
                "Transformation configuration SHA-256 requires manifest schema v10"
            )
        if config.condition in {"relative-time-v1", "temporal-ablation-v1"}:
            raise ValueError(
                f"{config.condition} observations require manifest schema v10"
            )
        return None
    if config.expected_transformation_configuration_sha256 is None:
        raise ValueError(
            "Manifest schema v10 requires a preregistered transformation "
            "configuration SHA-256"
        )
    configuration = transformation_configuration_for_condition(config.condition)
    return TransformationProvenance.from_configuration(
        configuration,
        expected_sha256=config.expected_transformation_configuration_sha256,
    )


def _temperature(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)
