"""Evaluate oracle diagnostic invariants against a transformed ModelView."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal

from diagbench.schema import DiagnosticInvariant, EvidenceReference, Incident, ModelView
from diagbench.schema.models import JSONValue

InvariantStatus = Literal[
    "genuine_preservation",
    "broken",
    "degenerate_all_to_one",
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
    raise ValueError(f"Unsupported invariant relation: {invariant.relation}")


def _as_datetime(value: JSONValue) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"Timestamp invariant operand must be a string: {value!r}")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
