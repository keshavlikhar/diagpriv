"""Privacy transformation conditions."""

from diagpriv.transformations.format_preserving_v1 import (
    TRANSFORMATION_VERSION as FORMAT_PRESERVING_TRANSFORMATION_VERSION,
    format_preserving_incident,
    structural_pattern,
)
from diagpriv.transformations.hmac_v1 import (
    HMAC_KEY_ENVIRONMENT_VARIABLE,
    TRANSFORMATION_VERSION as HMAC_TRANSFORMATION_VERSION,
    hmac_incident,
    hmac_key_fingerprint,
    hmac_token,
    parse_hmac_key_hex,
)
from diagpriv.transformations.redaction_v1 import (
    TRANSFORMATION_VERSION as REDACTION_TRANSFORMATION_VERSION,
    redact_incident,
    redaction_placeholder,
)
from diagpriv.transformations.relative_time_v1 import (
    ANCHOR_RULE as RELATIVE_TIME_ANCHOR_RULE,
    PRECISION as RELATIVE_TIME_PRECISION,
    TRANSFORMATION_VERSION as RELATIVE_TIME_TRANSFORMATION_VERSION,
    relative_time_incident,
    transformation_configuration as relative_time_configuration,
)
from diagpriv.transformations.tokenization_v1 import (
    TRANSFORMATION_VERSION as TOKENIZATION_TRANSFORMATION_VERSION,
    tokenize_incident,
)

# Backward-compatible package export for the already-frozen redaction baseline.
TRANSFORMATION_VERSION = REDACTION_TRANSFORMATION_VERSION

__all__ = [
    "FORMAT_PRESERVING_TRANSFORMATION_VERSION",
    "HMAC_KEY_ENVIRONMENT_VARIABLE",
    "HMAC_TRANSFORMATION_VERSION",
    "REDACTION_TRANSFORMATION_VERSION",
    "RELATIVE_TIME_ANCHOR_RULE",
    "RELATIVE_TIME_PRECISION",
    "RELATIVE_TIME_TRANSFORMATION_VERSION",
    "TOKENIZATION_TRANSFORMATION_VERSION",
    "TRANSFORMATION_VERSION",
    "format_preserving_incident",
    "hmac_incident",
    "hmac_key_fingerprint",
    "hmac_token",
    "parse_hmac_key_hex",
    "redact_incident",
    "redaction_placeholder",
    "tokenize_incident",
    "relative_time_configuration",
    "relative_time_incident",
    "structural_pattern",
]
