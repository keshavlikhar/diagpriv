"""Generate Incident 002: a missing effect after a reference-shape defect."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import hashlib
from pathlib import Path
import random
import string

from diagbench.schema import (
    ComponentMapping,
    DiagnosticInvariant,
    EvidenceReference,
    ExpectedEvidence,
    Incident,
    LogEntry,
    SensitiveField,
    StructuredRootCause,
    StructuredRootCauseV2,
)
from diagbench.schema.models import JSONValue
from diagbench.structural import (
    STRUCTURAL_SIGNATURE_VERSION,
    structural_signature,
)

FAMILY_ID = "incident_002_format_defect"
GENERATOR_VERSION = "incident-002-generator-v1"
DEFAULT_SEED = 1001
DEVELOPMENT_SEEDS = range(1000, 2000)
DEFAULT_OUTPUT = (
    Path(__file__).parents[1]
    / "incidents"
    / "incident_002_format_defect"
    / "incident.json"
)

_TEMPLATES = {
    "hyphenated_mixed_a": "UU-DDDD-lU",
    "underscored_mixed": "UUU_DDDDD_U",
    "slashed_mixed": "DD/UUU/DDDD",
    "hyphenated_mixed_b": "UU-DDD-U-DD",
    "dotted_mixed": "UU.DDDD.ll",
}
_INTAKE_ALIASES = ("queue-front", "submission-gateway", "intake-node")
_EXECUTOR_ALIASES = ("apply-worker", "record-builder", "provision-agent")
_DEPENDENCY_ALIASES = ("reference-index", "external-directory", "registry-lookup")
_ACCEPT_MESSAGES = ("Opaque envelope accepted", "Operation envelope accepted")
_QUEUE_MESSAGES = ("Opaque envelope queued", "Operation envelope queued")
_START_MESSAGES = ("Operation processing started", "Work item processing started")
_LOOKUP_MESSAGES = ("Lookup observation recorded", "Reference lookup completed")
_END_MESSAGES = ("Operation processing ended", "Work item processing ended")
_EFFECT_MESSAGES = ("Destination record stored", "Provisioned record committed")
_WARNING_MESSAGES = (
    "Dependency response time elevated",
    "Connection pool pressure observed",
    "Dependency latency warning observed",
)
_BANNED_REFERENCE_FRAGMENTS = ("BAD", "INVALID", "TEST", "ERROR", "BROKEN")
SUPPORTED_GENERATION_DEFECTS = (
    "missing_separator",
    "extra_separator",
    "truncation",
    "fixed_width_mismatch",
    "leading_zero_loss",
    "case_class_mismatch",
)
_OBSERVABLE_DELTA_BY_GENERATION_DEFECT = {
    "missing_separator": "missing_separator",
    "extra_separator": "extra_separator",
    "truncation": "truncation",
    "fixed_width_mismatch": "fixed_width_mismatch",
    "leading_zero_loss": "numeric_run_leading_position_deletion",
    "case_class_mismatch": "case_class_mismatch",
}


def _rng_for(seed: int) -> tuple[random.Random, str]:
    if seed not in DEVELOPMENT_SEEDS:
        raise ValueError(
            "Incident 002 construction is development-only; seed must be in 1000-1999"
        )
    domain = f"{FAMILY_ID}\0{GENERATOR_VERSION}\0{seed}".encode("ascii")
    digest = hashlib.sha256(domain).digest()
    return random.Random(int.from_bytes(digest, "big")), digest.hex()


def _neutral_id(rng: random.Random, prefix: str, used: set[str]) -> str:
    while True:
        candidate = f"{prefix}-{rng.randrange(10_000_000, 99_999_999)}"
        if candidate not in used:
            used.add(candidate)
            return candidate


def _timestamp(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _reference(
    source: str,
    evidence_id: str | None = None,
    field: str | None = None,
    **selector: str,
) -> EvidenceReference:
    if evidence_id is not None:
        selector["evidence_id"] = evidence_id
    return EvidenceReference(source, selector, field)


def _digit_run_starts(template: str) -> tuple[int, ...]:
    return tuple(
        index
        for index, atom in enumerate(template)
        if atom == "D" and (index == 0 or template[index - 1] != "D")
    )


def _render_reference(
    rng: random.Random, template: str, *, forced: dict[int, str] | None = None
) -> str:
    forced = forced or {}
    output: list[str] = []
    for index, atom in enumerate(template):
        if index in forced:
            output.append(forced[index])
        elif atom == "U":
            output.append(rng.choice(string.ascii_uppercase))
        elif atom == "l":
            output.append(rng.choice(string.ascii_lowercase))
        elif atom == "D":
            output.append(rng.choice(string.digits))
        else:
            output.append(atom)
    value = "".join(output)
    if any(fragment in value for fragment in _BANNED_REFERENCE_FRAGMENTS):
        return _render_reference(rng, template, forced=forced)
    return value


def _unique_reference(
    rng: random.Random,
    template: str,
    used: set[str],
    *,
    forced: dict[int, str] | None = None,
) -> str:
    while True:
        value = _render_reference(rng, template, forced=forced)
        if value not in used:
            used.add(value)
            return value


def _mutate_reference(
    rng: random.Random, valid: str, template: str, defect: str
) -> tuple[str, int, str]:
    if defect == "missing_separator":
        positions = [i for i, atom in enumerate(template) if atom not in "UlD"]
        position = rng.choice(positions)
        return valid[:position] + valid[position + 1 :], position, "deletion"
    if defect == "extra_separator":
        positions = [
            i
            for i in range(1, len(template))
            if template[i - 1] in "UlD" and template[i] in "UlD"
        ]
        position = rng.choice(positions)
        separator = rng.choice("-_/.")
        return valid[:position] + separator + valid[position:], position, "insertion"
    if defect == "truncation":
        return valid[:-1], len(valid) - 1, "deletion"
    if defect == "leading_zero_loss":
        positions = _digit_run_starts(template)
        position = next(index for index in positions if valid[index] == "0")
        return valid[:position] + valid[position + 1 :], position, "deletion"
    if defect == "case_class_mismatch":
        positions = [i for i, atom in enumerate(template) if atom in "Ul"]
        position = rng.choice(positions)
        changed = valid[position].swapcase()
        return valid[:position] + changed + valid[position + 1 :], position, "substitution"
    if defect == "fixed_width_mismatch":
        operation = rng.choice(("insertion", "deletion"))
        positions = [
            i
            for i, atom in enumerate(template[:-1])
            if atom in "UlD"
            and not (atom == "D" and (i == 0 or template[i - 1] != "D"))
        ]
        position = rng.choice(positions)
        if operation == "deletion":
            return valid[:position] + valid[position + 1 :], position, operation
        alphabet = {
            "U": string.ascii_uppercase,
            "l": string.ascii_lowercase,
            "D": string.digits,
        }[template[position]]
        inserted = rng.choice(alphabet)
        return valid[:position] + inserted + valid[position:], position, operation
    raise ValueError(f"Unsupported structural defect: {defect}")


def generate_incident_002(seed: int = DEFAULT_SEED) -> Incident:
    """Create a deterministic development instance of Incident Family 002."""
    rng, generation_domain = _rng_for(seed)
    used_ids: set[str] = set()
    used_references: set[str] = set()
    template_name, template = rng.choice(tuple(_TEMPLATES.items()))
    defect = rng.choice(SUPPORTED_GENERATION_DEFECTS)
    observable_delta = _OBSERVABLE_DELTA_BY_GENERATION_DEFECT[defect]
    forced: dict[int, str] = {}
    if defect == "leading_zero_loss":
        forced[rng.choice(_digit_run_starts(template))] = "0"

    control_count = rng.randint(5, 8)
    control_references = [
        _unique_reference(rng, template, used_references, forced=forced)
        for _ in range(control_count)
    ]
    latent_valid_reference = _unique_reference(
        rng, template, used_references, forced=forced
    )
    target_reference, defect_position, defect_operation = _mutate_reference(
        rng, latent_valid_reference, template, defect
    )
    if target_reference in used_references:
        raise AssertionError("Generated target reference collided with a healthy reference")
    used_references.add(target_reference)

    target_position = rng.randint(2, control_count - 2)
    latency_control_index, recovery_control_index = rng.sample(
        range(control_count), 2
    )
    intake_alias = rng.choice(_INTAKE_ALIASES)
    executor_alias = rng.choice(_EXECUTOR_ALIASES)
    dependency_alias = rng.choice(_DEPENDENCY_ALIASES)
    base = datetime(2034, 1, 1, tzinfo=UTC) + timedelta(
        days=rng.randrange(365),
        hours=rng.randrange(7, 19),
        minutes=rng.randrange(60),
        seconds=rng.randrange(60),
    )

    chronological: list[tuple[str, int | None, str]] = []
    control_cursor = 0
    for position in range(control_count + 1):
        if position == target_position:
            chronological.append(("target", None, target_reference))
        else:
            chronological.append(
                ("control", control_cursor, control_references[control_cursor])
            )
            control_cursor += 1

    processing_attempts: list[dict[str, JSONValue]] = []
    lookup_observations: list[dict[str, JSONValue]] = []
    effect_records: list[dict[str, JSONValue]] = []
    logs: list[LogEntry] = []
    operation_data: dict[str, dict[str, JSONValue]] = {}

    for sequence_index, (kind, control_index, external_reference) in enumerate(
        chronological
    ):
        operation_id = _neutral_id(rng, "OP", used_ids)
        processing_id = _neutral_id(rng, "EV", used_ids)
        received_at = base + timedelta(
            seconds=sequence_index * 12,
            milliseconds=rng.randrange(20, 700),
        )
        started_at = received_at + timedelta(milliseconds=rng.randrange(20, 81))
        first_lookup_at = started_at + timedelta(milliseconds=rng.randrange(25, 111))
        is_target = kind == "target"
        is_latency = kind == "control" and control_index == latency_control_index
        is_recovery = kind == "control" and control_index == recovery_control_index
        lookup_rows: list[dict[str, JSONValue]] = []

        if is_recovery:
            first_lookup_id = _neutral_id(rng, "EV", used_ids)
            lookup_rows.append(
                {
                    "evidence_id": first_lookup_id,
                    "operation_id": operation_id,
                    "external_reference": external_reference,
                    "lookup_result": "no_match",
                    "match_mode": "exact",
                    "observed_at": _timestamp(first_lookup_at),
                    "dependency_alias": dependency_alias,
                    "executor_alias": executor_alias,
                    "latency_ms": rng.randrange(35, 110),
                }
            )
            final_lookup_at = first_lookup_at + timedelta(milliseconds=rng.randrange(180, 451))
            final_lookup_id = _neutral_id(rng, "EV", used_ids)
            lookup_rows.append(
                {
                    "evidence_id": final_lookup_id,
                    "operation_id": operation_id,
                    "external_reference": external_reference,
                    "lookup_result": "match",
                    "match_mode": "exact",
                    "observed_at": _timestamp(final_lookup_at),
                    "dependency_alias": dependency_alias,
                    "executor_alias": executor_alias,
                    "latency_ms": rng.randrange(30, 95),
                }
            )
        else:
            final_lookup_at = first_lookup_at
            final_lookup_id = _neutral_id(rng, "EV", used_ids)
            lookup_rows.append(
                {
                    "evidence_id": final_lookup_id,
                    "operation_id": operation_id,
                    "external_reference": external_reference,
                    "lookup_result": "no_match" if is_target else "match",
                    "match_mode": "exact",
                    "observed_at": _timestamp(final_lookup_at),
                    "dependency_alias": dependency_alias,
                    "executor_alias": executor_alias,
                    "latency_ms": (
                        rng.randrange(650, 901) if is_latency else rng.randrange(25, 121)
                    ),
                }
            )

        completed_at = final_lookup_at + timedelta(milliseconds=rng.randrange(20, 91))
        processing_attempts.append(
            {
                "evidence_id": processing_id,
                "operation_id": operation_id,
                "external_reference": external_reference,
                "received_at": _timestamp(received_at),
                "completed_at": _timestamp(completed_at),
                "intake_alias": intake_alias,
                "executor_alias": executor_alias,
                "final_state": "closed" if is_target else "completed",
                "effect_created": not is_target,
            }
        )
        lookup_observations.extend(lookup_rows)

        effect_id: str | None = None
        effect_evidence_id: str | None = None
        if not is_target:
            effect_id = _neutral_id(rng, "EF", used_ids)
            effect_evidence_id = _neutral_id(rng, "EV", used_ids)
            effect_records.append(
                {
                    "evidence_id": effect_evidence_id,
                    "operation_id": operation_id,
                    "effect_id": effect_id,
                    "state": "active",
                    "created_at": _timestamp(completed_at),
                    "executor_alias": executor_alias,
                }
            )

        event_ids = [_neutral_id(rng, "EV", used_ids) for _ in range(5)]
        logs.extend(
            [
                LogEntry(
                    event_ids[0],
                    _timestamp(received_at),
                    "INFO",
                    intake_alias,
                    rng.choice(_ACCEPT_MESSAGES),
                    {"operation_id": operation_id},
                ),
                LogEntry(
                    event_ids[1],
                    _timestamp(received_at + timedelta(milliseconds=10)),
                    "INFO",
                    intake_alias,
                    rng.choice(_QUEUE_MESSAGES),
                    {"operation_id": operation_id},
                ),
                LogEntry(
                    event_ids[2],
                    _timestamp(started_at),
                    "INFO",
                    executor_alias,
                    rng.choice(_START_MESSAGES),
                    {
                        "operation_id": operation_id,
                        "external_reference": external_reference,
                    },
                ),
                LogEntry(
                    event_ids[3],
                    _timestamp(final_lookup_at),
                    "INFO",
                    executor_alias,
                    rng.choice(_LOOKUP_MESSAGES),
                    {
                        "operation_id": operation_id,
                        "external_reference": external_reference,
                        "lookup_result": "no_match" if is_target else "match",
                    },
                ),
                LogEntry(
                    event_ids[4],
                    _timestamp(completed_at),
                    "INFO",
                    executor_alias,
                    rng.choice(_END_MESSAGES),
                    {"operation_id": operation_id},
                ),
            ]
        )
        if effect_id is not None:
            logs.append(
                LogEntry(
                    _neutral_id(rng, "EV", used_ids),
                    _timestamp(completed_at + timedelta(milliseconds=1)),
                    "INFO",
                    executor_alias,
                    rng.choice(_EFFECT_MESSAGES),
                    {"operation_id": operation_id, "effect_id": effect_id},
                )
            )

        operation_data[operation_id] = {
            "kind": kind,
            "control_index": control_index,
            "processing_id": processing_id,
            "reference": external_reference,
            "received_at": _timestamp(received_at),
            "completed_at": _timestamp(completed_at),
            "lookup_ids": [row["evidence_id"] for row in lookup_rows],
            "lookup_times": [row["observed_at"] for row in lookup_rows],
            "event_ids": event_ids,
            "effect_evidence_id": effect_evidence_id,
            "is_latency": is_latency,
            "is_recovery": is_recovery,
        }

    target_operation_id = next(
        operation_id
        for operation_id, data in operation_data.items()
        if data["kind"] == "target"
    )
    control_operation_ids = tuple(
        operation_id
        for operation_id, data in operation_data.items()
        if data["kind"] == "control"
    )
    latency_operation_id = next(
        operation_id
        for operation_id, data in operation_data.items()
        if data["is_latency"]
    )
    recovery_operation_id = next(
        operation_id
        for operation_id, data in operation_data.items()
        if data["is_recovery"]
    )
    primary_control_id = next(
        operation_id
        for operation_id in control_operation_ids
        if operation_id != recovery_operation_id
    )

    dependency_health: list[dict[str, JSONValue]] = []
    target_received = datetime.fromisoformat(
        str(operation_data[target_operation_id]["received_at"]).replace("Z", "+00:00")
    )
    health_samples = (
        (-rng.uniform(18, 32), "none"),
        (rng.uniform(-4, 4), "latency_elevated"),
        (rng.uniform(18, 32), "none"),
    )
    for offset_seconds, warning in health_samples:
        dependency_health.append(
            {
                "evidence_id": _neutral_id(rng, "EV", used_ids),
                "dependency_alias": dependency_alias,
                "observed_at": _timestamp(target_received + timedelta(seconds=offset_seconds)),
                "availability_state": "available",
                "warning": warning,
                "error_rate": round(rng.uniform(0.001, 0.018), 4),
            }
        )
    for row in dependency_health:
        if row["warning"] != "none":
            logs.append(
                LogEntry(
                    _neutral_id(rng, "EV", used_ids),
                    str(row["observed_at"]),
                    "WARN",
                    dependency_alias,
                    rng.choice(_WARNING_MESSAGES),
                    {"sample_window_seconds": rng.choice((30, 60, 120))},
                )
            )

    rng.shuffle(processing_attempts)
    rng.shuffle(lookup_observations)
    rng.shuffle(effect_records)
    rng.shuffle(dependency_health)
    logs.sort(key=lambda entry: (entry.timestamp, entry.evidence_id))
    structured_evidence = {
        "processing_attempts": processing_attempts,
        "lookup_observations": lookup_observations,
        "effect_records": effect_records,
        "dependency_health": dependency_health,
    }

    def operation_ref(
        operation_id: str, source: str, field: str | None = None, *, lookup_index: int = -1
    ) -> EvidenceReference:
        data = operation_data[operation_id]
        if source == "processing_attempts":
            return _reference(source, str(data["processing_id"]), field)
        if source == "lookup_observations":
            lookup_ids = data["lookup_ids"]
            assert isinstance(lookup_ids, list)
            return _reference(source, str(lookup_ids[lookup_index]), field)
        if source == "logs":
            event_ids = data["event_ids"]
            assert isinstance(event_ids, list)
            return _reference(source, str(event_ids[2]), field)
        raise ValueError(f"Unsupported operation evidence source: {source}")

    target_shape_ref = operation_ref(
        target_operation_id, "processing_attempts", "external_reference"
    )
    control_shape_refs = tuple(
        operation_ref(operation_id, "processing_attempts", "external_reference")
        for operation_id in control_operation_ids
    )
    target_lookup_ref = operation_ref(
        target_operation_id, "lookup_observations", "lookup_result"
    )
    primary_lookup_ref = operation_ref(
        primary_control_id, "lookup_observations", "lookup_result"
    )
    before_control_id = str(chronological[target_position - 1][1])
    after_control_id = str(chronological[target_position + 1][1])
    controls_by_index = {
        str(data["control_index"]): operation_id
        for operation_id, data in operation_data.items()
        if data["kind"] == "control"
    }
    before_operation_id = controls_by_index[before_control_id]
    after_operation_id = controls_by_index[after_control_id]

    invariants: list[DiagnosticInvariant] = [
        DiagnosticInvariant(
            "healthy_identifier_pattern_consistency",
            "same_structural_pattern",
            control_shape_refs,
            True,
            "essential",
            "Successful controls establish one common visible identifier shape.",
        ),
        DiagnosticInvariant(
            "target_identifier_pattern_anomaly",
            "structural_pattern_anomaly",
            (target_shape_ref, *control_shape_refs),
            True,
            "essential",
            "The target shape differs from the unanimous healthy-control shape.",
        ),
        DiagnosticInvariant(
            "target_identifier_defect_signature",
            "structural_defect",
            (target_shape_ref, *control_shape_refs),
            observable_delta,
            "essential",
            "The visible shape delta matches the declared observable one-edit relation.",
        ),
    ]
    if len(target_reference) != len(latent_valid_reference):
        invariants.append(
            DiagnosticInvariant(
                "target_identifier_length_delta",
                "length_delta",
                (target_shape_ref, control_shape_refs[0]),
                len(target_reference) - len(latent_valid_reference),
                "essential",
                "The target/control length delta agrees with the visible one-edit defect.",
            )
        )
    invariants.extend(
        [
            DiagnosticInvariant(
                "target_identifier_cross_source_identity",
                "equal",
                (
                    target_shape_ref,
                    operation_ref(
                        target_operation_id,
                        "lookup_observations",
                        "external_reference",
                    ),
                    operation_ref(target_operation_id, "logs", "external_reference"),
                ),
                True,
                "essential",
                "Target processing, lookup, and log evidence refer to one identifier.",
            ),
            DiagnosticInvariant(
                "control_identifier_cross_source_identity",
                "equal",
                (
                    operation_ref(
                        primary_control_id,
                        "processing_attempts",
                        "external_reference",
                    ),
                    operation_ref(
                        primary_control_id,
                        "lookup_observations",
                        "external_reference",
                    ),
                    operation_ref(primary_control_id, "logs", "external_reference"),
                ),
                True,
                "essential",
                "A successful control is consistently linked across evidence sources.",
            ),
            DiagnosticInvariant(
                "target_lookup_miss_state",
                "equal",
                (target_lookup_ref,),
                "no_match",
                "essential",
                "The target exact lookup produced no match.",
            ),
            DiagnosticInvariant(
                "control_lookup_success_state",
                "equal",
                (primary_lookup_ref,),
                "match",
                "essential",
                "A well-shaped control exact lookup succeeded.",
            ),
            DiagnosticInvariant(
                "control_effect_presence",
                "equal",
                tuple(
                    _reference(
                        "effect_records",
                        str(operation_data[operation_id]["effect_evidence_id"]),
                        "state",
                    )
                    for operation_id in control_operation_ids
                ),
                "active",
                "essential",
                "Every successful control created an active effect record.",
            ),
            DiagnosticInvariant(
                "target_event_order",
                "ordered_before",
                (
                    operation_ref(target_operation_id, "processing_attempts", "received_at"),
                    operation_ref(target_operation_id, "lookup_observations", "observed_at"),
                    operation_ref(target_operation_id, "processing_attempts", "completed_at"),
                ),
                True,
                "essential",
                "The target was received before lookup and closed after lookup.",
            ),
            DiagnosticInvariant(
                "target_effect_absence",
                "match_count",
                (
                    _reference(
                        "effect_records", operation_id=target_operation_id
                    ),
                ),
                0,
                "essential",
                "No effect record belongs to the target operation.",
            ),
            DiagnosticInvariant(
                "target_and_control_identifier_distinctness",
                "all_distinct",
                (target_shape_ref, *control_shape_refs),
                True,
                "essential",
                "The target and every control remain distinguishable identifiers.",
            ),
            DiagnosticInvariant(
                "controls_bracket_target",
                "ordered_before",
                (
                    operation_ref(before_operation_id, "processing_attempts", "received_at"),
                    operation_ref(target_operation_id, "processing_attempts", "received_at"),
                    operation_ref(after_operation_id, "processing_attempts", "received_at"),
                ),
                True,
                "supportive",
                "Successful controls occur immediately before and after the target.",
            ),
            DiagnosticInvariant(
                "shared_executor_role",
                "equal",
                tuple(
                    operation_ref(operation_id, "processing_attempts", "executor_alias")
                    for operation_id in (target_operation_id, *control_operation_ids)
                ),
                executor_alias,
                "supportive",
                "Target and controls were processed by the same executor alias.",
            ),
            DiagnosticInvariant(
                "dependency_remained_available",
                "equal",
                tuple(
                    _reference("dependency_health", str(row["evidence_id"]), "availability_state")
                    for row in dependency_health
                ),
                "available",
                "supportive",
                "Dependency health samples show availability despite bounded warnings.",
            ),
            DiagnosticInvariant(
                "latency_control_lookup_success",
                "equal",
                (
                    operation_ref(
                        latency_operation_id, "lookup_observations", "lookup_result"
                    ),
                ),
                "match",
                "supportive",
                "A high-latency control lookup still succeeded.",
            ),
            DiagnosticInvariant(
                "benign_miss_recovery",
                "sequence_equals",
                (
                    operation_ref(
                        recovery_operation_id,
                        "lookup_observations",
                        "lookup_result",
                        lookup_index=0,
                    ),
                    operation_ref(
                        recovery_operation_id,
                        "lookup_observations",
                        "lookup_result",
                        lookup_index=1,
                    ),
                ),
                ["no_match", "match"],
                "supportive",
                "A healthy reference has an initial miss followed by a successful lookup.",
            ),
            DiagnosticInvariant(
                "benign_miss_recovery_order",
                "ordered_before",
                (
                    operation_ref(
                        recovery_operation_id,
                        "lookup_observations",
                        "observed_at",
                        lookup_index=0,
                    ),
                    operation_ref(
                        recovery_operation_id,
                        "lookup_observations",
                        "observed_at",
                        lookup_index=1,
                    ),
                ),
                True,
                "supportive",
                "The benign miss precedes its later successful lookup.",
            ),
            DiagnosticInvariant(
                "target_no_follow_on_lookup",
                "match_count",
                (
                    _reference(
                        "lookup_observations", operation_id=target_operation_id
                    ),
                ),
                1,
                "supportive",
                "The target has no second lookup, replay, or special follow-on action.",
            ),
            DiagnosticInvariant(
                "effect_record_cardinality",
                "row_count",
                tuple(
                    _reference("effect_records", str(row["evidence_id"]))
                    for row in effect_records
                ),
                control_count,
                "supportive",
                "Exactly one effect record exists for each healthy control.",
            ),
            DiagnosticInvariant(
                "literal_external_reference_identity",
                "preserve_literal",
                (target_shape_ref,),
                False,
                "discardable",
                "The exact target reference literal is unnecessary; its relationships and shape matter.",
            ),
        ]
    )

    expected_evidence = (
        ExpectedEvidence(
            "The target reference has a distinct one-edit shape delta from successful controls.",
            (target_shape_ref, *control_shape_refs[:3]),
        ),
        ExpectedEvidence(
            "The target lookup misses and no target effect record exists.",
            (
                operation_ref(target_operation_id, "lookup_observations"),
                operation_ref(target_operation_id, "processing_attempts"),
            ),
        ),
        ExpectedEvidence(
            "Controls succeed around the target, including latency and benign-miss controls.",
            (
                operation_ref(latency_operation_id, "lookup_observations"),
                operation_ref(
                    recovery_operation_id,
                    "lookup_observations",
                    lookup_index=0,
                ),
                operation_ref(
                    recovery_operation_id,
                    "lookup_observations",
                    lookup_index=1,
                ),
            ),
        ),
    )

    return Incident(
        incident_id=FAMILY_ID,
        title="Incident 002 — Missing Provisioning Effect from Reference-Shape Defect",
        category="provisioning_missing_effect",
        description=(
            "An opaque operation reaches its executor, where an unhandled one-edit "
            "external-reference shape defect causes an exact lookup miss and no effect."
        ),
        troubleshooting_question=(
            "One submitted provisioning operation did not create its expected destination "
            "record. Review the surrounding operational evidence and identify the most "
            "likely root cause."
        ),
        ground_truth=StructuredRootCause(
            outcome="missing_provisioning_effect",
            trigger="unexpected_external_reference_shape",
            failure_mechanism="missing_reference_validation_or_normalization",
            affected_component="operation_executor",
            logical_operation_repeated=False,
            explanation=(
                "The executor used an unexpected external-reference shape in an exact "
                "lookup without the required input handling, so no provisioning effect was created."
            ),
        ),
        ground_truth_v2=StructuredRootCauseV2(
            observed_outcome="missing_effect",
            trigger="malformed_or_unexpected_input",
            subsequent_action="no_follow_on_action",
            failure_mechanism="validation_or_input_handling_failure",
            affected_component="operation_executor",
            logical_operation_repeated=False,
            explanation=(
                "The executor did not validate or normalize a structurally unexpected "
                "external reference before exact lookup; the miss created no effect."
            ),
        ),
        component_mappings=(
            ComponentMapping("request_ingress", (intake_alias,)),
            ComponentMapping("operation_executor", (executor_alias,)),
            ComponentMapping("dependency_or_downstream", (dependency_alias,)),
        ),
        structured_evidence=structured_evidence,
        log_evidence=tuple(logs),
        sensitive_fields=(
            SensitiveField(
                "processing_attempts.external_reference",
                "external_subject_identifier",
                "consistent_pseudonym",
                "Reference values are sensitive and must remain linkable across evidence sources.",
            ),
            SensitiveField(
                "lookup_observations.external_reference",
                "external_subject_identifier",
                "consistent_pseudonym",
                "Reference values are sensitive and must remain linkable across evidence sources.",
            ),
            SensitiveField(
                "logs.external_reference",
                "external_subject_identifier",
                "consistent_pseudonym",
                "Reference values are sensitive and must remain linkable across evidence sources.",
            ),
        ),
        diagnostic_invariants=tuple(invariants),
        expected_evidence=expected_evidence,
        difficulty="medium",
        metadata={
            "benchmark_version": "diagbench-v0.3",
            "family_id": FAMILY_ID,
            "generator_version": GENERATOR_VERSION,
            "structural_signature_version": STRUCTURAL_SIGNATURE_VERSION,
            "seed": seed,
            "seed_split": "development",
            "generation_domain_sha256": generation_domain,
            "structural_template_name": template_name,
            "structural_template": template,
            "defect_class": defect,
            "observable_structural_delta": observable_delta,
            "defect_position": defect_position,
            "defect_operation": defect_operation,
            "latent_valid_reference": latent_valid_reference,
            "target_external_reference": target_reference,
            "target_operation_id": target_operation_id,
            "control_operation_ids": list(control_operation_ids),
            "target_chronological_position": target_position,
            "latency_control_operation_id": latency_operation_id,
            "recovery_control_operation_id": recovery_operation_id,
            "intake_alias": intake_alias,
            "executor_alias": executor_alias,
            "dependency_alias": dependency_alias,
            "healthy_structural_signature": structural_signature(latent_valid_reference),
            "target_structural_signature": structural_signature(target_reference),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    incident = generate_incident_002(args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(incident.to_json(), encoding="utf-8")


if __name__ == "__main__":
    main()
