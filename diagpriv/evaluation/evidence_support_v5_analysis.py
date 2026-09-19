"""Explicit, provider-free secondary v5 analysis of the frozen Stage-1 artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from diagbench.generators.incident_003_v3 import generate_incident_003_v3
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION
from diagpriv.evaluation.evidence_support_v5 import score_evidence_support_v5
from diagpriv.evaluation.incident_003_v3_evidence_v5 import (
    build_incident_003_v3_evidence_rubric_v5,
)
from diagpriv.evaluation.incident_003_v3_evidence_v5_semantics import (
    Incident003V3EvidenceSemanticEvaluatorV5,
)
from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.response import RCAResponseV3
from diagpriv.evaluation.scoring_v3 import RCAScoreV3

FROZEN_STAGE1_SHA256 = (
    "b5b567e5966047bc075cdfa2287b13a700e83eb870f2366ee0291dac595505a2"
)
ANALYSIS_VERSION = "incident-003-v3-stage1-evidence-v5-secondary-analysis-v1"


def analyze_frozen_stage1_v5(path: Path) -> dict[str, Any]:
    """Rescore citations under v5 without mutating v4 records or RCA labels."""
    original = path.read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    if digest != FROZEN_STAGE1_SHA256:
        raise ValueError("Frozen Stage-1 artifact SHA-256 mismatch")

    cases: list[dict[str, Any]] = []
    for line in original.decode("utf-8").splitlines():
        manifest = ExperimentManifest.from_json(line)
        if manifest.evidence_support_version != "evidence-support-v4":
            raise ValueError("Stage-1 secondary analysis requires frozen v4 records")
        if not isinstance(manifest.response.response, RCAResponseV3):
            raise ValueError("Stage-1 secondary analysis requires valid RCA-v3 responses")
        if not isinstance(manifest.score, RCAScoreV3):
            raise ValueError("Stage-1 secondary analysis requires frozen v3 scores")
        if manifest.query_role not in {"target", "temporal_twin"}:
            raise ValueError("Stage-1 record is missing a supported query role")
        incident = generate_incident_003_v3(
            manifest.seed, manifest.query_role
        )
        rubric = build_incident_003_v3_evidence_rubric_v5(incident)
        v5 = score_evidence_support_v5(
            manifest.response.response.supporting_evidence,
            incident.model_view(),
            rubric,
            Incident003V3EvidenceSemanticEvaluatorV5(
                TEMPORAL_SEMANTICS_VERSION
            ),
        )
        v4 = manifest.score
        cases.append(
            {
                "case_id": manifest.case_id,
                "seed": manifest.seed,
                "query_role": manifest.query_role,
                "frozen_rca_exact": v4.exact_root_cause_correct,
                "frozen_failure_mechanism_correct": (
                    v4.failure_mechanism_correct
                ),
                "v4": {
                    "evidence_supported": v4.evidence_supported,
                    "essential_requirement_coverage": (
                        v4.essential_requirement_coverage
                    ),
                    "useful_citation_precision": v4.useful_citation_precision,
                    "selected_evidence_paths": list(v4.selected_evidence_paths),
                    "missing_essential_requirements": list(
                        v4.missing_essential_requirements
                    ),
                },
                "v5": {
                    "evidence_supported": v5.evidence_supported,
                    "essential_requirement_coverage": (
                        v5.essential_requirement_coverage
                    ),
                    "useful_citation_precision": v5.useful_citation_precision,
                    "selected_evidence_paths": list(v5.selected_evidence_paths),
                    "missing_essential_requirements": list(
                        v5.missing_essential_requirements
                    ),
                    "wrong_subject_citation_count": (
                        v5.wrong_subject_citation_count
                    ),
                    "invalid_citation_count": v5.invalid_citation_count,
                },
            }
        )

    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Frozen Stage-1 artifact changed during v5 analysis")
    return {
        "analysis_version": ANALYSIS_VERSION,
        "source_artifact": str(path),
        "source_sha256": digest,
        "status": "post-hoc secondary analysis; frozen v4 scores remain primary",
        "case_count": len(cases),
        "v4_evidence_supported_count": sum(
            bool(item["v4"]["evidence_supported"]) for item in cases
        ),
        "v5_evidence_supported_count": sum(
            bool(item["v5"]["evidence_supported"]) for item in cases
        ),
        "frozen_rca_exact_count": sum(bool(item["frozen_rca_exact"]) for item in cases),
        "frozen_mechanism_failure_case_ids": [
            item["case_id"]
            for item in cases
            if not item["frozen_failure_mechanism_correct"]
        ],
        "cases": cases,
        "provider_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline v5 secondary analysis of frozen Incident 003 Stage 1"
    )
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = analyze_frozen_stage1_v5(args.results)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        if args.output.exists():
            raise FileExistsError(f"Refusing to overwrite analysis: {args.output}")
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
