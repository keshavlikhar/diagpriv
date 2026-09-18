"""Offline causal-isolation audits for Incident 003 v3."""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations
import json
import re
from typing import Iterable

from diagbench.audits.incident_003 import temporally_ablated_model_view
from diagbench.generators.incident_003_v3 import (
    AUDIT_SEEDS,
    FAMILY_ID,
    NEUTRAL_QUESTION_TEMPLATE,
    generate_incident_003_v3,
)
from diagbench.relative_time import RELATIVE_TIME_SEMANTICS_VERSION, parse_relative_time
from diagbench.schema import Incident, ModelView
from diagbench.schema.models import JSONValue
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION, parse_timestamp
from diagpriv.evaluation.evidence_support_v4 import score_evidence_support_v4
from diagpriv.evaluation.incident_003_v3_evidence import (
    build_incident_003_v3_evidence_rubric,
)
from diagpriv.evaluation.incident_003_v3_evidence_semantics import (
    Incident003V3EvidenceSemanticEvaluator,
)
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations.provenance import TEMPORAL_SEMANTICS_UNAVAILABLE
from diagpriv.transformations.relative_time_v1 import relative_time_incident

AUDIT_VERSION = "incident-003-v3-causal-isolation-audit-v1"
PROJECTION_VERSION = "incident-003-v3-nontemporal-projection-v1"

_TIMESTAMP_FIELDS = {
    "workflow_attempts": {"dispatched_at", "deadline_at"},
    "execution_observations": {"started_at", "completed_at"},
    "effect_records": {"created_at"},
    "compensation_records": {"started_at", "completed_at"},
    "dependency_health": {"observed_at"},
    "logs": {"timestamp"},
}
_IDENTIFIER_FIELDS = {
    "evidence_id",
    "operation_id",
    "effect_id",
    "compensation_id",
}
_BANNED_MESSAGE_TERMS = (
    " after ",
    " before ",
    " late ",
    " concurrent",
    " overlap",
    "still executing",
    "not cancelled",
    "fencing failure",
    "rollback raced",
    "completion after compensation",
)
_KNOWN_CUES = (
    "workflow_compensated",
    "execution_success",
    "active_effect",
    "compensation_present",
    "deadline_event_present",
    "compensation_event_present",
    "record_inventory",
    "event_inventory",
)


def non_temporal_operation_projection(
    view: ModelView, operation_id: str
) -> dict[str, JSONValue]:
    """Project one operation while removing identity, timestamps, and row order."""
    structured: dict[str, JSONValue] = {}
    for source, rows in sorted(view.structured_evidence.items()):
        projected = [
            _project_mapping(source, row)
            for row in rows
            if row.get("operation_id") == operation_id
        ]
        structured[source] = sorted(projected, key=_canonical)
    logs = [
        _project_mapping("logs", entry.to_dict())
        for entry in view.log_evidence
        if entry.attributes.get("operation_id") == operation_id
    ]
    logs.sort(key=_canonical)
    return {
        "projection_version": PROJECTION_VERSION,
        "structured_evidence": structured,
        "log_evidence": logs,
    }


