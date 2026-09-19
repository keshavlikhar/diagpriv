"""Prospective, coverage-aware reporting for Incident 003 v3 Stage 2 only."""

from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
from typing import Iterable

from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.pricing import PricingSnapshot
from diagpriv.evaluation.scoring_v3 import RCAScoreV3

REPORT_VERSION = "incident-003-v3-stage2-evidence-v5-report-v1"
_MECHANISM_CONCURRENCY = "incorrect_concurrency_control"
_MECHANISM_STATE = "incorrect_state_transition"


def summarize_stage2_v5(
    definition: PilotDefinition,
    manifests: Iterable[ExperimentManifest],
    *,
    pricing: PricingSnapshot | None = None,
    result_sha256: str | None = None,
) -> dict[str, object]:
    """Keep unattempted, invalid, and incorrect observations distinct."""
    if (
        definition.manifest_schema_version != "raw-rca-manifest-v12"
        or definition.condition != "relative-time-v1"
        or definition.expected_evidence_support_version != "evidence-support-v5"
    ):
        raise ValueError("Stage-2 v5 reporting requires the prospective v12 config")
    planned = definition.paired_case_plan()
    by_case: dict[str, ExperimentManifest] = {}
    expected_ids = {case_id for _, _, case_id in planned}
    for manifest in manifests:
        if (
            manifest.manifest_schema_version != "raw-rca-manifest-v12"
            or manifest.case_id not in expected_ids
            or manifest.experiment_id
            != f"{definition.pilot_id}-development-{manifest.case_id}-call-1"
            or manifest.condition != definition.condition
            or manifest.evidence_support_version != "evidence-support-v5"
            or manifest.model_input_sha256
            != definition.expected_model_input_sha256_by_case_id[manifest.case_id]
            or manifest.evidence_requirement_set_sha256
            != definition.expected_evidence_requirement_set_sha256_by_case_id[manifest.case_id]
        ):
            raise ValueError("Observation does not belong to frozen Stage-2 v5 protocol")
        if manifest.case_id in by_case:
            raise ValueError(f"Duplicate Stage-2 case: {manifest.case_id}")
        by_case[manifest.case_id] = manifest

    valid = [
        item for item in by_case.values()
        if item.response.status == "valid" and isinstance(item.score, RCAScoreV3)
    ]
    scores = [item.score for item in valid]
    statuses = Counter(item.response.status for item in by_case.values())

    def count(field: str) -> int:
        return sum(bool(getattr(score, field)) for score in scores)

    def average(field: str) -> float | None:
        return sum(float(getattr(score, field)) for score in scores) / len(scores) if scores else None

    roles: dict[str, dict[str, object]] = {}
    for role in definition.query_roles:
        role_valid = [item for item in valid if item.query_role == role]
        roles[role] = {
            "planned": len(definition.development_seeds),
            "observed_denominator": len(role_valid),
            "valid_coverage": len(role_valid) / len(definition.development_seeds),
            "exact_correct": sum(bool(item.score.exact_root_cause_correct) for item in role_valid),
            "mechanism_correct": sum(bool(item.score.failure_mechanism_correct) for item in role_valid),
        }

    pair_patterns: dict[str, str] = {}
    pair_unavailability: dict[str, dict[str, str]] = {}
    pair_exact = pair_mechanism = observed_pairs = 0
    for seed in definition.development_seeds:
        target = by_case.get(f"{seed}:target")
        twin = by_case.get(f"{seed}:temporal_twin")
        if (
            target is None or twin is None
            or target.response.status != "valid" or twin.response.status != "valid"
            or not isinstance(target.score, RCAScoreV3)
            or not isinstance(twin.score, RCAScoreV3)
        ):
            pair_patterns[str(seed)] = "unavailable"
            pair_unavailability[str(seed)] = {
                "target": "unattempted" if target is None else target.response.status,
                "temporal_twin": "unattempted" if twin is None else twin.response.status,
            }
            continue
        observed_pairs += 1
        pair_exact += int(target.score.exact_root_cause_correct and twin.score.exact_root_cause_correct)
        pair_mechanism += int(
            target.score.failure_mechanism_correct
            and twin.score.failure_mechanism_correct
        )
        target_label = target.response.response.failure_mechanism
        twin_label = twin.response.response.failure_mechanism
        if (target_label, twin_label) == (_MECHANISM_CONCURRENCY, _MECHANISM_STATE):
            pair_patterns[str(seed)] = "correct_mechanism_flip"
        elif target_label == twin_label == _MECHANISM_CONCURRENCY:
            pair_patterns[str(seed)] = "both_concurrency"
        elif target_label == twin_label == _MECHANISM_STATE:
            pair_patterns[str(seed)] = "both_state_transition"
        elif (target_label, twin_label) == (_MECHANISM_STATE, _MECHANISM_CONCURRENCY):
            pair_patterns[str(seed)] = "reversed_mechanism_flip"
        else:
            pair_patterns[str(seed)] = "one_or_both_other_valid_mechanism_labels"

    evidence_by_case = {
        case_id: {
            "evidence_supported": manifest.score.evidence_supported,
            "essential_requirement_coverage": manifest.score.essential_requirement_coverage,
            "contrast_requirement_coverage": manifest.score.contrast_requirement_coverage,
            "supportive_requirement_coverage": manifest.score.supportive_requirement_coverage,
            "useful_citation_precision": manifest.score.useful_citation_precision,
            "invalid_citation_count": manifest.score.invalid_citation_count,
            "wrong_subject_citation_count": manifest.score.wrong_subject_citation_count,
            "selected_evidence_paths": list(manifest.score.selected_evidence_paths),
            "missing_essential_requirements": list(manifest.score.missing_essential_requirements),
        }
        for case_id, manifest in by_case.items()
        if manifest in valid
    }
    costs = [] if pricing is None else [pricing.estimate_usd(item) for item in by_case.values()]
    return {
        "report_version": REPORT_VERSION,
        "status": "pending" if not by_case else ("complete" if len(by_case) == len(planned) else "partial"),
        "planned_cases": len(planned),
        "attempted_calls": len(by_case),
        "attempted_coverage": len(by_case) / len(planned),
        "valid_responses": len(valid),
        "observed_denominator": len(valid),
        "planned_denominator": len(planned),
        "valid_coverage": len(valid) / len(planned),
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
            "mechanism_correct": pair_mechanism,
            "exact_correct": pair_exact,
            "patterns": pair_patterns,
            "unavailability": pair_unavailability,
        },
        "evidence_v5": {
            "supported_count": count("evidence_supported"),
            "average_essential_requirement_coverage": average("essential_requirement_coverage"),
            "average_contrast_requirement_coverage": average("contrast_requirement_coverage"),
            "average_supportive_requirement_coverage": average("supportive_requirement_coverage"),
            "average_useful_citation_precision": average("useful_citation_precision"),
            "invalid_citation_count": sum(score.invalid_citation_count for score in scores),
            "wrong_subject_citation_count": sum(score.wrong_subject_citation_count for score in scores),
            "by_case": evidence_by_case,
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


def stage2_v5_result_sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
