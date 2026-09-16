"""Strict semantics for the relative-time-v1 model-visible representation."""

from __future__ import annotations

import re
from typing import Iterable

RELATIVE_TIME_SEMANTICS_VERSION = "relative-time-semantics-v1"
RELATIVE_TIME_UNIT = "milliseconds"

_RELATIVE_TIME_PATTERN = re.compile(r"^T\+(0|[1-9]\d*)ms$")


def parse_relative_time(value: str) -> int:
    """Parse one canonical nonnegative relative offset into milliseconds."""
    if not isinstance(value, str):
        raise ValueError(
            f"{RELATIVE_TIME_SEMANTICS_VERSION} requires a string offset"
        )
    match = _RELATIVE_TIME_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError(
            f"{RELATIVE_TIME_SEMANTICS_VERSION} requires T+<integer>ms"
        )
    return int(match.group(1))


def before(first: str, second: str) -> bool:
    """Return whether the first relative instant is strictly earlier."""
    return parse_relative_time(first) < parse_relative_time(second)


def after(first: str, second: str) -> bool:
    """Return whether the first relative instant is strictly later."""
    return parse_relative_time(first) > parse_relative_time(second)


def equal(first: str, second: str) -> bool:
    """Return whether two relative values denote the same incident-local instant."""
    return parse_relative_time(first) == parse_relative_time(second)


def interval_duration_seconds(start: str, end: str) -> float:
    """Return a nonnegative relative interval duration in seconds."""
    start_ms = parse_relative_time(start)
    end_ms = parse_relative_time(end)
    if end_ms < start_ms:
        raise ValueError("Relative-time interval end precedes its start")
    return (end_ms - start_ms) / 1000


def intervals_overlap(
    first_start: str,
    first_end: str,
    second_start: str,
    second_end: str,
) -> bool:
    """Return whether two positive half-open relative intervals overlap."""
    first_start_ms = parse_relative_time(first_start)
    first_end_ms = parse_relative_time(first_end)
    second_start_ms = parse_relative_time(second_start)
    second_end_ms = parse_relative_time(second_end)
    if first_start_ms >= first_end_ms or second_start_ms >= second_end_ms:
        raise ValueError("Relative-time overlap requires positive-duration intervals")
    return max(first_start_ms, second_start_ms) < min(
        first_end_ms, second_end_ms
    )


def ordered_sequence(values: Iterable[str], *, allow_equal: bool = False) -> bool:
    """Return whether a relative-time sequence is monotonically ordered."""
    parsed = tuple(parse_relative_time(value) for value in values)
    if len(parsed) < 2:
        raise ValueError("Relative ordering requires at least two timestamps")
    comparator = (lambda left, right: left <= right) if allow_equal else (
        lambda left, right: left < right
    )
    return all(comparator(left, right) for left, right in zip(parsed, parsed[1:]))


def paired_before(values: Iterable[str]) -> bool:
    """Require every consecutive relative timestamp pair to be strictly ordered."""
    pairs = tuple(values)
    if not pairs or len(pairs) % 2:
        raise ValueError("Paired relative ordering requires a non-empty even sequence")
    return all(
        before(pairs[index], pairs[index + 1])
        for index in range(0, len(pairs), 2)
    )
