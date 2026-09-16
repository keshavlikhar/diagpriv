"""Offline privacy and semantic audits for relative-time-v1."""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from itertools import combinations
import re
from typing import Iterable

from diagbench.generators.incident_003_v2 import generate_incident_003_v2
from diagbench.relative_time import (
    RELATIVE_TIME_SEMANTICS_VERSION,
    intervals_overlap as relative_intervals_overlap,
    parse_relative_time,
)
from diagbench.schema import Incident, ModelView
from diagbench.schema.models import JSONValue
from diagbench.temporal import intervals_overlap, parse_timestamp
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations.format_preserving_v1 import format_preserving_incident
from diagpriv.transformations.hmac_v1 import hmac_incident
from diagpriv.transformations.redaction_v1 import redact_incident
from diagpriv.transformations.relative_time_v1 import relative_time_incident
from diagpriv.transformations.tokenization_v1 import tokenize_incident

AUDIT_VERSION = "relative-time-v1-offline-audit-v1"
MATRIX_VERSION = "incident-003-relative-time-matrix-v1"
PUBLIC_AUDIT_HMAC_KEY = bytes(range(32))

_RFC3339_SEARCH = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})"
)
_CALENDAR_SEARCH = re.compile(r"\d{4}-\d{2}-\d{2}")
_WALL_CLOCK_SEARCH = re.compile(r"\d{2}:\d{2}:\d{2}")
_EPOCH_SEARCH = re.compile(r"^-?\d{10,19}(?:\.\d+)?$")

_TEMPORAL_RELATIONS = {
    "ordered_before",
    "paired_before",
    "interval_seconds",
    "intervals_overlap",
}
_HEALTHY_TEMPORAL_INVARIANTS = {
    "control_completion_precedes_deadline",
    "successful_controls_bracket_target_chronologically",
    "benign_slow_control_succeeds_before_deadline",
}
_LEGITIMATE_TEMPORAL_INVARIANTS = {"legitimate_compensation_event_order"}


def audit_relative_time_incident(incident: Incident) -> dict[str, JSONValue]:
    """Audit one Incident 003 instance using only raw/transformed ModelViews."""
    raw = incident.model_view()
    transformed = relative_time_incident(incident)
    repeated = relative_time_incident(incident)
    raw_occurrences = _timestamp_occurrences(incident, raw)
    transformed_occurrences = _timestamp_occurrences(incident, transformed)
    raw_by_slot = {slot: value for slot, value in raw_occurrences}
    transformed_by_slot = {slot: value for slot, value in transformed_occurrences}
    if set(raw_by_slot) != set(transformed_by_slot):
        raise ValueError("Timestamp slots changed during relative-time transformation")

    parsed_raw = {slot: parse_timestamp(value) for slot, value in raw_by_slot.items()}
    parsed_relative = {
        slot: parse_relative_time(value)
        for slot, value in transformed_by_slot.items()
    }
    anchor = min(parsed_raw.values())
    expected_relative = {
        slot: _timedelta_milliseconds(instant - anchor)
        for slot, instant in parsed_raw.items()
    }
    original_values = tuple(raw_by_slot.values())
    transformed_values = tuple(transformed_by_slot.values())
    transformed_json = transformed.to_json()

    pairwise_equality = True
    pairwise_order = True
    pairwise_duration = True
    for first, second in combinations(raw_by_slot, 2):
        raw_first = parsed_raw[first]
        raw_second = parsed_raw[second]
        relative_first = parsed_relative[first]
        relative_second = parsed_relative[second]
        pairwise_equality &= (raw_first == raw_second) == (
            relative_first == relative_second
        )
        pairwise_order &= (raw_first < raw_second) == (
            relative_first < relative_second
        ) and (raw_first > raw_second) == (relative_first > relative_second)
        pairwise_duration &= _timedelta_milliseconds(
            raw_second - raw_first
        ) == (relative_second - relative_first)

    invariant_results = evaluate_invariants(
        incident,
        transformed,
        temporal_semantics_version=RELATIVE_TIME_SEMANTICS_VERSION,
    )
    invariant_by_name = {result.name: result for result in invariant_results}
    temporal_results = tuple(
        result
        for result in invariant_results
        if result.relation in _TEMPORAL_RELATIONS
    )
    essential_temporal_results = tuple(
        result for result in temporal_results if result.necessity == "essential"
    )
    overlap_preserved = _overlap_invariants_preserved(incident, transformed)
    deadline_preserved = all(
        invariant_by_name[name].preserved
        for name in (
            "target_deadline_precedes_original_completion",
            "target_compensation_after_deadline",
            "control_completion_precedes_deadline",
        )
    )

    checks = {
        "transformation_deterministic": transformed == repeated,
        "original_literal_timestamps_removed": (
            not set(original_values).intersection(transformed_values)
            and all(value not in transformed_json for value in original_values)
            and _literal_time_syntax_absent(transformed_values)
        ),
        "one_shared_incident_local_anchor": (
            min(parsed_relative.values()) == 0
            and parsed_relative == expected_relative
            and all(
                parsed_raw[slot]
                - timedelta(milliseconds=parsed_relative[slot])
                == anchor
                for slot in parsed_raw
            )
        ),
        "all_transformed_temporal_values_parse": (
            len(parsed_relative) == len(transformed_values)
        ),
        "timestamp_equality_preserved": pairwise_equality,
        "strict_ordering_preserved": pairwise_order,
        "required_durations_preserved": pairwise_duration,
        "positive_overlap_preserved": overlap_preserved,
        "deadline_crossing_preserved": deadline_preserved,
        "all_essential_temporal_invariants_preserved": all(
            result.preserved and result.status == "genuine_preservation"
            for result in essential_temporal_results
        ),
        "healthy_control_temporal_invariants_preserved": all(
            invariant_by_name[name].preserved
            for name in _HEALTHY_TEMPORAL_INVARIANTS
        ),
        "legitimate_compensation_temporal_invariants_preserved": all(
            invariant_by_name[name].preserved
            for name in _LEGITIMATE_TEMPORAL_INVARIANTS
        ),
        "non_temporal_model_view_unchanged": (
            _temporal_masked_view(incident, raw)
            == _temporal_masked_view(incident, transformed)
        ),
        "row_cardinality_unchanged": _row_cardinality(raw)
        == _row_cardinality(transformed),
        "row_order_unchanged": _row_order(raw) == _row_order(transformed),
        "evidence_ids_unchanged": _evidence_ids(raw) == _evidence_ids(transformed),
        "source_and_linkage_unchanged": _linkage_projection(raw)
        == _linkage_projection(transformed),
    }
    return {
        "audit_version": AUDIT_VERSION,
        "seed": incident.metadata["seed"],
        "timestamp_occurrences": len(raw_occurrences),
        "distinct_raw_instants": len(set(parsed_raw.values())),
        "anchor_is_minimum_visible_instant": True,
        "checks": checks,
        "passed": all(checks.values()),
        "temporal_invariant_status": {
            result.name: result.status for result in temporal_results
        },
    }


