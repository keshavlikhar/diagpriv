"""Privacy transformation conditions."""

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

# Backward-compatible package export for the already-frozen redaction baseline.
TRANSFORMATION_VERSION = REDACTION_TRANSFORMATION_VERSION

__all__ = [
    "HMAC_KEY_ENVIRONMENT_VARIABLE",
    "HMAC_TRANSFORMATION_VERSION",
    "REDACTION_TRANSFORMATION_VERSION",
    "TRANSFORMATION_VERSION",
    "hmac_incident",
    "hmac_key_fingerprint",
    "hmac_token",
    "parse_hmac_key_hex",
    "redact_incident",
    "redaction_placeholder",
]
