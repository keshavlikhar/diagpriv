"""Offline audit of non-temporal shortcut cues in Incident 003 v2."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from typing import Iterable

from diagbench.audits.incident_003 import temporally_ablated_model_view
from diagbench.generators.incident_003_v2 import (
    FAMILY_ID,
    generate_incident_003_v2,
)
from diagbench.schema import Incident, ModelView
from diagbench.schema.models import JSONValue

CUE_AUDIT_VERSION = "incident-003-v2-nontemporal-cue-audit-v1"
DEVELOPMENT_AUDIT_MIN_SEED = 1000
DEVELOPMENT_AUDIT_MAX_SEED = 1199

CUE_NAMES = (
    "explicit_deadline_lexical_cue",
    "deadline_schema_name_cue",
    "compensation_record_cue",
    "compensation_lexical_cue",
    "successful_execution_cue",
    "active_effect_cue",
    "compensated_workflow_cue",
    "terminal_state_contradiction",
    "orchestrator_role_cue",
    "executor_role_cue",
    "cancellation_or_fencing_lexical_cue",
    "late_or_overlap_lexical_cue",
    "temporal_relation_available",
)

MESSAGE_CONCEPTS: dict[str, tuple[str, ...]] = {
    "dispatch_recorded": ("workflow_dispatch",),
    "execution_started": ("execution_lifecycle",),
    "dependency_observed": ("dependency_health",),
    "execution_progress": ("execution_progress",),
    "deadline_reached": ("deadline",),
    "compensation_started": ("compensation_or_rollback",),
    "compensation_completed": ("compensation_or_rollback",),
    "execution_completed": ("execution_result",),
    "effect_recorded": ("effect_presence",),
    "workflow_state_recorded": ("workflow_state",),
    "workflow_checkpoint": ("workflow_state",),
}

_VOLATILE_OR_OPAQUE_FIELDS = {
    "evidence_id",
    "operation_id",
    "effect_id",
    "compensation_id",
    "timestamp",
    "dispatched_at",
    "deadline_at",
    "started_at",
    "completed_at",
    "created_at",
    "observed_at",
}


def audit_incident_003_cues(incident: Incident) -> dict[str, JSONValue]:
    """Audit one development instance after the frozen temporal ablation."""
    _validate_incident(incident)
    view = temporally_ablated_model_view(incident)
    operations = _operation_records(view)
    role_ids = _role_ids(incident)
    profiles = {
        operation_id: _operation_profile(records)
        for operation_id, records in operations.items()
    }
    signatures = {
        operation_id: _operation_signatures(records, profiles[operation_id])
        for operation_id, records in operations.items()
    }
    target_id = role_ids["target"]
    control_ids = tuple(
        operation_id for operation_id in operations if operation_id != target_id
    )
    target_signatures = signatures[target_id]
    return {
        "audit_version": CUE_AUDIT_VERSION,
        "seed": int(incident.metadata["seed"]),
        "temporal_ablation_version": "incident-003-temporal-ablation-v1",
        "temporal_semantics": "unavailable",
        "target_profile": profiles[target_id],
        "legitimate_compensation_profile": profiles[role_ids["legitimate"]],
        "benign_slow_profile": profiles[role_ids["benign_slow"]],
        "healthy_control_profiles": [
            profiles[operation_id] for operation_id in role_ids["healthy"]
        ],
        "target_signatures": target_signatures,
        "signature_collisions": {
            name: sorted(
                operation_id
                for operation_id in control_ids
                if signatures[operation_id][name] == signature
            )
            for name, signature in target_signatures.items()
        },
        "schema_inventory": _schema_inventory(view),
        "message_inventory": _message_inventory(view),
        "aliases": {
            "orchestrator": str(incident.metadata["orchestrator_alias"]),
            "executor": str(incident.metadata["executor_alias"]),
            "dependency": str(incident.metadata["dependency_alias"]),
        },
    }


def audit_incident_003_cue_range(
    seeds: Iterable[int],
) -> dict[str, JSONValue]:
    """Aggregate cue frequencies and counterfactual separability offline."""
    seed_values = tuple(seeds)
    if not seed_values or any(
        seed < DEVELOPMENT_AUDIT_MIN_SEED
        or seed > DEVELOPMENT_AUDIT_MAX_SEED
        for seed in seed_values
    ):
        raise ValueError(
            "Incident 003 cue audit is restricted to development seeds 1000-1199"
        )

    role_counts = Counter[str]()
    cue_counts: dict[str, Counter[str]] = {
        role: Counter() for role in ("target", "healthy", "legitimate", "benign_slow")
    }
    signature_counts: dict[str, dict[str, Counter[str]]] = {
        name: {
            role: Counter()
            for role in ("target", "healthy", "legitimate", "benign_slow")
        }
        for name in (
            "full_categorical_signature",
            "terminal_state_signature",
            "record_type_signature",
            "message_event_signature",
        )
    }
    schema_paths: dict[str, dict[str, object]] = {}
    message_templates: dict[str, set[str]] = defaultdict(set)
    aliases: dict[str, Counter[str]] = {
        "orchestrator": Counter(),
        "executor": Counter(),
        "dependency": Counter(),
    }

    for seed in seed_values:
        incident = generate_incident_003_v2(seed)
        view = temporally_ablated_model_view(incident)
        operations = _operation_records(view)
        role_ids = _role_ids(incident)
        profiles = {
            operation_id: _operation_profile(records)
            for operation_id, records in operations.items()
        }
        signatures = {
            operation_id: _operation_signatures(records, profiles[operation_id])
            for operation_id, records in operations.items()
        }

        role_members = {
            "target": (role_ids["target"],),
            "healthy": role_ids["healthy"],
            "legitimate": (role_ids["legitimate"],),
            "benign_slow": (role_ids["benign_slow"],),
        }
        for role, operation_ids in role_members.items():
            role_counts[role] += len(operation_ids)
            for operation_id in operation_ids:
                profile = profiles[operation_id]
                for cue in CUE_NAMES:
                    cue_counts[role][cue] += int(bool(profile[cue]))
                for name, signature in signatures[operation_id].items():
                    signature_counts[name][role][_canonical(signature)] += 1

        for entry in _schema_inventory(view):
            path = str(entry["path"])
            aggregate = schema_paths.setdefault(
                path,
                {
                    "path": path,
                    "classification": entry["classification"],
                    "leaked_concepts": entry["leaked_concepts"],
                    "value_kind": entry["value_kind"],
                    "values": set(),
                },
            )
            values = aggregate["values"]
            assert isinstance(values, set)
            values.update(str(value) for value in entry["representative_values"])

        for entry in _message_inventory(view):
            message_templates[str(entry["event_kind"])].update(
                str(message) for message in entry["messages"]
            )
        aliases["orchestrator"][str(incident.metadata["orchestrator_alias"])] += 1
        aliases["executor"][str(incident.metadata["executor_alias"])] += 1
        aliases["dependency"][str(incident.metadata["dependency_alias"])] += 1

    cue_frequency: dict[str, JSONValue] = {}
    for cue in CUE_NAMES:
        cue_frequency[cue] = {
            role: {
                "count": cue_counts[role][cue],
                "total": role_counts[role],
                "rate": cue_counts[role][cue] / role_counts[role],
            }
            for role in role_counts
        }

    separability: dict[str, JSONValue] = {}
    for name, counts_by_role in signature_counts.items():
        target_signatures = set(counts_by_role["target"])
        control_signatures = set(counts_by_role["healthy"]) | set(
            counts_by_role["legitimate"]
        )
        collisions = target_signatures & control_signatures
        separability[name] = {
            "target_unique_signature_count": len(target_signatures),
            "healthy_unique_signature_count": len(counts_by_role["healthy"]),
            "legitimate_unique_signature_count": len(
                counts_by_role["legitimate"]
            ),
            "target_control_collision_count": len(collisions),
            "target_operations_with_colliding_signature": sum(
                counts_by_role["target"][signature] for signature in collisions
            ),
            "perfectly_separable": not collisions,
        }

    schema_inventory = []
    for path in sorted(schema_paths):
        entry = schema_paths[path]
        values = entry.pop("values")
        assert isinstance(values, set)
        entry["representative_values"] = sorted(values)
        schema_inventory.append(entry)

    message_inventory = [
        {
            "event_kind": event_kind,
            "messages": sorted(messages),
            "leaked_concepts": list(MESSAGE_CONCEPTS.get(event_kind, ())),
            "explicitly_implies_late_overlap_or_control_failure": any(
                _contains_any(
                    message,
                    ("late", "overlap", "still active", "not cancelled", "fencing"),
                )
                for message in messages
            ),
        }
        for event_kind, messages in sorted(message_templates.items())
    ]

    return {
        "audit_version": CUE_AUDIT_VERSION,
        "sample_size": len(seed_values),
        "seed_min": min(seed_values),
        "seed_max": max(seed_values),
        "role_counts": dict(role_counts),
        "cue_frequency": cue_frequency,
        "counterfactual_separability": separability,
        "schema_inventory": schema_inventory,
        "message_inventory": message_inventory,
        "alias_frequencies": {
            role: dict(sorted(counter.items())) for role, counter in aliases.items()
        },
        "provider_calls": 0,
    }


def _validate_incident(incident: Incident) -> None:
    if incident.incident_id != FAMILY_ID:
        raise ValueError("Cue audit supports Incident 003 v2 only")
    seed = int(incident.metadata["seed"])
    if seed < DEVELOPMENT_AUDIT_MIN_SEED or seed > DEVELOPMENT_AUDIT_MAX_SEED:
        raise ValueError("Cue audit is restricted to development seeds 1000-1199")


def _role_ids(incident: Incident) -> dict[str, object]:
    return {
        "target": str(incident.metadata["target_operation_id"]),
        "healthy": tuple(
            str(value) for value in incident.metadata["healthy_control_operation_ids"]
        ),
        "legitimate": str(
            incident.metadata["legitimate_compensation_operation_id"]
        ),
        "benign_slow": str(incident.metadata["slow_control_operation_id"]),
    }


def _operation_records(view: ModelView) -> dict[str, dict[str, list[dict]]]:
    operations: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for source, rows in view.structured_evidence.items():
        for row in rows:
            operation_id = row.get("operation_id")
            if operation_id is not None:
                operations[str(operation_id)][source].append(row)
    for log in view.log_evidence:
        operation_id = log.attributes.get("operation_id")
        if operation_id is not None:
            operations[str(operation_id)]["logs"].append(log.to_dict())
    return {operation_id: dict(sources) for operation_id, sources in operations.items()}


def _operation_profile(records: dict[str, list[dict]]) -> dict[str, JSONValue]:
    workflow = _single(records, "workflow_attempts")
    execution = _single(records, "execution_observations")
    effects = records.get("effect_records", [])
    compensations = records.get("compensation_records", [])
    logs = records.get("logs", [])
    messages = tuple(str(row.get("message", "")).lower() for row in logs)
    event_kinds = tuple(
        str(_attributes(row).get("event_kind", "")).lower() for row in logs
    )
    all_values = tuple(_walk_strings(records))
    workflow_state = str(workflow.get("workflow_state", ""))
    execution_result = str(execution.get("result", ""))
    effect_states = tuple(str(row.get("state", "")) for row in effects)
    compensation_result = tuple(str(row.get("result", "")) for row in compensations)
    return {
        "explicit_deadline_lexical_cue": any(
            _contains_any(value, ("deadline", "timeout"))
            for value in (*messages, *event_kinds)
        ),
        "deadline_schema_name_cue": "deadline_at" in workflow,
        "compensation_record_cue": bool(compensations),
        "compensation_lexical_cue": any(
            _contains_any(value, ("compensation", "rollback"))
            for value in (*messages, *event_kinds)
        ),
        "successful_execution_cue": execution_result == "success",
        "active_effect_cue": "active" in effect_states,
        "compensated_workflow_cue": workflow_state == "compensated",
        "terminal_state_contradiction": (
            workflow_state == "compensated"
            and execution_result == "success"
            and "active" in effect_states
        ),
        "orchestrator_role_cue": bool(workflow.get("orchestrator_alias")),
        "executor_role_cue": bool(execution.get("executor_alias")),
        "cancellation_or_fencing_lexical_cue": any(
            _contains_any(value, ("cancel", "fenc")) for value in all_values
        ),
        "late_or_overlap_lexical_cue": any(
            _contains_word_or_phrase(
                value, ("late", "overlap", "still active", "after rollback")
            )
            for value in all_values
        ),
        "temporal_relation_available": False,
        "workflow_state": workflow_state,
        "compensation_state": str(workflow.get("compensation_state", "")),
        "execution_result": execution_result,
        "effect_presence": bool(effects),
        "effect_states": list(effect_states),
        "compensation_presence": bool(compensations),
        "compensation_results": list(compensation_result),
        "event_kinds": sorted(set(event_kinds)),
    }


def _operation_signatures(
    records: dict[str, list[dict]], profile: dict[str, JSONValue]
) -> dict[str, JSONValue]:
    return {
        "full_categorical_signature": {
            "workflow_state": profile["workflow_state"],
            "compensation_state": profile["compensation_state"],
            "execution_result": profile["execution_result"],
            "effect_presence": profile["effect_presence"],
            "effect_states": profile["effect_states"],
            "compensation_presence": profile["compensation_presence"],
            "compensation_results": profile["compensation_results"],
            "event_kinds": profile["event_kinds"],
        },
        "terminal_state_signature": {
            "workflow_state": profile["workflow_state"],
            "execution_result": profile["execution_result"],
            "effect_states": profile["effect_states"],
            "compensation_presence": profile["compensation_presence"],
        },
        "record_type_signature": sorted(
            source for source, rows in records.items() if source != "logs" and rows
        ),
        "message_event_signature": profile["event_kinds"],
    }


def _schema_inventory(view: ModelView) -> list[dict[str, JSONValue]]:
    values_by_path: dict[str, list[object]] = defaultdict(list)
    values_by_path["troubleshooting_question"].append(view.troubleshooting_question)
    for source, rows in view.structured_evidence.items():
        values_by_path[f"structured_evidence.{source}"].append("<record-present>")
        for row in rows:
            for key, value in row.items():
                values_by_path[f"structured_evidence.{source}.{key}"].append(value)
    values_by_path["log_evidence"].append("<record-present>")
    for log in view.log_evidence:
        data = log.to_dict()
        for key, value in data.items():
            if key == "attributes":
                for attr_key, attr_value in _attributes(data).items():
                    values_by_path[f"log_evidence.attributes.{attr_key}"].append(
                        attr_value
                    )
            else:
                values_by_path[f"log_evidence.{key}"].append(value)

    inventory = []
    for path, values in sorted(values_by_path.items()):
        field = path.rsplit(".", maxsplit=1)[-1]
        classification, concepts = _classify_schema_path(path)
        if field in _VOLATILE_OR_OPAQUE_FIELDS:
            value_kind = (
                "opaque-temporal-marker"
                if field
                in {
                    "timestamp",
                    "dispatched_at",
                    "deadline_at",
                    "started_at",
                    "completed_at",
                    "created_at",
                    "observed_at",
                }
                else "identifier"
            )
            representative = [f"<{value_kind}>"]
        elif all(isinstance(value, (int, float)) for value in values):
            value_kind = "numeric"
            representative = ["<numeric>"]
        else:
            value_kind = "categorical-or-text"
            representative = sorted({str(value) for value in values})
        inventory.append(
            {
                "path": path,
                "classification": classification,
                "leaked_concepts": list(concepts),
                "value_kind": value_kind,
                "representative_values": representative,
            }
        )
    return inventory


def _classify_schema_path(path: str) -> tuple[str, tuple[str, ...]]:
    if path == "troubleshooting_question":
        return "strong cue", ("inconsistent_state",)
    if path.endswith("orchestrator_alias"):
        return "near-label leakage", ("workflow_orchestrator",)
    if path.endswith("executor_alias"):
        return "strong cue", ("operation_executor",)
    if path.endswith("deadline_at"):
        return "strong cue", ("timeout_or_deadline", "deadline_exists")
    if (
        "compensation_records" in path
        or path.endswith("compensation_state")
        or path.endswith("compensation_id")
    ):
        return "strong cue", ("compensation_or_rollback",)
    if path.endswith("workflow_state"):
        return "strong cue", ("workflow_terminal_state",)
    if "effect_records" in path and path.endswith("state"):
        return "strong cue", ("downstream_effect_state",)
    if path.endswith("result"):
        return "strong cue", ("execution_outcome",)
    if path.endswith("state"):
        return "strong cue", ("terminal_or_effect_state",)
    if path.endswith("event_kind") or path.endswith("message"):
        return "strong cue", ("event_semantics",)
    if path.endswith("service"):
        return "strong cue", ("component_role",)
    if path.endswith("operation_id"):
        return "weak cue", ("cross_source_identity",)
    if path.endswith(
        ("dispatched_at", "started_at", "completed_at", "created_at", "observed_at")
    ):
        return "weak cue", ("event_boundary_exists",)
    if path.endswith("warning") or path.endswith("latency_ms"):
        return "weak cue", ("dependency_distractor",)
    if path == "structured_evidence.effect_records":
        return "strong cue", ("downstream_effect_presence", "record_type")
    if path in {
        "structured_evidence.workflow_attempts",
        "structured_evidence.execution_observations",
    }:
        return "weak cue", ("record_type",)
    if path == "structured_evidence.compensation_records":
        return "strong cue", ("compensation_or_rollback", "record_type")
    return "neutral", ()


def _message_inventory(view: ModelView) -> list[dict[str, JSONValue]]:
    messages: dict[str, set[str]] = defaultdict(set)
    for log in view.log_evidence:
        event_kind = str(log.attributes.get("event_kind", ""))
        messages[event_kind].add(log.message)
    return [
        {
            "event_kind": event_kind,
            "messages": sorted(texts),
            "leaked_concepts": list(MESSAGE_CONCEPTS.get(event_kind, ())),
            "explicitly_implies_late_overlap_or_control_failure": any(
                _contains_any(
                    text,
                    ("late", "overlap", "still active", "not cancelled", "fencing"),
                )
                for text in texts
            ),
        }
        for event_kind, texts in sorted(messages.items())
    ]


def _single(records: dict[str, list[dict]], source: str) -> dict:
    rows = records.get(source, [])
    if len(rows) != 1:
        raise ValueError(f"Expected one {source} row; found {len(rows)}")
    return rows[0]


def _attributes(row: dict) -> dict:
    value = row.get("attributes", {})
    return value if isinstance(value, dict) else {}


def _walk_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value.lower()]
    if isinstance(value, dict):
        strings: list[str] = []
        for item in value.values():
            strings.extend(_walk_strings(item))
        return strings
    if isinstance(value, (list, tuple)):
        strings = []
        for item in value:
            strings.extend(_walk_strings(item))
        return strings
    return []


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in terms)


def _contains_word_or_phrase(value: str, terms: tuple[str, ...]) -> bool:
    normalized = "".join(character if character.isalnum() else " " for character in value.lower())
    words = normalized.split()
    padded = f" {' '.join(words)} "
    return any(f" {term} " in padded for term in terms)


def _canonical(value: JSONValue) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--seed-end", type=int, default=1199)
    args = parser.parse_args()
    report = audit_incident_003_cue_range(
        range(args.seed_start, args.seed_end + 1)
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