def audit_relative_time_range(seeds: Iterable[int]) -> dict[str, JSONValue]:
    """Run the frozen development-construction audit without protected seeds."""
    seed_values = tuple(seeds)
    if not seed_values or any(seed < 1000 or seed > 1199 for seed in seed_values):
        raise ValueError("Relative-time audit is restricted to seeds 1000-1199")
    reports = tuple(
        audit_relative_time_incident(generate_incident_003_v2(seed))
        for seed in seed_values
    )
    check_names = tuple(reports[0]["checks"])
    check_counts = {
        name: sum(bool(report["checks"][name]) for report in reports)
        for name in check_names
    }
    granularity = _granularity_audit(seed_values)
    equality_1021 = audit_seed_1021_equality()
    return {
        "audit_version": AUDIT_VERSION,
        "sample_size": len(seed_values),
        "seed_min": min(seed_values),
        "seed_max": max(seed_values),
        "per_instance_check_count": len(check_names),
        "check_evaluations": len(seed_values) * len(check_names),
        "passed_check_evaluations": sum(check_counts.values()),
        "failed_check_evaluations": (
            len(seed_values) * len(check_names) - sum(check_counts.values())
        ),
        "checks": {
            name: {"passed": count == len(seed_values), "count": count}
            for name, count in sorted(check_counts.items())
        },
        "precision_audit": granularity,
        "seed_1021_equality": equality_1021,
        "passed": (
            all(report["passed"] for report in reports)
            and bool(equality_1021["passed"])
            and bool(granularity["milliseconds_required"])
        ),
    }


def audit_seed_1021_equality() -> dict[str, JSONValue]:
    """Verify the reviewed equal-completion seed remains genuinely equal."""
    incident = generate_incident_003_v2(1021)
    raw = incident.model_view()
    transformed = relative_time_incident(incident)
    target = str(incident.metadata["target_operation_id"])
    raw_execution = _row(raw, "execution_observations", target)
    raw_compensation = _row(raw, "compensation_records", target)
    transformed_execution = _row(transformed, "execution_observations", target)
    transformed_compensation = _row(transformed, "compensation_records", target)
    raw_equal = raw_execution["completed_at"] == raw_compensation["completed_at"]
    transformed_equal = (
        transformed_execution["completed_at"]
        == transformed_compensation["completed_at"]
    )
    parsed_equal = parse_relative_time(
        str(transformed_execution["completed_at"])
    ) == parse_relative_time(str(transformed_compensation["completed_at"]))
    return {
        "seed": 1021,
        "raw_equal": raw_equal,
        "transformed_equal": transformed_equal,
        "parsed_equal": parsed_equal,
        "passed": raw_equal and transformed_equal and parsed_equal,
    }


