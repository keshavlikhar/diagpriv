"""Provider-independent raw RCA baseline evaluation primitives."""

from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.pricing import PricingSnapshot
from diagpriv.evaluation.providers import (
    FakeProvider,
    ModelProvider,
    OpenAIResponsesProvider,
)
from diagpriv.evaluation.response import ParsedResponse, RCAResponse, parse_response
from diagpriv.evaluation.reporting import (
    PilotSummary,
    inspection_records,
    summarize_manifests,
)
from diagpriv.evaluation.runner import RawRunConfig, pilot_seed_plan, run_raw_experiment
from diagpriv.evaluation.scoring import RCAScore, score_response

__all__ = [
    "ExperimentManifest",
    "FakeProvider",
    "ModelProvider",
    "OpenAIResponsesProvider",
    "ParsedResponse",
    "PilotDefinition",
    "PilotSummary",
    "PricingSnapshot",
    "RCAResponse",
    "RCAScore",
    "RawRunConfig",
    "parse_response",
    "pilot_seed_plan",
    "run_raw_experiment",
    "score_response",
    "inspection_records",
    "summarize_manifests",
]