def audit_incident_003_v3(incident: Incident) -> dict[str, JSONValue]:
    """Audit one v3 construction without consulting a provider."""
    _validate_incident(incident)
    raw = incident.model_view()
    relative = relative_time_incident(incident)
    ablated = temporally_ablated_model_view(incident)
    target = str(incident.metadata["target_operation_id"])
    twin = str(incident.metadata["temporal_twin_operation_id"])
    safe = str(incident.metadata["safe_control_operation_id"])

    target_projection = non_temporal_operation_projection(ablated, target)
    twin_projection = non_temporal_operation_projection(ablated, twin)
    projection_differences = _projection_differences(
        target_projection, twin_projection
    )
    signatures = {
        role: _signature_families(ablated, operation_id)
        for role, operation_id in {
            "target": target,
            "temporal_twin": twin,
            "safe_control": safe,
        }.items()
    }
    collision_by_family = {
        name: signatures["target"][name] == signatures["temporal_twin"][name]
        for name in signatures["target"]
    }

    raw_invariants = evaluate_invariants(
        incident, raw, temporal_semantics_version=TEMPORAL_SEMANTICS_VERSION
    )
    relative_invariants = evaluate_invariants(
        incident,
        relative,
        temporal_semantics_version=RELATIVE_TIME_SEMANTICS_VERSION,
    )
    timestamp_slots_raw = _timestamp_slots(incident, raw)
    timestamp_slots_relative = _timestamp_slots(incident, relative)
    timestamp_slots_ablated = _timestamp_slots(incident, ablated)
    raw_parsed = {slot: parse_timestamp(value) for slot, value in timestamp_slots_raw}
    relative_parsed = {
        slot: parse_relative_time(value) for slot, value in timestamp_slots_relative
    }
    pairwise = _pairwise_temporal_preservation(raw_parsed, relative_parsed)
    ablation_values = tuple(value for _, value in timestamp_slots_ablated)
    ablation_unavailable = all(
        not _parses(parse_timestamp, value)
        and not _parses(parse_relative_time, value)
        for value in ablation_values
    )

    raw_target_overlap = _operation_overlap(raw, target, parse_timestamp)
    raw_twin_overlap = _operation_overlap(raw, twin, parse_timestamp)
    relative_target_overlap = _operation_overlap(relative, target, parse_relative_time)
    relative_twin_overlap = _operation_overlap(relative, twin, parse_relative_time)
    evidence = _evidence_audit(incident, raw, relative, ablated)
    cue_vectors = {
        role: _known_cue_vector(ablated, operation_id)
        for role, operation_id in {
            "target": target,
            "temporal_twin": twin,
        }.items()
    }
    conjunctions = _conjunction_separators(cue_vectors)
    message_audit = _message_audit(raw, target, twin)
    schema_audit = _schema_audit(raw, target, twin)
    question_target = NEUTRAL_QUESTION_TEMPLATE.format(operation_id=target)
    question_twin = NEUTRAL_QUESTION_TEMPLATE.format(operation_id=twin)
    question_equal = (
        question_target.replace(target, "<operation_id>")
        == question_twin.replace(twin, "<operation_id>")
    )
    feature_target = _feature_tokens(target_projection)
    feature_twin = _feature_tokens(twin_projection)
    raw_non_temporal = _whole_view_non_temporal_projection(raw)
    relative_non_temporal = _whole_view_non_temporal_projection(relative)
    ablated_non_temporal = _whole_view_non_temporal_projection(ablated)
    generated_again = generate_incident_003_v3(int(incident.metadata["seed"]))

    checks = {
        "generator_and_oracle_deterministic": incident == generated_again,
        "generator_metadata_versioned": (
            incident.metadata["generator_version"] == "incident-003-generator-v3"
            and incident.metadata["protocol_version"]
            == "incident-003-temporal-protocol-v3"
        ),
        "question_template_equal": question_equal,
        "non_temporal_projection_exact_match": not projection_differences,
        "all_signature_families_collide": all(collision_by_family.values()),
        "no_single_feature_separator": feature_target == feature_twin,
        "no_known_2_3_4_feature_conjunction_separator": all(
            not values for values in conjunctions.values()
        ),
        "message_templates_balanced": bool(message_audit["passed"]),
        "schema_and_record_inventory_balanced": bool(schema_audit["passed"]),
        "all_control_record_and_event_inventories_match": all(
            signatures["target"][name] == signatures[role][name]
            for role in ("temporal_twin", "safe_control")
            for name in ("record_type_signature", "message_event_signature")
        ),
        "component_roles_balanced": _role_aliases_balanced(raw, target, twin, safe),
        "raw_invariants_all_pass": all(item.preserved for item in raw_invariants),
        "relative_invariants_all_pass": all(
            item.preserved and item.status == "genuine_preservation"
            for item in relative_invariants
        ),
        "relative_timestamp_slots_unchanged": (
            tuple(slot for slot, _ in timestamp_slots_raw)
            == tuple(slot for slot, _ in timestamp_slots_relative)
        ),
        "relative_pairwise_equality_order_duration_preserved": all(
            pairwise.values()
        ),
        "relative_non_temporal_model_view_preserved": (
            raw_non_temporal == relative_non_temporal
        ),
        "raw_target_overlaps_twin_does_not": (
            raw_target_overlap and not raw_twin_overlap
        ),
        "relative_target_overlaps_twin_does_not": (
            relative_target_overlap and not relative_twin_overlap
        ),
        "ablation_temporal_values_unavailable": ablation_unavailable,
        "ablation_temporal_values_unique": (
            len(ablation_values) == len(set(ablation_values))
        ),
        "ablation_non_temporal_pair_collision": (
            target_projection == twin_projection
        ),
        "ablation_non_temporal_model_view_preserved": (
            raw_non_temporal == ablated_non_temporal
        ),
        "raw_evidence_v4_satisfiable": bool(evidence["raw"]["evidence_supported"]),
        "relative_evidence_v4_satisfiable": bool(
            evidence["relative-time-v1"]["evidence_supported"]
        ),
        "ablation_evidence_v4_temporally_unsatisfied": (
            not bool(evidence["temporal-ablation-v1"]["evidence_supported"])
            and bool(evidence["temporal-ablation-v1"]["temporal_requirements_missing"])
        ),
    }
    return {
        "audit_version": AUDIT_VERSION,
        "seed": incident.metadata["seed"],
        "pair": {"target": target, "temporal_twin": twin},
        "projection_equal": not projection_differences,
        "projection_differences": projection_differences,
        "projection_difference_classification": [],
        "signature_collisions": collision_by_family,
        "single_feature_target_only": sorted(feature_target - feature_twin),
        "single_feature_twin_only": sorted(feature_twin - feature_target),
        "conjunction_separators": conjunctions,
        "message_audit": message_audit,
        "schema_audit": schema_audit,
        "temporal_invariant_status": {
            "raw": {item.name: item.status for item in raw_invariants},
            "relative-time-v1": {
                item.name: item.status for item in relative_invariants
            },
        },
        "relative_time_pairwise_checks": pairwise,
        "temporal_ablation": {
            "timestamp_count": len(ablation_values),
            "all_unavailable": ablation_unavailable,
            "all_unique": len(ablation_values) == len(set(ablation_values)),
            "chronological_log_order_removed": _ablation_log_order_is_neutral(ablated),
        },
        "evidence_support_v4": evidence,
        "checks": checks,
        "passed": all(checks.values()),
        "provider_calls": 0,
    }


