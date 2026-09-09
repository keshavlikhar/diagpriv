"""Versioned construction of the raw RCA model prompt."""

from __future__ import annotations

from pathlib import Path

from diagbench.schema import ModelView

PROMPT_VERSION = "raw-rca-v1"
PROMPT_PATH = Path(__file__).parent / "prompts" / "raw_rca_v1.txt"


def prompt_template() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_prompt(model_view: ModelView) -> str:
    """Render a prompt from ModelView only; no Incident object is accepted."""
    template = prompt_template()
    marker = "{{MODEL_VIEW_JSON}}"
    if template.count(marker) != 1:
        raise ValueError("Prompt template must contain exactly one model-view marker")
    return template.replace(marker, model_view.to_json(indent=2).rstrip())

