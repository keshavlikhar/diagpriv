"""Versioned construction of the raw RCA v2 model prompt."""

from __future__ import annotations

import hashlib
from pathlib import Path

from diagbench.schema import ModelView

PROMPT_VERSION = "raw-rca-v2"
PROMPT_SHA256 = "744f1f62b6db7e0655d52692b929c3a2a9c3d86f8beaaefb76526ab0b2ea8a2d"
PROMPT_PATH = Path(__file__).parent / "prompts" / "raw_rca_v2.txt"


def prompt_template_v2() -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    actual = hashlib.sha256(template.encode("utf-8")).hexdigest()
    if actual != PROMPT_SHA256:
        raise ValueError(
            f"Prompt hash mismatch for {PROMPT_VERSION}: {actual} != {PROMPT_SHA256}"
        )
    return template


def build_prompt_v2(model_view: ModelView) -> str:
    """Render the v2 prompt from ModelView only."""
    template = prompt_template_v2()
    marker = "{{MODEL_VIEW_JSON}}"
    if template.count(marker) != 1:
        raise ValueError("Prompt template must contain exactly one model-view marker")
    return template.replace(marker, model_view.to_json(indent=2).rstrip())