def audit_incident_003_v3_range(seeds: Iterable[int]) -> dict[str, JSONValue]:
    """Audit a development-only range and enforce the 200-instance gates."""
    seed_values = tuple(seeds)
    allowed = set(AUDIT_SEEDS)
    if not seed_values or any(seed not in allowed for seed in seed_values):
        raise ValueError("Incident 003 v3 audit is restricted to seeds 1200-1399")
    reports = tuple(
        audit_incident_003_v3(generate_incident_003_v3(seed))
        for seed in seed_values
    )
    check_names = tuple(reports[0]["checks"])
    check_counts = {
        name: sum(bool(report["checks"][name]) for report in reports)
        for name in check_names
    }
    signature_counts = {
        name: sum(bool(report["signature_collisions"][name]) for report in reports)
        for name in reports[0]["signature_collisions"]
    }
    conjunction_counts = {
        size: sum(
            len(report["conjunction_separators"][size]) for report in reports
        )
        for size in ("2", "3", "4")
    }
    return {
        "audit_version": AUDIT_VERSION,
        "sample_size": len(seed_values),
        "seed_min": min(seed_values),
        "seed_max": max(seed_values),
        "pair_count": len(seed_values),
        "exact_projection_match_count": sum(
            bool(report["projection_equal"]) for report in reports
        ),
        "per_pair_projection": [
            {
                "seed": report["seed"],
                "equal": report["projection_equal"],
                "differences": report["projection_differences"],
            }
            for report in reports
        ],
        "signature_collision_counts": signature_counts,
        "single_feature_separator_count": sum(
            bool(report["single_feature_target_only"])
            or bool(report["single_feature_twin_only"])
            for report in reports
        ),
        "conjunction_separator_counts": conjunction_counts,
        "check_counts": {
            name: {"passed": count == len(reports), "count": count}
            for name, count in sorted(check_counts.items())
        },
        "failed_seeds": [
            int(report["seed"]) for report in reports if not report["passed"]
        ],
        "passed": all(report["passed"] for report in reports),
        "provider_calls": 0,
    }


