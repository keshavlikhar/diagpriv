"""Final offline identifier, position, and ordering audit for Incident 003 v3.

This module is deliberately diagnostic.  It does not mutate benchmark output or
repair failures that it discovers.  In particular, a failed acceptance gate is
part of the audit result rather than a reason to normalize the generator here.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import json
import re
from typing import Iterable, Mapping

from diagbench.audits.incident_003 import temporally_ablated_model_view
from diagbench.audits.incident_003_v3 import (
    audit_incident_003_v3_range,
    non_temporal_operation_projection,
)
from diagbench.generators.incident_003_v3 import (
    AUDIT_SEEDS,
    FAMILY_ID,
    NEUTRAL_QUESTION_TEMPLATE,
    generate_incident_003_v3,
    incident_003_v3_query_case,
)
from diagbench.relative_time import RELATIVE_TIME_SEMANTICS_VERSION
from diagbench.schema import Incident, IncidentV3, ModelView
from diagbench.schema.models import JSONValue
from diagbench.temporal import TEMPORAL_SEMANTICS_VERSION
from diagpriv.evaluation.evidence_support_v4 import score_evidence_support_v4
from diagpriv.evaluation.incident_003_v3_evidence import (
    build_incident_003_v3_evidence_rubric,
)
from diagpriv.evaluation.incident_003_v3_evidence_semantics import (
    Incident003V3EvidenceSemanticEvaluator,
)
from diagpriv.invariants import evaluate_invariants
from diagpriv.transformations.provenance import TEMPORAL_SEMANTICS_UNAVAILABLE
from diagpriv.transformations.relative_time_v1 import relative_time_incident

LEAKAGE_AUDIT_VERSION = "incident-003-v3-final-leakage-audit-v1"
CANONICAL_RENAMING_VERSION = "incident-003-v3-audit-canonical-renaming-v1"
ID_PERMUTATION_VERSION = "incident-003-v3-audit-id-permutation-v1"
ROW_PERMUTATION_VERSION = "incident-003-v3-audit-row-permutation-v1"

_ROLES = ("target", "temporal_twin", "safe_control")
_ROLE_METADATA = {
    "target": "target_operation_id",
    "temporal_twin": "temporal_twin_operation_id",
    "safe_control": "safe_control_operation_id",
}
_ID_PATTERN = re.compile(r"^(OP|EF|CP|EV)-(\d{8})$")
_ID_SUBSTITUTION_PATTERN = re.compile(r"(?:OP|EF|CP|EV)-\d{8}")
_FORBIDDEN_MODEL_TERMS = (
    "target",
    "twin",
    "safe_control",
    "safe-control",
    "incorrect_concurrency_control",
    "incorrect_state_transition",
    "safe-compensation",
    "operation_roles",
    "target_mechanism",
    "temporal_twin_mechanism",
    "query_role",
    "queried_operation_id",
)


def audit_incident_003_v3_leakage_range(
    seeds: Iterable[int] = AUDIT_SEEDS,
) -> dict[str, JSONValue]:
    """Audit model-visible identifier and positional shortcuts offline."""
    seed_values = tuple(seeds)
    allowed = set(AUDIT_SEEDS)
    if not seed_values or any(seed not in allowed for seed in seed_values):
        raise ValueError("Incident 003 v3 leakage audit is restricted to seeds 1200-1399")

    incidents = tuple(generate_incident_003_v3(seed) for seed in seed_values)
    position_counts = _new_position_counts()
    identifier_stats = _new_identifier_stats()
    marker_slot_order: dict[str, Counter[str]] = defaultdict(Counter)
    canonical_passes = 0
    id_permutation_passes = 0
    row_permutation_passes = 0
    rendered_isomorphism_passes = 0
    question_template_passes = 0
    hidden_metadata_passes = 0
    marker_structure_passes = 0
    query_evidence_equal = 0
    query_serialization_equal = 0
    query_question_equal = 0
    query_oracle_only_mechanism_differs = 0
    query_oracle_conflicts = 0
    raw_target_evidence_passes = 0
    raw_twin_evidence_passes = 0
    relative_target_evidence_passes = 0
    relative_twin_evidence_passes = 0
    ablated_query_isomorphism_passes = 0
    ablated_target_unidentifiable = 0
    ablated_twin_unidentifiable = 0
    safe_control_invariant_passes = 0

    for incident in incidents:
        twin_query = incident_003_v3_query_case(incident, "temporal_twin")
        raw = incident.model_view()
        twin_raw = twin_query.model_view()
        relative = relative_time_incident(incident)
        twin_relative = relative_time_incident(twin_query)
        ablated = temporally_ablated_model_view(incident)
        twin_ablated = temporally_ablated_model_view(twin_query)
        role_ids = _role_ids(incident)
        _collect_positions(position_counts, raw, ablated, role_ids)
        _collect_identifier_stats(identifier_stats, raw, role_ids)
        _collect_marker_stats(marker_slot_order, ablated, role_ids)

        target_slice = _canonical_operation_slice(
            ablated, role_ids["target"]
        )
        twin_slice = _canonical_operation_slice(
            ablated, role_ids["temporal_twin"]
        )
        canonical_equal = target_slice == twin_slice
        canonical_passes += canonical_equal
        rendered_isomorphism_passes += canonical_equal

        id_permutation_passes += _id_permutation_preserves_semantics(incident)
        row_permutation_passes += _row_permutation_preserves_semantics(incident)

        target_question = NEUTRAL_QUESTION_TEMPLATE.format(
            operation_id=role_ids["target"]
        )
        twin_question = NEUTRAL_QUESTION_TEMPLATE.format(
            operation_id=role_ids["temporal_twin"]
        )
        question_template_passes += (
            target_question.replace(role_ids["target"], "OP_A")
            == twin_question.replace(role_ids["temporal_twin"], "OP_A")
        )

        model_json = raw.to_json(indent=None).lower()
        hidden_metadata_passes += not any(
            term in model_json for term in _FORBIDDEN_MODEL_TERMS
        )
        marker_structure_passes += _marker_structure_is_role_neutral(ablated)

        query_evidence_equal += (
            raw.structured_evidence == twin_raw.structured_evidence
            and raw.log_evidence == twin_raw.log_evidence
        )
        query_serialization_equal += _serialized_evidence(raw) == _serialized_evidence(
            twin_raw
        )
        query_question_equal += _normalized_question(
            raw.troubleshooting_question, role_ids["target"]
        ) == _normalized_question(
            twin_raw.troubleshooting_question, role_ids["temporal_twin"]
        )
        query_oracle_only_mechanism_differs += _only_mechanism_differs(
            incident, twin_query
        )
        query_oracle_conflicts += (
            incident.ground_truth_v3.failure_mechanism
            == "incorrect_concurrency_control"
            and twin_query.ground_truth_v3.failure_mechanism
            == "incorrect_state_transition"
        )

        target_raw_score = _evidence_score(
            incident, raw, TEMPORAL_SEMANTICS_VERSION
        )
        twin_raw_score = _evidence_score(
            twin_query, twin_raw, TEMPORAL_SEMANTICS_VERSION
        )
        target_relative_score = _evidence_score(
            incident, relative, RELATIVE_TIME_SEMANTICS_VERSION
        )
        twin_relative_score = _evidence_score(
            twin_query, twin_relative, RELATIVE_TIME_SEMANTICS_VERSION
        )
        target_ablated_score = _evidence_score(
            incident, ablated, TEMPORAL_SEMANTICS_UNAVAILABLE
        )
        twin_ablated_score = _evidence_score(
            twin_query, twin_ablated, TEMPORAL_SEMANTICS_UNAVAILABLE
        )
        raw_target_evidence_passes += target_raw_score.evidence_supported
        raw_twin_evidence_passes += twin_raw_score.evidence_supported
        relative_target_evidence_passes += target_relative_score.evidence_supported
        relative_twin_evidence_passes += twin_relative_score.evidence_supported
        ablated_target_unidentifiable += not target_ablated_score.evidence_supported
        ablated_twin_unidentifiable += not twin_ablated_score.evidence_supported
        ablated_query_isomorphism_passes += _ablated_query_pair_isomorphic(
            incident, twin_query, ablated, twin_ablated
        )
        safe_results = [
            item
            for item in evaluate_invariants(
                incident,
                raw,
                temporal_semantics_version=TEMPORAL_SEMANTICS_VERSION,
            )
            if item.name.startswith("v3_safe_control_")
        ]
        safe_control_invariant_passes += bool(safe_results) and all(
            item.preserved for item in safe_results
        )

    sample_size = len(incidents)
    identifier_report = _finalize_identifier_stats(identifier_stats, sample_size)
    position_report = _finalize_positions(position_counts, sample_size)
    marker_report = _finalize_marker_stats(
        marker_slot_order, position_report, marker_structure_passes, sample_size
    )
    existing = audit_incident_003_v3_range(seed_values)

    positional_separators = list(position_report["perfect_separators"])
    question_position_separators = (
        ["queried_operation.raw_log_group_ordinal"]
        if "raw_logs.group_ordinal" in positional_separators
        else []
    )
    grouping_separators = (
        ["raw_logs.operation_block_order"]
        if "raw_logs.group_ordinal" in positional_separators
        else []
    )
    source_row_separators = [
        item for item in positional_separators if item.startswith("structured_evidence.")
    ]
    gates = {
        "no_literal_identifier_perfect_separator": not identifier_report[
            "perfect_separators"
        ],
        "no_queried_subject_positional_perfect_separator": not positional_separators,
        "no_nontemporal_row_or_grouping_perfect_separator": (
            not source_row_separators
            and not position_report["ablated_log_perfect_separators"]
        ),
        "canonical_id_renaming_preserves_v3_conclusions": (
            canonical_passes == sample_size
        ),
        "id_permutation_preserves_oracle_and_evidence_semantics": (
            id_permutation_passes == sample_size
        ),
        "row_permutation_preserves_oracle_and_evidence_semantics": (
            row_permutation_passes == sample_size
        ),
        "order_preserving_rendered_nontemporal_isomorphism": (
            rendered_isomorphism_passes == sample_size
        ),
        "question_templates_class_neutral_after_id_normalization": (
            question_template_passes == sample_size
        ),
        "hidden_generator_oracle_metadata_absent_from_model_view": (
            hidden_metadata_passes == sample_size
        ),
        "temporal_ablation_markers_add_no_class_correlated_artifact": (
            marker_structure_passes == sample_size
            and not marker_report["perfect_separators"]
        ),
        "existing_25_acceptance_gates_pass": bool(existing["passed"]),
        "raw_log_role_position_not_perfect_separator": not positional_separators,
        "queried_subject_position_not_mechanism_separator": not question_position_separators,
        "paired_queries_share_underlying_incident_evidence": (
            query_evidence_equal == sample_size
        ),
        "evidence_serialization_independent_of_query_role": (
            query_serialization_equal == sample_size
        ),
        "balanced_query_population_feasible": sample_size > 0,
        "raw_target_query_has_concurrency_evidence": (
            raw_target_evidence_passes == sample_size
        ),
        "raw_twin_query_has_state_transition_evidence": (
            raw_twin_evidence_passes == sample_size
        ),
        "relative_time_preserves_both_query_diagnoses": (
            relative_target_evidence_passes == sample_size
            and relative_twin_evidence_passes == sample_size
        ),
        "ablated_query_pair_rendered_inputs_isomorphic": (
            ablated_query_isomorphism_passes == sample_size
        ),
        "ablated_pair_has_conflicting_mechanism_oracles": (
            query_oracle_conflicts == sample_size
        ),
        "paired_mechanisms_have_no_nontemporal_feature_separator": (
            canonical_passes == sample_size
        ),
        "paired_mechanisms_have_no_known_2_3_4_conjunction_separator": all(
            count == 0 for count in existing["conjunction_separator_counts"].values()  # type: ignore[union-attr]
        ),
        "literal_ids_do_not_reveal_query_mechanism": (
            not identifier_report["perfect_separators"]
        ),
        "ta1_markers_reveal_neither_query_mechanism_nor_role": (
            marker_structure_passes == sample_size
            and not marker_report["perfect_separators"]
        ),
        "safe_control_invariants_remain_valid": (
            safe_control_invariant_passes == sample_size
        ),
    }
    separator_counts = {
        "literal_identifier": len(identifier_report["perfect_separators"]),
        "target_position": len(positional_separators),
        "source_row_index": len(source_row_separators),
        "evidence_id_pattern": len(identifier_report["evidence_id_separators"]),
        "grouping_or_order": len(grouping_separators),
        "question_position": len(question_position_separators),
        "ta1_marker_derived": len(marker_report["perfect_separators"]),
    }
    return {
        "audit_version": LEAKAGE_AUDIT_VERSION,
        "sample_size": sample_size,
        "seed_min": min(seed_values),
        "seed_max": max(seed_values),
        "identifier_generation": identifier_report,
        "target_position": position_report,
        "grouping_order": {
            "perfect_separators": grouping_separators,
            "finding": (
                "Raw chronological logs contain three contiguous operation blocks in "
                "fixed target, temporal-twin, safe-control order."
                if grouping_separators
                else "No class-specific group ordering was found."
            ),
        },
        "canonical_renaming": {
            "version": CANONICAL_RENAMING_VERSION,
            "passed_count": canonical_passes,
            "pair_count": sample_size,
        },
        "id_permutation": {
            "version": ID_PERMUTATION_VERSION,
            "passed_count": id_permutation_passes,
            "pair_count": sample_size,
        },
        "row_permutation": {
            "version": ROW_PERMUTATION_VERSION,
            "passed_count": row_permutation_passes,
            "pair_count": sample_size,
        },
        "rendered_nontemporal_isomorphism": {
            "comparison_view": "temporal-ablation-v1",
            "preserves_model_visible_row_order": True,
            "passed_count": rendered_isomorphism_passes,
            "pair_count": sample_size,
        },
        "question_identity_position": {
            "normalized_template_passed_count": question_template_passes,
            "pair_count": sample_size,
            "position_perfect_separators": question_position_separators,
        },
        "paired_queries": {
            "query_case_version": "incident-003-v3-paired-query-v1",
            "target_query_count": sample_size,
            "twin_query_count": sample_size,
            "balanced_population_size": sample_size * 2,
            "underlying_evidence_equal_count": query_evidence_equal,
            "serialized_evidence_equal_count": query_serialization_equal,
            "normalized_question_equal_count": query_question_equal,
            "only_mechanism_dimension_differs_count": (
                query_oracle_only_mechanism_differs
            ),
            "conflicting_mechanism_oracle_count": query_oracle_conflicts,
            "raw_target_evidence_supported_count": raw_target_evidence_passes,
            "raw_twin_evidence_supported_count": raw_twin_evidence_passes,
            "relative_target_evidence_supported_count": (
                relative_target_evidence_passes
            ),
            "relative_twin_evidence_supported_count": (
                relative_twin_evidence_passes
            ),
            "ablated_target_evidence_unsupported_count": (
                ablated_target_unidentifiable
            ),
            "ablated_twin_evidence_unsupported_count": ablated_twin_unidentifiable,
            "ablated_query_pair_isomorphism_count": (
                ablated_query_isomorphism_passes
            ),
            "isomorphism_method": (
                "Exact query-independent evidence serialization plus normalized "
                "question template and canonical queried-subject slice; no row is "
                "sorted or moved by query role."
            ),
        },
        "safe_control": {
            "all_declared_invariants_pass_count": safe_control_invariant_passes,
            "pair_count": sample_size,
        },
        "hidden_metadata_exclusion": {
            "passed_count": hidden_metadata_passes,
            "pair_count": sample_size,
            "searched_terms": list(_FORBIDDEN_MODEL_TERMS),
        },
        "temporal_ablation_marker": marker_report,
        "separator_counts": separator_counts,
        "acceptance_gates": gates,
        "failed_acceptance_gates": [
            name for name, passed in gates.items() if not passed
        ],
        "existing_audit": {
            "acceptance_gate_count": len(existing["check_counts"]),
            "passed": existing["passed"],
        },
        "passed": all(gates.values()),
        "readiness": "READY TO COMMIT" if all(gates.values()) else "BLOCKED",
        "provider_calls": 0,
    }


def _serialized_evidence(view: ModelView) -> str:
    return json.dumps(
        {
            "structured_evidence": view.structured_evidence,
            "log_evidence": [entry.to_dict() for entry in view.log_evidence],
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _normalized_question(question: str, operation_id: str) -> str:
    return question.replace(operation_id, "<queried_operation_id>")


def _only_mechanism_differs(
    target_query: IncidentV3, twin_query: IncidentV3
) -> bool:
    for target_oracle, twin_oracle in (
        (target_query.ground_truth, twin_query.ground_truth),
        (target_query.ground_truth_v2, twin_query.ground_truth_v2),
        (target_query.ground_truth_v3, twin_query.ground_truth_v3),
    ):
        target_data = target_oracle.to_dict()
        twin_data = twin_oracle.to_dict()
        target_mechanism = target_data.pop("failure_mechanism")
        twin_mechanism = twin_data.pop("failure_mechanism")
        target_data.pop("explanation", None)
        twin_data.pop("explanation", None)
        if target_data != twin_data or target_mechanism == twin_mechanism:
            return False
    return True


def _evidence_score(
    incident: IncidentV3, view: ModelView, temporal_semantics_version: str
):
    rubric = build_incident_003_v3_evidence_rubric(incident)
    cited = tuple(
        evidence_id
        for binding in rubric.subject_bindings
        for evidence_id in binding.evidence_ids
    )
    return score_evidence_support_v4(
        cited,
        view,
        rubric,
        Incident003V3EvidenceSemanticEvaluator(temporal_semantics_version),
    )


def _ablated_query_pair_isomorphic(
    target_query: IncidentV3,
    twin_query: IncidentV3,
    target_view: ModelView,
    twin_view: ModelView,
) -> bool:
    """Check the pointed pair without sorting or moving rendered rows.

    Query-independent evidence must be byte-equivalent in its existing order;
    the question template is normalized only at its subject token; and the two
    queried subject slices must be canonically isomorphic. These checks jointly
    preserve query linkage while avoiding a query-dependent serializer.
    """
    target_id = str(target_query.metadata["queried_operation_id"])
    twin_id = str(twin_query.metadata["queried_operation_id"])
    return bool(
        _serialized_evidence(target_view) == _serialized_evidence(twin_view)
        and _normalized_question(target_view.troubleshooting_question, target_id)
        == _normalized_question(twin_view.troubleshooting_question, twin_id)
        and _canonical_operation_slice(target_view, target_id)
        == _canonical_operation_slice(twin_view, twin_id)
    )


def _role_ids(incident: Incident) -> dict[str, str]:
    return {
        role: str(incident.metadata[key]) for role, key in _ROLE_METADATA.items()
    }


def _new_position_counts() -> dict[str, object]:
    return {
        "structured": defaultdict(lambda: defaultdict(Counter)),
        "raw_first": defaultdict(Counter),
        "raw_last": defaultdict(Counter),
        "raw_group": defaultdict(Counter),
        "raw_contiguous": defaultdict(Counter),
        "ablated_first": defaultdict(Counter),
        "ablated_last": defaultdict(Counter),
    }


def _collect_positions(
    counts: dict[str, object],
    raw: ModelView,
    ablated: ModelView,
    role_ids: Mapping[str, str],
) -> None:
    structured = counts["structured"]
    assert isinstance(structured, defaultdict)
    for source, rows in raw.structured_evidence.items():
        for role, operation_id in role_ids.items():
            index = next(
                index
                for index, row in enumerate(rows)
                if row.get("operation_id") == operation_id
            )
            structured[source][role][index] += 1

    raw_roles = [
        _role_for_id(str(entry.attributes["operation_id"]), role_ids)
        for entry in raw.log_evidence
    ]
    ablated_roles = [
        _role_for_id(str(entry.attributes["operation_id"]), role_ids)
        for entry in ablated.log_evidence
    ]
    raw_blocks = [raw_roles[0]]
    for role in raw_roles[1:]:
        if role != raw_blocks[-1]:
            raw_blocks.append(role)
    for role in _ROLES:
        raw_indices = [index for index, item in enumerate(raw_roles) if item == role]
        ablated_indices = [
            index for index, item in enumerate(ablated_roles) if item == role
        ]
        counts["raw_first"][role][raw_indices[0]] += 1  # type: ignore[index]
        counts["raw_last"][role][raw_indices[-1]] += 1  # type: ignore[index]
        counts["raw_group"][role][raw_blocks.index(role)] += 1  # type: ignore[index]
        counts["raw_contiguous"][role][
            raw_indices == list(range(raw_indices[0], raw_indices[-1] + 1))
        ] += 1  # type: ignore[index]
        counts["ablated_first"][role][ablated_indices[0]] += 1  # type: ignore[index]
        counts["ablated_last"][role][ablated_indices[-1]] += 1  # type: ignore[index]


def _finalize_positions(
    counts: dict[str, object], sample_size: int
) -> dict[str, JSONValue]:
    structured = counts["structured"]
    assert isinstance(structured, defaultdict)
    structured_report = {
        source: {
            role: _counter(counter) for role, counter in by_role.items()
        }
        for source, by_role in sorted(structured.items())
    }
    separators: list[str] = []
    for source, by_role in structured.items():
        if _role_property_perfectly_separates(by_role, sample_size):
            separators.append(f"structured_evidence.{source}.row_index")
    for key, label in (
        ("raw_first", "raw_logs.first_index"),
        ("raw_last", "raw_logs.last_index"),
        ("raw_group", "raw_logs.group_ordinal"),
    ):
        values = counts[key]
        assert isinstance(values, defaultdict)
        if _role_property_perfectly_separates(values, sample_size):
            separators.append(label)
    ablated_separators = []
    for key, label in (
        ("ablated_first", "ablated_logs.first_index"),
        ("ablated_last", "ablated_logs.last_index"),
    ):
        values = counts[key]
        assert isinstance(values, defaultdict)
        if _role_property_perfectly_separates(values, sample_size):
            ablated_separators.append(label)
    return {
        "structured_row_index_distributions": structured_report,
        "raw_log_first_index_distributions": _role_counters(counts["raw_first"]),
        "raw_log_first_index_summary": _role_position_summaries(
            counts["raw_first"]
        ),
        "raw_log_last_index_distributions": _role_counters(counts["raw_last"]),
        "raw_log_group_ordinal_distributions": _role_counters(counts["raw_group"]),
        "raw_log_contiguous_block_counts": _role_counters(counts["raw_contiguous"]),
        "ablated_log_first_index_distributions": _role_counters(
            counts["ablated_first"]
        ),
        "ablated_log_last_index_distributions": _role_counters(
            counts["ablated_last"]
        ),
        "perfect_separators": separators,
        "ablated_log_perfect_separators": ablated_separators,
    }


def _new_identifier_stats() -> dict[str, object]:
    return {
        "format": defaultdict(lambda: defaultdict(Counter)),
        "rank": defaultdict(lambda: defaultdict(Counter)),
        "first_digit": defaultdict(lambda: defaultdict(Counter)),
        "last_digit": defaultdict(lambda: defaultdict(Counter)),
        "parity": defaultdict(lambda: defaultdict(Counter)),
        "numeric_values": defaultdict(lambda: defaultdict(list)),
        "evidence_min_rank": defaultdict(Counter),
        "evidence_max_rank": defaultdict(Counter),
    }


def _collect_identifier_stats(
    stats: dict[str, object], view: ModelView, role_ids: Mapping[str, str]
) -> None:
    by_role = _identifier_catalog(view, role_ids)
    for kind in ("operation", "effect", "compensation"):
        values = {role: str(by_role[role][kind][0]) for role in _ROLES}
        ranked = {
            value: rank for rank, value in enumerate(sorted(values.values()))
        }
        for role, value in values.items():
            match = _ID_PATTERN.fullmatch(value)
            assert match is not None
            digits = match.group(2)
            stats["format"][kind][role][  # type: ignore[index]
                f"{match.group(1)}-dddddddd|len={len(value)}"
            ] += 1
            stats["rank"][kind][role][ranked[value]] += 1  # type: ignore[index]
            stats["first_digit"][kind][role][digits[0]] += 1  # type: ignore[index]
            stats["last_digit"][kind][role][digits[-1]] += 1  # type: ignore[index]
            stats["parity"][kind][role][str(int(digits) % 2)] += 1  # type: ignore[index]
            stats["numeric_values"][kind][role].append(int(digits))  # type: ignore[index]

    all_evidence = sorted(
        str(value)
        for role in _ROLES
        for value in by_role[role]["evidence"]
    )
    evidence_rank = {value: rank for rank, value in enumerate(all_evidence)}
    for role in _ROLES:
        ranks = [evidence_rank[str(value)] for value in by_role[role]["evidence"]]
        stats["evidence_min_rank"][role][min(ranks)] += 1  # type: ignore[index]
        stats["evidence_max_rank"][role][max(ranks)] += 1  # type: ignore[index]


def _finalize_identifier_stats(
    stats: dict[str, object], sample_size: int
) -> dict[str, JSONValue]:
    perfect: list[str] = []
    report: dict[str, JSONValue] = {}
    for property_name in ("format", "rank", "first_digit", "last_digit", "parity"):
        by_kind = stats[property_name]
        assert isinstance(by_kind, defaultdict)
        report[property_name] = {
            kind: {role: _counter(counter) for role, counter in roles.items()}
            for kind, roles in sorted(by_kind.items())
        }
        for kind, roles in by_kind.items():
            if _role_property_perfectly_separates(roles, sample_size):
                perfect.append(f"{kind}.{property_name}")
    numeric = stats["numeric_values"]
    assert isinstance(numeric, defaultdict)
    numeric_ranges: dict[str, JSONValue] = {}
    for kind, roles in sorted(numeric.items()):
        numeric_ranges[kind] = {
            role: {"min": min(values), "max": max(values)}
            for role, values in roles.items()
        }
        ranges = [(min(values), max(values)) for values in roles.values()]
        if all(
            left_max < right_min or right_max < left_min
            for index, (left_min, left_max) in enumerate(ranges)
            for right_min, right_max in ranges[index + 1 :]
        ):
            perfect.append(f"{kind}.numeric_range")
    evidence_separators = []
    for property_name in ("evidence_min_rank", "evidence_max_rank"):
        roles = stats[property_name]
        assert isinstance(roles, defaultdict)
        if _role_property_perfectly_separates(roles, sample_size):
            evidence_separators.append(property_name)
    return {
        "visible_identifier_kinds": [
            "operation_id",
            "effect_id",
            "compensation_id",
            "evidence_id",
        ],
        "absent_identifier_kinds": [
            "separate_execution_id",
            "separate_workflow_attempt_id",
            "separate_correlation_id",
        ],
        "format_distributions": report["format"],
        "lexical_rank_distributions": report["rank"],
        "first_digit_distributions": report["first_digit"],
        "last_digit_distributions": report["last_digit"],
        "parity_distributions": report["parity"],
        "numeric_ranges": numeric_ranges,
        "evidence_min_rank_distributions": _role_counters(
            stats["evidence_min_rank"]
        ),
        "evidence_max_rank_distributions": _role_counters(
            stats["evidence_max_rank"]
        ),
        "generation_order": {
            "internal_role_order": ["target", "temporal_twin", "safe_control"],
            "ordinal_encoded_in_identifier": False,
            "independence_mechanism": (
                "A SHA-256 domain-separated seed initializes a local PRNG; each "
                "identifier is an independent fixed-width random draw with collision "
                "rejection, and no creation ordinal is embedded in the literal."
            ),
        },
        "perfect_separators": perfect,
        "evidence_id_separators": evidence_separators,
    }


def _identifier_catalog(
    view: ModelView, role_ids: Mapping[str, str]
) -> dict[str, dict[str, list[str]]]:
    result = {
        role: {
            "operation": [operation_id],
            "effect": [],
            "compensation": [],
            "evidence": [],
        }
        for role, operation_id in role_ids.items()
    }
    for rows in view.structured_evidence.values():
        for row in rows:
            role = _role_for_id(str(row["operation_id"]), role_ids)
            result[role]["evidence"].append(str(row["evidence_id"]))
            if "effect_id" in row:
                result[role]["effect"].append(str(row["effect_id"]))
            if "compensation_id" in row:
                result[role]["compensation"].append(str(row["compensation_id"]))
    for entry in view.log_evidence:
        role = _role_for_id(str(entry.attributes["operation_id"]), role_ids)
        result[role]["evidence"].append(entry.evidence_id)
    return result


def _canonical_operation_slice(
    view: ModelView, operation_id: str
) -> dict[str, JSONValue]:
    """Rename one subject by structural path while preserving rendered row order."""
    replacements: dict[str, str] = {operation_id: "OP_A"}
    structured: dict[str, JSONValue] = {}
    for source, rows in view.structured_evidence.items():
        selected = [row for row in rows if row.get("operation_id") == operation_id]
        canonical_rows = []
        for row_index, row in enumerate(selected):
            evidence_id = str(row["evidence_id"])
            replacements[evidence_id] = f"EV_{source}_{row_index}"
            if "effect_id" in row:
                replacements[str(row["effect_id"])] = "EF_A"
            if "compensation_id" in row:
                replacements[str(row["compensation_id"])] = "CP_A"
            canonical_rows.append((source, row))
        structured[source] = canonical_rows  # type: ignore[assignment]
    log_rows = [
        entry.to_dict()
        for entry in view.log_evidence
        if entry.attributes.get("operation_id") == operation_id
    ]
    for row in log_rows:
        event_kind = str(row["attributes"]["event_kind"])  # type: ignore[index]
        replacements[str(row["evidence_id"])] = f"EV_logs_{event_kind}"

    def normalize(value: JSONValue, source: str | None = None) -> JSONValue:
        if isinstance(value, dict):
            normalized: dict[str, JSONValue] = {}
            for key, item in value.items():
                if key in {
                    "timestamp",
                    "dispatched_at",
                    "deadline_at",
                    "started_at",
                    "completed_at",
                    "created_at",
                    "observed_at",
                }:
                    normalized[key] = "<timestamp>"
                else:
                    normalized[key] = normalize(item, source)
            return normalized
        if isinstance(value, list):
            return [normalize(item, source) for item in value]
        if isinstance(value, tuple):
            return [normalize(item, source) for item in value]
        if isinstance(value, str):
            return _replace_string_ids(value, replacements)
        return value

    rendered_structured: dict[str, JSONValue] = {}
    for source, tagged_rows in structured.items():
        assert isinstance(tagged_rows, list)
        rendered_structured[source] = [
            normalize(row, source) for _, row in tagged_rows  # type: ignore[misc]
        ]
    return {
        "canonical_renaming_version": CANONICAL_RENAMING_VERSION,
        "structured_evidence": rendered_structured,
        "log_evidence": [normalize(row, "logs") for row in log_rows],
    }


def _id_permutation_preserves_semantics(incident: IncidentV3) -> bool:
    literals = sorted(set(_ID_SUBSTITUTION_PATTERN.findall(incident.to_json(indent=None))))
    # ``findall`` returns the entire match because the pattern has no capture group.
    by_prefix: dict[str, list[str]] = defaultdict(list)
    for value in literals:
        by_prefix[value[:2]].append(value)
    mapping: dict[str, str] = {}
    for values in by_prefix.values():
        ordered = sorted(values)
        rotated = ordered[1:] + ordered[:1]
        mapping.update(zip(ordered, rotated, strict=True))
    permuted = IncidentV3.from_dict(_replace_ids(incident.to_dict(), mapping))
    if incident.ground_truth_v3 != permuted.ground_truth_v3:
        return False
    original_invariants = evaluate_invariants(
        incident,
        incident.model_view(),
        temporal_semantics_version=TEMPORAL_SEMANTICS_VERSION,
    )
    permuted_invariants = evaluate_invariants(
        permuted,
        permuted.model_view(),
        temporal_semantics_version=TEMPORAL_SEMANTICS_VERSION,
    )
    if [(item.name, item.preserved) for item in original_invariants] != [
        (item.name, item.preserved) for item in permuted_invariants
    ]:
        return False
    rubric = build_incident_003_v3_evidence_rubric(permuted)
    cited = tuple(
        evidence_id
        for binding in rubric.subject_bindings
        for evidence_id in binding.evidence_ids
    )
    score = score_evidence_support_v4(
        cited,
        permuted.model_view(),
        rubric,
        Incident003V3EvidenceSemanticEvaluator(TEMPORAL_SEMANTICS_VERSION),
    )
    target = str(permuted.metadata["target_operation_id"])
    twin = str(permuted.metadata["temporal_twin_operation_id"])
    return bool(
        score.evidence_supported
        and non_temporal_operation_projection(
            temporally_ablated_model_view(permuted), target
        )
        == non_temporal_operation_projection(
            temporally_ablated_model_view(permuted), twin
        )
    )


def _row_permutation_preserves_semantics(incident: IncidentV3) -> bool:
    data = deepcopy(incident.to_dict())
    structured = data["structured_evidence"]
    assert isinstance(structured, dict)
    for rows in structured.values():
        assert isinstance(rows, list)
        rows.reverse()
    permuted = IncidentV3.from_dict(data)
    invariants = evaluate_invariants(
        permuted,
        permuted.model_view(),
        temporal_semantics_version=TEMPORAL_SEMANTICS_VERSION,
    )
    rubric = build_incident_003_v3_evidence_rubric(permuted)
    cited = tuple(
        evidence_id
        for binding in rubric.subject_bindings
        for evidence_id in binding.evidence_ids
    )
    score = score_evidence_support_v4(
        cited,
        permuted.model_view(),
        rubric,
        Incident003V3EvidenceSemanticEvaluator(TEMPORAL_SEMANTICS_VERSION),
    )
    ablated = temporally_ablated_model_view(permuted)
    reversed_ablated = ModelView(
        troubleshooting_question=ablated.troubleshooting_question,
        structured_evidence={
            source: list(reversed(rows))
            for source, rows in ablated.structured_evidence.items()
        },
        log_evidence=tuple(reversed(ablated.log_evidence)),
    )
    role_ids = _role_ids(permuted)
    return bool(
        all(item.preserved for item in invariants)
        and score.evidence_supported
        and _canonical_operation_slice(
            reversed_ablated, role_ids["target"]
        )
        == _canonical_operation_slice(
            reversed_ablated, role_ids["temporal_twin"]
        )
    )


def _replace_ids(value: JSONValue, mapping: Mapping[str, str]) -> JSONValue:
    if isinstance(value, dict):
        return {key: _replace_ids(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_ids(item, mapping) for item in value]
    if isinstance(value, str):
        return _replace_string_ids(value, mapping)
    return value


def _replace_string_ids(value: str, mapping: Mapping[str, str]) -> str:
    return _ID_SUBSTITUTION_PATTERN.sub(
        lambda match: mapping.get(match.group(0), match.group(0)), value
    )


def _collect_marker_stats(
    counts: dict[str, Counter[str]],
    view: ModelView,
    role_ids: Mapping[str, str],
) -> None:
    by_role_slot: dict[str, dict[str, str]] = {role: {} for role in _ROLES}
    timestamp_fields = {
        "workflow_attempts": ("dispatched_at", "deadline_at"),
        "execution_observations": ("started_at", "completed_at"),
        "effect_records": ("created_at",),
        "compensation_records": ("started_at", "completed_at"),
        "dependency_health": ("observed_at",),
    }
    for source, fields in timestamp_fields.items():
        for row in view.structured_evidence[source]:
            role = _role_for_id(str(row["operation_id"]), role_ids)
            for field in fields:
                by_role_slot[role][f"{source}.{field}"] = str(row[field])
    for entry in view.log_evidence:
        role = _role_for_id(str(entry.attributes["operation_id"]), role_ids)
        slot = f"logs.{entry.attributes['event_kind']}.timestamp"
        by_role_slot[role][slot] = entry.timestamp
    for slot in sorted(by_role_slot["target"]):
        target = by_role_slot["target"][slot]
        twin = by_role_slot["temporal_twin"][slot]
        relation = "lt" if target < twin else "gt" if target > twin else "eq"
        counts[slot][relation] += 1


def _finalize_marker_stats(
    counts: dict[str, Counter[str]],
    position_report: dict[str, JSONValue],
    passed_count: int,
    sample_size: int,
) -> dict[str, JSONValue]:
    perfect = [
        f"marker_lexical_order.{slot}"
        for slot, counter in sorted(counts.items())
        if len(counter) == 1
    ]
    perfect.extend(position_report["ablated_log_perfect_separators"])  # type: ignore[arg-type]
    return {
        "marker_template": "TA1::<source>::<evidence_id>::<field>",
        "structure_role_neutral_count": passed_count,
        "pair_count": sample_size,
        "target_vs_twin_lexical_order_by_slot": {
            slot: _counter(counter) for slot, counter in sorted(counts.items())
        },
        "perfect_separators": perfect,
    }


def _marker_structure_is_role_neutral(view: ModelView) -> bool:
    marker = re.compile(
        r"^TA1::(?P<source>[a-z_]+)::(?P<evidence>EV-\d{8})::(?P<field>[a-z_]+)$"
    )
    for source, rows in view.structured_evidence.items():
        for row in rows:
            for field, value in row.items():
                if field not in {
                    "dispatched_at",
                    "deadline_at",
                    "started_at",
                    "completed_at",
                    "created_at",
                    "observed_at",
                }:
                    continue
                match = marker.fullmatch(str(value))
                if match is None or match.group("source") != source:
                    return False
                if match.group("evidence") != str(row["evidence_id"]):
                    return False
                if match.group("field") != field:
                    return False
    for entry in view.log_evidence:
        match = marker.fullmatch(entry.timestamp)
        if (
            match is None
            or match.group("source") != "logs"
            or match.group("evidence") != entry.evidence_id
            or match.group("field") != "timestamp"
        ):
            return False
    return True


def _role_for_id(value: str, role_ids: Mapping[str, str]) -> str:
    return next(role for role, operation_id in role_ids.items() if value == operation_id)


def _role_property_perfectly_separates(
    by_role: Mapping[str, Counter], sample_size: int
) -> bool:
    if set(by_role) != set(_ROLES):
        return False
    if any(sum(counter.values()) != sample_size for counter in by_role.values()):
        return False
    value_sets = [set(by_role[role]) for role in _ROLES]
    return all(
        left.isdisjoint(right)
        for index, left in enumerate(value_sets)
        for right in value_sets[index + 1 :]
    )


def _counter(value: Counter) -> dict[str, int]:
    return {str(key): count for key, count in sorted(value.items(), key=lambda x: str(x[0]))}


def _role_counters(value: object) -> dict[str, JSONValue]:
    assert isinstance(value, defaultdict)
    return {role: _counter(value[role]) for role in _ROLES}


def _role_position_summaries(value: object) -> dict[str, JSONValue]:
    assert isinstance(value, defaultdict)
    result: dict[str, JSONValue] = {}
    for role in _ROLES:
        positions = [
            int(position)
            for position, count in value[role].items()
            for _ in range(count)
        ]
        positions.sort()
        middle = len(positions) // 2
        median = (
            positions[middle]
            if len(positions) % 2
            else (positions[middle - 1] + positions[middle]) / 2
        )
        result[role] = {
            "mean": sum(positions) / len(positions),
            "median": median,
        }
    return result
