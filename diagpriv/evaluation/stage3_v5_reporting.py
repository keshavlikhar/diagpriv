"""Coverage-aware prospective Stage-3 report; never reinterpret Stage 2."""

from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
from typing import Iterable

from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.pricing import PricingSnapshot
from diagpriv.evaluation.scoring_v3 import RCAScoreV3
from diagpriv.evaluation.stage3_v5_frozen import (
    STAGE3_MANIFEST_VERSION,
    STAGE3_TRANSFORMATION_SHA256,
)

REPORT_VERSION = "incident-003-v3-stage3-evidence-v5-report-v1"
_CONCURRENCY = "incorrect_concurrency_control"
_STATE = "incorrect_state_transition"


def summarize_stage3_v5(
    definition: PilotDefinition,
    manifests: Iterable[ExperimentManifest],
    *,
    pricing: PricingSnapshot | None = None,
    result_sha256: str | None = None,
) -> dict[str, object]:
    """Use observed denominators; unavailable is not an RCA category."""
    if (
        definition.manifest_schema_version != STAGE3_MANIFEST_VERSION
        or definition.condition != "temporal-ablation-v1"
        or definition.expected_evidence_support_version != "evidence-support-v5"
    ):
        raise ValueError("Stage-3 v5 reporting requires the prospective v13 config")
    planned = definition.paired_case_plan()
    expected_ids = {case_id for _, _, case_id in planned}
    by_case: dict[str, ExperimentManifest] = {}
    for manifest in manifests:
        case_id = manifest.case_id
        if (
            manifest.manifest_schema_version != STAGE3_MANIFEST_VERSION
            or case_id not in expected_ids
            or manifest.experiment_id
            != f"{definition.pilot_id}-development-{case_id}-call-1"
            or manifest.condition != "temporal-ablation-v1"
            or manifest.evidence_support_version != "evidence-support-v5"
            or manifest.model_input_sha256
            != definition.expected_model_input_sha256_by_case_id[case_id]
            or manifest.evidence_requirement_set_sha256
            != definition.expected_evidence_requirement_set_sha256_by_case_id[case_id]
            or manifest.transformation_provenance is None
            or manifest.transformation_provenance.transformation_configuration_sha256
            != STAGE3_TRANSFORMATION_SHA256
        ):
            raise ValueError("Observation does not belong to frozen Stage-3 v5 protocol")
        if case_id in by_case:
            raise ValueError(f"Duplicate Stage-3 case: {case_id}")
        by_case[case_id] = manifest

    valid = {
        case_id: item
        for case_id, item in by_case.items()
        if item.response.status == "valid" and isinstance(item.score, RCAScoreV3)
    }
    scores = [item.score for item in valid.values()]
    statuses = Counter(item.response.status for item in by_case.values())

    def count(field: str) -> int:
        return sum(bool(getattr(score, field)) for score in scores)

    def average(field: str) -> float | None:
        return (
            sum(float(getattr(score, field)) for score in scores) / len(scores)
            if scores else None
        )

    roles: dict[str, dict[str, object]] = {}
    for role in definition.query_roles:
        observed = [item for item in valid.values() if item.query_role == role]
        roles[role] = {
            "planned": len(definition.development_seeds),
            "observed_denominator": len(observed),
            "valid_coverage": len(observed) / len(definition.development_seeds),
            "exact_correct": sum(bool(item.score.exact_root_cause_correct) for item in observed),
            "mechanism_correct": sum(bool(item.score.failure_mechanism_correct) for item in observed),
        }

    patterns: dict[str, str] = {}
    unavailability: dict[str, dict[str, str]] = {}
    observed_pairs = paired_mechanism = paired_exact = 0
    for seed in definition.development_seeds:
        target = valid.get(f"{seed}:target")
        twin = valid.get(f"{seed}:temporal_twin")
        if target is None or twin is None:
            patterns[str(seed)] = "unavailable"
            unavailability[str(seed)] = {
                role: (
                    "unattempted"
                    if f"{seed}:{role}" not in by_case
                    else by_case[f"{seed}:{role}"].response.status
                )
                for role in ("target", "temporal_twin")
            }
            continue
        observed_pairs += 1
        paired_exact += int(
            target.score.exact_root_cause_correct
            and twin.score.exact_root_cause_correct
        )
        paired_mechanism += int(
            target.score.failure_mechanism_correct
            and twin.score.failure_mechanism_correct
        )
        labels = (
            target.response.response.failure_mechanism,
            twin.response.response.failure_mechanism,
        )
        if labels == (_CONCURRENCY, _STATE):
            patterns[str(seed)] = "correct_mechanism_flip"
        elif labels == (_CONCURRENCY, _CONCURRENCY):
            patterns[str(seed)] = "both_concurrency"
        elif labels == (_STATE, _STATE):
            patterns[str(seed)] = "both_state_transition"
        elif labels == (_STATE, _CONCURRENCY):
            patterns[str(seed)] = "reversed_mechanism_flip"
        else:
            patterns[str(seed)] = "one_or_both_other_valid_mechanism_labels"

    by_case_evidence = {
        case_id: {
            "evidence_supported": item.score.evidence_supported,
            "essential_requirement_coverage": item.score.essential_requirement_coverage,
            "contrast_requirement_coverage": item.score.contrast_requirement_coverage,
            "supportive_requirement_coverage": item.score.supportive_requirement_coverage,
            "useful_citation_precision": item.score.useful_citation_precision,
            "invalid_citation_count": item.score.invalid_citation_count,
            "wrong_subject_citation_count": item.score.wrong_subject_citation_count,
            "selected_evidence_paths": list(item.score.selected_evidence_paths),
            "missing_essential_requirements": list(item.score.missing_essential_requirements),
        }
        for case_id, item in valid.items()
    }
    costs = [] if pricing is None else [pricing.estimate_usd(item) for item in by_case.values()]
    planned_count = len(planned)
    return {
        "report_version": REPORT_VERSION,
        "status": (
            "pending" if not by_case else
            "complete" if len(by_case) == planned_count else "partial"
        ),
        "planned_cases": planned_count,
        "attempted_calls": len(by_case),
        "unattempted_calls": planned_count - len(by_case),
        "attempted_coverage": len(by_case) / planned_count,
        "valid_responses": len(valid),
        "observed_denominator": len(valid),
        "planned_denominator": planned_count,
        "valid_coverage": len(valid) / planned_count,
        "rca": {
            "exact_correct": count("exact_root_cause_correct"),
            "observed_outcome_correct": count("outcome_correct"),
            "trigger_correct": count("trigger_correct"),
            "subsequent_action_correct": count("subsequent_action_correct"),
            "failure_mechanism_correct": count("failure_mechanism_correct"),
            "affected_component_correct": count("affected_component_correct"),
        },
        "roles": roles,
        "paired": {
            "planned": len(definition.development_seeds),
            "observed_denominator": observed_pairs,
            "valid_coverage": observed_pairs / len(definition.development_seeds),
            "mechanism_correct": paired_mechanism,
            "exact_correct": paired_exact,
            "patterns": patterns,
            "unavailability": unavailability,
        },
        "evidence_v5": {
            "supported_count": count("evidence_supported"),
            "average_essential_requirement_coverage": average("essential_requirement_coverage"),
            "average_contrast_requirement_coverage": average("contrast_requirement_coverage"),
            "average_supportive_requirement_coverage": average("supportive_requirement_coverage"),
            "average_useful_citation_precision": average("useful_citation_precision"),
            "invalid_citation_count": sum(score.invalid_citation_count for score in scores),
            "wrong_subject_citation_count": sum(score.wrong_subject_citation_count for score in scores),
            "by_case": by_case_evidence,
        },
        "infrastructure": {
            "provider_failures": statuses["provider_error"],
            "rate_limits": statuses["rate_limited"],
            "refusals": statuses["refusal"],
            "parser_failures": sum(
                count for status, count in statuses.items()
                if status not in {"valid", "provider_error", "rate_limited", "refusal"}
            ),
        },
        "tokens": {
            "input": sum(item.input_token_count or 0 for item in by_case.values()),
            "output": sum(item.output_token_count or 0 for item in by_case.values()),
            "reasoning": sum(item.reasoning_token_count or 0 for item in by_case.values()),
            "reasoning_available_calls": sum(item.reasoning_token_count is not None for item in by_case.values()),
            "total": sum(item.total_token_count or 0 for item in by_case.values()),
        },
        "estimated_cost_usd": (
            sum(costs) if costs and all(cost is not None for cost in costs) else None
        ),
        "pricing_snapshot_id": None if pricing is None else pricing.pricing_snapshot_id,
        "result_artifact_sha256": result_sha256,
    }


def stage3_v5_result_sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