def _project_mapping(source: str, value: dict[str, JSONValue]) -> dict[str, JSONValue]:
    result: dict[str, JSONValue] = {}
    for key, item in sorted(value.items()):
        if key in _IDENTIFIER_FIELDS:
            result[key] = f"<{key}>"
        elif key in _TIMESTAMP_FIELDS.get(source, set()):
            result[key] = "<timestamp>"
        elif key == "attributes" and isinstance(item, dict):
            result[key] = _project_mapping("attributes", item)
        else:
            result[key] = deepcopy(item)
    return result


def _projection_differences(
    left: dict[str, JSONValue], right: dict[str, JSONValue]
) -> list[JSONValue]:
    if left == right:
        return []
    return [{"classification": "unacceptable label leakage", "left": left, "right": right}]


def _signature_families(view: ModelView, operation_id: str) -> dict[str, str]:
    projection = non_temporal_operation_projection(view, operation_id)
    rows = {
        source: values[0]
        for source, values in projection["structured_evidence"].items()  # type: ignore[union-attr]
    }
    logs = projection["log_evidence"]
    workflow = rows["workflow_attempts"]
    execution = rows["execution_observations"]
    effect = rows["effect_records"]
    compensation = rows["compensation_records"]
    event_kinds = sorted(
        str(entry["attributes"]["event_kind"]) for entry in logs  # type: ignore[index]
    )
    return {
        "full_categorical_signature": _canonical(projection),
        "terminal_state_signature": _canonical(
            {
                "workflow_state": workflow["workflow_state"],
                "execution_result": execution["result"],
                "effect_state": effect["state"],
                "compensation_result": compensation["result"],
            }
        ),
        "record_type_signature": _canonical(sorted(rows)),
        "message_event_signature": _canonical(event_kinds),
    }


def _feature_tokens(value: JSONValue, prefix: str = "") -> set[str]:
    if isinstance(value, dict):
        result: set[str] = set()
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            result.add(f"field:{path}")
            result.update(_feature_tokens(item, path))
        return result
    if isinstance(value, list):
        result = set()
        for item in value:
            result.update(_feature_tokens(item, prefix))
        return result
    return {f"value:{prefix}={value}"}


def _known_cue_vector(view: ModelView, operation_id: str) -> dict[str, JSONValue]:
    rows = {
        source: next(row for row in values if row.get("operation_id") == operation_id)
        for source, values in view.structured_evidence.items()
    }
    event_kinds = sorted(
        str(entry.attributes.get("event_kind"))
        for entry in view.log_evidence
        if entry.attributes.get("operation_id") == operation_id
    )
    return {
        "workflow_compensated": rows["workflow_attempts"]["workflow_state"] == "compensated",
        "execution_success": rows["execution_observations"]["result"] == "success",
        "active_effect": rows["effect_records"]["state"] == "active",
        "compensation_present": bool(rows["compensation_records"]),
        "deadline_event_present": "deadline_reached" in event_kinds,
        "compensation_event_present": "compensation_started" in event_kinds,
        "record_inventory": tuple(sorted(rows)),
        "event_inventory": tuple(event_kinds),
    }