def incident_003_privacy_invariant_matrix(
    incident: Incident,
) -> dict[str, JSONValue]:
    """Compare implemented timestamp conditions without making model claims."""
    raw = incident.model_view()
    views = {
        "raw": raw,
        "redaction-v1": redact_incident(incident),
        "hmac-v1": hmac_incident(incident, key=PUBLIC_AUDIT_HMAC_KEY),
        "tokenization-v1": tokenize_incident(incident),
        "format-preserving-v1": format_preserving_incident(incident),
        "relative-time-v1": relative_time_incident(incident),
    }
    raw_values = tuple(value for _, value in _timestamp_occurrences(incident, raw))
    report: dict[str, JSONValue] = {}
    for condition, view in views.items():
        values = tuple(value for _, value in _timestamp_occurrences(incident, view))
        if condition == "raw":
            parser = parse_timestamp
            semantics = "temporal-semantics-v1"
        elif condition == "relative-time-v1":
            parser = parse_relative_time
            semantics = RELATIVE_TIME_SEMANTICS_VERSION
        else:
            parser = None
            semantics = None

        parseable = parser is not None and all(
            _parses(parser, value) for value in values
        )
        temporal_invariants = False
        if semantics is not None:
            temporal_invariants = all(
                result.preserved
                for result in evaluate_invariants(
                    incident,
                    view,
                    temporal_semantics_version=semantics,
                )
                if result.relation in _TEMPORAL_RELATIONS
                and result.necessity != "discardable"
            )
        equality_status = _equality_status(raw_values, values, condition)
        relation_status = (
            "genuine_preservation"
            if parseable and temporal_invariants
            else "expected_non_preservation"
        )
        report[condition] = {
            "literal_timestamp_secrecy": (
                "broken"
                if condition == "raw"
                else (
                    "genuine_preservation"
                    if not set(raw_values).intersection(values)
                    else "broken"
                )
            ),
            "parseable_temporal_values": (
                "genuine_preservation"
                if parseable
                else "expected_non_preservation"
            ),
            "timestamp_equality": equality_status,
            "strict_ordering": relation_status,
            "duration": relation_status,
            "overlap": relation_status,
            "deadline_crossing": relation_status,
            "required_temporal_invariants": relation_status,
        }
    return {"matrix_version": MATRIX_VERSION, "conditions": report}


def _timestamp_occurrences(
    incident: Incident, view: ModelView
) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for annotation in incident.sensitive_fields:
        if annotation.classification != "operational_timestamp":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        if source == "logs":
            for index, entry in enumerate(view.log_evidence):
                data = entry.to_dict()
                value = data[field] if field in data else entry.attributes[field]
                result.append((f"logs:{index}:{field}", str(value)))
        else:
            for index, row in enumerate(view.structured_evidence[source]):
                result.append((f"{source}:{index}:{field}", str(row[field])))
    return tuple(result)


def _literal_time_syntax_absent(values: tuple[str, ...]) -> bool:
    return all(
        _RFC3339_SEARCH.search(value) is None
        and _CALENDAR_SEARCH.search(value) is None
        and _WALL_CLOCK_SEARCH.search(value) is None
        and "Z" not in value
        and _EPOCH_SEARCH.fullmatch(value) is None
        for value in values
    )


def _temporal_masked_view(incident: Incident, view: ModelView) -> dict[str, JSONValue]:
    data = deepcopy(view.to_dict())
    for annotation in incident.sensitive_fields:
        if annotation.classification != "operational_timestamp":
            continue
        source, field = annotation.path.split(".", maxsplit=1)
        if source == "logs":
            logs = data["log_evidence"]
            assert isinstance(logs, list)
            for entry in logs:
                assert isinstance(entry, dict)
                if field in entry:
                    entry[field] = "[TEMPORAL]"
                else:
                    attributes = entry["attributes"]
                    assert isinstance(attributes, dict)
                    if field in attributes:
                        attributes[field] = "[TEMPORAL]"
        else:
            structured = data["structured_evidence"]
            assert isinstance(structured, dict)
            rows = structured[source]
            assert isinstance(rows, list)
            for row in rows:
                assert isinstance(row, dict)
                row[field] = "[TEMPORAL]"
    return data


def _overlap_invariants_preserved(incident: Incident, transformed: ModelView) -> bool:
    for invariant in incident.diagnostic_invariants:
        if invariant.relation != "intervals_overlap":
            continue
        raw_values = tuple(str(incident.resolve_reference(ref)) for ref in invariant.operands)
        transformed_values = tuple(
            str(_resolve_view_reference(transformed, ref)) for ref in invariant.operands
        )
        if intervals_overlap(*raw_values) != relative_intervals_overlap(
            *transformed_values
        ):
            return False
    return True


