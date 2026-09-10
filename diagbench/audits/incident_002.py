"""Offline validity checks for Incident Family 002."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
from typing import Iterable

from diagbench.generators.incident_002 import generate_incident_002
from diagbench.schema import Incident, ModelView
from diagbench.schema.models import JSONValue
from diagbench.structural import structural_defect_matches, structural_signature
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations.format_preserving_v1 import format_preserving_incident
from diagpriv.transformations.hmac_v1 import hmac_incident
from diagpriv.transformations.redaction_v1 import redact_incident
from diagpriv.transformations.tokenization_v1 import tokenize_incident

_CAUSE_BEARING_TERMS = (
    "malformed",
    "invalid",
    "format",
    "normalization",
    "truncation",
    "defect",
    "separator",
    "separator defect",
    "format_valid",
    "missing_or_ineffective_idempotency",
)
_STRUCTURAL_INVARIANTS = {
    "healthy_identifier_pattern_consistency",
    "target_identifier_pattern_anomaly",
    "target_identifier_defect_signature",
    "target_identifier_length_delta",
}
_RELATIONAL_INVARIANTS = {
    "target_identifier_cross_source_identity",
    "control_identifier_cross_source_identity",
    "target_and_control_identifier_distinctness",
}


def shape_ablated_model_view(incident: Incident) -> ModelView:
    """Remove external-reference shape while preserving its equality relation.

    The ephemeral map is derived over the complete view, assigned by a stable
    digest ordering, applied across every annotated source, and discarded.
    Tokens share one synthetic output signature so no original length,
    separator, or character-class pattern remains.
    """
    data = deepcopy(incident.model_view().to_dict())
    paths = tuple(
        annotation.path
        for annotation in incident.sensitive_fields
        if annotation.classification == "external_subject_identifier"
    )
    values = {
        value
        for path in paths
        for value in _path_values(data, path)
        if isinstance(value, str)
    }
    ordered = sorted(
        values,
        key=lambda value: (
            hashlib.sha256(b"incident-002-shape-ablation-v1\0" + value.encode()).digest(),
            value,
        ),
    )
    mapping = {value: f"REF_{index:06d}" for index, value in enumerate(ordered, 1)}
    for path in paths:
        _replace_path(data, path, mapping)
    return ModelView.from_dict(data)


def audit_shape_ablation(incident: Incident) -> dict[str, JSONValue]:
    """Check that removing shape also removes the unique mechanical cause clue."""
    ablated = shape_ablated_model_view(incident)
    target_operation_id = str(incident.metadata["target_operation_id"])
    before_rows = incident.model_view().structured_evidence["processing_attempts"]
    after_rows = ablated.structured_evidence["processing_attempts"]
    before_patterns = {
        str(row["operation_id"]): structural_signature(str(row["external_reference"]))
        for row in before_rows
    }
    after_patterns = {
        str(row["operation_id"]): structural_signature(str(row["external_reference"]))
        for row in after_rows
    }
    healthy_before = {
        pattern
        for operation_id, pattern in before_patterns.items()
        if operation_id != target_operation_id
    }
    target_was_unique_shape = (
        len(healthy_before) == 1
        and before_patterns[target_operation_id] not in healthy_before
    )
    shape_removed = len(set(after_patterns.values())) == 1
    miss_operations = {
        str(row["operation_id"])
        for row in ablated.structured_evidence["lookup_observations"]
        if row["lookup_result"] == "no_match"
    }
    serialized = ablated.to_json().lower()
    no_cause_marker = all(term not in serialized for term in _CAUSE_BEARING_TERMS)
    no_unique_miss_shortcut = len(miss_operations) >= 2
    mechanically_unique_after_ablation = not (
        shape_removed and no_cause_marker and no_unique_miss_shortcut
    )
    return {
        "audit_version": "incident-002-shape-ablation-v1",
        "target_was_unique_structural_outlier": target_was_unique_shape,
        "all_external_references_share_one_ablated_signature": shape_removed,
        "lookup_miss_operation_count": len(miss_operations),
        "cause_bearing_marker_present": not no_cause_marker,
        "format_cause_mechanically_unique_after_ablation": mechanically_unique_after_ablation,
        "passed": target_was_unique_shape and not mechanically_unique_after_ablation,
    }


def audit_transformation_expectations(
    incident: Incident, *, hmac_key: bytes
) -> dict[str, JSONValue]:
    """Evaluate the approved relationship/structure expectation matrix."""
    views = {
        "raw": incident.model_view(),
        "redaction-v1": redact_incident(incident),
        "hmac-v1": hmac_incident(incident, key=hmac_key),
        "tokenization-v1": tokenize_incident(incident),
        "format-preserving-v1": format_preserving_incident(incident),
    }
    expected = {
        "raw": (True, True),
        "redaction-v1": (False, False),
        "hmac-v1": (False, True),
        "tokenization-v1": (False, True),
        "format-preserving-v1": (True, True),
    }
    report: dict[str, JSONValue] = {}
    for condition, view in views.items():
        results = {result.name: result for result in evaluate_invariants(incident, view)}
        present_structural = _STRUCTURAL_INVARIANTS.intersection(results)
        structural_available = all(
            results[name].preserved
            and results[name].status == "genuine_preservation"
            for name in present_structural
        )
        relationships_preserved = all(
            results[name].preserved for name in _RELATIONAL_INVARIANTS
        )
        collapse = any(
            result.status == "degenerate_pattern_collapse"
            for result in results.values()
        )
        expected_structure, expected_relationships = expected[condition]
        report[condition] = {
            "structural_evidence_available": structural_available,
            "relationships_preserved": relationships_preserved,
            "degenerate_pattern_collapse_reported": collapse,
            "expectation_met": (
                structural_available == expected_structure
                and relationships_preserved == expected_relationships
            ),
            "invariants": {
                name: result.to_dict() for name, result in sorted(results.items())
            },
        }
    return report


def audit_incident_002_sample(seeds: Iterable[int]) -> dict[str, JSONValue]:
    """Run deterministic construction checks over development instances only."""
    seed_values = tuple(seeds)
    if not seed_values:
        raise ValueError("Construction audit requires at least one development seed")
    defects: Counter[str] = Counter()
    observable_deltas: Counter[str] = Counter()
    templates: Counter[str] = Counter()
    target_positions: Counter[int] = Counter()
    target_row_positions: Counter[int] = Counter()
    control_counts: Counter[int] = Counter()
    defect_positions: Counter[int] = Counter()
    intake_aliases: Counter[str] = Counter()
    executor_aliases: Counter[str] = Counter()
    dependency_aliases: Counter[str] = Counter()
    message_variants: Counter[str] = Counter()
    target_dates: Counter[str] = Counter()
    checks = Counter()

    for seed in seed_values:
        incident = generate_incident_002(seed)
        checks["deterministic_generation"] += incident == generate_incident_002(seed)
        expected_domain = hashlib.sha256(
            (
                f"{incident.metadata['family_id']}\0"
                f"{incident.metadata['generator_version']}\0{seed}"
            ).encode("ascii")
        ).hexdigest()
        incident_001_domain = hashlib.sha256(
            f"incident_001_duplicate_payment\0incident-001-generator-v1\0{seed}".encode(
                "ascii"
            )
        ).hexdigest()
        checks["family_domain_separation"] += (
            incident.metadata["generation_domain_sha256"] == expected_domain
            and expected_domain != incident_001_domain
        )
        defects[str(incident.metadata["defect_class"])] += 1
        observable_deltas[str(incident.metadata["observable_structural_delta"])] += 1
        templates[str(incident.metadata["structural_template_name"])] += 1
        target_positions[int(incident.metadata["target_chronological_position"])] += 1
        defect_positions[int(incident.metadata["defect_position"])] += 1
        intake_aliases[str(incident.metadata["intake_alias"])] += 1
        executor_aliases[str(incident.metadata["executor_alias"])] += 1
        dependency_aliases[str(incident.metadata["dependency_alias"])] += 1
        message_variants.update(entry.message for entry in incident.log_evidence)
        control_ids = tuple(str(item) for item in incident.metadata["control_operation_ids"])
        control_counts[len(control_ids)] += 1
        target_id = str(incident.metadata["target_operation_id"])
        processing = incident.structured_evidence["processing_attempts"]
        target_row_positions[
            next(
                index
                for index, row in enumerate(processing)
                if str(row["operation_id"]) == target_id
            )
        ] += 1
        by_operation = {str(row["operation_id"]): row for row in processing}
        target_dates[str(by_operation[target_id]["received_at"])[:10]] += 1
        healthy_values = tuple(
            str(by_operation[operation_id]["external_reference"])
            for operation_id in control_ids
        )
        target_value = str(by_operation[target_id]["external_reference"])
        template = str(incident.metadata["structural_template"])
        latent = str(incident.metadata["latent_valid_reference"])
        checks["healthy_pattern_consistency"] += (
            len({structural_signature(value) for value in healthy_values}) == 1
            and structural_signature(healthy_values[0]) == template
        )
        checks["visible_defect_matches"] += structural_defect_matches(
            healthy_values,
            target_value,
            str(incident.metadata["observable_structural_delta"]),
        )
        checks["latent_target_conforms"] += structural_signature(latent) == template
        evidence_ids = _evidence_ids(incident)
        checks["evidence_ids_unique"] += len(evidence_ids) == len(set(evidence_ids))
        operation_ids = {
            str(row["operation_id"])
            for row in incident.structured_evidence["processing_attempts"]
        }
        effect_ids = {
            str(row["effect_id"])
            for row in incident.structured_evidence["effect_records"]
        }
        checks["entity_id_namespaces_collision_free"] += (
            len(operation_ids) == len(processing)
            and len(effect_ids) == len(incident.structured_evidence["effect_records"])
            and set(evidence_ids).isdisjoint(operation_ids)
            and set(evidence_ids).isdisjoint(effect_ids)
            and operation_ids.isdisjoint(effect_ids)
        )
        checks["cross_source_identity"] += _cross_source_identity_holds(incident)
        lookups = incident.structured_evidence["lookup_observations"]
        miss_operations = {
            str(row["operation_id"])
            for row in lookups
            if row["lookup_result"] == "no_match"
        }
        recovery_id = str(incident.metadata["recovery_control_operation_id"])
        recovery_states = {
            str(row["lookup_result"])
            for row in lookups
            if str(row["operation_id"]) == recovery_id
        }
        checks["benign_miss_distractor_present"] += (
            len(miss_operations) == 2
            and target_id in miss_operations
            and recovery_id in miss_operations
            and recovery_states == {"no_match", "match"}
        )
        latency_id = str(incident.metadata["latency_control_operation_id"])
        checks["latency_control_succeeds"] += any(
            str(row["operation_id"]) == latency_id
            and row["lookup_result"] == "match"
            and isinstance(row["latency_ms"], int)
            and row["latency_ms"] >= 650
            for row in lookups
        )
        checks["dependency_available_with_warning"] += (
            all(
                row["availability_state"] == "available"
                for row in incident.structured_evidence["dependency_health"]
            )
            and any(
                row["warning"] != "none"
                for row in incident.structured_evidence["dependency_health"]
            )
        )
        checks["same_executor_for_target_and_controls"] += len(
            {str(row["executor_alias"]) for row in processing}
        ) == 1
        checks["minimum_successful_controls"] += len(control_ids) >= 5
        results = evaluate_invariants(incident, incident.model_view())
        checks["all_required_invariants_hold"] += all(
            result.preserved for result in results if result.necessity != "discardable"
        )
        necessities = {result.necessity for result in results}
        checks["necessity_classes_complete"] += necessities == {
            "essential",
            "supportive",
            "discardable",
        }
        serialized = incident.model_view().to_json().lower()
        checks["oracle_model_view_separation"] += all(
            marker not in serialized
            for marker in (
                "ground_truth",
                "diagnostic_invariants",
                "expected_evidence",
                "sensitive_fields",
                "latent_valid_reference",
                "defect_class",
                "component_mappings",
            )
        )
        checks["no_cause_bearing_vocabulary"] += all(
            term not in serialized for term in _CAUSE_BEARING_TERMS
        )
        checks["controls_bracket_target"] += next(
            result.preserved for result in results if result.name == "controls_bracket_target"
        )
        checks["shape_ablation_passes"] += bool(audit_shape_ablation(incident)["passed"])

    sample_size = len(seed_values)
    return {
        "audit_version": "incident-002-construction-audit-v1",
        "sample_size": sample_size,
        "seed_min": min(seed_values),
        "seed_max": max(seed_values),
        "checks": {
            name: {"passed": count == sample_size, "count": count}
            for name, count in sorted(checks.items())
        },
        "defect_counts": dict(sorted(defects.items())),
        "observable_delta_counts": dict(sorted(observable_deltas.items())),
        "template_counts": dict(sorted(templates.items())),
        "target_position_counts": {
            str(key): value for key, value in sorted(target_positions.items())
        },
        "target_row_position_counts": {
            str(key): value for key, value in sorted(target_row_positions.items())
        },
        "control_count_distribution": {
            str(key): value for key, value in sorted(control_counts.items())
        },
        "defect_position_counts": {
            str(key): value for key, value in sorted(defect_positions.items())
        },
        "intake_alias_counts": dict(sorted(intake_aliases.items())),
        "executor_alias_counts": dict(sorted(executor_aliases.items())),
        "dependency_alias_counts": dict(sorted(dependency_aliases.items())),
        "message_variant_count": len(message_variants),
        "distinct_target_dates": len(target_dates),
        "defects_vary": len(defects) > 1,
        "templates_vary": len(templates) > 1,
        "target_positions_vary": len(target_positions) > 1,
        "row_order_varies": len(target_row_positions) > 1,
        "aliases_vary": all(
            len(counter) > 1
            for counter in (intake_aliases, executor_aliases, dependency_aliases)
        ),
        "messages_vary": len(message_variants) > 1,
    }


def _path_values(data: dict[str, JSONValue], path: str) -> tuple[JSONValue, ...]:
    source, field = path.split(".", maxsplit=1)
    if source != "logs":
        structured = data["structured_evidence"]
        assert isinstance(structured, dict)
        rows = structured[source]
        assert isinstance(rows, list)
        return tuple(row[field] for row in rows if isinstance(row, dict))
    logs = data["log_evidence"]
    assert isinstance(logs, list)
    values: list[JSONValue] = []
    for entry in logs:
        assert isinstance(entry, dict)
        attributes = entry.get("attributes")
        if isinstance(attributes, dict) and field in attributes:
            values.append(attributes[field])
    return tuple(values)


def _replace_path(
    data: dict[str, JSONValue], path: str, mapping: dict[str, str]
) -> None:
    source, field = path.split(".", maxsplit=1)
    if source != "logs":
        structured = data["structured_evidence"]
        assert isinstance(structured, dict)
        rows = structured[source]
        assert isinstance(rows, list)
        for row in rows:
            assert isinstance(row, dict)
            value = row[field]
            assert isinstance(value, str)
            row[field] = mapping[value]
        return
    logs = data["log_evidence"]
    assert isinstance(logs, list)
    for entry in logs:
        assert isinstance(entry, dict)
        attributes = entry.get("attributes")
        if isinstance(attributes, dict) and field in attributes:
            value = attributes[field]
            assert isinstance(value, str)
            attributes[field] = mapping[value]


def _evidence_ids(incident: Incident) -> tuple[str, ...]:
    structured_ids = tuple(
        str(row["evidence_id"])
        for rows in incident.structured_evidence.values()
        for row in rows
    )
    return (*structured_ids, *(entry.evidence_id for entry in incident.log_evidence))


def _cross_source_identity_holds(incident: Incident) -> bool:
    references: dict[str, set[str]] = {}
    for source in ("processing_attempts", "lookup_observations"):
        for row in incident.structured_evidence[source]:
            references.setdefault(str(row["operation_id"]), set()).add(
                str(row["external_reference"])
            )
    for entry in incident.log_evidence:
        operation_id = entry.attributes.get("operation_id")
        external_reference = entry.attributes.get("external_reference")
        if operation_id is not None and external_reference is not None:
            references.setdefault(str(operation_id), set()).add(
                str(external_reference)
            )
    return bool(references) and all(len(values) == 1 for values in references.values())
