"""Provider-independent raw RCA baseline evaluation primitives."""

from diagpriv.evaluation.manifest import ExperimentManifest
from diagpriv.evaluation.pilot import PilotDefinition
from diagpriv.evaluation.pricing import PricingSnapshot
from diagpriv.evaluation.providers import (
    FakeProvider,
    ModelProvider,
    OpenAIResponsesProvider,
    SanitizedAPIError,
)
from diagpriv.evaluation.response import (
    ParsedResponse,
    RCAResponse,
    RCAResponseV2,
    RCAResponseV3,
    parse_response,
    parse_response_v2,
    parse_response_v3,
)
from diagpriv.evaluation.reporting import (
    PilotSummary,
    inspection_records,
    summarize_manifests,
)
from diagpriv.evaluation.runner import RawRunConfig, pilot_seed_plan, run_raw_experiment
from diagpriv.evaluation.scoring import RCAScore, score_response
from diagpriv.evaluation.scoring_v2 import (
    ProtocolVersionError,
    RCAScoreV2,
    score_response_v2,
)
from diagpriv.evaluation.scoring_v3 import RCAScoreV3, score_response_v3

__all__ = [
    "ExperimentManifest",
    "FakeProvider",
    "ModelProvider",
    "OpenAIResponsesProvider",
    "SanitizedAPIError",
    "ParsedResponse",
    "PilotDefinition",
    "PilotSummary",
    "PricingSnapshot",
    "RCAResponse",
    "RCAResponseV2",
    "RCAResponseV3",
    "RCAScore",
    "RCAScoreV2",
    "RCAScoreV3",
    "RawRunConfig",
    "parse_response",
    "parse_response_v2",
    "parse_response_v3",
    "pilot_seed_plan",
    "run_raw_experiment",
    "score_response",
    "score_response_v2",
    "score_response_v3",
    "ProtocolVersionError",
    "inspection_records",
    "summarize_manifests",
]
