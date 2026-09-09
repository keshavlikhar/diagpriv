"""Structured model response parsing with explicit failure outcomes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Literal, Self

from diagpriv.evaluation.taxonomy import canonical_category

ParseStatus = Literal[
    "valid",
    "malformed_json",
    "missing_fields",
    "invalid_schema",
    "unknown_category",
    "refusal",
    "empty_response",
    "provider_error",
    "rate_limited",
]


class MissingResponseFieldsError(ValueError):
    def __init__(self, fields: set[str]) -> None:
        self.fields = fields
        super().__init__(f"Missing RCA response fields: {sorted(fields)}")


@dataclass(frozen=True, slots=True)
class RCAResponse:
    observed_outcome: str
    trigger: str
    failure_mechanism: str
    affected_component: str
    supporting_evidence: tuple[str, ...]
    explanation: str
    confidence: float

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["supporting_evidence"] = list(self.supporting_evidence)
        return data

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        required = {field.name for field in cls.__dataclass_fields__.values()}
        missing = required.difference(data)
        if missing:
            raise MissingResponseFieldsError(missing)
        if set(data) != required:
            raise ValueError("RCA response contains unsupported fields")
        text_fields = (
            "observed_outcome",
            "trigger",
            "failure_mechanism",
            "affected_component",
            "explanation",
        )
        if any(not isinstance(data[field], str) or not data[field].strip() for field in text_fields):
            raise ValueError("RCA response text fields must be non-empty strings")
        evidence = data["supporting_evidence"]
        if not isinstance(evidence, list) or any(
            not isinstance(item, str) or not item.strip() for item in evidence
        ):
            raise ValueError("supporting_evidence must be a list of evidence ID strings")
        confidence = data["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be numeric")
        if not 0.0 <= float(confidence) <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        return cls(
            observed_outcome=data["observed_outcome"],
            trigger=data["trigger"],
            failure_mechanism=data["failure_mechanism"],
            affected_component=data["affected_component"],
            supporting_evidence=tuple(evidence),
            explanation=data["explanation"],
            confidence=float(confidence),
        )

    @classmethod
    def from_json(cls, payload: str) -> Self:
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("RCA response must be a JSON object")
        return cls.from_dict(data)


@dataclass(frozen=True, slots=True)
class ParsedResponse:
    status: ParseStatus
    raw_output: str
    response: RCAResponse | None = None
    error: str | None = None
    unknown_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "raw_output": self.raw_output,
            "response": None if self.response is None else self.response.to_dict(),
            "error": self.error,
            "unknown_fields": list(self.unknown_fields),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        response = data.get("response")
        return cls(
            status=data["status"],
            raw_output=data["raw_output"],
            response=None if response is None else RCAResponse.from_dict(response),
            error=data.get("error"),
            unknown_fields=tuple(data.get("unknown_fields", [])),
        )


def parse_response(raw_output: str) -> ParsedResponse:
    """Parse provider text without silently dropping any failure mode."""
    if not raw_output.strip():
        return ParsedResponse("empty_response", raw_output, error="Provider returned no text")
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as error:
        lowered = raw_output.lower()
        refusal_markers = ("i cannot", "i can't", "unable to comply", "cannot assist")
        if any(marker in lowered for marker in refusal_markers):
            return ParsedResponse("refusal", raw_output, error="Provider refused the task")
        return ParsedResponse("malformed_json", raw_output, error=str(error))
    if not isinstance(data, dict):
        return ParsedResponse("invalid_schema", raw_output, error="Response is not an object")
    try:
        response = RCAResponse.from_dict(data)
    except MissingResponseFieldsError as error:
        return ParsedResponse("missing_fields", raw_output, error=str(error))
    except ValueError as error:
        return ParsedResponse("invalid_schema", raw_output, error=str(error))

    unknown = tuple(
        field
        for field in ("observed_outcome", "trigger", "failure_mechanism")
        if canonical_category(field, getattr(response, field)) is None
    )
    if unknown:
        return ParsedResponse(
            "unknown_category",
            raw_output,
            response=response,
            error=f"Unknown category values in: {', '.join(unknown)}",
            unknown_fields=unknown,
        )
    return ParsedResponse("valid", raw_output, response=response)
