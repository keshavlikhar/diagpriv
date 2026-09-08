"""Generate Incident 001: Duplicate Payment."""

from __future__ import annotations

import argparse
from pathlib import Path
import random

from diagbench.schema import (
    DiagnosticInvariant,
    ExpectedEvidence,
    Incident,
    LogEntry,
    SensitiveField,
)

DEFAULT_SEED = 1001
DEFAULT_OUTPUT = (
    Path(__file__).parents[1]
    / "incidents"
    / "incident_001_duplicate_payment"
    / "incident.json"
)


def generate_incident_001(seed: int = DEFAULT_SEED) -> Incident:
    """Create deterministic, entirely fictional duplicate-payment evidence."""
    rng = random.Random(seed)
    suffix = rng.randrange(100_000, 999_999)
    customer_id = f"SYN-CUST-{suffix}"
    account_id = f"SYN-ACCT-{rng.randrange(100_000, 999_999)}"
    request_id = f"SYN-REQ-{rng.randrange(100_000, 999_999)}"

    structured_evidence = {
        "customers": [
            {
                "customer_id": customer_id,
                "name": "Avery Example (Fictional)",
                "ssn": "000-12-3456",
                "email": "avery.example@example.invalid",
            },
            {
                "customer_id": "SYN-CUST-REFERENCE",
                "name": "Morgan Sample (Fictional)",
                "ssn": "000-98-7654",
                "email": "morgan.sample@example.invalid",
            },
        ],
        "accounts": [
            {"account_id": account_id, "customer_id": customer_id},
            {"account_id": "SYN-ACCT-REFERENCE", "customer_id": "SYN-CUST-REFERENCE"},
        ],
        "payments": [
            {
                "payment_id": "SYN-PAY-NORMAL-BEFORE",
                "customer_id": "SYN-CUST-REFERENCE",
                "account_id": "SYN-ACCT-REFERENCE",
                "request_id": "SYN-REQ-NORMAL-BEFORE",
                "amount": "19.95",
                "status": "succeeded",
                "created_at": "2030-04-12T09:14:40.000Z",
            },
            {
                "payment_id": "SYN-PAY-DUPLICATE-A",
                "customer_id": customer_id,
                "account_id": account_id,
                "request_id": request_id,
                "amount": "84.20",
                "status": "succeeded",
                "created_at": "2030-04-12T09:15:02.120Z",
            },
            {
                "payment_id": "SYN-PAY-DUPLICATE-B",
                "customer_id": customer_id,
                "account_id": account_id,
                "request_id": request_id,
                "amount": "84.20",
                "status": "succeeded",
                "created_at": "2030-04-12T09:15:04.887Z",
            },
            {
                "payment_id": "SYN-PAY-NORMAL-AFTER",
                "customer_id": "SYN-CUST-REFERENCE",
                "account_id": "SYN-ACCT-REFERENCE",
                "request_id": "SYN-REQ-NORMAL-AFTER",
                "amount": "7.50",
                "status": "succeeded",
                "created_at": "2030-04-12T09:16:10.000Z",
            },
        ],
    }

    logs = (
        LogEntry(
            "2030-04-12T09:15:02.100Z",
            "INFO",
            "payment-api",
            "Payment request accepted",
            {"request_id": request_id, "customer_id": customer_id, "attempt": 1},
        ),
        LogEntry(
            "2030-04-12T09:15:02.120Z",
            "INFO",
            "payment-worker",
            "Payment inserted",
            {
                "request_id": request_id,
                "payment_id": "SYN-PAY-DUPLICATE-A",
                "idempotency_check": False,
            },
        ),
        LogEntry(
            "2030-04-12T09:15:04.800Z",
            "WARN",
            "payment-api",
            "Upstream timeout caused client retry",
            {"request_id": request_id, "attempt": 2},
        ),
        LogEntry(
            "2030-04-12T09:15:04.887Z",
            "INFO",
            "payment-worker",
            "Retry inserted as a new payment",
            {
                "request_id": request_id,
                "payment_id": "SYN-PAY-DUPLICATE-B",
                "idempotency_check": False,
            },
        ),
        LogEntry(
            "2030-04-12T09:16:10.000Z",
            "INFO",
            "payment-worker",
            "Unrelated payment inserted",
            {"request_id": "SYN-REQ-NORMAL-AFTER", "attempt": 1},
        ),
    )

    sensitive_fields = (
        SensitiveField("customers.name", "direct_identifier", "remove_or_pseudonymize", "Identity is not diagnostic."),
        SensitiveField("customers.ssn", "highly_sensitive_identifier", "remove_or_pseudonymize", "Value is wholly synthetic and not diagnostic."),
        SensitiveField("customers.email", "contact_identifier", "remove_or_pseudonymize", "Contact address is not diagnostic."),
        SensitiveField("customers.customer_id", "customer_identifier", "consistent_pseudonym", "Joinability is diagnostic; the literal ID is not."),
        SensitiveField("accounts.customer_id", "customer_identifier", "consistent_pseudonym", "This copy must remain joinable to the customer record."),
        SensitiveField("accounts.account_id", "account_identifier", "consistent_pseudonym", "Account equality is diagnostic; the literal ID is not."),
        SensitiveField("payments.customer_id", "customer_identifier", "consistent_pseudonym", "Customer equality across payment rows is diagnostic."),
        SensitiveField("payments.account_id", "account_identifier", "consistent_pseudonym", "Account equality across payment rows is diagnostic."),
        SensitiveField("logs.customer_id", "customer_identifier", "consistent_pseudonym", "Cross-source identity may be diagnostic."),
        SensitiveField("payments.request_id", "operational_identifier", "consistent_pseudonym", "The request value is replaceable but its correlation must survive."),
        SensitiveField("logs.request_id", "operational_identifier", "consistent_pseudonym", "The request value is replaceable but its correlation must survive."),
        SensitiveField("payments.payment_id", "operational_identifier", "pseudonymize_independently", "Payment-row distinction matters; literal values do not."),
        SensitiveField("logs.payment_id", "operational_identifier", "pseudonymize_independently", "Log-to-row correlation matters; literal values do not."),
    )

    invariants = (
        DiagnosticInvariant("customer_equality", "equality", ("payments.customer_id",), True, "Duplicate rows must retain the same customer relationship."),
        DiagnosticInvariant("account_equality", "equality", ("payments.account_id",), True, "Duplicate rows must retain the same account relationship."),
        DiagnosticInvariant("payment_duplicate", "duplicates", ("payments.customer_id", "payments.account_id", "payments.request_id", "payments.amount"), True, "The two successful records must remain recognizable as one logical payment."),
        DiagnosticInvariant("request_correlation", "cross_source_identity", ("payments.request_id", "logs.request_id"), True, "Payment rows must correlate with request and retry logs."),
        DiagnosticInvariant("amount_equality", "numeric_equality", ("payments.amount",), True, "The two problematic amounts must remain equal."),
        DiagnosticInvariant("timestamp_order", "ordering", ("payments.created_at", "logs.timestamp"), True, "Initial processing must precede the timeout, retry, and duplicate insert."),
        DiagnosticInvariant("duplicate_interval", "temporal_interval", ("payments.created_at",), True, "The 2.767-second gap between duplicate records is diagnostic."),
        DiagnosticInvariant("payment_row_count", "row_cardinality", ("payments.payment_id",), True, "Both duplicate rows and surrounding rows must remain present."),
        DiagnosticInvariant("literal_customer_identity", "string_format", ("customers.name", "customers.ssn", "customers.email", "customers.customer_id"), False, "Literal identity values are unnecessary for this diagnosis."),
        DiagnosticInvariant("literal_account_identity", "string_format", ("accounts.account_id",), False, "The literal account identifier is unnecessary for this diagnosis."),
    )

    expected = (
        ExpectedEvidence("Two successful payments share customer, account, request, and amount.", ("payments.customer_id", "payments.account_id", "payments.request_id", "payments.amount", "payments.status")),
        ExpectedEvidence("The second payment follows the first by 2.767 seconds.", ("payments.created_at",)),
        ExpectedEvidence("Logs show a timeout-triggered retry and no idempotency check on either insert.", ("logs.request_id", "logs.timestamp", "logs.idempotency_check")),
    )

    return Incident(
        incident_id="incident_001_duplicate_payment",
        title="Incident 001 — Duplicate Payment",
        category="payment_processing",
        description="A fictional customer was charged twice for one logical payment.",
        troubleshooting_question="Why was this customer charged twice?",
        ground_truth_root_cause="A client retried after an upstream timeout, and the payment worker processed the same request twice because it did not enforce an idempotency check.",
        structured_evidence=structured_evidence,
        log_evidence=logs,
        sensitive_fields=sensitive_fields,
        diagnostic_invariants=invariants,
        expected_evidence=expected,
        difficulty="easy",
        metadata={
            "schema_version": "0.1",
            "benchmark_version": "0.1",
            "synthetic": True,
            "fictionality_notice": "All people, identifiers, events, and systems are fictional synthetic test data.",
            "seed": seed,
        },
    )


def write_incident(path: Path = DEFAULT_OUTPUT, seed: int = DEFAULT_SEED) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_incident_001(seed).to_json(), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(write_incident(args.output, args.seed))


if __name__ == "__main__":
    main()
