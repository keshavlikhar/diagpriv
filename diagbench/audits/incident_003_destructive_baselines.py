"""Offline audits for the Incident 003 destructive temporal baselines."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from itertools import combinations
from typing import Callable, Iterable

from diagbench.audits.incident_003 import (
    audit_temporal_ablation,
    temporally_ablated_model_view,
)
from diagbench.generators.incident_003_v2 import generate_incident_003_v2
from diagbench.schema import Incident, ModelView
from diagbench.schema.models import JSONValue
from diagbench.temporal import parse_timestamp
from diagpriv.transformations.format_preserving_v1 import format_preserving_incident
from diagpriv.transformations.hmac_v1 import hmac_incident
from diagpriv.transformations.redaction_v1 import redact_incident
from diagpriv.transformations.tokenization_v1 import tokenize_incident
from diagpriv.evaluation.evidence_support_v4 import score_evidence_support_v4
from diagpriv.evaluation.incident_003_v2_evidence import (
    build_incident_003_v2_evidence_rubric,
)
from diagpriv.evaluation.incident_003_v2_evidence_semantics import (
    Incident003V2EvidenceSemanticEvaluator,
)

AUDIT_VERSION = "incident-003-destructive-baselines-audit-v1"
TEMPORAL_SEMANTICS_UNAVAILABLE = "temporal-semantics-unavailable-v1"

STATUS_GENUINE = "G"
STATUS_BROKEN = "B"
STATUS_DEGENERATE = "D"
STATUS_EXPECTED_NON_PRESERVATION = "E"

CONDITIONS = (
    "temporal-ablation-v1",
    "redaction-v1",
    "hmac-v1",
    "tokenization-v1",
    "format-preserving-v1",
)

CORE_EVIDENCE_REQUIREMENTS = (
    "target_identity_linkage",
    "deadline_before_original_completion",
    "compensation_after_deadline",
    "execution_compensation_overlap",
    "late_successful_original_effect",
    "inconsistent_terminal_workflow_effect_state",
)

_TEMPORAL_FIELDS = {
    "workflow_attempts": ("dispatched_at", "deadline_at"),
    "execution_observations": ("started_at", "completed_at"),
    "effect_records": ("created_at",),
    "compensation_records": ("started_at", "completed_at"),
    "dependency_health": ("observed_at",),
    "logs": ("timestamp",),
}


def destructive_condition_views(
    incident: Incident, *, hmac_key: bytes
) -> dict[str, ModelView]:
    """Build each historical condition independently from the raw incident."""
    return {
        "temporal-ablation-v1": temporally_ablated_model_view(incident),
        "redaction-v1": redact_incident(incident),
        "hmac-v1": hmac_incident(incident, key=hmac_key),
        "tokenization-v1": tokenize_incident(incident),
        "format-preserving-v1": format_preserving_incident(incident),
    }


def audit_destructive_baseline_incident(
    incident: Incident, *, hmac_key: bytes
) -> dict[str, JSONValue]:
    """Classify one instance without assigning semantics to opaque strings.

    The four temporal relation families are intentionally classified as ``E``
    whenever the condition has no temporal parser. Lexical order, token order,
    format resemblance, and accidental equality are never treated as time.
    """
    raw = incident.model_view()
    raw_temporal = _timestamp_occurrences(incident, raw)
    raw_values = tuple(raw_temporal.values())
    raw_non_temporal = _canonical_non_temporal_projection(incident, raw)
    raw_non_sensitive = _canonical_non_sensitive_projection(incident, raw)
    raw_ids = _evidence_ids(raw)
    raw_cardinality = _row_cardinality(raw)
    raw_source_structure = _source_structure(raw)
    raw_identity_relations = _identity_relations(incident, raw)
    reports: dict[str, JSONValue] = {}

    factories: dict[str, Callable[[], ModelView]] = {
        "temporal-ablation-v1": lambda: temporally_ablated_model_view(incident),
        "redaction-v1": lambda: redact_incident(incident),
        "hmac-v1": lambda: hmac_incident(incident, key=hmac_key),
        "tokenization-v1": lambda: tokenize_incident(incident),
        "format-preserving-v1": lambda: format_preserving_incident(incident),
    }
    for condition, factory in factories.items():
        transformed = factory()
        repeated = factory()
        temporal = _timestamp_occurrences(incident, transformed)
        if temporal.keys() != raw_temporal.keys():
            raise ValueError(f"Timestamp slots changed under {condition}")
        values = tuple(temporal.values())
        parseable_count = sum(_parses_raw_timestamp(value) for value in values)
        literal_secrecy = (
            not set(raw_values).intersection(values)
            and all(value not in transformed.to_json() for value in raw_values)
        )
        equality_status = _timestamp_equality_status(
            raw_temporal, temporal, condition
        )
        identity_relations = _identity_relations(incident, transformed)
        introduced_identifier_collapses = _introduced_identifier_collapses(
            raw_identity_relations, identity_relations
        )
        cross_source_linkage = _cross_source_linkage_status(
            condition, raw_identity_relations, identity_relations
        )
        expected_log_order = (
            STATUS_EXPECTED_NON_PRESERVATION
            if condition == "temporal-ablation-v1"
            else STATUS_GENUINE
        )
        report: dict[str, JSONValue] = {
            "temporal_semantics_version": TEMPORAL_SEMANTICS_UNAVAILABLE,
            "transformation_determinism": _status(transformed == repeated),
            "timestamp_literal_secrecy": _status(literal_secrecy),
            "timestamp_parseability": (
                STATUS_EXPECTED_NON_PRESERVATION
                if parseable_count == 0
                else STATUS_BROKEN
            ),
            "timestamp_equality": equality_status,
            "strict_ordering": STATUS_EXPECTED_NON_PRESERVATION,
            "duration": STATUS_EXPECTED_NON_PRESERVATION,
            "positive_overlap": STATUS_EXPECTED_NON_PRESERVATION,
            "deadline_crossing": STATUS_EXPECTED_NON_PRESERVATION,
            "all_essential_temporal_invariants": (
                STATUS_EXPECTED_NON_PRESERVATION
            ),
            "healthy_control_temporal_invariants": (
                STATUS_EXPECTED_NON_PRESERVATION
            ),
            "legitimate_compensation_temporal_invariants": (
                STATUS_EXPECTED_NON_PRESERVATION
            ),
            "non_temporal_model_view": (
                STATUS_GENUINE
                if _canonical_non_temporal_projection(incident, transformed)
                == raw_non_temporal
                else STATUS_EXPECTED_NON_PRESERVATION
            ),
            "non_sensitive_operational_evidence": _status(
                _canonical_non_sensitive_projection(incident, transformed)
                == raw_non_sensitive
            ),
            "evidence_ids": _status(_evidence_ids(transformed) == raw_ids),
            "row_cardinality": _status(
                _row_cardinality(transformed) == raw_cardinality
            ),
            "structured_row_order": _status(
                _structured_row_order(transformed) == _structured_row_order(raw)
            ),
            "log_row_order": expected_log_order
            if _log_row_order(transformed) != _log_row_order(raw)
            else STATUS_GENUINE,
            "source_structure": _status(
                _source_structure(transformed) == raw_source_structure
            ),
            "cross_source_linkage": cross_source_linkage,
            "identifier_distinctness": (
                STATUS_DEGENERATE
                if introduced_identifier_collapses
                else STATUS_GENUINE
            ),
            "timestamp_occurrences": len(values),
            "parseable_timestamp_occurrences": parseable_count,
        }
        reports[condition] = report

    ablation = audit_temporal_ablation(incident)
    return {
        "audit_version": AUDIT_VERSION,
        "seed": incident.metadata["seed"],
        "conditions": reports,
        "temporal_ablation_passed": bool(ablation["passed"]),
    }


def audit_destructive_baseline_range(
    seeds: Iterable[int], *, hmac_key: bytes
) -> dict[str, JSONValue]:
    """Audit only Incident 003 development constructions 1000--1199."""
    seed_values = tuple(seeds)
    if not seed_values or any(seed < 1000 or seed > 1199 for seed in seed_values):
        raise ValueError(
            "Destructive-baseline audit is restricted to development seeds 1000-1199"
        )
    reports = tuple(
        audit_destructive_baseline_incident(
            generate_incident_003_v2(seed), hmac_key=hmac_key
        )
        for seed in seed_values
    )
    matrix: dict[str, JSONValue] = {}
    for condition in CONDITIONS:
        metrics = tuple(
            key
            for key in reports[0]["conditions"][condition]  # type: ignore[index]
            if key
            not in {"temporal_semantics_version", "timestamp_occurrences", "parseable_timestamp_occurrences"}
        )
        condition_report: dict[str, JSONValue] = {}
        for metric in metrics:
            counter = Counter(
                str(report["conditions"][condition][metric])  # type: ignore[index]
                for report in reports
            )
            condition_report[metric] = {
                "status": next(iter(counter)) if len(counter) == 1 else "MIXED",
                "counts": {
                    status: counter.get(status, 0)
                    for status in (
                        STATUS_GENUINE,
                        STATUS_BROKEN,
                        STATUS_DEGENERATE,
                        STATUS_EXPECTED_NON_PRESERVATION,
                    )
                },
            }
        condition_report["temporal_semantics_version"] = (
            TEMPORAL_SEMANTICS_UNAVAILABLE
        )
        condition_report["timestamp_occurrences"] = sum(
            int(report["conditions"][condition]["timestamp_occurrences"])  # type: ignore[index]
            for report in reports
        )
        condition_report["parseable_timestamp_occurrences"] = sum(
            int(report["conditions"][condition]["parseable_timestamp_occurrences"])  # type: ignore[index]
            for report in reports
        )
        matrix[condition] = condition_report
    return {
        "audit_version": AUDIT_VERSION,
        "sample_size": len(seed_values),
        "seed_min": min(seed_values),
        "seed_max": max(seed_values),
        "conditions": matrix,
        "temporal_ablation_pass_count": sum(
            bool(report["temporal_ablation_passed"]) for report in reports
        ),
        "passed": all(bool(report["temporal_ablation_passed"]) for report in reports)
        and all(
            all(
                report["conditions"][condition][metric] == expected  # type: ignore[index]
                for metric, expected in _expected_statuses(condition).items()
            )
            for report in reports
            for condition in CONDITIONS
        ),
    }


def audit_destructive_evidence_satisfiability_incident(
    incident: Incident, *, hmac_key: bytes
) -> dict[str, JSONValue]:
    """Score a deterministic complete citation set against transformed evidence."""
    rubric = build_incident_003_v2_evidence_rubric(incident)
    complete_evidence = tuple(
        sorted(
            {
                evidence_id
                for binding in rubric.subject_bindings
                for evidence_id in binding.evidence_ids
            }
        )
    )
    evaluator = Incident003V2EvidenceSemanticEvaluator(
        TEMPORAL_SEMANTICS_UNAVAILABLE
    )
    conditions: dict[str, JSONValue] = {}
    for condition, view in destructive_condition_views(
        incident, hmac_key=hmac_key
    ).items():
        score = score_evidence_support_v4(
            complete_evidence, view, rubric, evaluator
        )
        satisfied = set(score.satisfied_essential_requirements)
        conditions[condition] = {
            requirement: requirement in satisfied
            for requirement in CORE_EVIDENCE_REQUIREMENTS
        }
    return {
        "seed": incident.metadata["seed"],
        "temporal_semantics_version": TEMPORAL_SEMANTICS_UNAVAILABLE,
        "conditions": conditions,
    }


def audit_destructive_evidence_satisfiability_range(
    seeds: Iterable[int], *, hmac_key: bytes
) -> dict[str, JSONValue]:
    """Aggregate semantic evidence satisfiability over development seeds only."""
    seed_values = tuple(seeds)
    if not seed_values or any(seed < 1000 or seed > 1199 for seed in seed_values):
        raise ValueError(
            "Destructive evidence audit is restricted to development seeds 1000-1199"
        )
    reports = tuple(
        audit_destructive_evidence_satisfiability_incident(
            generate_incident_003_v2(seed), hmac_key=hmac_key
        )
        for seed in seed_values
    )
    matrix: dict[str, JSONValue] = {}
    for condition in CONDITIONS:
        matrix[condition] = {
            requirement: {
                "satisfied": sum(
                    bool(report["conditions"][condition][requirement])  # type: ignore[index]
                    for report in reports
                ),
                "unsatisfied": sum(
                    not bool(report["conditions"][condition][requirement])  # type: ignore[index]
                    for report in reports
                ),
            }
            for requirement in CORE_EVIDENCE_REQUIREMENTS
        }
    temporal_requirements = CORE_EVIDENCE_REQUIREMENTS[1:5]
    return {
        "sample_size": len(seed_values),
        "seed_min": min(seed_values),
        "seed_max": max(seed_values),
        "temporal_semantics_version": TEMPORAL_SEMANTICS_UNAVAILABLE,
        "conditions": matrix,
        "no_temporal_false_positive": all(
            matrix[condition][requirement]["satisfied"] == 0  # type: ignore[index]
            for condition in CONDITIONS
            for requirement in temporal_requirements
        ),
    }


def _expected_statuses(condition: str) -> dict[str, str]:
    expected = {
        "transformation_determinism": STATUS_GENUINE,
        "timestamp_literal_secrecy": STATUS_GENUINE,
        "timestamp_parseability": STATUS_EXPECTED_NON_PRESERVATION,
        "timestamp_equality": STATUS_EXPECTED_NON_PRESERVATION,
        "strict_ordering": STATUS_EXPECTED_NON_PRESERVATION,
        "duration": STATUS_EXPECTED_NON_PRESERVATION,
        "positive_overlap": STATUS_EXPECTED_NON_PRESERVATION,
        "deadline_crossing": STATUS_EXPECTED_NON_PRESERVATION,
        "all_essential_temporal_invariants": STATUS_EXPECTED_NON_PRESERVATION,
        "healthy_control_temporal_invariants": STATUS_EXPECTED_NON_PRESERVATION,
        "legitimate_compensation_temporal_invariants": (
            STATUS_EXPECTED_NON_PRESERVATION
        ),
        "non_temporal_model_view": STATUS_EXPECTED_NON_PRESERVATION,
        "non_sensitive_operational_evidence": STATUS_GENUINE,
        "evidence_ids": STATUS_GENUINE,
        "row_cardinality": STATUS_GENUINE,
        "structured_row_order": STATUS_GENUINE,
        "log_row_order": STATUS_GENUINE,
        "source_structure": STATUS_GENUINE,
        "cross_source_linkage": STATUS_GENUINE,
        "identifier_distinctness": STATUS_GENUINE,
    }
    if condition == "temporal-ablation-v1":
        expected["non_temporal_model_view"] = STATUS_GENUINE
        expected["log_row_order"] = STATUS_EXPECTED_NON_PRESERVATION
    elif condition == "redaction-v1":
        expected["timestamp_equality"] = STATUS_DEGENERATE
        expected["cross_source_linkage"] = STATUS_EXPECTED_NON_PRESERVATION
        expected["identifier_distinctness"] = STATUS_DEGENERATE
    return expected


def _timestamp_occurrences(
    incident: Incident, view: ModelView
) -> dict[str, str]:
    result: dict[str, str] = {}
    for annotation in incident.sensitive_fields:
        if annotation.classification != "operational_timestamp":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        if source == "logs":
            for entry in view.log_evidence:
                data = entry.to_dict()
                value = data[field] if field in data else entry.attributes[field]
                result[f"logs:{entry.evidence_id}:{field}"] = str(value)
        else:
            for row in view.structured_evidence[source]:
                result[f"{source}:{row['evidence_id']}:{field}"] = str(row[field])
    return result


def _timestamp_equality_status(
    raw: dict[str, str], transformed: dict[str, str], condition: str
) -> str:
    slots = tuple(sorted(raw))
    preserved = all(
        (raw[first] == raw[second])
        == (transformed[first] == transformed[second])
        for first, second in combinations(slots, 2)
    )
    if preserved and condition not in {"temporal-ablation-v1", "redaction-v1"}:
        return STATUS_GENUINE
    false_equalities = any(
        raw[first] != raw[second]
        and transformed[first] == transformed[second]
        for first, second in combinations(slots, 2)
    )
    if false_equalities:
        return STATUS_DEGENERATE
    return STATUS_EXPECTED_NON_PRESERVATION


def _canonical_non_temporal_projection(
    incident: Incident, view: ModelView
) -> dict[str, JSONValue]:
    data = deepcopy(view.to_dict())
    _mask_annotations(incident, data, temporal_only=True)
    return _canonicalize_rows(data)


def _canonical_non_sensitive_projection(
    incident: Incident, view: ModelView
) -> dict[str, JSONValue]:
    data = deepcopy(view.to_dict())
    _mask_annotations(incident, data, temporal_only=False)
    return _canonicalize_rows(data)


def _mask_annotations(
    incident: Incident, data: dict[str, JSONValue], *, temporal_only: bool
) -> None:
    for annotation in incident.sensitive_fields:
        if temporal_only and annotation.classification != "operational_timestamp":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        if source == "logs":
            logs = data["log_evidence"]
            assert isinstance(logs, list)
            for entry in logs:
                assert isinstance(entry, dict)
                if field in entry:
                    entry[field] = "[ANNOTATED]"
                else:
                    attributes = entry["attributes"]
                    assert isinstance(attributes, dict)
                    if field in attributes:
                        attributes[field] = "[ANNOTATED]"
        else:
            structured = data["structured_evidence"]
            assert isinstance(structured, dict)
            rows = structured[source]
            assert isinstance(rows, list)
            for row in rows:
                assert isinstance(row, dict)
                row[field] = "[ANNOTATED]"


def _canonicalize_rows(data: dict[str, JSONValue]) -> dict[str, JSONValue]:
    structured = data["structured_evidence"]
    logs = data["log_evidence"]
    assert isinstance(structured, dict) and isinstance(logs, list)
    for rows in structured.values():
        assert isinstance(rows, list)
        rows.sort(key=lambda row: str(row["evidence_id"]))  # type: ignore[index]
    logs.sort(key=lambda row: str(row["evidence_id"]))  # type: ignore[index]
    return data


def _identity_relations(
    incident: Incident, view: ModelView
) -> dict[tuple[str, str], bool]:
    occurrences: dict[str, str] = {}
    for annotation in incident.sensitive_fields:
        if annotation.classification == "operational_timestamp":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        if source == "logs":
            for entry in view.log_evidence:
                value = entry.attributes.get(field)
                if value is not None:
                    occurrences[f"logs:{entry.evidence_id}:{field}"] = str(value)
        else:
            for row in view.structured_evidence[source]:
                occurrences[f"{source}:{row['evidence_id']}:{field}"] = str(row[field])
    slots = tuple(sorted(occurrences))
    return {
        (first, second): occurrences[first] == occurrences[second]
        for first, second in combinations(slots, 2)
    }


def _introduced_identifier_collapses(
    raw: dict[tuple[str, str], bool], transformed: dict[tuple[str, str], bool]
) -> bool:
    return any(not raw[pair] and transformed[pair] for pair in raw)


def _cross_source_linkage_status(
    condition: str,
    raw: dict[tuple[str, str], bool],
    transformed: dict[tuple[str, str], bool],
) -> str:
    if raw == transformed:
        return STATUS_GENUINE
    if condition == "redaction-v1":
        return STATUS_EXPECTED_NON_PRESERVATION
    return STATUS_BROKEN


def _evidence_ids(view: ModelView) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(row["evidence_id"])
            for rows in view.structured_evidence.values()
            for row in rows
        )
    ) + tuple(sorted(entry.evidence_id for entry in view.log_evidence))


def _row_cardinality(view: ModelView) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted(
            (
                *((source, len(rows)) for source, rows in view.structured_evidence.items()),
                ("logs", len(view.log_evidence)),
            )
        )
    )


def _structured_row_order(view: ModelView) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        sorted(
            (
                source,
                tuple(str(row["evidence_id"]) for row in rows),
            )
            for source, rows in view.structured_evidence.items()
        )
    )


def _log_row_order(view: ModelView) -> tuple[str, ...]:
    return tuple(entry.evidence_id for entry in view.log_evidence)


def _source_structure(view: ModelView) -> tuple[str, ...]:
    return tuple(sorted((*view.structured_evidence.keys(), "logs")))


def _parses_raw_timestamp(value: str) -> bool:
    try:
        parse_timestamp(value)
    except ValueError:
        return False
    return True


def _status(value: bool) -> str:
    return STATUS_GENUINE if value else STATUS_BROKEN