def _conjunction_separators(
    vectors: dict[str, dict[str, JSONValue]],
) -> dict[str, list[JSONValue]]:
    result: dict[str, list[JSONValue]] = {"2": [], "3": [], "4": []}
    for size in (2, 3, 4):
        for names in combinations(_KNOWN_CUES, size):
            target = tuple(vectors["target"][name] for name in names)
            twin = tuple(vectors["temporal_twin"][name] for name in names)
            if target != twin:
                result[str(size)].append(
                    {
                        "features": list(names),
                        "target": list(target),
                        "twin": list(twin),
                    }
                )
    return result


def _message_audit(view: ModelView, target: str, twin: str) -> dict[str, JSONValue]:
    def messages(operation_id: str) -> tuple[tuple[str, str], ...]:
        return tuple(sorted(
            (str(entry.attributes.get("event_kind")), entry.message)
            for entry in view.log_evidence
            if entry.attributes.get("operation_id") == operation_id
        ))
    target_messages = messages(target)
    twin_messages = messages(twin)
    serialized = " " + " ".join(message.lower() for _, message in target_messages) + " "
    banned = [term.strip() for term in _BANNED_MESSAGE_TERMS if term in serialized]
    return {
        "target_twin_exact_match": target_messages == twin_messages,
        "banned_relation_terms": banned,
        "passed": target_messages == twin_messages and not banned,
    }


def _schema_audit(view: ModelView, target: str, twin: str) -> dict[str, JSONValue]:
    target_projection = non_temporal_operation_projection(view, target)
    twin_projection = non_temporal_operation_projection(view, twin)
    target_sources = sorted(target_projection["structured_evidence"])  # type: ignore[arg-type]
    twin_sources = sorted(twin_projection["structured_evidence"])  # type: ignore[arg-type]
    strong_matched = [
        "workflow_attempts.deadline_at",
        "compensation_records",
        "execution_observations.result",
        "effect_records.state",
        "workflow_attempts.workflow_state",
        "logs.attributes.event_kind",
    ]
    weak_matched = [
        "structured_evidence.*.service_alias",
        "operation_id",
    ]
    return {
        "source_names_match": target_sources == twin_sources,
        "record_cardinality_match": (
            _record_counts(target_projection) == _record_counts(twin_projection)
        ),
        "strong_cues_present_but_matched": strong_matched,
        "weak_cues_present_but_matched": weak_matched,
        "near_label_leakage": [],
        "passed": target_projection == twin_projection,
    }


def _record_counts(projection: dict[str, JSONValue]) -> dict[str, int]:
    structured = projection["structured_evidence"]
    assert isinstance(structured, dict)
    return {
        source: len(rows)
        for source, rows in structured.items()
        if isinstance(rows, list)
    }


def _whole_view_non_temporal_projection(view: ModelView) -> dict[str, JSONValue]:
    operation_ids = sorted(
        {
            str(row["operation_id"])
            for rows in view.structured_evidence.values()
            for row in rows
        }
    )
    projections = [
        non_temporal_operation_projection(view, operation_id)
        for operation_id in operation_ids
    ]
    return {"operations": sorted(projections, key=_canonical)}


def _role_aliases_balanced(
    view: ModelView, target: str, twin: str, safe: str
) -> bool:
    def aliases(operation_id: str) -> tuple[str, str, str]:
        workflow = next(
            row
            for row in view.structured_evidence["workflow_attempts"]
            if row["operation_id"] == operation_id
        )
        execution = next(
            row
            for row in view.structured_evidence["execution_observations"]
            if row["operation_id"] == operation_id
        )
        dependency = next(
            row
            for row in view.structured_evidence["dependency_health"]
            if row["operation_id"] == operation_id
        )
        return (
            str(workflow["service_alias"]),
            str(execution["service_alias"]),
            str(dependency["service_alias"]),
        )

    return aliases(target) == aliases(twin) == aliases(safe)


