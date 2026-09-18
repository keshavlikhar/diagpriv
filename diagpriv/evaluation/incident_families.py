"""Explicit incident-family routing for provider evaluation."""

from __future__ import annotations

import hashlib
from typing import Literal

from diagbench.generators.incident_001 import generate_incident_001, seed_split
from diagbench.generators.incident_002 import (
    FAMILY_ID as INCIDENT_002_FAMILY,
    generate_incident_002,
)
from diagbench.generators.incident_003 import (
    FAMILY_ID as INCIDENT_003_FAMILY,
    generate_incident_003,
)
from diagbench.generators.incident_003_v2 import (
    FAMILY_ID as INCIDENT_003_V2_FAMILY,
    generate_incident_003_v2,
)
from diagbench.generators.incident_003_v3 import (
    FAMILY_ID as INCIDENT_003_V3_FAMILY,
    QueryRole as Incident003V3QueryRole,
    generate_incident_003_v3,
)
from diagbench.schema import Incident

INCIDENT_001_FAMILY = "incident_001"
SUPPORTED_INCIDENT_FAMILIES = (
    INCIDENT_001_FAMILY,
    INCIDENT_002_FAMILY,
    INCIDENT_003_FAMILY,
    INCIDENT_003_V2_FAMILY,
    INCIDENT_003_V3_FAMILY,
)

# Frozen by ascending first occurrence of each Incident 002 generator-side defect
# class, beginning at development seed 1000 and stopping when all six appeared.
INCIDENT_002_DEVELOPMENT_SEEDS = (1000, 1001, 1003, 1004, 1005, 1017)
INCIDENT_002_SEED_SELECTION_VERSION = (
    "incident-002-first-defect-class-occurrence-v1"
)

# Frozen by ascending seed, retaining the first two occurrences of each of the
# four temporal templates and stopping immediately when every template had two.
INCIDENT_003_DEVELOPMENT_SEEDS = (
    1000,
    1001,
    1002,
    1003,
    1004,
    1015,
    1017,
    1018,
)
INCIDENT_003_SEED_SELECTION_VERSION = (
    "incident-003-first-two-per-temporal-template-v1"
)

# Frozen before any v3 provider observation. Starting at seed 1019, retain the
# first two seeds per temporal template and stop once all four have two.
INCIDENT_003_V2_DEVELOPMENT_SEEDS = (
    1019,
    1020,
    1021,
    1022,
    1023,
    1025,
    1026,
    1028,
)
INCIDENT_003_V2_SEED_SELECTION_VERSION = (
    "incident-003-v2-first-two-per-temporal-template-unobserved-v1"
)

INCIDENT_003_V3_QUALIFICATION_SEEDS = (1319, 1299, 1387, 1222)
INCIDENT_003_V3_SEED_SELECTION_VERSION = (
    "incident-003-v3-paired-qualification-v1"
)
INCIDENT_003_V3_QUERY_ROLES: tuple[Incident003V3QueryRole, ...] = (
    "target",
    "temporal_twin",
)


def select_incident_003_v3_qualification_seeds() -> tuple[int, ...]:
    """Apply the frozen, content-independent qualification selection rule."""
    ranked = sorted(
        (
            hashlib.sha256(
                f"{INCIDENT_003_V3_SEED_SELECTION_VERSION}|{seed}".encode("ascii")
            ).hexdigest(),
            seed,
        )
        for seed in range(1200, 1400)
    )
    return tuple(seed for _, seed in ranked[:4])

IncidentFamily = Literal[
    "incident_001",
    "incident_002_format_defect",
    "incident_003_temporal_compensation",
    "incident_003_temporal_compensation_v2",
    "incident_003_temporal_compensation_v3",
]


def generate_evaluation_incident(
    family: str,
    seed: int,
    *,
    query_role: Incident003V3QueryRole | None = None,
) -> Incident:
    """Generate a configured family without implicit cross-family fallback."""
    if query_role is not None and family != INCIDENT_003_V3_FAMILY:
        raise ValueError("Query roles are valid only for Incident 003 v3")
    if family == INCIDENT_001_FAMILY:
        return generate_incident_001(seed)
    if family == INCIDENT_002_FAMILY:
        return generate_incident_002(seed)
    if family == INCIDENT_003_FAMILY:
        return generate_incident_003(seed)
    if family == INCIDENT_003_V2_FAMILY:
        return generate_incident_003_v2(seed)
    if family == INCIDENT_003_V3_FAMILY:
        if query_role not in INCIDENT_003_V3_QUERY_ROLES:
            raise ValueError(
                "Incident 003 v3 evaluation requires an explicit paired query role"
            )
        return generate_incident_003_v3(seed, query_role)
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
    if family == INCIDENT_003_FAMILY:
        return (
            "development"
            if seed in INCIDENT_003_DEVELOPMENT_SEEDS
            else "unassigned"
        )
    if family == INCIDENT_003_V2_FAMILY:
        return (
            "development"
            if seed in INCIDENT_003_V2_DEVELOPMENT_SEEDS
            else "unassigned"
        )
    if family == INCIDENT_003_V3_FAMILY:
        return (
            "development"
            if seed in INCIDENT_003_V3_QUALIFICATION_SEEDS
            else "unassigned"
        )
    raise ValueError(f"Unsupported incident family: {family}")


def incident_003_v3_case_id(
    construction_seed: int, query_role: Incident003V3QueryRole
) -> str:
    """Return the stable paired observation identity used by manifest v11."""
    if query_role not in INCIDENT_003_V3_QUERY_ROLES:
        raise ValueError(f"Unsupported Incident 003 v3 query role: {query_role}")
    return f"{construction_seed}:{query_role}"
