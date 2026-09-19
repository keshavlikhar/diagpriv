"""Fail when tracked text files contain high-confidence secret patterns.

Only file paths and rule names are reported. Matching content is never printed.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import stat
import subprocess


RULES = {
    "private key": re.compile(r"-{5}BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-{5}"),
    "GitHub token": re.compile(r"g[h][pousr]_[A-Za-z0-9]{20,}"),
    "OpenAI project or service token": re.compile(
        r"s[k]-(?:proj|svcacct)-[A-Za-z0-9_-]{20,}"
    ),
    "AWS access key": re.compile(r"A[K]IA[0-9A-Z]{16}"),
    "Google API key": re.compile(r"A[I]za[0-9A-Za-z_-]{30,}"),
    "Slack token": re.compile(r"x[oapb][a-z]?-[0-9A-Za-z-]{20,}"),
    "bearer authorization value": re.compile(
        r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._~+/-]{20,}", re.IGNORECASE
    ),
}


def tracked_paths() -> list[Path]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    return [Path(os.fsdecode(item)) for item in output.split(b"\0") if item]


def main() -> int:
    findings: dict[Path, list[str]] = {}

    for path in tracked_paths():
        try:
            mode = path.lstat().st_mode
            if not stat.S_ISREG(mode):
                continue
            data = path.read_bytes()
        except OSError:
            findings[path] = ["unreadable tracked file"]
            continue

        if b"\0" in data:
            continue
        text = data.decode("utf-8", errors="ignore")
        matches = [name for name, pattern in RULES.items() if pattern.search(text)]
        if matches:
            findings[path] = matches

    if findings:
        print("Potential secrets detected in tracked files (values redacted):")
        for path, rules in sorted(findings.items(), key=lambda item: str(item[0])):
            print(f"- {path}: {', '.join(rules)}")
        return 1

    print("No high-confidence secret patterns detected in tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
