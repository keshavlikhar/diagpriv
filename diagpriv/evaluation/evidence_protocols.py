"""Family-specific evidence-rubric dispatch outside the generic evaluator."""

from __future__ import annotations

from diagbench.generators.incident_003_v2 import FAMILY_ID as INCIDENT_003_V2_FAMILY
from diagbench.generators.incident_003_v3 import FAMILY_ID as INCIDENT_003_V3_FAMILY
from diagbench.schema import Incident
from diagpriv.evaluation.evidence_support_v3 import EvidenceRubricV3
from diagpriv.evaluation.evidence_support_v4 import EvidenceSemanticEvaluatorV4
from diagpriv.evaluation.incident_003_v2_evidence import (
    build_incident_003_v2_evidence_rubric,
)
from diagpriv.evaluation.incident_003_v2_evidence_semantics import (
    Incident003V2EvidenceSemanticEvaluator,
)
from diagpriv.evaluation.incident_003_v3_evidence import (
    build_incident_003_v3_evidence_rubric,
)
from diagpriv.evaluation.incident_003_v3_evidence_semantics import (
    Incident003V3EvidenceSemanticEvaluator,
)


def build_evidence_rubric_v3(incident: Incident) -> EvidenceRubricV3:
    if incident.incident_id == INCIDENT_003_V2_FAMILY:
        return build_incident_003_v2_evidence_rubric(incident)
    if incident.incident_id == INCIDENT_003_V3_FAMILY:
        return build_incident_003_v3_evidence_rubric(incident)
    raise ValueError(f"No v3 evidence protocol registered for {incident.incident_id}")


def build_evidence_semantic_evaluator_v4(
    incident: Incident, temporal_semantics_version: str
) -> EvidenceSemanticEvaluatorV4:
    """Select a family evaluator without placing family logic in the scorer."""
    if incident.incident_id == INCIDENT_003_V2_FAMILY:
        return Incident003V2EvidenceSemanticEvaluator(
            temporal_semantics_version=temporal_semantics_version
        )
    if incident.incident_id == INCIDENT_003_V3_FAMILY:
        return Incident003V3EvidenceSemanticEvaluator(
            temporal_semantics_version=temporal_semantics_version
        )
    raise ValueError(
        f"No v4 evidence semantic evaluator registered for {incident.incident_id}"
    )
