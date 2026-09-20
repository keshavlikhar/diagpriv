"""Versioned deterministic exposure vectors over raw/released ModelViews.

Oracle labels and sensitive literals are used only inside this local evaluator.
Neither is serialized into the report. No provider client is imported here.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
from itertools import combinations
import json
from pathlib import Path
from typing import Any, Iterable

from diagbench.audits.incident_003 import temporally_ablated_model_view
from diagbench.generators.incident_001 import generate_incident_001
from diagbench.generators.incident_002 import generate_incident_002
from diagbench.generators.incident_003_v3 import generate_incident_003_v3
from diagbench.relative_time import parse_relative_time
from diagbench.schema import Incident, ModelView, SensitiveField
from diagbench.temporal import parse_timestamp
from diagpriv.transformations import (
    format_preserving_incident,
    hmac_incident,
    redact_incident,
    relative_time_incident,
    tokenize_incident,
)
from diagpriv.transformations.provenance import transformation_configuration_for_condition

ANALYSIS_VERSION = "privacy-exposure-analysis-v1"
SOURCE_MAIN_COMMIT = "649707d163729e2db0550a6042029de3828ae711"
ARTIFACT_PATH = Path("docs/data/privacy_exposure_development_v1.json")
_PUBLIC_TEST_KEY_LABEL = b"diagpriv-public-privacy-exposure-v1-synthetic-test-key"
_PUBLIC_TEST_KEY = hashlib.sha256(_PUBLIC_TEST_KEY_LABEL).digest()
_MISSING = object()
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_SCALAR_CONDITIONS = (
    "raw", "redaction-v1", "hmac-v1", "tokenization-v1", "format-preserving-v1"
)
_TEMPORAL_CONDITIONS = ("raw", "relative-time-v1", "temporal-ablation-v1")
_SEEDS = {
    "incident_001_duplicate_payment": (1000, 1001, 1002, 1003, 1004),
    "incident_002_format_defect": (1000, 1001, 1003, 1004, 1005, 1017),
    "incident_003_temporal_compensation_v3": (1319, 1299, 1387, 1222),
}
_RATIO_KEYS = (
    "protected_literal_exposure", "protected_literal_not_visible",
    "direct_non_temporal_literal_exposure", "direct_non_temporal_literal_not_visible",
    "equal_pair_preservation", "unequal_pair_separation",
    "multiplicity_histogram_preservation",
    "cross_source_equal_pair_preservation", "cross_source_unequal_pair_separation",
    "format_shape_preservation", "record_count_preservation",
    "sensitive_field_presence_preservation", "distinct_entity_count_preservation",
    "absolute_timestamp_exposure", "temporal_pair_evaluability",
    "temporal_order_preservation", "temporal_interval_preservation",
    "secret_literal_exposure",
)


class SecretExposureError(ValueError):
    """A classified secret is visible; intentionally omit its value."""


@dataclass(frozen=True, slots=True)
class CountMetric:
    numerator: int
    denominator: int

    def to_dict(self) -> dict[str, int | float | str | None]:
        return {
            "numerator": self.numerator,
            "denominator": self.denominator,
            "fraction": self.numerator / self.denominator if self.denominator else None,
            "status": "measured" if self.denominator else "not_applicable",
        }


@dataclass(frozen=True, slots=True)
class _Occurrence:
    path: str
    source: str
    field: str
    classification: str
    raw: object
    released: object

    @property
    def group(self) -> tuple[str, str]:
        return (self.classification, self.field)


def _typed(value: object) -> tuple[str, str]:
    return (
        type(value).__name__,
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False),
    )


def _row_index(view: ModelView) -> dict[str, dict[str, dict[str, Any]]]:
    sources: dict[str, Iterable[dict[str, Any]]] = {
        **view.structured_evidence,
        "logs": tuple(item.to_dict() for item in view.log_evidence),
    }
    indexed: dict[str, dict[str, dict[str, Any]]] = {}
    for source, rows in sources.items():
        by_id: dict[str, dict[str, Any]] = {}
        for row in rows:
            evidence_id = row.get("evidence_id")
            if not isinstance(evidence_id, str) or evidence_id in by_id:
                raise ValueError("ModelView rows require unique visible evidence IDs")
            by_id[evidence_id] = row
        indexed[source] = by_id
    return indexed


def _field(row: dict[str, Any] | None, field: str) -> object:
    if row is None:
        return _MISSING
    if field in row:
        return row[field]
    attributes = row.get("attributes")
    if isinstance(attributes, dict) and field in attributes:
        return attributes[field]
    return _MISSING


def _occurrences(
    raw: ModelView, released: ModelView, annotations: tuple[SensitiveField, ...]
) -> list[_Occurrence]:
    raw_rows, released_rows = _row_index(raw), _row_index(released)
    found: list[_Occurrence] = []
    seen_paths: set[str] = set()
    for annotation in annotations:
        if annotation.path in seen_paths or annotation.path.count(".") != 1:
            raise ValueError("Sensitive annotations need unique source.field paths")
        seen_paths.add(annotation.path)
        source, field = annotation.path.split(".")
        if source not in raw_rows:
            raise ValueError("Sensitive annotation refers to an absent raw source")
        matches = 0
        for evidence_id, row in raw_rows[source].items():
            value = _field(row, field)
            if value is _MISSING:
                continue
            if isinstance(value, (dict, list)):
                raise ValueError("Exposure v1 requires annotated scalar values")
            matches += 1
            transformed = _field(released_rows.get(source, {}).get(evidence_id), field)
            found.append(_Occurrence(
                annotation.path, source, field, annotation.classification,
                value, transformed,
            ))
        if not matches:
            raise ValueError("Sensitive annotation has no raw visible occurrence")
    return found


def _walk_scalars(value: object) -> Iterable[object]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _walk_scalars(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _walk_scalars(child)
    else:
        yield value


def _visible_values(view: ModelView) -> tuple[set[tuple[str, str]], tuple[str, ...]]:
    values = tuple(_walk_scalars(view.to_dict()))
    return {_typed(value) for value in values}, tuple(
        value for value in values if isinstance(value, str)
    )


def _literal_visible(
    value: object, keys: set[tuple[str, str]], strings: tuple[str, ...]
) -> bool:
    if _typed(value) in keys:
        return True
    return isinstance(value, str) and len(value) >= 6 and any(
        value in visible for visible in strings
    )


def _secret_visible(
    value: object, keys: set[tuple[str, str]], strings: tuple[str, ...]
) -> bool:
    """Fail closed on verbatim string secrets; keep non-string matching typed."""
    if _typed(value) in keys:
        return True
    return isinstance(value, str) and any(value in visible for visible in strings)


def _shape(value: str) -> str:
    return "".join(
        "U" if ch.isupper() else "l" if ch.islower() else "D" if ch.isdigit()
        else ch for ch in value
    )


def _format_category(item: _Occurrence) -> str:
    if item.released is _MISSING or item.released is None:
        return "absent"
    if _typed(item.raw) == _typed(item.released):
        return "exact_literal"
    if not isinstance(item.released, str):
        return "other_changed"
    if item.released.startswith("[REDACTED:") and item.released.endswith("]"):
        return "redacted_placeholder"
    if _shape(str(item.raw)) == _shape(item.released):
        return "changed_same_shape"
    if item.released.startswith(("HMAC1_", "TOK_")):
        return "opaque_token"
    try:
        parse_relative_time(item.released)
    except ValueError:
        return "other_changed"
    return "relative_offset"


def _temporal_value(value: object) -> tuple[str, int] | None:
    if not isinstance(value, str):
        return None
    try:
        delta = parse_timestamp(value) - _EPOCH
    except ValueError:
        try:
            return ("relative", parse_relative_time(value) * 1000)
        except ValueError:
            return None
    micros = (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds
    return ("absolute", micros)


def _temporal_occurrences(raw: ModelView, released: ModelView) -> list[tuple[str, object]]:
    raw_rows, released_rows = _row_index(raw), _row_index(released)
    result: list[tuple[str, object]] = []
    for source, rows in raw_rows.items():
        for evidence_id, row in rows.items():
            peer = released_rows.get(source, {}).get(evidence_id)
            for field, value in row.items():
                if _temporal_value(value) is not None:
                    result.append((value, _field(peer, field)))
            attributes = row.get("attributes")
            if isinstance(attributes, dict):
                for field, value in attributes.items():
                    if _temporal_value(value) is not None:
                        result.append((value, _field(peer, field)))
    return result


def _pair_metrics(items: list[_Occurrence]) -> dict[str, CountMetric]:
    groups: dict[tuple[str, str], list[_Occurrence]] = defaultdict(list)
    for item in items:
        if item.raw is not None:
            groups[item.group].append(item)
    counts = {name: [0, 0] for name in (
        "equal_pair_preservation", "unequal_pair_separation",
        "cross_source_equal_pair_preservation", "cross_source_unequal_pair_separation",
    )}
    frequency = [0, 0]
    distinct = [0, 0]
    for group in groups.values():
        raw_counts = Counter(_typed(item.raw) for item in group)
        if len(raw_counts) >= 2:
            distinct[1] += 1
            released_distinct = {
                _typed(item.released) for item in group if item.released is not _MISSING
            }
            distinct[0] += len(released_distinct) == len(raw_counts)
            if max(raw_counts.values()) >= 2:
                frequency[1] += 1
                released_counts = Counter(
                    _typed(item.released) for item in group if item.released is not _MISSING
                )
                frequency[0] += (
                    len(released_counts) == len(raw_counts)
                    and sorted(released_counts.values()) == sorted(raw_counts.values())
                )
        for left, right in combinations(group, 2):
            same_raw = _typed(left.raw) == _typed(right.raw)
            same_released = (
                left.released is not _MISSING
                and right.released is not _MISSING
                and _typed(left.released) == _typed(right.released)
            )
            main = "equal_pair_preservation" if same_raw else "unequal_pair_separation"
            counts[main][1] += 1
            counts[main][0] += same_released if same_raw else not same_released
            if left.source != right.source:
                cross = (
                    "cross_source_equal_pair_preservation" if same_raw
                    else "cross_source_unequal_pair_separation"
                )
                counts[cross][1] += 1
                counts[cross][0] += same_released if same_raw else not same_released
    return {
        **{name: CountMetric(*value) for name, value in counts.items()},
        "multiplicity_histogram_preservation": CountMetric(*frequency),
        "distinct_entity_count_preservation": CountMetric(*distinct),
    }


def analyze_model_views(
    raw: ModelView, released: ModelView, annotations: tuple[SensitiveField, ...]
) -> dict[str, object]:
    """Measure a release; the returned vector contains no original values."""
    items = _occurrences(raw, released, annotations)
    keys, strings = _visible_values(released)
    metrics: dict[str, CountMetric] = {}
    literal = [item for item in items if item.raw is not None]
    non_temporal = [item for item in literal if item.classification != "operational_timestamp"]
    metrics["protected_literal_exposure"] = CountMetric(
        sum(_literal_visible(item.raw, keys, strings) for item in literal), len(literal)
    )
    metrics["direct_non_temporal_literal_exposure"] = CountMetric(
        sum(_literal_visible(item.raw, keys, strings) for item in non_temporal),
        len(non_temporal),
    )
    metrics["protected_literal_not_visible"] = CountMetric(
        len(literal) - metrics["protected_literal_exposure"].numerator, len(literal)
    )
    metrics["direct_non_temporal_literal_not_visible"] = CountMetric(
        len(non_temporal) - metrics["direct_non_temporal_literal_exposure"].numerator,
        len(non_temporal),
    )
    secret_paths = {
        annotation.path for annotation in annotations
        if annotation.classification == "secret" or annotation.policy == "never_release"
    }
    secrets = [item for item in literal if item.path in secret_paths]
    secret_count = sum(_secret_visible(item.raw, keys, strings) for item in secrets)
    if secret_count:
        raise SecretExposureError("A classified secret is visible in the released ModelView")
    metrics["secret_literal_exposure"] = CountMetric(0, len(secrets))
    metrics.update(_pair_metrics(items))

    strings_only = [item for item in items if isinstance(item.raw, str)]
    categories = Counter(_format_category(item) for item in strings_only)
    metrics["format_shape_preservation"] = CountMetric(
        categories["exact_literal"] + categories["changed_same_shape"],
        len(strings_only),
    )
    raw_rows, released_rows = _row_index(raw), _row_index(released)
    metrics["record_count_preservation"] = CountMetric(
        sum(len(rows) == len(released_rows.get(source, {}))
            for source, rows in raw_rows.items()),
        len(raw_rows),
    )
    metrics["sensitive_field_presence_preservation"] = CountMetric(
        sum(item.released is not _MISSING for item in items), len(items)
    )

    times = _temporal_occurrences(raw, released)
    metrics["absolute_timestamp_exposure"] = CountMetric(
        sum(_literal_visible(value, keys, strings) for value, _ in times), len(times)
    )
    temporal_counts = [0, 0, 0, 0]
    for (raw_left, out_left), (raw_right, out_right) in combinations(times, 2):
        left_raw = _temporal_value(raw_left)
        right_raw = _temporal_value(raw_right)
        assert left_raw is not None and right_raw is not None
        if left_raw[1] == right_raw[1]:
            continue
        temporal_counts[3] += 1
        left = _temporal_value(out_left)
        right = _temporal_value(out_right)
        if left is None or right is None or left[0] != right[0]:
            continue
        temporal_counts[0] += 1
        temporal_counts[1] += (left[1] < right[1]) == (left_raw[1] < right_raw[1])
        temporal_counts[2] += abs(left[1] - right[1]) == abs(left_raw[1] - right_raw[1])
    for name, numerator in zip((
        "temporal_pair_evaluability", "temporal_order_preservation",
        "temporal_interval_preservation",
    ), temporal_counts[:3], strict=True):
        metrics[name] = CountMetric(numerator, temporal_counts[3])

    by_class: dict[str, dict[str, object]] = {}
    for classification in sorted({item.classification for item in items}):
        subset = [item for item in items if item.classification == classification and item.raw is not None]
        by_class[classification] = {
            "literal_exposure": CountMetric(
                sum(_literal_visible(item.raw, keys, strings) for item in subset), len(subset)
            ).to_dict(),
            "format_shape_preservation": CountMetric(
                sum(_format_category(item) in {"exact_literal", "changed_same_shape"}
                    for item in subset if isinstance(item.raw, str)),
                sum(isinstance(item.raw, str) for item in subset),
            ).to_dict(),
        }
    return {
        "analysis_version": ANALYSIS_VERSION,
        "metrics": {key: metrics[key].to_dict() for key in _RATIO_KEYS},
        "format_categories": dict(sorted(categories.items())),
        "by_class": by_class,
        "protected_occurrences": len(items),
    }


def _released_view(incident: Incident, condition: str) -> ModelView:
    if condition == "raw":
        return incident.model_view()
    if condition == "redaction-v1":
        return redact_incident(incident)
    if condition == "hmac-v1":
        return hmac_incident(incident, key=_PUBLIC_TEST_KEY)
    if condition == "tokenization-v1":
        return tokenize_incident(incident)
    if condition == "format-preserving-v1":
        return format_preserving_incident(incident)
    if condition == "relative-time-v1":
        return relative_time_incident(incident)
    if condition == "temporal-ablation-v1":
        return temporally_ablated_model_view(incident)
    raise ValueError("Unsupported offline exposure condition")


def _case_record(incident: Incident, condition: str, seed: int, role: str | None) -> dict[str, object]:
    vector = analyze_model_views(
        incident.model_view(), _released_view(incident, condition), incident.sensitive_fields
    )
    return {
        "incident_family": incident.incident_id,
        "case_id": f"{seed}:{role}" if role else str(seed),
        "construction_seed": seed,
        "query_role": role,
        "condition": condition,
        "transformation_version": transformation_configuration_for_condition(condition)[
            "transformation_version"
        ],
        "benchmark_version": str(incident.metadata.get("benchmark_version", "not_declared")),
        "generator_version": str(incident.metadata.get("generator_version", "not_declared")),
        "incident_protocol_version": str(incident.metadata.get("protocol_version", "not_declared")),
        "exposure": vector,
    }


def _aggregate(records: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        if record["query_role"] in {None, "target"}:
            grouped[(str(record["incident_family"]), str(record["condition"]))].append(record)
    summary = []
    for (family, condition), cases in sorted(grouped.items()):
        measures: dict[str, dict[str, int | float | str | None]] = {}
        for key in _RATIO_KEYS:
            entries = [case["exposure"]["metrics"][key] for case in cases]  # type: ignore[index]
            measures[key] = CountMetric(
                sum(int(entry["numerator"]) for entry in entries),
                sum(int(entry["denominator"]) for entry in entries),
            ).to_dict()
        category_counts: Counter[str] = Counter()
        class_totals: dict[str, dict[str, dict[str, int | float | str | None]]] = {}
        for case in cases:
            category_counts.update(case["exposure"]["format_categories"])  # type: ignore[index]
            for classification, dimensions in case["exposure"]["by_class"].items():  # type: ignore[index]
                bucket = class_totals.setdefault(classification, {})
                for dimension, entry in dimensions.items():
                    current = bucket.get(dimension)
                    numerator = int(entry["numerator"]) + (
                        0 if current is None else int(current["numerator"])
                    )
                    denominator = int(entry["denominator"]) + (
                        0 if current is None else int(current["denominator"])
                    )
                    bucket[dimension] = CountMetric(numerator, denominator).to_dict()
        summary.append({
            "incident_family": family,
            "condition": condition,
            "construction_count": len(cases),
            "metrics": measures,
            "format_categories": dict(sorted(category_counts.items())),
            "by_class": {
                key: class_totals[key] for key in sorted(class_totals)
            },
        })
    return summary


def _compact_case(record: dict[str, object]) -> dict[str, object]:
    """Keep reproducible per-case numerators/denominators without repetition."""
    exposure = record["exposure"]
    compact = {key: value for key, value in record.items() if key != "exposure"}
    compact["exposure"] = {
        "metric_counts": {
            key: [value["numerator"], value["denominator"]]
            for key, value in exposure["metrics"].items()  # type: ignore[index]
        },
        "format_categories": exposure["format_categories"],  # type: ignore[index]
        "class_metric_counts": {
            classification: {
                key: [value["numerator"], value["denominator"]]
                for key, value in dimensions.items()
            }
            for classification, dimensions in exposure["by_class"].items()  # type: ignore[index]
        },
    }
    return compact


def build_development_report() -> dict[str, object]:
    """Regenerate only preselected development cases; no provider or secrets."""
    records: list[dict[str, object]] = []
    for seed in _SEEDS["incident_001_duplicate_payment"]:
        incident = generate_incident_001(seed)
        records.extend(_case_record(incident, condition, seed, None) for condition in _SCALAR_CONDITIONS)
    for seed in _SEEDS["incident_002_format_defect"]:
        incident = generate_incident_002(seed)
        records.extend(_case_record(incident, condition, seed, None) for condition in _SCALAR_CONDITIONS)
    role_parity = True
    for seed in _SEEDS["incident_003_temporal_compensation_v3"]:
        paired: dict[str, dict[str, dict[str, object]]] = {}
        for role in ("target", "temporal_twin"):
            incident = generate_incident_003_v3(seed, role)
            paired[role] = {}
            for condition in _TEMPORAL_CONDITIONS:
                record = _case_record(incident, condition, seed, role)
                records.append(record)
                paired[role][condition] = record
        for condition in _TEMPORAL_CONDITIONS:
            role_parity &= (
                paired["target"][condition]["exposure"]
                == paired["temporal_twin"][condition]["exposure"]
            )
    return {
        "analysis_version": ANALYSIS_VERSION,
        "measurement_surface": "complete_model_visible_modelview",
        "development_only": True,
        "baseline_main_commit": SOURCE_MAIN_COMMIT,
        "synthetic_hmac_key_protocol": "public-test-only-sha256-derived-v1",
        "aggregation_rule": "micro-sum counts over constructions; Incident 003 target only after role parity",
        "case_metric_encoding": "[numerator, denominator]; null fraction when denominator is zero",
        "incident_003_role_vectors_equal": role_parity,
        "cases": [_compact_case(record) for record in records],
        "summary": _aggregate(records),
    }


def render_development_report() -> bytes:
    return (json.dumps(build_development_report(), indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline development ModelView exposure analysis")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path, help="Write deterministic development JSON")
    group.add_argument("--check", type=Path, help="Fail unless tracked JSON matches regeneration")
    args = parser.parse_args()
    payload = render_development_report()
    if args.check:
        if args.check.read_bytes() != payload:
            raise SystemExit("Exposure artifact differs from deterministic regeneration")
        print("Exposure artifact matches deterministic regeneration")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
        print(f"Wrote {args.output} ({len(payload)} bytes)")


if __name__ == "__main__":
    main()
