"""Evaluate oracle diagnostic invariants against a transformed ModelView."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal

from diagbench.schema import DiagnosticInvariant, EvidenceReference, Incident, ModelView
from diagbench.schema.models import JSONValue
from diagbench.structural import structural_defect_matches, structural_signature

InvariantStatus = Literal[
    "genuine_preservation",
    "broken",
    "degenerate_all_to_one",
    "degenerate_pattern_collapse",
    "expected_non_preservation",
]


@dataclass(frozen=True, slots=True)
class InvariantResult:
    name: str
    relation: str
    necessity: str
    preserved: bool
    status: InvariantStatus

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def evaluate_invariants(
    incident: Incident, transformed_view: ModelView
) -> tuple[InvariantResult, ...]:
    """Evaluate declared relationships without exposing oracle data in ModelView."""
    results: list[InvariantResult] = []
    for invariant in incident.diagnostic_invariants:
        preserved = _invariant_holds(incident, transformed_view, invariant)
        results.append(
            InvariantResult(
                name=invariant.name,
                relation=invariant.relation,
                necessity=invariant.necessity,
                preserved=preserved,
                status=_invariant_status(
                    incident, transformed_view, invariant, preserved
                ),
            )
        )
    return tuple(results)


def _invariant_status(
    incident: Incident,
    model_view: ModelView,
    invariant: DiagnosticInvariant,
    preserved: bool,
) -> InvariantStatus:
    if (
        preserved
        and invariant.relation == "preserve_literal"
        and invariant.expected is False
    ):
        return "expected_non_preservation"
    if not preserved:
        return "broken"
    if invariant.relation == "equal" and _is_degenerate_all_to_one(
        incident, model_view, invariant
    ):
        return "degenerate_all_to_one"
    if invariant.relation == "same_structural_pattern" and _is_pattern_collapse(
        incident, model_view, invariant
    ):
        return "degenerate_pattern_collapse"
    return "genuine_preservation"


def _is_degenerate_all_to_one(
    incident: Incident, model_view: ModelView, invariant: DiagnosticInvariant
) -> bool:
    operand_paths = {
        f"{reference.source}.{reference.field}"
        for reference in invariant.operands
        if reference.field is not None
    }
    if len(operand_paths) != 1:
        return False
    path = next(iter(operand_paths))
    if path not in {annotation.path for annotation in incident.sensitive_fields}:
        return False
    before = _path_values(incident.model_view(), path)
    after = _path_values(model_view, path)
    return len(_distinct(before)) > 1 and len(_distinct(after)) == 1


def _is_pattern_collapse(
    incident: Incident, model_view: ModelView, invariant: DiagnosticInvariant
) -> bool:
    operand_paths = {
        f"{reference.source}.{reference.field}"
        for reference in invariant.operands
        if reference.field is not None
    }
    sensitive_paths = {annotation.path for annotation in incident.sensitive_fields}
    if not operand_paths or not operand_paths.issubset(sensitive_paths):
        return False
    before = tuple(
        value
        for path in sorted(operand_paths)
        for value in _path_values(incident.model_view(), path)
        if isinstance(value, str)
    )
    after = tuple(
        value
        for path in sorted(operand_paths)
        for value in _path_values(model_view, path)
        if isinstance(value, str)
    )
    before_patterns = {structural_signature(value) for value in before}
    after_patterns = {structural_signature(value) for value in after}
    return len(before_patterns) > 1 and len(after_patterns) == 1


def _path_values(model_view: ModelView, path: str) -> tuple[JSONValue, ...]:
    source, field = path.split(".", maxsplit=1)
    if source != "logs":
        return tuple(row[field] for row in model_view.structured_evidence[source])
    values: list[JSONValue] = []
    for entry in model_view.log_evidence:
        data = entry.to_dict()
        if field in data:
            values.append(data[field])
        elif field in entry.attributes:
            values.append(entry.attributes[field])
    return tuple(values)


def _distinct(values: tuple[JSONValue, ...]) -> tuple[JSONValue, ...]:
    distinct: list[JSONValue] = []
    for value in values:
        if value not in distinct:
            distinct.append(value)
    return tuple(distinct)


def _resolve_view_reference(
    model_view: ModelView, reference: EvidenceReference
) -> JSONValue:
    if reference.source == "logs":
        candidates = [entry.to_dict() for entry in model_view.log_evidence]
    else:
        try:
            candidates = model_view.structured_evidence[reference.source]
        except KeyError as error:
            raise ValueError(f"Unknown evidence source: {reference.source}") from error

    matches = [
        item
        for item in candidates
        if all(item.get(key) == value for key, value in reference.selector.items())
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Reference must resolve once; found {len(matches)} matches: {reference}"
        )
    selected = matches[0]
    if reference.field is None:
        return selected
    if reference.field in selected:
        return selected[reference.field]
    attributes = selected.get("attributes")
    if isinstance(attributes, dict) and reference.field in attributes:
        return attributes[reference.field]
    raise ValueError(f"Unknown referenced field: {reference.field}")


def _invariant_holds(
    incident: Incident, model_view: ModelView, invariant: DiagnosticInvariant
) -> bool:
    if invariant.relation == "match_count":
        return _match_count(model_view, invariant) == invariant.expected
    after = tuple(
        _resolve_view_reference(model_view, reference)
        for reference in invariant.operands
    )
    if invariant.relation == "equal":
        equal = all(value == after[0] for value in after[1:])
        return equal and (invariant.expected is True or after[0] == invariant.expected)
    if invariant.relation == "not_equal":
        return len(after) == 2 and after[0] != after[1]
    if invariant.relation == "all_distinct":
        return all(
            value not in after[:index] for index, value in enumerate(after)
        )
    if invariant.relation == "ordered_before":
        timestamps = tuple(_as_datetime(value) for value in after)
        return all(first < second for first, second in zip(timestamps, timestamps[1:]))
    if invariant.relation == "interval_seconds":
        if len(after) != 2:
            return False
        interval = (_as_datetime(after[1]) - _as_datetime(after[0])).total_seconds()
        return interval == invariant.expected
    if invariant.relation == "row_count":
        return len(after) == invariant.expected
    if invariant.relation == "preserve_literal":
        before = tuple(
            incident.resolve_reference(reference) for reference in invariant.operands
        )
        literal_preserved = before == after
        return literal_preserved is invariant.expected
    if invariant.relation == "same_structural_pattern":
        return (
            len(after) >= 2
            and all(isinstance(value, str) for value in after)
            and len({structural_signature(value) for value in after}) == 1
            and invariant.expected is True
        )
    if invariant.relation == "structural_pattern_anomaly":
        if len(after) < 4 or not all(isinstance(value, str) for value in after):
            return False
        target, *controls = after
        control_patterns = {structural_signature(value) for value in controls}
        return (
            len(control_patterns) == 1
            and structural_signature(target) not in control_patterns
            and invariant.expected is True
        )
    if invariant.relation == "structural_defect":
        if len(after) < 4 or not all(isinstance(value, str) for value in after):
            return False
        if not isinstance(invariant.expected, str):
            return False
        target, *controls = after
        return structural_defect_matches(tuple(controls), target, invariant.expected)
    if invariant.relation == "length_delta":
        return (
            len(after) == 2
            and all(isinstance(value, str) for value in after)
            and isinstance(invariant.expected, int)
            and len(after[0]) - len(after[1]) == invariant.expected
        )
    if invariant.relation == "sequence_equals":
        return list(after) == invariant.expected
    raise ValueError(f"Unsupported invariant relation: {invariant.relation}")


def _match_count(model_view: ModelView, invariant: DiagnosticInvariant) -> int:
    if len(invariant.operands) != 1:
        raise ValueError("match_count requires exactly one evidence reference")
    reference = invariant.operands[0]
    if reference.field is not None:
        raise ValueError("match_count references a row, not a field")
    if reference.source == "logs":
        candidates = [entry.to_dict() for entry in model_view.log_evidence]
    else:
        try:
            candidates = model_view.structured_evidence[reference.source]
        except KeyError as error:
            raise ValueError(f"Unknown evidence source: {reference.source}") from error
    return sum(
        all(candidate.get(key) == value for key, value in reference.selector.items())
        for candidate in candidates
    )


def _as_datetime(value: JSONValue) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"Timestamp invariant operand must be a string: {value!r}")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
