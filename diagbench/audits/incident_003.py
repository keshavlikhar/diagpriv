"""Offline construction and temporal-ablation audits for Incident 003."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import replace
import hashlib
from typing import Callable, Iterable

from diagbench.generators.incident_003 import FAMILY_ID, generate_incident_003
from diagbench.schema import Incident, ModelView
from diagbench.schema.models import JSONValue
from diagbench.temporal import (
    before,
    intervals_overlap,
    ordered_sequence,
    parse_timestamp,
)
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations.format_preserving_v1 import format_preserving_incident
from diagpriv.transformations.hmac_v1 import hmac_incident
from diagpriv.transformations.redaction_v1 import redact_incident
from diagpriv.transformations.tokenization_v1 import tokenize_incident

TEMPORAL_ABLATION_VERSION = "incident-003-temporal-ablation-v1"
_TEMPORAL_ABLATION_MARKER_PREFIX = "TA1"

_CAUSE_BEARING_TERMS = (
    "premature compensation",
    "compensation started too early",
    "race condition",
    "overlap caused inconsistency",
    "deadline bug",
    "rollback raced success",
    "invalid transition",
    "state machine bug",
    "incorrect_state_transition",
    "inconsistent_state",
)
_TEMPORAL_RELATIONS = {
    "ordered_before",
    "paired_before",
    "interval_seconds",
    "intervals_overlap",
}
_CAUSAL_TEMPORAL_INVARIANTS = {
    "target_deadline_precedes_original_completion",
    "target_compensation_after_deadline",
    "target_compensation_precedes_original_completion",
    "target_execution_compensation_overlap",
    "target_success_after_compensation_start",
    "control_completion_precedes_deadline",
    "target_event_order",
}


def temporally_ablated_model_view(incident: Incident) -> ModelView:
    """Neutralize target timing while retaining non-temporal evidence.

    Every timestamp field remains present but receives a unique deterministic,
    non-parseable audit marker. The marker identifies only its evidence slot;
    it contains no original time and defines no equality, order, duration, or
    overlap semantics. Identities, linkage, row order, states, results,
    messages, aliases, effects, compensation presence, dependency observations,
    and all other non-temporal data remain byte-for-byte equivalent.
    """
    if incident.incident_id != FAMILY_ID:
        raise ValueError("Temporal ablation v1 supports Incident 003 only")
    data = deepcopy(incident.model_view().to_dict())
    structured = data["structured_evidence"]
    assert isinstance(structured, dict)

    timestamp_fields = {
        "workflow_attempts": ("dispatched_at", "deadline_at"),
        "execution_observations": ("started_at", "completed_at"),
        "effect_records": ("created_at",),
        "compensation_records": ("started_at", "completed_at"),
        "dependency_health": ("observed_at",),
    }
    for source, fields in timestamp_fields.items():
        rows = structured[source]
        assert isinstance(rows, list)
        for row in rows:
            assert isinstance(row, dict)
            evidence_id = str(row["evidence_id"])
            for field in fields:
                row[field] = _temporal_ablation_marker(source, evidence_id, field)

    log_rows = data["log_evidence"]
    assert isinstance(log_rows, list)
    for entry in log_rows:
        assert isinstance(entry, dict)
        entry["timestamp"] = _temporal_ablation_marker(
            "logs", str(entry["evidence_id"]), "timestamp"
        )
    log_rows.sort(
        key=lambda entry: (
            str(entry["attributes"]["event_kind"]),  # type: ignore[index]
            str(entry["evidence_id"]),
        )
    )
    return ModelView.from_dict(data)


def audit_temporal_ablation(incident: Incident) -> dict[str, JSONValue]:
    """Verify that ablation removes the unique causal timing signature."""
    original = incident.model_view()
    ablated = temporally_ablated_model_view(incident)
    target_id = str(incident.metadata["target_operation_id"])
    healthy_ids = tuple(
        str(value) for value in incident.metadata["healthy_control_operation_ids"]
    )
    legitimate_id = str(incident.metadata["legitimate_compensation_operation_id"])
    original_signatures = _causal_signature_operations(original)
    ablated_signatures = _causal_signature_operations(ablated)
    original_results = _invariant_map(incident, original)
    original_profiles = _operation_temporal_profiles(original)
    ablated_profiles = _operation_temporal_profiles(ablated)
    target_pre_profile = original_profiles[target_id]
    target_post_profile = ablated_profiles[target_id]
    post_applicable_statuses = tuple(
        status
        for profile in ablated_profiles.values()
        for status in profile.values()
        if status != "not_applicable"
    )
    post_true_by_operation = {
        operation_id: [
            name for name, status in profile.items() if status == "true"
        ]
        for operation_id, profile in ablated_profiles.items()
    }
    target_unique_true_predicates = sorted(
        name
        for name in post_true_by_operation[target_id]
        if all(
            name not in predicates
            for operation_id, predicates in post_true_by_operation.items()
            if operation_id != target_id
        )
    )
    ablated_timestamp_values = _timestamp_values(incident, ablated)
    serialized = ablated.to_json().lower()
    non_temporal_preserved = _non_temporal_projection(
        original
    ) == _non_temporal_projection(ablated)
    raw_target_log_order_causal = _log_order_has_target_causal_subsequence(
        original, target_id
    )
    ablated_causal_log_orders = [
        operation_id
        for operation_id in ablated_profiles
        if _log_order_has_target_causal_subsequence(ablated, operation_id)
    ]
    original_log_ids = tuple(entry.evidence_id for entry in original.log_evidence)
    ablated_log_ids = tuple(entry.evidence_id for entry in ablated.log_evidence)
    expected_pre_profile = {
        "dispatch_before_execution_start": "true",
        "execution_completion_before_deadline": "false",
        "deadline_before_execution_completion": "true",
        "deadline_before_compensation_start": "true",
        "compensation_start_before_execution_completion": "true",
        "execution_completion_before_compensation_start": "false",
        "execution_compensation_overlap": "true",
        "effect_after_compensation_start": "true",
        "effect_before_compensation_start": "false",
        "successful_completion_before_deadline_then_compensation": "false",
    }
    temporal_invariant_status = {
        invariant.name: _invariant_evaluation_status(incident, ablated, invariant.name)
        for invariant in incident.diagnostic_invariants
        if invariant.relation in _TEMPORAL_RELATIONS
    }
    non_temporal_status = {
        name: _invariant_evaluation_status(incident, ablated, name)
        for name in (
            "target_inconsistent_state",
            "target_effect_presence",
            "target_compensation_record_presence",
        )
    }
    markers_unique = len(ablated_timestamp_values) == len(
        set(ablated_timestamp_values)
    )
    markers_non_parseable = all(
        _temporal_value_status(value) == "unavailable"
        for value in ablated_timestamp_values
    )
    neutralized = {
        name: temporal_invariant_status[name]
        for name in (
            "target_deadline_precedes_original_completion",
            "target_compensation_after_deadline",
            "target_compensation_precedes_original_completion",
            "target_execution_compensation_overlap",
            "target_success_after_compensation_start",
            "control_completion_precedes_deadline",
            "target_event_order",
        )
    }
    result: dict[str, JSONValue] = {
        "audit_version": TEMPORAL_ABLATION_VERSION,
        "original_target_has_causal_signature": original_signatures == {target_id},
        "pre_ablation_target_temporal_profile": target_pre_profile,
        "pre_ablation_profile_matches_required_signature": (
            target_pre_profile == expected_pre_profile
        ),
        "post_ablation_target_temporal_profile": target_post_profile,
        "post_ablation_healthy_control_profiles": {
            operation_id: ablated_profiles[operation_id]
            for operation_id in healthy_ids
        },
        "post_ablation_legitimate_compensation_profile": ablated_profiles[
            legitimate_id
        ],
        "post_ablation_all_applicable_temporal_predicates_unavailable": (
            bool(post_applicable_statuses)
            and all(status == "unavailable" for status in post_applicable_statuses)
        ),
        "post_ablation_true_temporal_predicates_by_operation": post_true_by_operation,
        "post_ablation_target_unique_true_temporal_predicates": (
            target_unique_true_predicates
        ),
        "post_success_compensation_anomaly_status": target_post_profile[
            "successful_completion_before_deadline_then_compensation"
        ],
        "pre_ablation_target_log_order_has_causal_subsequence": (
            raw_target_log_order_causal
        ),
        "post_ablation_operations_with_causal_log_order": ablated_causal_log_orders,
        "chronological_log_row_order_neutralized": (
            original_log_ids != ablated_log_ids
            and set(original_log_ids) == set(ablated_log_ids)
            and _log_rows_use_audit_order(ablated)
        ),
        "ablated_causal_signature_operation_count": len(ablated_signatures),
        "ablated_target_causal_signature": target_id in ablated_signatures,
        "timestamp_ablation_classification": "unavailable_not_preserved",
        "timestamp_marker_count": len(ablated_timestamp_values),
        "timestamp_markers_unique": markers_unique,
        "timestamp_markers_non_parseable": markers_non_parseable,
        "degenerate_temporal_equality_count": (
            len(ablated_timestamp_values) - len(set(ablated_timestamp_values))
        ),
        "non_temporal_evidence_preserved": non_temporal_preserved,
        "row_cardinality_preserved": _row_counts(original) == _row_counts(ablated),
        "cause_bearing_text_present": any(term in serialized for term in _CAUSE_BEARING_TERMS),
        "neutralized_temporal_invariants": neutralized,
        "outcome_state_preserved": non_temporal_status["target_inconsistent_state"]
        == "true",
        "effect_presence_preserved": non_temporal_status["target_effect_presence"]
        == "true",
        "compensation_presence_preserved": non_temporal_status[
            "target_compensation_record_presence"
        ]
        == "true",
    }
    result["passed"] = bool(
        result["original_target_has_causal_signature"]
        and result["pre_ablation_profile_matches_required_signature"]
        and result["pre_ablation_target_log_order_has_causal_subsequence"]
        and result["ablated_causal_signature_operation_count"] == 0
        and result[
            "post_ablation_all_applicable_temporal_predicates_unavailable"
        ]
        and not result["post_ablation_target_unique_true_temporal_predicates"]
        and result["post_success_compensation_anomaly_status"] == "unavailable"
        and not result["post_ablation_operations_with_causal_log_order"]
        and result["chronological_log_row_order_neutralized"]
        and result["timestamp_markers_unique"]
        and result["timestamp_markers_non_parseable"]
        and result["degenerate_temporal_equality_count"] == 0
        and result["non_temporal_evidence_preserved"]
        and result["row_cardinality_preserved"]
        and not result["cause_bearing_text_present"]
        and all(status == "unavailable" for status in neutralized.values())
        and result["outcome_state_preserved"]
        and result["effect_presence_preserved"]
        and result["compensation_presence_preserved"]
        and all(
            original_results[name].preserved for name in _CAUSAL_TEMPORAL_INVARIANTS
        )
    )
    return result


def audit_timestamp_transformations(
    incident: Incident, *, hmac_key: bytes
) -> dict[str, JSONValue]:
    """Report implemented timestamp behavior and one prospective expectation."""
    views = {
        "raw": incident.model_view(),
        "redaction-v1": redact_incident(incident),
        "hmac-v1": hmac_incident(incident, key=hmac_key),
        "tokenization-v1": tokenize_incident(incident),
        "format-preserving-v1": format_preserving_incident(incident),
    }
    actions = {
        "raw": "unchanged_literal_timestamps",
        "redaction-v1": "path_generic_placeholders",
        "hmac-v1": "path_scoped_hmac_pseudonyms",
        "tokenization-v1": "path_scoped_ordinal_tokens",
        "format-preserving-v1": "path_scoped_character_pattern_pseudonyms",
    }
    original_timestamps = _timestamp_values(incident, incident.model_view())
    report: dict[str, JSONValue] = {}
    for condition, view in views.items():
        transformed_timestamps = _timestamp_values(incident, view)
        parseable = 0
        for value in transformed_timestamps:
            try:
                parse_timestamp(value)
            except ValueError:
                continue
            parseable += 1
        temporal_results, rejected = _safe_temporal_results(incident, view)
        report[condition] = {
            "implemented": True,
            "timestamp_action": actions[condition],
            "timestamp_occurrences": len(transformed_timestamps),
            "parseable_timestamp_occurrences": parseable,
            "all_literal_timestamps_removed": (
                condition != "raw"
                and not set(original_timestamps).intersection(transformed_timestamps)
            ),
            "required_temporal_invariants_preserved": all(
                temporal_results.get(name, False)
                for name in _CAUSAL_TEMPORAL_INVARIANTS
            ),
            "temporal_invariant_evaluation_rejected": rejected,
            "preserves_cross_field_temporal_semantics_by_design": condition == "raw",
        }
    report["relative-time-v1"] = {
        "implemented": False,
        "timestamp_action": "prospective_incident_relative_offsets",
        "all_literal_timestamps_removed": True,
        "required_temporal_invariants_preserved": "expected",
        "temporal_invariant_evaluation_rejected": False,
        "preserves_cross_field_temporal_semantics_by_design": True,
        "classification": "hypothetical_future_expectation_not_empirical_audit",
    }
    return report


def audit_incident_003_sample(seeds: Iterable[int]) -> dict[str, JSONValue]:
    """Run deterministic construction checks over development instances only."""
    seed_values = tuple(seeds)
    if not seed_values:
        raise ValueError("Construction audit requires at least one development seed")

    checks: Counter[str] = Counter()
    templates: Counter[str] = Counter()
    control_counts: Counter[int] = Counter()
    target_positions: Counter[int] = Counter()
    row_positions: dict[str, Counter[int]] = {
        source: Counter()
        for source in (
            "workflow_attempts",
            "execution_observations",
            "effect_records",
            "compensation_records",
        )
    }
    orchestrator_aliases: Counter[str] = Counter()
    executor_aliases: Counter[str] = Counter()
    dependency_aliases: Counter[str] = Counter()
    message_variants: Counter[str] = Counter()
    target_dates: Counter[str] = Counter()
    target_warning: Counter[str] = Counter()
    compensation_completion_relation: Counter[str] = Counter()
    collision_count = 0
    ablation_pass_count = 0

    for seed in seed_values:
        incident = generate_incident_003(seed)
        view = incident.model_view()
        target_id = str(incident.metadata["target_operation_id"])
        healthy_ids = tuple(
            str(value) for value in incident.metadata["healthy_control_operation_ids"]
        )
        legitimate_id = str(incident.metadata["legitimate_compensation_operation_id"])
        slow_id = str(incident.metadata["slow_control_operation_id"])
        workflows = _rows_by_operation(view.structured_evidence, "workflow_attempts")
        executions = _rows_by_operation(
            view.structured_evidence, "execution_observations"
        )
        effects = _optional_rows_by_operation(view.structured_evidence, "effect_records")
        compensations = _optional_rows_by_operation(
            view.structured_evidence, "compensation_records"
        )
        dependencies = _group_rows_by_operation(
            view.structured_evidence, "dependency_health"
        )
        target_workflow = workflows[target_id]
        target_execution = executions[target_id]
        target_compensation = compensations[target_id]
        target_effect = effects[target_id]

        checks["deterministic_generation"] += incident == generate_incident_003(seed)
        expected_domain = hashlib.sha256(
            f"{FAMILY_ID}\0{incident.metadata['generator_version']}\0{seed}".encode(
                "ascii"
            )
        ).hexdigest()
        checks["family_domain_separation"] += (
            incident.metadata["generation_domain_sha256"] == expected_domain
            and expected_domain
            != hashlib.sha256(
                f"incident_002_format_defect\0incident-002-generator-v1\0{seed}".encode(
                    "ascii"
                )
            ).hexdigest()
        )
        checks["oracle_labels"] += incident.ground_truth_v2.to_dict() == {
            "observed_outcome": "inconsistent_state",
            "trigger": "timeout_or_deadline",
            "subsequent_action": "compensation_or_rollback",
            "failure_mechanism": "incorrect_state_transition",
            "affected_component": "workflow_orchestrator",
            "logical_operation_repeated": False,
            "explanation": (
                "The workflow orchestrator transitioned into compensation at the deadline "
                "before original execution completed, allowing a later success to coexist "
                "with the compensated workflow state."
            ),
        }
        checks["target_inconsistent_state"] += (
            target_workflow["workflow_state"] == "compensated"
            and target_execution["result"] == "success"
            and target_compensation["result"] == "completed"
            and target_effect["state"] == "active"
        )
        checks["target_original_execution_succeeds"] += (
            target_execution["result"] == "success"
        )
        checks["target_deadline_precedes_completion"] += before(
            str(target_workflow["deadline_at"]), str(target_execution["completed_at"])
        )
        checks["target_compensation_after_deadline"] += before(
            str(target_workflow["deadline_at"]), str(target_compensation["started_at"])
        )
        checks["target_compensation_before_completion"] += before(
            str(target_compensation["started_at"]), str(target_execution["completed_at"])
        )
        checks["target_execution_compensation_overlap"] += intervals_overlap(
            str(target_execution["started_at"]),
            str(target_execution["completed_at"]),
            str(target_compensation["started_at"]),
            str(target_compensation["completed_at"]),
        )
        checks["target_effect_present"] += target_id in effects
        checks["healthy_controls_complete_before_deadline"] += all(
            before(
                str(executions[operation_id]["completed_at"]),
                str(workflows[operation_id]["deadline_at"]),
            )
            for operation_id in healthy_ids
        )
        checks["healthy_controls_have_no_compensation"] += all(
            workflows[operation_id]["compensation_state"] == "not_started"
            and operation_id not in compensations
            for operation_id in healthy_ids
        )
        checks["benign_slow_control_succeeds"] += (
            executions[slow_id]["result"] == "success"
            and before(
                str(executions[slow_id]["completed_at"]),
                str(workflows[slow_id]["deadline_at"]),
            )
        )
        warned_operations = {
            operation_id
            for operation_id, rows in dependencies.items()
            if any(row["warning"] != "none" for row in rows)
        }
        checks["latency_warning_not_target_unique"] += (
            slow_id in warned_operations
            and slow_id != target_id
            and (target_id not in warned_operations or len(warned_operations) >= 2)
        )
        checks["orchestrator_owns_deadline_compensation_state"] += (
            all(
                row["orchestrator_alias"] == incident.metadata["orchestrator_alias"]
                for row in workflows.values()
            )
            and all(
                row["orchestrator_alias"] == incident.metadata["orchestrator_alias"]
                for row in compensations.values()
            )
        )
        checks["executor_owns_only_execution_effect"] += (
            all(
                row["executor_alias"] == incident.metadata["executor_alias"]
                for row in executions.values()
            )
            and all(
                row["executor_alias"] == incident.metadata["executor_alias"]
                for row in effects.values()
            )
        )
        expected_operations = {target_id, legitimate_id, *healthy_ids}
        checks["cross_source_operation_identity"] += (
            set(workflows) == expected_operations
            and set(executions) == expected_operations
            and set(dependencies) == expected_operations
            and set(effects) == expected_operations - {legitimate_id}
            and set(compensations) == {target_id, legitimate_id}
            and {
                str(entry.attributes["operation_id"]) for entry in view.log_evidence
            }
            == expected_operations
        )
        checks["unrelated_operations_distinct"] += len(expected_operations) == len(
            chronological_ids(view)
        )
        identifiers = _all_identifiers(incident)
        collision_free = len(identifiers) == len(set(identifiers))
        collision_count += 0 if collision_free else 1
        checks["identifier_namespaces_collision_free"] += collision_free
        serialized = view.to_json().lower()
        checks["no_answer_leaking_text"] += all(
            term not in serialized for term in _CAUSE_BEARING_TERMS
        )
        ablation = audit_temporal_ablation(incident)
        ablation_pass_count += int(bool(ablation["passed"]))
        checks["temporal_ablation_passes"] += bool(ablation["passed"])
        counts = _evidence_count_by_operation(view)
        checks["per_operation_evidence_count_balanced"] += len(set(counts.values())) == 1
        checks["legitimate_compensation_distractor"] += (
            executions[legitimate_id]["result"] == "cancelled"
            and legitimate_id not in effects
            and compensations[legitimate_id]["result"] == "completed"
            and before(
                str(executions[legitimate_id]["completed_at"]),
                str(compensations[legitimate_id]["started_at"]),
            )
        )
        checks["dependency_available"] += all(
            row["availability_state"] == "available"
            for rows in dependencies.values()
            for row in rows
        )
        results = evaluate_invariants(incident, view)
        checks["all_required_invariants_hold"] += all(
            result.preserved for result in results if result.necessity != "discardable"
        )
        checks["necessity_classes_complete"] += {
            result.necessity for result in results
        } == {"essential", "supportive", "discardable"}
        checks["model_view_oracle_separation"] += all(
            marker not in serialized
            for marker in (
                "ground_truth",
                "diagnostic_invariants",
                "expected_evidence",
                "sensitive_fields",
                "component_mappings",
                "target_operation_id",
                "healthy_control_operation_ids",
            )
        )

        templates[str(incident.metadata["temporal_template_name"])] += 1
        control_counts[len(healthy_ids)] += 1
        target_positions[int(incident.metadata["target_chronological_position"])] += 1
        for source, counter in row_positions.items():
            rows = view.structured_evidence[source]
            counter[
                next(
                    index
                    for index, row in enumerate(rows)
                    if row["operation_id"] == target_id
                )
            ] += 1
        orchestrator_aliases[str(incident.metadata["orchestrator_alias"])] += 1
        executor_aliases[str(incident.metadata["executor_alias"])] += 1
        dependency_aliases[str(incident.metadata["dependency_alias"])] += 1
        message_variants.update(entry.message for entry in view.log_evidence)
        target_dates[str(target_workflow["dispatched_at"])[:10]] += 1
        target_warning["present" if target_id in warned_operations else "absent"] += 1
        compensation_completion_relation[
            "compensation_completes_before_original"
            if before(
                str(target_compensation["completed_at"]),
                str(target_execution["completed_at"]),
            )
            else "original_completes_before_compensation"
        ] += 1

    sample_size = len(seed_values)
    total_checks = len(checks)
    passed_evaluations = sum(checks.values())
    total_evaluations = sample_size * total_checks
    return {
        "audit_version": "incident-003-construction-audit-v1",
        "sample_size": sample_size,
        "seed_min": min(seed_values),
        "seed_max": max(seed_values),
        "check_count": total_checks,
        "check_evaluations": total_evaluations,
        "passed_check_evaluations": passed_evaluations,
        "failed_check_evaluations": total_evaluations - passed_evaluations,
        "checks": {
            name: {"passed": count == sample_size, "count": count}
            for name, count in sorted(checks.items())
        },
        "template_distribution": dict(sorted(templates.items())),
        "control_count_distribution": {
            str(key): value for key, value in sorted(control_counts.items())
        },
        "target_chronological_position_distribution": {
            str(key): value for key, value in sorted(target_positions.items())
        },
        "target_row_position_distributions": {
            source: {str(key): value for key, value in sorted(counter.items())}
            for source, counter in sorted(row_positions.items())
        },
        "orchestrator_alias_distribution": dict(sorted(orchestrator_aliases.items())),
        "executor_alias_distribution": dict(sorted(executor_aliases.items())),
        "dependency_alias_distribution": dict(sorted(dependency_aliases.items())),
        "message_variant_distribution": dict(sorted(message_variants.items())),
        "distinct_calendar_dates": len(target_dates),
        "target_warning_distribution": dict(sorted(target_warning.items())),
        "compensation_completion_order_distribution": dict(
            sorted(compensation_completion_relation.items())
        ),
        "collision_count": collision_count,
        "temporal_ablation_pass_count": ablation_pass_count,
        "templates_vary": len(templates) > 1,
        "control_counts_vary": len(control_counts) > 1,
        "target_chronological_positions_vary": len(target_positions) > 1,
        "row_positions_vary": all(len(counter) > 1 for counter in row_positions.values()),
        "aliases_vary": all(
            len(counter) > 1
            for counter in (orchestrator_aliases, executor_aliases, dependency_aliases)
        ),
        "messages_vary": len(message_variants) > 1,
        "dates_vary": len(target_dates) > 1,
        "warning_placement_varies": len(target_warning) > 1,
    }


def chronological_ids(view: ModelView) -> tuple[str, ...]:
    """Return operation IDs ordered by visible workflow dispatch time."""
    rows = view.structured_evidence["workflow_attempts"]
    return tuple(
        str(row["operation_id"])
        for row in sorted(rows, key=lambda row: parse_timestamp(str(row["dispatched_at"])))
    )


def _invariant_map(incident: Incident, view: ModelView) -> dict[str, object]:
    return {result.name: result for result in evaluate_invariants(incident, view)}


def _safe_temporal_results(
    incident: Incident, view: ModelView
) -> tuple[dict[str, bool], bool]:
    results: dict[str, bool] = {}
    rejected = False
    for invariant in incident.diagnostic_invariants:
        if invariant.relation not in _TEMPORAL_RELATIONS:
            continue
        narrowed = replace(incident, diagnostic_invariants=(invariant,))
        try:
            results[invariant.name] = evaluate_invariants(narrowed, view)[0].preserved
        except ValueError:
            results[invariant.name] = False
            rejected = True
    return results, rejected


def _timestamp_values(incident: Incident, view: ModelView) -> tuple[str, ...]:
    values: list[str] = []
    for annotation in incident.sensitive_fields:
        if annotation.classification != "operational_timestamp":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        if source == "logs":
            for entry in view.log_evidence:
                data = entry.to_dict()
                value = data[field] if field in data else entry.attributes[field]
                values.append(str(value))
        else:
            values.extend(
                str(row[field]) for row in view.structured_evidence[source]
            )
    return tuple(values)


def _causal_signature_operations(view: ModelView) -> set[str]:
    workflows = _rows_by_operation(view.structured_evidence, "workflow_attempts")
    executions = _rows_by_operation(view.structured_evidence, "execution_observations")
    compensations = _optional_rows_by_operation(
        view.structured_evidence, "compensation_records"
    )
    matches: set[str] = set()
    for operation_id in compensations:
        try:
            causal_order = ordered_sequence(
                (
                    str(workflows[operation_id]["dispatched_at"]),
                    str(executions[operation_id]["started_at"]),
                    str(workflows[operation_id]["deadline_at"]),
                    str(compensations[operation_id]["started_at"]),
                    str(executions[operation_id]["completed_at"]),
                )
            )
            overlap = _execution_compensation_overlap(view, operation_id)
        except ValueError:
            continue
        if causal_order and overlap and executions[operation_id]["result"] == "success":
            matches.add(operation_id)
    return matches


def _operation_temporal_profiles(
    view: ModelView,
) -> dict[str, dict[str, JSONValue]]:
    workflows = _rows_by_operation(view.structured_evidence, "workflow_attempts")
    executions = _rows_by_operation(view.structured_evidence, "execution_observations")
    effects = _optional_rows_by_operation(view.structured_evidence, "effect_records")
    compensations = _optional_rows_by_operation(
        view.structured_evidence, "compensation_records"
    )
    profiles: dict[str, dict[str, JSONValue]] = {}
    for operation_id, workflow in workflows.items():
        execution = executions[operation_id]
        profile: dict[str, JSONValue] = {
            "dispatch_before_execution_start": _relation_status(
                lambda: before(
                    str(workflow["dispatched_at"]), str(execution["started_at"])
                )
            ),
            "execution_completion_before_deadline": _relation_status(
                lambda: before(
                    str(execution["completed_at"]), str(workflow["deadline_at"])
                )
            ),
            "deadline_before_execution_completion": _relation_status(
                lambda: before(
                    str(workflow["deadline_at"]), str(execution["completed_at"])
                )
            ),
        }
        compensation = compensations.get(operation_id)
        if compensation is None:
            profile.update(
                {
                    "deadline_before_compensation_start": "not_applicable",
                    "compensation_start_before_execution_completion": "not_applicable",
                    "execution_completion_before_compensation_start": "not_applicable",
                    "execution_compensation_overlap": "not_applicable",
                    "effect_after_compensation_start": "not_applicable",
                    "effect_before_compensation_start": "not_applicable",
                    "successful_completion_before_deadline_then_compensation": (
                        "not_applicable"
                    ),
                }
            )
            profiles[operation_id] = profile
            continue

        completion_before_deadline = str(
            profile["execution_completion_before_deadline"]
        )
        deadline_before_compensation = _relation_status(
            lambda: before(
                str(workflow["deadline_at"]), str(compensation["started_at"])
            )
        )
        profile.update(
            {
                "deadline_before_compensation_start": deadline_before_compensation,
                "compensation_start_before_execution_completion": _relation_status(
                    lambda: before(
                        str(compensation["started_at"]),
                        str(execution["completed_at"]),
                    )
                ),
                "execution_completion_before_compensation_start": _relation_status(
                    lambda: before(
                        str(execution["completed_at"]),
                        str(compensation["started_at"]),
                    )
                ),
                "execution_compensation_overlap": _relation_status(
                    lambda: _execution_compensation_overlap(view, operation_id)
                ),
            }
        )
        effect = effects.get(operation_id)
        if effect is None:
            profile["effect_after_compensation_start"] = "not_applicable"
            profile["effect_before_compensation_start"] = "not_applicable"
        else:
            profile["effect_after_compensation_start"] = _relation_status(
                lambda: before(
                    str(compensation["started_at"]), str(effect["created_at"])
                )
            )
            profile["effect_before_compensation_start"] = _relation_status(
                lambda: before(
                    str(effect["created_at"]), str(compensation["started_at"])
                )
            )
        profile["successful_completion_before_deadline_then_compensation"] = (
            _combined_relation_status(
                completion_before_deadline,
                deadline_before_compensation,
            )
            if execution["result"] == "success"
            else "not_applicable"
        )
        profiles[operation_id] = profile
    return profiles


def _log_order_has_target_causal_subsequence(
    view: ModelView, operation_id: str
) -> bool:
    event_kinds = tuple(
        str(entry.attributes["event_kind"])
        for entry in view.log_evidence
        if entry.attributes["operation_id"] == operation_id
    )
    expected = (
        "dispatch_recorded",
        "execution_started",
        "deadline_reached",
        "compensation_started",
        "execution_completed",
        "effect_recorded",
    )
    expected_index = 0
    for event_kind in event_kinds:
        if event_kind == expected[expected_index]:
            expected_index += 1
            if expected_index == len(expected):
                return True
    return False


def _log_rows_use_audit_order(view: ModelView) -> bool:
    observed = tuple(
        (str(entry.attributes["event_kind"]), entry.evidence_id)
        for entry in view.log_evidence
    )
    return observed == tuple(sorted(observed))


def _relation_status(predicate: Callable[[], bool]) -> str:
    try:
        return "true" if predicate() else "false"
    except ValueError:
        return "unavailable"


def _combined_relation_status(*statuses: str) -> str:
    if "unavailable" in statuses:
        return "unavailable"
    if "not_applicable" in statuses:
        return "not_applicable"
    return "true" if all(status == "true" for status in statuses) else "false"


def _invariant_evaluation_status(
    incident: Incident, view: ModelView, invariant_name: str
) -> str:
    invariant = next(
        item for item in incident.diagnostic_invariants if item.name == invariant_name
    )
    narrowed = replace(incident, diagnostic_invariants=(invariant,))
    try:
        return "true" if evaluate_invariants(narrowed, view)[0].preserved else "false"
    except ValueError:
        return "unavailable"


def _temporal_value_status(value: str) -> str:
    try:
        parse_timestamp(value)
    except ValueError:
        return "unavailable"
    return "available"


def _temporal_ablation_marker(source: str, evidence_id: str, field: str) -> str:
    return f"{_TEMPORAL_ABLATION_MARKER_PREFIX}::{source}::{evidence_id}::{field}"


def _execution_compensation_overlap(view: ModelView, operation_id: str) -> bool:
    executions = _rows_by_operation(view.structured_evidence, "execution_observations")
    compensations = _optional_rows_by_operation(
        view.structured_evidence, "compensation_records"
    )
    execution = executions[operation_id]
    compensation = compensations[operation_id]
    return intervals_overlap(
        str(execution["started_at"]),
        str(execution["completed_at"]),
        str(compensation["started_at"]),
        str(compensation["completed_at"]),
    )


def _operations_with_compensation(view: ModelView) -> tuple[str, ...]:
    return tuple(
        sorted(
            _optional_rows_by_operation(
                view.structured_evidence, "compensation_records"
            )
        )
    )


def _rows_by_operation(
    structured: dict[str, list[dict[str, JSONValue]]], source: str
) -> dict[str, dict[str, JSONValue]]:
    rows = _optional_rows_by_operation(structured, source)
    if not rows:
        raise ValueError(f"Expected evidence rows for source: {source}")
    return rows


def _optional_rows_by_operation(
    structured: dict[str, list[dict[str, JSONValue]]], source: str
) -> dict[str, dict[str, JSONValue]]:
    rows = structured[source]
    result: dict[str, dict[str, JSONValue]] = {}
    for row in rows:
        operation_id = str(row["operation_id"])
        if operation_id in result:
            raise ValueError(f"Expected at most one {source} row per operation")
        result[operation_id] = row
    return result


def _group_rows_by_operation(
    structured: dict[str, list[dict[str, JSONValue]]], source: str
) -> dict[str, list[dict[str, JSONValue]]]:
    grouped: dict[str, list[dict[str, JSONValue]]] = {}
    for row in structured[source]:
        grouped.setdefault(str(row["operation_id"]), []).append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: str(row["evidence_id"]))
    return grouped


def _row_counts(view: ModelView) -> dict[str, int]:
    return {
        **{source: len(rows) for source, rows in view.structured_evidence.items()},
        "logs": len(view.log_evidence),
    }


def _without_timestamps(value: JSONValue) -> JSONValue:
    timestamp_fields = {
        "timestamp",
        "dispatched_at",
        "deadline_at",
        "started_at",
        "completed_at",
        "created_at",
        "observed_at",
    }
    if isinstance(value, dict):
        return {
            key: _without_timestamps(item)
            for key, item in value.items()
            if key not in timestamp_fields
        }
    if isinstance(value, list):
        return [_without_timestamps(item) for item in value]
    return value


def _non_temporal_projection(view: ModelView) -> JSONValue:
    projected = _without_timestamps(view.to_dict())
    assert isinstance(projected, dict)
    logs = projected["log_evidence"]
    assert isinstance(logs, list)
    logs.sort(key=lambda entry: str(entry["evidence_id"]))  # type: ignore[index]
    return projected


def _all_identifiers(incident: Incident) -> tuple[str, ...]:
    view = incident.model_view()
    evidence_ids = tuple(
        str(row["evidence_id"])
        for rows in view.structured_evidence.values()
        for row in rows
    ) + tuple(entry.evidence_id for entry in view.log_evidence)
    operation_ids = tuple(
        str(row["operation_id"])
        for row in view.structured_evidence["workflow_attempts"]
    )
    effect_ids = tuple(
        str(row["effect_id"]) for row in view.structured_evidence["effect_records"]
    )
    compensation_ids = tuple(
        str(row["compensation_id"])
        for row in view.structured_evidence["compensation_records"]
    )
    return (*evidence_ids, *operation_ids, *effect_ids, *compensation_ids)


def _evidence_count_by_operation(view: ModelView) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for rows in view.structured_evidence.values():
        for row in rows:
            counts[str(row["operation_id"])] += 1
    for entry in view.log_evidence:
        counts[str(entry.attributes["operation_id"])] += 1
    return dict(counts)
