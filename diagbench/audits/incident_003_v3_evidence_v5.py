"""Offline construction audit for candidate Incident 003 evidence-support-v5."""

from __future__ import annotations

from typing import Iterable

from diagbench.audits.incident_003 import temporally_ablated_model_view
from diagbench.generators.incident_003_v3 import AUDIT_SEEDS, generate_incident_003_v3
from diagbench.relative_time import RELATIVE_TIME_SEMANTICS_VERSION
from diagbench.schema.models import JSONValue
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION
from diagpriv.evaluation.evidence_support_v5 import score_evidence_support_v5
from diagpriv.evaluation.incident_003_v3_evidence_v5 import (
    build_incident_003_v3_evidence_rubric_v5,
)
from diagpriv.evaluation.incident_003_v3_evidence_v5_semantics import (
    Incident003V3EvidenceSemanticEvaluatorV5,
)
from diagpriv.transformations.provenance import TEMPORAL_SEMANTICS_UNAVAILABLE
from diagpriv.transformations.relative_time_v1 import relative_time_incident

AUDIT_VERSION = "incident-003-v3-evidence-v5-construction-audit-v1"


def audit_incident_003_v3_evidence_v5_range(
    seeds: Iterable[int] = AUDIT_SEEDS,
) -> dict[str, JSONValue]:
    """Audit generic v5 paths without model responses or protected seeds."""
    seed_values = tuple(seeds)
    if not seed_values or any(seed not in set(AUDIT_SEEDS) for seed in seed_values):
        raise ValueError("Evidence v5 audit is restricted to seeds 1200-1399")

    role_reports: dict[str, dict[str, int]] = {
        role: {
            "raw_structured_supported": 0,
            "raw_logs_supported": 0,
            "relative_structured_supported": 0,
            "relative_logs_supported": 0,
            "ablation_structured_rejected": 0,
            "ablation_logs_rejected": 0,
            "wrong_role_rejected": 0,
            "safe_control_rejected": 0,
        }
        for role in ("target", "temporal_twin")
    }
    failures: list[str] = []

    for seed in seed_values:
        incidents = {
            role: generate_incident_003_v3(seed, role)  # type: ignore[arg-type]
            for role in ("target", "temporal_twin")
        }
        for role, incident in incidents.items():
            rubric = build_incident_003_v3_evidence_rubric_v5(incident)
            raw = incident.model_view()
            relative = relative_time_incident(incident)
            ablated = temporally_ablated_model_view(incident)
            structured = _complete_essential_citations(rubric, "structured")
            logs = _complete_essential_citations(rubric, "logs")
            checks = {
                "raw_structured_supported": _supported(
                    structured, raw, rubric, TEMPORAL_SEMANTICS_VERSION
                ),
                "raw_logs_supported": _supported(
                    logs, raw, rubric, TEMPORAL_SEMANTICS_VERSION
                ),
                "relative_structured_supported": _supported(
                    structured, relative, rubric, RELATIVE_TIME_SEMANTICS_VERSION
                ),
                "relative_logs_supported": _supported(
                    logs, relative, rubric, RELATIVE_TIME_SEMANTICS_VERSION
                ),
                "ablation_structured_rejected": not _supported(
                    structured, ablated, rubric, TEMPORAL_SEMANTICS_UNAVAILABLE
                ),
                "ablation_logs_rejected": not _supported(
                    logs, ablated, rubric, TEMPORAL_SEMANTICS_UNAVAILABLE
                ),
            }
            other_role = "temporal_twin" if role == "target" else "target"
            other_rubric = build_incident_003_v3_evidence_rubric_v5(
                incidents[other_role]
            )
            wrong_role_ids = _complete_essential_citations(other_rubric, "logs")
            safe_binding = next(
                binding
                for binding in rubric.subject_bindings
                if binding.binding_id == "safe-control"
            )
            checks["wrong_role_rejected"] = not _supported(
                wrong_role_ids, raw, rubric, TEMPORAL_SEMANTICS_VERSION
            )
            checks["safe_control_rejected"] = not _supported(
                safe_binding.evidence_ids, raw, rubric, TEMPORAL_SEMANTICS_VERSION
            )
            for name, passed in checks.items():
                role_reports[role][name] += int(passed)
                if not passed:
                    failures.append(f"{seed}:{role}:{name}")

    sample_size = len(seed_values)
    return {
        "audit_version": AUDIT_VERSION,
        "sample_size": sample_size,
        "case_count": sample_size * 2,
        "roles": role_reports,
        "failures": failures,
        "passed": not failures,
        "provider_calls": 0,
    }


def _complete_essential_citations(rubric, modality: str) -> tuple[str, ...]:
    result: list[str] = []
    for requirement in rubric.requirements:
        if requirement.kind != "essential":
            continue
        path = next(
            candidate
            for candidate in requirement.acceptable_paths
            if dict(candidate.semantic_parameters)["modality"] == modality
        )
        result.extend(path.evidence_ids)
    return tuple(dict.fromkeys(result))


def _supported(citations, view, rubric, semantics: str) -> bool:
    return score_evidence_support_v5(
        tuple(citations),
        view,
        rubric,
        Incident003V3EvidenceSemanticEvaluatorV5(semantics),
    ).evidence_supported