def _resolve_view_reference(view: ModelView, reference: object) -> JSONValue:
    source = getattr(reference, "source")
    selector = getattr(reference, "selector")
    field = getattr(reference, "field")
    candidates = (
        [entry.to_dict() for entry in view.log_evidence]
        if source == "logs"
        else view.structured_evidence[source]
    )
    matches = [
        row
        for row in candidates
        if all(row.get(key) == value for key, value in selector.items())
    ]
    if len(matches) != 1:
        raise ValueError("Audit evidence reference did not resolve exactly once")
    row = matches[0]
    if field is None:
        return row
    if field in row:
        return row[field]
    attributes = row.get("attributes")
    if isinstance(attributes, dict) and field in attributes:
        return attributes[field]
    raise ValueError("Audit evidence field is absent")


def _row_cardinality(view: ModelView) -> tuple[tuple[str, int], ...]:
    return tuple(
        sorted(
            (
                *((source, len(rows)) for source, rows in view.structured_evidence.items()),
                ("logs", len(view.log_evidence)),
            )
        )
    )


def _row_order(view: ModelView) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple(
        sorted(
            (
                *(
                    (
                        source,
                        tuple(str(row["evidence_id"]) for row in rows),
                    )
                    for source, rows in view.structured_evidence.items()
                ),
                ("logs", tuple(entry.evidence_id for entry in view.log_evidence)),
            )
        )
    )


def _evidence_ids(view: ModelView) -> tuple[str, ...]:
    return tuple(
        sorted(
            str(row["evidence_id"])
            for rows in view.structured_evidence.values()
            for row in rows
        )
    ) + tuple(sorted(entry.evidence_id for entry in view.log_evidence))


def _linkage_projection(view: ModelView) -> tuple[tuple[str, ...], ...]:
    structured = tuple(
        tuple(str(row.get("operation_id", "")) for row in rows)
        for _, rows in sorted(view.structured_evidence.items())
    )
    logs = tuple(str(entry.attributes.get("operation_id", "")) for entry in view.log_evidence)
    return (*structured, logs)


def _granularity_audit(seeds: tuple[int, ...]) -> dict[str, JSONValue]:
    millisecond_aligned = True
    subsecond_distinctions = 0
    minimum_positive_delta_ms: int | None = None
    for seed in seeds:
        incident = generate_incident_003_v2(seed)
        values = tuple(
            parse_timestamp(value)
            for _, value in _timestamp_occurrences(incident, incident.model_view())
        )
        anchor = min(values)
        offsets = sorted({_timedelta_milliseconds(value - anchor) for value in values})
        millisecond_aligned &= all(value.microsecond % 1000 == 0 for value in values)
        for first, second in zip(offsets, offsets[1:]):
            delta = second - first
            if delta > 0:
                minimum_positive_delta_ms = (
                    delta
                    if minimum_positive_delta_ms is None
                    else min(minimum_positive_delta_ms, delta)
                )
            if first // 1000 == second // 1000:
                subsecond_distinctions += 1
    return {
        "source_precision": "milliseconds",
        "all_values_millisecond_aligned": millisecond_aligned,
        "minimum_positive_delta_ms": minimum_positive_delta_ms,
        "strict_distinctions_lost_at_second_precision": subsecond_distinctions,
        "milliseconds_required": millisecond_aligned and subsecond_distinctions > 0,
    }


def _row(view: ModelView, source: str, operation_id: str) -> dict[str, JSONValue]:
    return next(
        row
        for row in view.structured_evidence[source]
        if row["operation_id"] == operation_id
    )


def _timedelta_milliseconds(delta: object) -> int:
    days = getattr(delta, "days")
    seconds = getattr(delta, "seconds")
    microseconds = getattr(delta, "microseconds")
    total_microseconds = (days * 86_400 + seconds) * 1_000_000 + microseconds
    if total_microseconds % 1000:
        raise ValueError("Audit encountered a non-millisecond-aligned duration")
    return total_microseconds // 1000


def _parses(parser: object, value: str) -> bool:
    try:
        parser(value)  # type: ignore[operator]
    except ValueError:
        return False
    return True


def _equality_status(
    raw_values: tuple[str, ...], transformed_values: tuple[str, ...], condition: str
) -> str:
    equality_preserved = all(
        (raw_values[first] == raw_values[second])
        == (transformed_values[first] == transformed_values[second])
        for first in range(len(raw_values))
        for second in range(first + 1, len(raw_values))
    )
    if equality_preserved:
        return "genuine_preservation"
    if condition == "redaction-v1" and len(set(transformed_values)) < len(
        set(raw_values)
    ):
        return "degenerate"
    return "expected_non_preservation"
