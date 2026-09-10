"""Explicit incident-family routing for provider evaluation."""

from __future__ import annotations

from typing import Literal

from diagbench.generators.incident_001 import generate_incident_001, seed_split
from diagbench.generators.incident_002 import (
    FAMILY_ID as INCIDENT_002_FAMILY,
    generate_incident_002,
)
from diagbench.schema import Incident

INCIDENT_001_FAMILY = "incident_001"
SUPPORTED_INCIDENT_FAMILIES = (
    INCIDENT_001_FAMILY,
    INCIDENT_002_FAMILY,
)

# Frozen by ascending first occurrence of each Incident 002 generator-side defect
# class, beginning at development seed 1000 and stopping when all six appeared.
INCIDENT_002_DEVELOPMENT_SEEDS = (1000, 1001, 1003, 1004, 1005, 1017)
INCIDENT_002_SEED_SELECTION_VERSION = (
    "incident-002-first-defect-class-occurrence-v1"
)

IncidentFamily = Literal["incident_001", "incident_002_format_defect"]


def generate_evaluation_incident(family: str, seed: int) -> Incident:
    """Generate a configured family without implicit cross-family fallback."""
    if family == INCIDENT_001_FAMILY:
        return generate_incident_001(seed)
    if family == INCIDENT_002_FAMILY:
        return generate_incident_002(seed)
    raise ValueError(f"Unsupported incident family: {family}")


def evaluation_seed_split(family: str, seed: int) -> str:
    """Classify a seed according to the selected family's evaluation protocol."""
    if family == INCIDENT_001_FAMILY:
        return seed_split(seed)
    if family == INCIDENT_002_FAMILY:
        return (
            "development"
            if seed in INCIDENT_002_DEVELOPMENT_SEEDS
            else "unassigned"
        )
    raise ValueError(f"Unsupported incident family: {family}")
