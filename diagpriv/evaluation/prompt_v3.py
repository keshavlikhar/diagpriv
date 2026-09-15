"""Versioned construction of the raw RCA v3 model prompt."""

from __future__ import annotations

import hashlib
from pathlib import Path

from diagbench.schema import ModelView

PROMPT_VERSION = "raw-rca-v3"
# Filled with the reviewed template digest; prompt_template_v3 verifies it at use time.
PROMPT_SHA256 = "a2fc07481c9cd33776086d16cd76fafaa27c2fdf162f4ae634885187d0d22139"
PROMPT_PATH = Path(__file__).parent / "prompts" / "raw_rca_v3.txt"


def prompt_template_v3() -> str:
    template = PROMPT_PATH.read_text(encoding="utf-8")
    actual = hashlib.sha256(template.encode("utf-8")).hexdigest()
    if actual != PROMPT_SHA256:
        raise ValueError(
            f"Prompt hash mismatch for {PROMPT_VERSION}: {actual} != {PROMPT_SHA256}"
        )
    return template


def build_prompt_v3(model_view: ModelView) -> str:
    """Render the v3 prompt from ModelView only."""
    template = prompt_template_v3()
    marker = "{{MODEL_VIEW_JSON}}"
    if template.count(marker) != 1:
        raise ValueError("Prompt template must contain exactly one model-view marker")
    return template.replace(marker, model_view.to_json(indent=2).rstrip())
