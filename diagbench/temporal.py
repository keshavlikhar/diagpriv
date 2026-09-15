"""Strict, reusable temporal semantics for benchmark-visible timestamps."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Iterable

TEMPORAL_SEMANTICS_VERSION = "temporal-semantics-v1"

_RFC3339_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)


def parse_timestamp(value: str) -> datetime:
    """Parse one explicit, timezone-aware RFC 3339 timestamp.

    Version 1 accepts a ``T`` separator, optional fractional seconds with at
    most microsecond precision, and either ``Z`` or an explicit numeric UTC
    offset. Naive datetimes, named timezones, whitespace normalization, and
    ambiguous alternate forms are rejected.
    """
    if not isinstance(value, str) or not _RFC3339_PATTERN.fullmatch(value):
        raise ValueError(
            f"{TEMPORAL_SEMANTICS_VERSION} requires an explicit RFC 3339 timestamp"
        )
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as error:
        raise ValueError(
            f"{TEMPORAL_SEMANTICS_VERSION} rejected a malformed timestamp"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(
            f"{TEMPORAL_SEMANTICS_VERSION} requires a timezone-aware timestamp"
        )
    return parsed


def before(first: str, second: str) -> bool:
    """Return whether the first instant is strictly before the second."""
    return parse_timestamp(first) < parse_timestamp(second)


def after(first: str, second: str) -> bool:
    """Return whether the first instant is strictly after the second."""
    return parse_timestamp(first) > parse_timestamp(second)


def equal(first: str, second: str) -> bool:
    """Return whether two timestamp strings denote the same instant."""
    return parse_timestamp(first) == parse_timestamp(second)


def interval_duration_seconds(start: str, end: str) -> float:
    """Return a non-negative interval duration in seconds."""
    start_time = parse_timestamp(start)
    end_time = parse_timestamp(end)
    if end_time < start_time:
        raise ValueError("Temporal interval end precedes its start")
    return (end_time - start_time).total_seconds()


def intervals_overlap(
    first_start: str,
    first_end: str,
    second_start: str,
    second_end: str,
) -> bool:
    """Return whether two valid half-open intervals overlap positively.

    Intervals use ``[start, end)`` semantics. Merely touching at one endpoint
    is not overlap, and zero-length or reversed intervals are rejected.
    """
    first_start_time = parse_timestamp(first_start)
    first_end_time = parse_timestamp(first_end)
    second_start_time = parse_timestamp(second_start)
    second_end_time = parse_timestamp(second_end)
    if first_start_time >= first_end_time or second_start_time >= second_end_time:
        raise ValueError("Temporal overlap requires two positive-duration intervals")
    return max(first_start_time, second_start_time) < min(
        first_end_time, second_end_time
    )


def ordered_sequence(values: Iterable[str], *, allow_equal: bool = False) -> bool:
    """Return whether a sequence is monotonically ordered in time."""
    parsed = tuple(parse_timestamp(value) for value in values)
    if len(parsed) < 2:
        raise ValueError("Temporal ordering requires at least two timestamps")
    comparator = (lambda left, right: left <= right) if allow_equal else (
        lambda left, right: left < right
    )
    return all(comparator(left, right) for left, right in zip(parsed, parsed[1:]))


def paired_before(values: Iterable[str]) -> bool:
    """Require every consecutive timestamp pair to be strictly ordered."""
    pairs = tuple(values)
    if not pairs or len(pairs) % 2:
        raise ValueError("Paired temporal ordering requires a non-empty even sequence")
    return all(before(pairs[index], pairs[index + 1]) for index in range(0, len(pairs), 2))
