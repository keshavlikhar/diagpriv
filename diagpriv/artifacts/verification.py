"""Provider-free exact-byte verification against the tracked artifact ledger."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit


SCHEMA_VERSION = "frozen-artifact-manifest-v1"
DEFAULT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path("artifacts/frozen_artifacts_v1.json")
_ID = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_LOCATOR_PART = re.compile(r"[A-Za-z0-9_.-]+\Z")
_SECRET_PATTERN = re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|sk-(?:proj|svcacct)-[A-Za-z0-9_-]{20,})")
_REQUIRED = {
    "artifact_id", "scientific_role", "local_path", "sha256", "byte_size",
    "size_status", "media_type", "incident_family", "condition", "split",
    "requested_model", "reasoning_effort", "prompt_version", "prompt_sha256",
    "manifest_schema_version", "scorer_version", "evidence_protocol_version",
    "transformation_version", "source_config", "publication_status",
    "archive_locator",
}


class ManifestError(ValueError):
    """The tracked ledger cannot safely be interpreted."""


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    local_path: PurePosixPath
    sha256: str
    byte_size: int | None


@dataclass(frozen=True)
class Verification:
    artifact_id: str
    status: str
    detail: str

    @property
    def exit_code(self) -> int:
        if self.status == "VERIFIED":
            return 0
        if self.status == "MISSING":
            return 2
        if self.status in {"SIZE_MISMATCH", "DIGEST_MISMATCH"}:
            return 3
        return 4


def _safe_relative_path(value: object, prefix: str, suffix: str) -> PurePosixPath:
    if not isinstance(value, str) or "\\" in value or value.startswith("/"):
        raise ManifestError(f"Invalid {prefix} path")
    path = PurePosixPath(value)
    if len(path.parts) < 2 or path.parts[0] != prefix or path.suffix != suffix:
        raise ManifestError(f"Invalid {prefix} path")
    if any(part in {".", "..", ""} for part in value.split("/")):
        raise ManifestError(f"Unsafe {prefix} path")
    return path


def _validate_locator(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, str) or _SECRET_PATTERN.search(value):
        raise ManifestError("Archive locator contains a secret-like value")
    try:
        parsed = urlsplit(value)
    except ValueError as exc:
        raise ManifestError("Malformed archive locator") from exc
    if parsed.scheme != "github-release" or parsed.query or parsed.fragment:
        raise ManifestError("Archive locator must be a credential-free github-release URI")
    if parsed.username or parsed.password or not parsed.netloc:
        raise ManifestError("Archive locator must not contain credentials")
    parts = (parsed.netloc, *parsed.path.strip("/").split("/"))
    if len(parts) != 4 or not all(_LOCATOR_PART.fullmatch(part) for part in parts):
        raise ManifestError("Malformed archive locator")
    if any(part in {".", ".."} for part in parts):
        raise ManifestError("Unsafe archive locator")


def load_manifest(path: Path) -> tuple[Artifact, ...]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManifestError("Cannot read a valid JSON manifest") from exc
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError("Unsupported manifest schema")
    rows = data.get("artifacts")
    if not isinstance(rows, list) or not rows:
        raise ManifestError("Manifest must contain artifacts")
    artifacts: list[Artifact] = []
    seen_ids: set[str] = set()
    seen_paths: set[PurePosixPath] = set()
    for row in rows:
        if not isinstance(row, dict) or not _REQUIRED.issubset(row):
            raise ManifestError("Artifact metadata is incomplete")
        artifact_id = row["artifact_id"]
        if not isinstance(artifact_id, str) or not _ID.fullmatch(artifact_id):
            raise ManifestError("Invalid artifact ID")
        local_path = _safe_relative_path(row["local_path"], "results", ".jsonl")
        if artifact_id in seen_ids or local_path in seen_paths:
            raise ManifestError("Duplicate artifact ID or local path")
        seen_ids.add(artifact_id)
        seen_paths.add(local_path)
        digest = row["sha256"]
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise ManifestError("Invalid SHA-256")
        size = row["byte_size"]
        if size is not None and (type(size) is not int or size < 0):
            raise ManifestError("Invalid byte size")
        if row["size_status"] not in {"verified_local", "not_inspected_validation"}:
            raise ManifestError("Invalid byte-size status")
        if (size is None) != (row["size_status"] == "not_inspected_validation"):
            raise ManifestError("Unknown size must be explicitly marked as uninspected validation")
        if row["split"] not in {"development", "validation"}:
            raise ManifestError("Invalid split")
        if size is None and row["split"] != "validation":
            raise ManifestError("Missing development artifact size")
        if row["publication_status"] not in {"private", "candidate_public", "aggregate_only"}:
            raise ManifestError("Invalid publication status")
        if row["media_type"] != "application/x-ndjson":
            raise ManifestError("Unexpected media type")
        for name in ("scientific_role", "incident_family", "condition", "requested_model",
                     "reasoning_effort", "prompt_version", "manifest_schema_version",
                     "scorer_version"):
            if not isinstance(row[name], str) or not row[name]:
                raise ManifestError(f"Invalid {name}")
        if not isinstance(row["prompt_sha256"], str) or not _SHA256.fullmatch(row["prompt_sha256"]):
            raise ManifestError("Invalid prompt-template SHA-256")
        for name in ("evidence_protocol_version", "transformation_version"):
            if row[name] is not None and (not isinstance(row[name], str) or not row[name]):
                raise ManifestError(f"Invalid {name}")
        _safe_relative_path(row["source_config"], "experiments", ".toml")
        _validate_locator(row["archive_locator"])
        artifacts.append(Artifact(artifact_id, local_path, digest, size))
    return tuple(artifacts)


def verify_artifact(artifact: Artifact, root: Path) -> Verification:
    root = root.resolve()
    path = root.joinpath(*artifact.local_path.parts)
    if path.is_symlink() or not path.resolve(strict=False).is_relative_to(root):
        return Verification(artifact.artifact_id, "UNSAFE_PATH", "artifact path escapes the repository")
    if not path.exists():
        return Verification(artifact.artifact_id, "MISSING", "artifact is absent; no provider rerun attempted")
    if not path.is_file():
        return Verification(artifact.artifact_id, "UNSAFE_PATH", "artifact is not a regular file")
    try:
        actual_size = path.stat().st_size
        if artifact.byte_size is not None and actual_size != artifact.byte_size:
            return Verification(artifact.artifact_id, "SIZE_MISMATCH", "exact byte size differs")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError:
        return Verification(artifact.artifact_id, "UNREADABLE", "artifact cannot be read")
    if digest != artifact.sha256:
        return Verification(artifact.artifact_id, "DIGEST_MISMATCH", "SHA-256 differs")
    if artifact.byte_size is None:
        return Verification(artifact.artifact_id, "SIZE_UNKNOWN", "digest matches; byte size is not frozen")
    return Verification(artifact.artifact_id, "VERIFIED", "SHA-256 and exact byte size match")
