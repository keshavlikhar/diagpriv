"""Canonical, non-secret transformation provenance for experiment manifests."""

from __future__ import annotations

import hashlib
import json
from typing import Mapping

from diagbench.relative_time import RELATIVE_TIME_SEMANTICS_VERSION
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION

TRANSFORMATION_CONFIGURATION_FIELDS = frozenset(
    {
        "transformation_version",
        "temporal_semantics_version",
        "anchor_rule",
        "precision",
        "representation",
        "annotation_classification",
        "scope_policy",
    }
)

RAW_TRANSFORMATION_CONFIGURATION = {
    "transformation_version": "raw",
    "temporal_semantics_version": TEMPORAL_SEMANTICS_VERSION,
    "anchor_rule": "not-applicable",
    "precision": "source-preserved",
    "representation": "RFC3339",
    "annotation_classification": "not-applicable",
    "scope_policy": "no-transformation",
}

RELATIVE_TIME_TRANSFORMATION_CONFIGURATION = {
    "transformation_version": "relative-time-v1",
    "temporal_semantics_version": RELATIVE_TIME_SEMANTICS_VERSION,
    "anchor_rule": "earliest-model-visible-annotated-timestamp-v1",
    "precision": "milliseconds",
    "representation": "T+<nonnegative-integer>ms",
    "annotation_classification": "operational_timestamp",
    "scope_policy": "annotated-model-view-fields-only",
}

TEMPORAL_SEMANTICS_UNAVAILABLE = "temporal-semantics-unavailable-v1"

TEMPORAL_ABLATION_TRANSFORMATION_CONFIGURATION = {
    "transformation_version": "incident-003-temporal-ablation-v1",
    "temporal_semantics_version": TEMPORAL_SEMANTICS_UNAVAILABLE,
    "anchor_rule": "not-applicable",
    "precision": "not-applicable",
    "representation": "unique-deterministic-nontemporal-marker",
    "annotation_classification": "operational_timestamp",
    "scope_policy": "annotated-timestamps-plus-deterministic-log-reordering",
}

REDACTION_TRANSFORMATION_CONFIGURATION = {
    "transformation_version": "redaction-v1",
    "temporal_semantics_version": TEMPORAL_SEMANTICS_UNAVAILABLE,
    "anchor_rule": "not-applicable",
    "precision": "not-applicable",
    "representation": "path-generic-placeholder",
    "annotation_classification": "all-sensitive-fields",
    "scope_policy": "annotated-model-view-fields-only",
}

HMAC_TRANSFORMATION_CONFIGURATION = {
    "transformation_version": "hmac-v1",
    "temporal_semantics_version": TEMPORAL_SEMANTICS_UNAVAILABLE,
    "anchor_rule": "not-applicable",
    "precision": "not-applicable",
    "representation": "namespaced-hmac-sha256-pseudonym",
    "annotation_classification": "all-sensitive-fields",
    "scope_policy": "annotated-model-view-fields-only",
}

TOKENIZATION_TRANSFORMATION_CONFIGURATION = {
    "transformation_version": "tokenization-v1",
    "temporal_semantics_version": TEMPORAL_SEMANTICS_UNAVAILABLE,
    "anchor_rule": "not-applicable",
    "precision": "not-applicable",
    "representation": "namespaced-deterministic-ordinal-token",
    "annotation_classification": "all-sensitive-fields",
    "scope_policy": "annotated-model-view-fields-only",
}

FORMAT_PRESERVING_TRANSFORMATION_CONFIGURATION = {
    "transformation_version": "format-preserving-v1",
    "temporal_semantics_version": TEMPORAL_SEMANTICS_UNAVAILABLE,
    "anchor_rule": "not-applicable",
    "precision": "not-applicable",
    "representation": "namespaced-character-class-pattern-pseudonym",
    "annotation_classification": "all-sensitive-fields",
    "scope_policy": "annotated-model-view-fields-only",
}


def canonical_transformation_configuration_json(
    configuration: Mapping[str, str],
) -> str:
    """Return the exact compact UTF-8 JSON preimage used for provenance."""
    if set(configuration) != TRANSFORMATION_CONFIGURATION_FIELDS:
        raise ValueError(
            "Transformation configuration must contain exactly the frozen fields"
        )
    if any(not isinstance(value, str) or not value for value in configuration.values()):
        raise ValueError("Transformation configuration values must be non-empty strings")
    return json.dumps(
        dict(configuration),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def transformation_configuration_sha256(
    configuration: Mapping[str, str],
) -> str:
    """Hash the exact canonical transformation-configuration representation."""
    payload = canonical_transformation_configuration_json(configuration)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def transformation_configuration_for_condition(condition: str) -> dict[str, str]:
    """Return the one frozen v10 configuration supported for a condition."""
    if condition == "raw":
        return dict(RAW_TRANSFORMATION_CONFIGURATION)
    if condition == "relative-time-v1":
        return dict(RELATIVE_TIME_TRANSFORMATION_CONFIGURATION)
    configurations = {
        "temporal-ablation-v1": TEMPORAL_ABLATION_TRANSFORMATION_CONFIGURATION,
        "redaction-v1": REDACTION_TRANSFORMATION_CONFIGURATION,
        "hmac-v1": HMAC_TRANSFORMATION_CONFIGURATION,
        "tokenization-v1": TOKENIZATION_TRANSFORMATION_CONFIGURATION,
        "format-preserving-v1": FORMAT_PRESERVING_TRANSFORMATION_CONFIGURATION,
    }
    try:
        return dict(configurations[condition])
    except KeyError as error:
        raise ValueError(
            f"Manifest v10 transformation provenance does not support {condition}"
        ) from error
