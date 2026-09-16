"""Family-specific evidence-rubric dispatch outside the generic evaluator."""

from __future__ import annotations

from diagbench.generators.incident_003_v2 import FAMILY_ID as INCIDENT_003_V2_FAMILY
from diagbench.schema import Incident
from diagpriv.evaluation.evidence_support_v3 import EvidenceRubricV3
from diagpriv.evaluation.incident_003_v2_evidence import (
    build_incident_003_v2_evidence_rubric,
)


def build_evidence_rubric_v3(incident: Incident) -> EvidenceRubricV3:
    if incident.incident_id == INCIDENT_003_V2_FAMILY:
        return build_incident_003_v2_evidence_rubric(incident)
    raise ValueError(f"No v3 evidence protocol registered for {incident.incident_id}")
