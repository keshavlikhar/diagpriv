"""Check that the manuscript's checked-in numbers derive from frozen sources."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).parents[1]
_renderer = runpy.run_path(str(ROOT / "paper/render_tables.py"))
DATA_PATH = _renderer["DATA_PATH"]
OUTPUT = _renderer["OUTPUT"]
generated_outputs = _renderer["generated_outputs"]


def test_generated_paper_assets_match_checked_in_bytes() -> None:
    outputs = generated_outputs()
    assert len(outputs) == 7
    for name, expected in outputs.items():
        assert (OUTPUT / name).read_bytes() == expected


def test_paper_exposure_source_is_the_frozen_development_artifact() -> None:
    data = json.loads(DATA_PATH.read_text())
    source = ROOT / data["privacy_exposure"]["path"]
    assert data["development_only"] is True
    assert data["source_main_sha"] == "0339ded4266370f260b83c35292d24aff7ab88cd"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == (
        "beffb1fe1d53250670921ef2817c5a111bf2bf41e3bff7ba474940cd58d0ebc2"
    )
    exposure = json.loads(source.read_text())
    assert exposure["analysis_version"] == "privacy-exposure-analysis-v1"
    assert len(exposure["cases"]) == 79
    assert len(exposure["summary"]) == 13


def test_frozen_utility_counts_and_hashes_are_explicitly_versioned() -> None:
    data = json.loads(DATA_PATH.read_text())
    i001 = data["incident_001"]
    assert [(row["condition"], row["exact"]) for row in i001["development"]] == [
        ("raw", 5), ("redaction-v1", 4), ("hmac-v1", 5),
        ("tokenization-v1", 5), ("format-preserving-v1", 4),
    ]
    assert i001["validation_raw"]["exact"] == 10
    assert i001["validation_raw"]["overall"] == 9
    i002 = data["incident_002"]
    assert [row["valid"] for row in i002["primary"]] == [18, 9, 18, 17, 18]
    assert [row["exact"] for row in i002["recovered_sensitivity"]] == [9, 0, 1, 0, 4]
    assert [row["trigger"] for row in i002["recovered_sensitivity"]] == [15, 2, 1, 2, 10]
    stages = data["incident_003_v3"]["stages"]
    assert [row["exact"] for row in stages] == [7, 6, 4]
    assert [row["paired_mechanism"] for row in stages] == [3, 2, 0]
    assert [row["evidence_supported"] for row in stages] == [0, 4, 0]
    assert stages[0]["secondary_evidence_supported"] == 3
    for digest in (
        [row["artifact_sha256"] for row in i001["development"]]
        + [i001["validation_raw"]["artifact_sha256"]]
        + list(i002["artifact_sha256"].values())
        + [row["artifact_sha256"] for row in stages]
    ):
        assert len(digest) == 64
        assert all(character in "0123456789abcdef" for character in digest)


def test_paper_source_documents_exist() -> None:
    data = json.loads(DATA_PATH.read_text())
    sources = [data["incident_001"]["source_document"], data["incident_002"]["source_document"]]
    sources.extend(data["incident_003_v3"]["source_documents"])
    assert all((ROOT / path).is_file() for path in sources)
    i001_doc = (ROOT / data["incident_001"]["source_document"]).read_text()
    for item in data["incident_001"]["development"]:
        assert item["artifact_sha256"] in i001_doc
    assert data["incident_001"]["validation_raw"]["artifact_sha256"] in i001_doc
    i002_doc = (ROOT / data["incident_002"]["source_document"]).read_text()
    for digest in data["incident_002"]["artifact_sha256"].values():
        assert digest in i002_doc
    for stage, source in zip(
        data["incident_003_v3"]["stages"],
        data["incident_003_v3"]["source_documents"],
        strict=True,
    ):
        assert stage["artifact_sha256"] in (ROOT / source).read_text()