def _timestamp_slots(incident: Incident, view: ModelView) -> tuple[tuple[str, str], ...]:
    values: list[tuple[str, str]] = []
    for annotation in incident.sensitive_fields:
        if annotation.classification != "operational_timestamp":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        if source == "logs":
            values.extend(
                (f"logs:{index}:{field}", str(getattr(entry, field)))
                for index, entry in enumerate(view.log_evidence)
            )
        else:
            values.extend(
                (f"{source}:{index}:{field}", str(row[field]))
                for index, row in enumerate(view.structured_evidence[source])
            )
    return tuple(values)


def _pairwise_temporal_preservation(
    raw: dict[str, object], relative: dict[str, int]
) -> dict[str, bool]:
    equality = ordering = duration = True
    for left, right in combinations(raw, 2):
        equality &= (raw[left] == raw[right]) == (relative[left] == relative[right])
        ordering &= (raw[left] < raw[right]) == (  # type: ignore[operator]
            relative[left] < relative[right]
        )
        duration &= int(
            (raw[right] - raw[left]).total_seconds() * 1000  # type: ignore[operator,union-attr]
        ) == relative[right] - relative[left]
    return {"equality": equality, "strict_ordering": ordering, "duration": duration}


def _operation_overlap(view: ModelView, operation_id: str, parser) -> bool:
    execution = next(
        row
        for row in view.structured_evidence["execution_observations"]
        if row["operation_id"] == operation_id
    )
    compensation = next(
        row
        for row in view.structured_evidence["compensation_records"]
        if row["operation_id"] == operation_id
    )
    execution_start = parser(str(execution["started_at"]))
    execution_end = parser(str(execution["completed_at"]))
    compensation_start = parser(str(compensation["started_at"]))
    compensation_end = parser(str(compensation["completed_at"]))
    if not (execution_start < execution_end and compensation_start < compensation_end):
        raise ValueError("Operation intervals must have positive duration")
    return max(execution_start, compensation_start) < min(
        execution_end, compensation_end
    )


def _evidence_audit(
    incident: Incident,
    raw: ModelView,
    relative: ModelView,
    ablated: ModelView,
) -> dict[str, JSONValue]:
    rubric = build_incident_003_v3_evidence_rubric(incident)
    evidence_ids = tuple(binding.evidence_ids for binding in rubric.subject_bindings)
    cited = tuple(item for group in evidence_ids for item in group)
    result: dict[str, JSONValue] = {}
    for name, view, semantics in (
        ("raw", raw, TEMPORAL_SEMANTICS_VERSION),
        ("relative-time-v1", relative, RELATIVE_TIME_SEMANTICS_VERSION),
        ("temporal-ablation-v1", ablated, TEMPORAL_SEMANTICS_UNAVAILABLE),
    ):
        score = score_evidence_support_v4(
            cited,
            view,
            rubric,
            Incident003V3EvidenceSemanticEvaluator(semantics),
        )
        data = score.to_dict()
        data["temporal_requirements_missing"] = any(
            name in set(score.missing_essential_requirements)
            for name in (
                "deadline_before_original_completion",
                "compensation_after_deadline",
                "execution_compensation_overlap",
                "late_successful_original_effect",
            )
        )
        result[name] = data
    return result


def _ablation_log_order_is_neutral(view: ModelView) -> bool:
    keys = tuple(
        (str(entry.attributes.get("event_kind")), entry.evidence_id)
        for entry in view.log_evidence
    )
    return keys == tuple(sorted(keys))


def _parses(parser, value: str) -> bool:
    try:
        parser(value)
    except (TypeError, ValueError):
        return False
    return True


def _validate_incident(incident: Incident) -> None:
    if incident.incident_id != FAMILY_ID:
        raise ValueError("Incident 003 v3 audit requires Incident 003 v3")
    seed = int(incident.metadata["seed"])
    if seed not in set(AUDIT_SEEDS):
        raise ValueError("Incident 003 v3 audit is restricted to seeds 1200-1399")


def _canonical(value: JSONValue) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))
