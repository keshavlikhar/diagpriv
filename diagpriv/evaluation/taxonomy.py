"""Deterministic label normalization for the initial RCA protocol."""

from __future__ import annotations

import re


def normalize_label(value: str) -> str:
    """Normalize a model-supplied label without semantic model grading."""
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return normalized.strip("_")


OUTCOME_ALIASES = {
    "duplicate_payment": "duplicate_payment",
    "double_charge": "duplicate_payment",
    "customer_charged_twice": "duplicate_payment",
    "repeated_payment": "duplicate_payment",
}
TRIGGER_ALIASES = {
    "retry_after_timeout": "retry_after_timeout",
    "caller_retry_after_timeout": "retry_after_timeout",
    "repeated_request_after_timeout": "retry_after_timeout",
    "request_repeated_after_timeout": "retry_after_timeout",
}
MECHANISM_ALIASES = {
    "missing_or_ineffective_idempotency": "missing_or_ineffective_idempotency",
    "missing_idempotency": "missing_or_ineffective_idempotency",
    "ineffective_idempotency": "missing_or_ineffective_idempotency",
    "request_not_deduplicated": "missing_or_ineffective_idempotency",
    "lack_of_idempotency": "missing_or_ineffective_idempotency",
}


def canonical_category(field: str, value: str) -> str | None:
    normalized = normalize_label(value)
    aliases = {
        "observed_outcome": OUTCOME_ALIASES,
        "trigger": TRIGGER_ALIASES,
        "failure_mechanism": MECHANISM_ALIASES,
    }
    return aliases[field].get(normalized)

