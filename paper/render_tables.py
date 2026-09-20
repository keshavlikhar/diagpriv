"""Render development-only LaTeX tables from frozen results and exposure data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "paper/data/frozen_development_results_v1.json"
OUTPUT = ROOT / "paper/generated"

CONDITIONS = (
    "raw", "redaction-v1", "hmac-v1", "tokenization-v1", "format-preserving-v1"
)
LABELS = {
    "raw": "Raw",
    "redaction-v1": "Redaction",
    "hmac-v1": "HMAC",
    "tokenization-v1": "Tokenization",
    "format-preserving-v1": "Format-preserving",
    "relative-time-v1": "Relative-time",
    "temporal-ablation-v1": "Temporal ablation",
}
FIGURE_LABELS = {
    "raw": "Raw",
    "relative-time-v1": "Relative",
    "temporal-ablation-v1": "Ablation",
}


def _count(metric: dict[str, object]) -> str:
    numerator, denominator = metric["numerator"], metric["denominator"]
    return f"{numerator}/{denominator}" if denominator else "n/a"


def _row(*cells: str) -> str:
    return " & ".join(cells) + r" \\"


def _table(
    *, label: str, caption: str, columns: str, header: tuple[str, ...],
    rows: list[tuple[str, ...]], note: str = "", wide: bool = False,
    numbered: bool = True,
) -> str:
    body = "\n".join(_row(*entry) for entry in rows)
    tabular = (
        f"\\begin{{tabular}}{{{columns}}}\n\\toprule\n"
        f"{_row(*header)}\n\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}"
    )
    if wide:
        tabular = f"\\resizebox{{\\textwidth}}{{!}}{{%\n{tabular}%\n}}"
    if not numbered:
        return (
            "\\begin{center}\n\\small\n"
            f"\\textbf{{{caption}}}\\par\\medskip\n{tabular}\n"
            "\\end{center}\n"
        )
    return (
        "\\begin{table}[H]\n\\centering\n\\small\n"
        f"{tabular}\n\\caption{{{caption}}}\n\\label{{{label}}}\n"
        f"{'\\footnotesize ' + note + chr(10) if note else ''}"
        "\\end{table}\n"
    )


def generated_outputs() -> dict[str, bytes]:
    data = json.loads(DATA_PATH.read_text())
    if data["data_version"] != "paper-frozen-development-results-v1":
        raise ValueError("Unexpected paper data version")
    exposure_path = ROOT / data["privacy_exposure"]["path"]
    exposure_bytes = exposure_path.read_bytes()
    if hashlib.sha256(exposure_bytes).hexdigest() != data["privacy_exposure"]["sha256"]:
        raise ValueError("Frozen privacy-exposure artifact hash mismatch")
    exposure = json.loads(exposure_bytes)
    if exposure["analysis_version"] != data["privacy_exposure"]["analysis_version"]:
        raise ValueError("Privacy-exposure analysis version mismatch")
    summary = {
        (entry["incident_family"], entry["condition"]): entry["metrics"]
        for entry in exposure["summary"]
    }

    family_rows = [
        ("001", "Duplicate payment effect", "Identifier equality and cross-source linkage",
         "Timeout, re-arrival, missing idempotency"),
        ("002", "Missing provisioning effect", "External-reference format and shape",
         "Malformed reference, exact lookup miss"),
        ("003 v3", "Premature compensation / twin", "Deadline order and interval overlap",
         "Overlapping execution versus serialized invalid transition"),
    ]
    files: dict[str, str] = {}
    files["table1_families.tex"] = _table(
        label="tab:families",
        caption="Three synthetic incident families and their intended diagnostic dependencies.",
        columns="llll", header=("Family", "Observed problem", "Key invariant", "Mechanism contrast"),
        rows=family_rows, wide=True,
    )

    scalar_rows = []
    for family_id, family_label in (
        ("incident_001_duplicate_payment", "001"),
        ("incident_002_format_defect", "002"),
    ):
        for condition in CONDITIONS:
            metrics = summary[(family_id, condition)]
            scalar_rows.append((
                family_label, LABELS[condition],
                _count(metrics["direct_non_temporal_literal_exposure"]),
                _count(metrics["equal_pair_preservation"]),
                _count(metrics["unequal_pair_separation"]),
                _count(metrics["multiplicity_histogram_preservation"]),
                _count(metrics["cross_source_equal_pair_preservation"]),
                _count(metrics["format_shape_preservation"]),
            ))
    files["table2a_scalar_exposure.tex"] = _table(
        label="tab:scalar-exposure",
        caption="Development representation exposure for annotated identifiers. Counts are retained relationships or shapes over eligible denominators, not a privacy score.",
        columns="llrrrrrr",
        header=("Family", "Condition", "Literal", "Equal", "Unequal", "Frequency", "Cross-source", "Shape"),
        rows=scalar_rows, wide=True,
    )

    temporal_rows = []
    temporal_family = "incident_003_temporal_compensation_v3"
    for condition in ("raw", "relative-time-v1", "temporal-ablation-v1"):
        metrics = summary[(temporal_family, condition)]
        temporal_rows.append((
            LABELS[condition],
            _count(metrics["direct_non_temporal_literal_exposure"]),
            _count(metrics["absolute_timestamp_exposure"]),
            _count(metrics["temporal_pair_evaluability"]),
            _count(metrics["temporal_order_preservation"]),
            _count(metrics["temporal_interval_preservation"]),
            _count(metrics["record_count_preservation"]),
        ))
    files["table2b_temporal_exposure.tex"] = _table(
        label="tab:temporal-exposure",
        caption="Incident 003 v3 development exposure, counting each construction once across two query roles. Ablation's temporal zeros mean unavailable parseable relations, not reversed time.",
        columns="lrrrrrr",
        header=("Condition", "ID literal", "Absolute", "Evaluable", "Order", "Exact gap", "Records"),
        rows=temporal_rows, wide=True, numbered=False,
    )

    i001 = data["incident_001"]
    i002 = data["incident_002"]
    utility_rows = [
        ("001", LABELS[row["condition"]], f'{row["exact"]}/{row["valid"]}', "--", "--", "--")
        for row in i001["development"]
    ]
    utility_rows.extend((
        "002", LABELS[row["condition"]], f'{row["exact"]}/{row["valid"]}',
        f'{row["trigger"]}/{row["valid"]}',
        f'{row["mechanism"]}/{row["valid"]}',
        f'{row["component"]}/{row["valid"]}',
    ) for row in i002["recovered_sensitivity"])
    files["table3_utility.tex"] = _table(
        label="tab:utility",
        caption="Frozen development RCA: Incident 001 uses five Luna calls per condition; Incident 002 reports the 18-slot Sol transport-recovered sensitivity view, not the primary as-executed view.",
        columns="llrrrr",
        header=("Family", "Condition", "Exact RCA", "Trigger", "Mechanism", "Component"),
        rows=utility_rows, wide=True,
    )

    stages = data["incident_003_v3"]["stages"]
    stage_rows = [
        (
            LABELS[row["condition"]], f'{row["valid"]}/8', f'{row["exact"]}/8',
            f'{row["target_mechanism"]}/4', f'{row["twin_mechanism"]}/4',
            f'{row["paired_mechanism"]}/4', f'{row["paired_exact"]}/4',
        )
        for row in stages
    ]
    files["table4_temporal_utility.tex"] = _table(
        label="tab:temporal-utility",
        caption="Incident 003 v3 frozen paired development observations. All three stages used four constructions with target and temporal-twin queries.",
        columns="lrrrrrr",
        header=("Condition", "Valid", "Exact RCA", "Target mech.", "Twin mech.", "Paired mech.", "Paired exact"),
        rows=stage_rows, wide=True,
    )

    evidence_rows = [
        ("Raw Stage 1", "v4 primary", f'{stages[0]["evidence_supported"]}/8', "Pre-refinement"),
        ("Raw Stage 1", "v5 post-hoc", f'{stages[0]["secondary_evidence_supported"]}/8', "Secondary only"),
        ("Relative-time Stage 2", "v5 prospective", f'{stages[1]["evidence_supported"]}/8', "Frozen before calls"),
        ("Temporal ablation Stage 3", "v5 prospective", f'{stages[2]["evidence_supported"]}/8', "Frozen before calls"),
    ]
    files["table5_evidence.tex"] = _table(
        label="tab:evidence",
        caption="Incident 003 evidence support. Stage-1 v5 is a post-hoc rescore; only Stages 2 and 3 are directly comparable under prospective v5.",
        columns="llrl", header=("Observation", "Protocol", "Supported", "Status"),
        rows=evidence_rows, wide=True,
    )

    bars = []
    for index, row in enumerate(stages):
        height = row["paired_mechanism"]
        left = 1.25 * index
        right = left + 0.72
        center = left + 0.36
        bars.append(
            f"\\fill[diagblue!{85 - 18 * index}] ({left:.2f},0) "
            f"rectangle ({right:.2f},{height});\n"
            f"\\node[above] at ({center:.2f},{height}) {{{height}/4}};\n"
            f"\\node[below,align=center,font=\\scriptsize] at "
            f"({center:.2f},-0.08) {{{FIGURE_LABELS[row['condition']]}}};"
        )
    files["figure3_paired.tex"] = (
        "\\begin{figure}[H]\n\\centering\n"
        "\\begin{tikzpicture}[x=1.2cm,y=0.56cm]\n"
        "\\definecolor{diagblue}{RGB}{43,91,139}\n"
        "\\draw[->] (0,0) -- (4.1,0);\n"
        "\\draw[->] (0,0) -- (0,4.3) node[above,font=\\scriptsize] {pairs};\n"
        "\\foreach \\y in {1,2,3,4} {\\draw (-0.05,\\y) -- (0.05,\\y) "
        "node[left,xshift=-4pt,font=\\scriptsize] {\\y};}\n"
        + "\n".join(bars) + "\n"
        "\\end{tikzpicture}\n"
        "\\caption{Paired mechanism discrimination in four frozen Incident 003 v3 "
        "development constructions. Raw counts only; no uncertainty bars or "
        "equivalence claim.}\n\\label{fig:paired}\n\\end{figure}\n"
    )
    return {name: content.encode("utf-8") for name, content in files.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="Regenerate checked-in LaTeX")
    group.add_argument("--check", action="store_true", help="Verify byte-identical LaTeX")
    args = parser.parse_args()
    outputs = generated_outputs()
    for name, expected in sorted(outputs.items()):
        destination = OUTPUT / name
        if args.check:
            if not destination.exists() or destination.read_bytes() != expected:
                raise SystemExit(f"Generated paper asset differs: {destination}")
        else:
            destination.write_bytes(expected)
    print(f"{'Verified' if args.check else 'Generated'} {len(outputs)} paper assets")


if __name__ == "__main__":
    main()
