"""Generate the Incident 001 family: a repeated logical payment operation."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path
import random

from diagbench.schema import (
    ComponentMapping,
    DiagnosticInvariant,
    EvidenceReference,
    ExpectedEvidence,
    Incident,
    LogEntry,
    SensitiveField,
    StructuredRootCause,
)

DEFAULT_SEED = 1001
DEVELOPMENT_SEEDS = range(1000, 2000)
VALIDATION_SEEDS = range(2000, 3000)
RETIRED_EVALUATION_SEEDS = range(10_000, 11_000)
EVALUATION_SEEDS = range(20_000, 21_000)
DEFAULT_OUTPUT = (
    Path(__file__).parents[1]
    / "incidents"
    / "incident_001_duplicate_payment"
    / "incident.json"
)

_FIRST_NAMES = ("Avery", "Casey", "Jordan", "Morgan", "Quinn", "Riley", "Rowan")
_LAST_NAMES = ("Example", "Placeholder", "Sample", "Testerson")
_GATEWAY_SERVICES = ("edge-handler", "request-router", "transaction-api")
_WORKER_SERVICES = ("ledger-writer", "operation-worker", "transaction-processor")
_RECEIVE_MESSAGES = ("Inbound operation accepted", "Operation received")
_WRITE_MESSAGES = ("Record committed", "Write completed")
_TIMEOUT_MESSAGES = ("Caller-facing deadline elapsed", "Response deadline exceeded")


def seed_split(seed: int) -> str:
    """Return the documented experimental split for a seed."""
    if seed in DEVELOPMENT_SEEDS:
        return "development"
    if seed in VALIDATION_SEEDS:
        return "validation"
    if seed in RETIRED_EVALUATION_SEEDS:
        return "retired"
    if seed in EVALUATION_SEEDS:
        return "evaluation"
    return "unassigned"


def _neutral_id(rng: random.Random, prefix: str, used: set[str]) -> str:
    while True:
        candidate = f"SYN-{prefix}-{rng.randrange(10_000_000, 99_999_999)}"
        if candidate not in used:
            used.add(candidate)
            return candidate


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _reference(
    source: str, evidence_id: str, field: str | None = None
) -> EvidenceReference:
    return EvidenceReference(source, {"evidence_id": evidence_id}, field)


def generate_incident_001(seed: int = DEFAULT_SEED) -> Incident:
    """Create one deterministic instance with a fixed cause and varied nuisance data."""
    rng = random.Random(seed)
    used_ids: set[str] = set()
    gateway_service = rng.choice(_GATEWAY_SERVICES)
    worker_service = rng.choice(_WORKER_SERVICES)

    customer_count = rng.randint(3, 6)
    name_pairs = rng.sample(
        [(first, last) for first in _FIRST_NAMES for last in _LAST_NAMES],
        customer_count,
    )
    customers: list[dict[str, object]] = []
    accounts: list[dict[str, object]] = []
    for index, (first, last) in enumerate(name_pairs):
        customer_id = _neutral_id(rng, "CUST", used_ids)
        account_id = _neutral_id(rng, "ACCT", used_ids)
        customers.append(
            {
                "evidence_id": _neutral_id(rng, "EVD", used_ids),
                "customer_id": customer_id,
                "name": f"{first} {last} (Fictional)",
                "ssn": f"000-{rng.randrange(10, 100):02d}-{rng.randrange(1000, 10_000):04d}",
                "email": f"{first.lower()}.{last.lower()}.{index}@example.invalid",
            }
        )
        accounts.append(
            {
                "evidence_id": _neutral_id(rng, "EVD", used_ids),
                "account_id": account_id,
                "customer_id": customer_id,
            }
        )

    target_index = rng.randrange(customer_count)
    target_customer_id = str(customers[target_index]["customer_id"])
    target_account_id = str(accounts[target_index]["account_id"])
    target_customer_evidence_id = str(customers[target_index]["evidence_id"])
    target_account_evidence_id = str(accounts[target_index]["evidence_id"])
    target_request_id = _neutral_id(rng, "REQ", used_ids)
    first_payment_id = _neutral_id(rng, "PAY", used_ids)
    second_payment_id = _neutral_id(rng, "PAY", used_ids)
    first_payment_evidence_id = _neutral_id(rng, "EVD", used_ids)
    second_payment_evidence_id = _neutral_id(rng, "EVD", used_ids)
    first_transport_id = _neutral_id(rng, "TRN", used_ids)
    second_transport_id = _neutral_id(rng, "TRN", used_ids)

    base = datetime(2030, 1, 1, tzinfo=UTC) + timedelta(
        days=rng.randrange(730),
        hours=rng.randrange(8, 18),
        minutes=rng.randrange(60),
        seconds=rng.randrange(60),
    )
    first_write_at = base + timedelta(milliseconds=rng.randrange(25, 121))
    timeout_at = base + timedelta(milliseconds=rng.randrange(900, 2501))
    second_receive_at = timeout_at + timedelta(milliseconds=rng.randrange(250, 1501))
    second_write_at = second_receive_at + timedelta(milliseconds=rng.randrange(25, 121))
    target_amount = f"{rng.randrange(2_500, 25_001) / 100:.2f}"

    payments: list[dict[str, object]] = [
        {
            "evidence_id": first_payment_evidence_id,
            "payment_id": first_payment_id,
            "customer_id": target_customer_id,
            "account_id": target_account_id,
            "request_id": target_request_id,
            "amount": target_amount,
            "status": "succeeded",
            "created_at": _timestamp(first_write_at),
        },
        {
            "evidence_id": second_payment_evidence_id,
            "payment_id": second_payment_id,
            "customer_id": target_customer_id,
            "account_id": target_account_id,
            "request_id": target_request_id,
            "amount": target_amount,
            "status": "succeeded",
            "created_at": _timestamp(second_write_at),
        },
    ]

    unrelated_payment_ids: list[str] = []
    unrelated_payment_evidence_ids: list[str] = []
    unrelated_request_ids: list[str] = []
    unrelated_count = rng.randint(4, 8)
    for index in range(unrelated_count):
        owner_index = rng.randrange(customer_count)
        payment_id = _neutral_id(rng, "PAY", used_ids)
        payment_evidence_id = _neutral_id(rng, "EVD", used_ids)
        request_id = _neutral_id(rng, "REQ", used_ids)
        unrelated_payment_ids.append(payment_id)
        unrelated_payment_evidence_ids.append(payment_evidence_id)
        unrelated_request_ids.append(request_id)
        offset = (-180 + index * (360 / max(1, unrelated_count - 1)))
        offset += rng.uniform(-8, 8)
        created_at = base + timedelta(seconds=offset)
        payments.append(
            {
                "evidence_id": payment_evidence_id,
                "payment_id": payment_id,
                "customer_id": customers[owner_index]["customer_id"],
                "account_id": accounts[owner_index]["account_id"],
                "request_id": request_id,
                "amount": f"{rng.randrange(500, 40_001) / 100:.2f}",
                "status": "succeeded",
                "created_at": _timestamp(created_at),
            }
        )

    benign_request_id = _neutral_id(rng, "REQ", used_ids)
    benign_payment_id = _neutral_id(rng, "PAY", used_ids)
    benign_payment_evidence_id = _neutral_id(rng, "EVD", used_ids)
    benign_owner = (target_index + 1) % customer_count
    benign_start = base - timedelta(seconds=rng.randrange(20, 50))
    benign_timeout = benign_start + timedelta(milliseconds=rng.randrange(700, 1801))
    benign_return = benign_timeout + timedelta(milliseconds=rng.randrange(250, 1001))
    benign_write = benign_return + timedelta(milliseconds=rng.randrange(25, 121))
    payments.append(
        {
            "evidence_id": benign_payment_evidence_id,
            "payment_id": benign_payment_id,
            "customer_id": customers[benign_owner]["customer_id"],
            "account_id": accounts[benign_owner]["account_id"],
            "request_id": benign_request_id,
            "amount": f"{rng.randrange(500, 40_001) / 100:.2f}",
            "status": "succeeded",
            "created_at": _timestamp(benign_write),
        }
    )
    unrelated_payment_ids.append(benign_payment_id)
    unrelated_payment_evidence_ids.append(benign_payment_evidence_id)
    unrelated_request_ids.append(benign_request_id)

    target_event_ids = [_neutral_id(rng, "EVD", used_ids) for _ in range(5)]
    logs: list[LogEntry] = [
        LogEntry(
            target_event_ids[0],
            _timestamp(base),
            "INFO",
            gateway_service,
            rng.choice(_RECEIVE_MESSAGES),
            {"request_id": target_request_id, "transport_id": first_transport_id},
        ),
        LogEntry(
            target_event_ids[1],
            _timestamp(first_write_at),
            "INFO",
            worker_service,
            rng.choice(_WRITE_MESSAGES),
            {"request_id": target_request_id, "payment_id": first_payment_id},
        ),
        LogEntry(
            target_event_ids[2],
            _timestamp(timeout_at),
            "WARN",
            gateway_service,
            rng.choice(_TIMEOUT_MESSAGES),
            {"request_id": target_request_id, "http_status": 504},
        ),
        LogEntry(
            target_event_ids[3],
            _timestamp(second_receive_at),
            "INFO",
            gateway_service,
            rng.choice(_RECEIVE_MESSAGES),
            {"request_id": target_request_id, "transport_id": second_transport_id},
        ),
        LogEntry(
            target_event_ids[4],
            _timestamp(second_write_at),
            "INFO",
            worker_service,
            rng.choice(_WRITE_MESSAGES),
            {"request_id": target_request_id, "payment_id": second_payment_id},
        ),
    ]

    for payment_id, request_id in zip(
        unrelated_payment_ids[:-1], unrelated_request_ids[:-1], strict=True
    ):
        payment = next(row for row in payments if row["payment_id"] == payment_id)
        logs.append(
            LogEntry(
                _neutral_id(rng, "EVD", used_ids),
                str(payment["created_at"]),
                "INFO",
                worker_service,
                rng.choice(_WRITE_MESSAGES),
                {"request_id": request_id, "payment_id": payment_id},
            )
        )

    benign_transport_ids = (
        _neutral_id(rng, "TRN", used_ids),
        _neutral_id(rng, "TRN", used_ids),
    )
    logs.extend(
        [
            LogEntry(
                _neutral_id(rng, "EVD", used_ids),
                _timestamp(benign_start),
                "INFO",
                gateway_service,
                rng.choice(_RECEIVE_MESSAGES),
                {"request_id": benign_request_id, "transport_id": benign_transport_ids[0]},
            ),
            LogEntry(
                _neutral_id(rng, "EVD", used_ids),
                _timestamp(benign_timeout),
                "WARN",
                gateway_service,
                rng.choice(_TIMEOUT_MESSAGES),
                {"request_id": benign_request_id, "http_status": 504},
            ),
            LogEntry(
                _neutral_id(rng, "EVD", used_ids),
                _timestamp(benign_return),
                "INFO",
                gateway_service,
                rng.choice(_RECEIVE_MESSAGES),
                {"request_id": benign_request_id, "transport_id": benign_transport_ids[1]},
            ),
            LogEntry(
                _neutral_id(rng, "EVD", used_ids),
                _timestamp(benign_write),
                "INFO",
                worker_service,
                rng.choice(_WRITE_MESSAGES),
                {"request_id": benign_request_id, "payment_id": benign_payment_id},
            ),
        ]
    )

    warning_messages = ("Connection pool utilization elevated", "Dependency response delayed")
    for _ in range(rng.randint(1, 3)):
        logs.append(
            LogEntry(
                _neutral_id(rng, "EVD", used_ids),
                _timestamp(base + timedelta(seconds=rng.uniform(-150, 150))),
                "WARN",
                rng.choice((gateway_service, worker_service)),
                rng.choice(warning_messages),
                {"sample_window_seconds": rng.choice((30, 60, 120))},
            )
        )

    rng.shuffle(customers)
    rng.shuffle(accounts)
    rng.shuffle(payments)
    logs.sort(key=lambda entry: (entry.timestamp, entry.evidence_id))
    structured_evidence = {
        "customers": customers,
        "accounts": accounts,
        "payments": payments,
    }

    def payment_a(field: str | None = None) -> EvidenceReference:
        return _reference("payments", first_payment_evidence_id, field)

    def payment_b(field: str | None = None) -> EvidenceReference:
        return _reference("payments", second_payment_evidence_id, field)

    def target_log(index: int, field: str | None = None) -> EvidenceReference:
        return _reference("logs", target_event_ids[index], field)

    def customer_ref(field: str | None = None) -> EvidenceReference:
        return _reference("customers", target_customer_evidence_id, field)

    def account_ref(field: str | None = None) -> EvidenceReference:
        return _reference("accounts", target_account_evidence_id, field)

    unrelated_request_references = tuple(
        _reference("payments", evidence_id, "request_id")
        for evidence_id in unrelated_payment_evidence_ids
    )
    diagnostic_invariants = (
        DiagnosticInvariant(
            "target_request_equality",
            "equal",
            (payment_a("request_id"), payment_b("request_id")),
            True,
            "essential",
            "Both affected payment rows belong to the same logical request.",
        ),
        DiagnosticInvariant(
            "target_request_cross_source_identity",
            "equal",
            (
                payment_a("request_id"),
                payment_b("request_id"),
                *(target_log(index, "request_id") for index in range(5)),
            ),
            True,
            "essential",
            "The affected rows correlate with the request, timeout, and write events.",
        ),
        DiagnosticInvariant(
            "unrelated_request_inequality",
            "all_distinct",
            (payment_a("request_id"), *unrelated_request_references),
            True,
            "essential",
            "Unrelated operations must not become falsely equal to the target request or each other.",
        ),
        DiagnosticInvariant(
            "target_payment_distinctness",
            "not_equal",
            (payment_a("payment_id"), payment_b("payment_id")),
            True,
            "essential",
            "Two distinct persisted payment records must remain distinguishable.",
        ),
        DiagnosticInvariant(
            "target_event_order",
            "ordered_before",
            tuple(target_log(index, "timestamp") for index in range(5)),
            True,
            "essential",
            "Request receipt and first write precede the timeout, second receipt, and second write.",
        ),
        DiagnosticInvariant(
            "target_success_state",
            "equal",
            (payment_a("status"), payment_b("status")),
            "succeeded",
            "essential",
            "Both distinct records represent completed charges.",
        ),
        DiagnosticInvariant(
            "target_customer_equality",
            "equal",
            (payment_a("customer_id"), payment_b("customer_id")),
            True,
            "supportive",
            "Customer equality corroborates that the two records affect one customer.",
        ),
        DiagnosticInvariant(
            "target_account_equality",
            "equal",
            (payment_a("account_id"), payment_b("account_id")),
            True,
            "supportive",
            "Account equality corroborates that the two records affect one account.",
        ),
        DiagnosticInvariant(
            "target_amount_equality",
            "equal",
            (payment_a("amount"), payment_b("amount")),
            True,
            "supportive",
            "Equal amounts support the repeated-operation interpretation.",
        ),
        DiagnosticInvariant(
            "payment_row_cardinality",
            "row_count",
            tuple(
                _reference("payments", str(row["evidence_id"]))
                for row in payments
            ),
            len(payments),
            "supportive",
            "The generated evidence includes bounded surrounding payment activity.",
        ),
        DiagnosticInvariant(
            "exact_rearrival_interval",
            "interval_seconds",
            (target_log(2, "timestamp"), target_log(3, "timestamp")),
            (second_receive_at - timeout_at).total_seconds(),
            "discardable",
            "The exact interval is nuisance data; causal ordering is sufficient.",
        ),
        DiagnosticInvariant(
            "literal_customer_identity",
            "preserve_literal",
            (
                customer_ref("name"),
                customer_ref("ssn"),
                customer_ref("email"),
                customer_ref("customer_id"),
            ),
            False,
            "discardable",
            "Literal customer identity is unnecessary for diagnosis.",
        ),
        DiagnosticInvariant(
            "literal_account_identity",
            "preserve_literal",
            (account_ref("account_id"),),
            False,
            "discardable",
            "The literal account identifier is unnecessary for diagnosis.",
        ),
    )

    expected_evidence = (
        ExpectedEvidence(
            "Two distinct successful records share one request identifier.",
            (
                payment_a("payment_id"),
                payment_a("request_id"),
                payment_a("status"),
                payment_b("payment_id"),
                payment_b("request_id"),
                payment_b("status"),
            ),
        ),
        ExpectedEvidence(
            "The first write precedes a caller-visible timeout and a second receipt and write.",
            tuple(target_log(index) for index in range(5)),
        ),
        ExpectedEvidence(
            "The second transport has the same request identifier but a different transport identifier.",
            (
                target_log(0, "request_id"),
                target_log(0, "transport_id"),
                target_log(3, "request_id"),
                target_log(3, "transport_id"),
            ),
        ),
    )

    sensitive_fields = (
        SensitiveField("customers.name", "direct_identifier", "remove_or_pseudonymize", "Literal identity is not diagnostic."),
        SensitiveField("customers.ssn", "highly_sensitive_identifier", "remove_or_pseudonymize", "Literal identity is not diagnostic."),
        SensitiveField("customers.email", "contact_identifier", "remove_or_pseudonymize", "Literal identity is not diagnostic."),
        SensitiveField("customers.customer_id", "customer_identifier", "consistent_pseudonym", "Only selected relationships may be diagnostic."),
        SensitiveField("accounts.customer_id", "customer_identifier", "consistent_pseudonym", "Only selected relationships may be diagnostic."),
        SensitiveField("accounts.account_id", "account_identifier", "consistent_pseudonym", "Only selected relationships may be diagnostic."),
        SensitiveField("payments.customer_id", "customer_identifier", "consistent_pseudonym", "Equality is supportive; literal value is unnecessary."),
        SensitiveField("payments.account_id", "account_identifier", "consistent_pseudonym", "Equality is supportive; literal value is unnecessary."),
        SensitiveField("payments.request_id", "operational_identifier", "consistent_pseudonym", "Selected equality and inequality relationships are essential."),
        SensitiveField("logs.request_id", "operational_identifier", "consistent_pseudonym", "Cross-source identity is essential."),
        SensitiveField("payments.payment_id", "operational_identifier", "pseudonymize_independently", "Distinctness and selected log correlation matter."),
        SensitiveField("logs.payment_id", "operational_identifier", "pseudonymize_independently", "Selected log-to-row correlation is supportive."),
        SensitiveField("logs.transport_id", "operational_identifier", "pseudonymize_independently", "Distinct arrivals are supporting evidence."),
    )

    return Incident(
        incident_id="incident_001_duplicate_payment",
        title="Incident 001 — Duplicate Payment",
        category="duplicate_payment",
        description="A repeated logical operation produced two successful payment records.",
        troubleshooting_question=(
            "A customer reports being charged twice. Investigate the evidence and "
            "identify the most likely root cause."
        ),
        ground_truth=StructuredRootCause(
            outcome="duplicate_payment",
            trigger="retry_after_timeout",
            failure_mechanism="missing_or_ineffective_idempotency",
            affected_component="payment_worker",
            logical_operation_repeated=True,
            explanation=(
                "A caller repeated one logical request after a response timeout, and "
                "the payment worker persisted both arrivals as separate payments."
            ),
        ),
        component_mappings=(
            ComponentMapping("payment_worker", (worker_service,)),
        ),
        structured_evidence=structured_evidence,
        log_evidence=tuple(logs),
        sensitive_fields=sensitive_fields,
        diagnostic_invariants=diagnostic_invariants,
        expected_evidence=expected_evidence,
        difficulty="medium",
        metadata={
            "schema_version": "0.2",
            "benchmark_version": "0.2",
            "synthetic": True,
            "fictionality_notice": (
                "All people, identifiers, events, and systems are fictional synthetic test data."
            ),
            "seed": seed,
            "seed_split": seed_split(seed),
            "target_payment_ids": [first_payment_id, second_payment_id],
            "target_request_id": target_request_id,
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
