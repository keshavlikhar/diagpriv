"""Command-line entry point for provider-free artifact verification."""

from __future__ import annotations

import argparse
from pathlib import Path

from .verification import DEFAULT_MANIFEST, DEFAULT_ROOT, ManifestError, load_manifest, verify_artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m diagpriv.artifacts")
    subcommands = parser.add_subparsers(dest="command", required=True)
    verify = subcommands.add_parser("verify", help="verify local bytes; never download or rerun")
    selection = verify.add_mutually_exclusive_group(required=True)
    selection.add_argument("--all", action="store_true")
    selection.add_argument("--artifact", metavar="ID")
    verify.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    verify.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest_path = args.manifest or root / DEFAULT_MANIFEST
    try:
        artifacts = load_manifest(manifest_path)
    except ManifestError as exc:
        print(f"INVALID_MANIFEST: {exc}")
        return 4
    selected = artifacts if args.all else tuple(a for a in artifacts if a.artifact_id == args.artifact)
    if not selected:
        print("UNKNOWN_ARTIFACT: ID not present in manifest")
        return 4
    exit_code = 0
    for artifact in selected:
        result = verify_artifact(artifact, root)
        print(f"{result.artifact_id}: {result.status} — {result.detail}")
        exit_code = max(exit_code, result.exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
