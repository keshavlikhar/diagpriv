"""Provider-free archive verification using synthetic bytes only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from diagpriv.artifacts.__main__ import main
from diagpriv.artifacts.verification import (
    DEFAULT_MANIFEST,
    DEFAULT_ROOT,
    ManifestError,
    load_manifest,
    verify_artifact,
)


SYNTHETIC_BYTES = b'{"synthetic":"not a provider observation"}\n'


def _row() -> dict[str, object]:
    return {
        "artifact_id": "synthetic-test-artifact",
        "scientific_role": "synthetic verification fixture",
        "local_path": "results/synthetic.jsonl",
        "sha256": hashlib.sha256(SYNTHETIC_BYTES).hexdigest(),
        "byte_size": len(SYNTHETIC_BYTES),
        "size_status": "verified_local",
        "media_type": "application/x-ndjson",
        "incident_family": "synthetic-test-family",
        "condition": "raw",
        "split": "development",
        "requested_model": "synthetic-model",
        "reasoning_effort": "none",
        "prompt_version": "synthetic-prompt-v1",
        "prompt_sha256": "a" * 64,
        "manifest_schema_version": "synthetic-manifest-v1",
        "scorer_version": "synthetic-scorer-v1",
        "evidence_protocol_version": None,
        "transformation_version": "raw",
        "source_config": "experiments/synthetic.toml",
        "publication_status": "private",
        "archive_locator": None,
    }


def _manifest(tmp_path: Path, rows: list[dict[str, object]] | None = None) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"schema_version": "frozen-artifact-manifest-v1",
                                "artifacts": rows or [_row()]}), encoding="utf-8")
    return path


def test_known_good_digest_and_size_do_not_mutate_artifact(tmp_path: Path) -> None:
    path = tmp_path / "results" / "synthetic.jsonl"
    path.parent.mkdir()
    path.write_bytes(SYNTHETIC_BYTES)
    before = path.read_bytes()
    result = verify_artifact(load_manifest(_manifest(tmp_path))[0], tmp_path)
    assert result.status == "VERIFIED"
    assert result.exit_code == 0
    assert path.read_bytes() == before


def test_missing_artifact_is_distinct_from_corruption(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest = _manifest(tmp_path)
    result = verify_artifact(load_manifest(manifest)[0], tmp_path)
    assert result.status == "MISSING"
    assert main(["verify", "--all", "--root", str(tmp_path), "--manifest", str(manifest)]) == 2
    assert "MISSING" in capsys.readouterr().out
    assert not (tmp_path / "results" / "synthetic.jsonl").exists()


def test_wrong_size_and_wrong_digest_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "results" / "synthetic.jsonl"
    path.parent.mkdir()
    path.write_bytes(SYNTHETIC_BYTES + b"x")
    assert verify_artifact(load_manifest(_manifest(tmp_path))[0], tmp_path).status == "SIZE_MISMATCH"
    altered = _row()
    altered["sha256"] = "b" * 64
    altered["byte_size"] = len(SYNTHETIC_BYTES) + 1
    assert verify_artifact(load_manifest(_manifest(tmp_path, [altered]))[0], tmp_path).status == "DIGEST_MISMATCH"


def test_duplicate_ids_and_paths_are_rejected(tmp_path: Path) -> None:
    duplicate = _row()
    with pytest.raises(ManifestError, match="Duplicate"):
        load_manifest(_manifest(tmp_path, [_row(), duplicate]))
    duplicate["artifact_id"] = "different-id"
    with pytest.raises(ManifestError, match="Duplicate"):
        load_manifest(_manifest(tmp_path, [_row(), duplicate]))


@pytest.mark.parametrize("bad", ["{", "[]", '{"schema_version":"wrong","artifacts":[]}'])
def test_malformed_manifest_fails(tmp_path: Path, bad: str) -> None:
    path = tmp_path / "bad.json"
    path.write_text(bad, encoding="utf-8")
    with pytest.raises(ManifestError):
        load_manifest(path)


@pytest.mark.parametrize("locator", [
    "https://example.org/file?token=synthetic",
    "github-release://user:synthetic@owner/repo/tag/asset",
    "github-release://owner/repo/tag/asset?signature=synthetic",
    "github-release://owner/repo/../asset",
])
def test_secret_bearing_or_unsafe_locator_is_rejected(tmp_path: Path, locator: str) -> None:
    row = _row()
    row["archive_locator"] = locator
    with pytest.raises(ManifestError):
        load_manifest(_manifest(tmp_path, [row]))


def test_credential_free_locator_is_only_metadata(tmp_path: Path) -> None:
    row = _row()
    row["archive_locator"] = "github-release://owner/private-repo/frozen-v1/synthetic.jsonl"
    assert load_manifest(_manifest(tmp_path, [row]))[0].artifact_id == row["artifact_id"]
    assert not (tmp_path / "results").exists()


def test_unknown_byte_size_is_explicit_and_not_fully_verified(tmp_path: Path) -> None:
    row = _row()
    row["split"] = "validation"
    row["byte_size"] = None
    row["size_status"] = "not_inspected_validation"
    path = tmp_path / "results" / "synthetic.jsonl"
    path.parent.mkdir()
    path.write_bytes(SYNTHETIC_BYTES)
    result = verify_artifact(load_manifest(_manifest(tmp_path, [row]))[0], tmp_path)
    assert result.status == "SIZE_UNKNOWN"
    assert result.exit_code == 4


def test_path_traversal_and_symlink_escape_are_rejected(tmp_path: Path) -> None:
    row = _row()
    row["local_path"] = "results/../outside.jsonl"
    with pytest.raises(ManifestError, match="Unsafe"):
        load_manifest(_manifest(tmp_path, [row]))
    outside = tmp_path.parent / f"{tmp_path.name}-outside.jsonl"
    outside.write_bytes(SYNTHETIC_BYTES)
    results = tmp_path / "results"
    results.mkdir()
    (results / "synthetic.jsonl").symlink_to(outside)
    assert verify_artifact(load_manifest(_manifest(tmp_path))[0], tmp_path).status == "UNSAFE_PATH"


def test_provider_credentials_not_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DIAGPRIV_HMAC_KEY_HEX", raising=False)
    path = tmp_path / "results" / "synthetic.jsonl"
    path.parent.mkdir()
    path.write_bytes(SYNTHETIC_BYTES)
    assert main(["verify", "--artifact", "synthetic-test-artifact", "--root", str(tmp_path),
                 "--manifest", str(_manifest(tmp_path))]) == 0


def test_tracked_paper_inventory_is_development_metadata_only() -> None:
    manifest = DEFAULT_ROOT / DEFAULT_MANIFEST
    rows = load_manifest(manifest)
    assert len(rows) == 20
    assert len({a.artifact_id for a in rows}) == 20
    assert sum(a.byte_size is None for a in rows) == 1
    assert all(a.local_path.parts[0] == "results" for a in rows)
    ledger = (DEFAULT_ROOT / "paper/data/frozen_development_results_v1.json").read_text()
    metadata = json.loads(manifest.read_text())
    assert all(row["sha256"] in ledger for row in metadata["artifacts"])
    assert all((DEFAULT_ROOT / row["source_config"]).is_file() for row in metadata["artifacts"])
    assert all(row["archive_locator"] is None for row in metadata["artifacts"])
