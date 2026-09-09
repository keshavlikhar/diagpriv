"""Provider-independent invocation contracts, an offline fake, and one adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from typing import Literal, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class ModelRequest:
    prompt: str
    model: str
    model_version: str | None
    decoding_settings: dict[str, float | int | str | bool | None]
    reasoning_effort: str | None = None


@dataclass(frozen=True, slots=True)
class InvocationResult:
    status: Literal["success", "provider_error", "rate_limited", "refusal"]
    raw_output: str = ""
    error: str | None = None
    provider_returned_model: str | None = None
    response_id: str | None = None
    provider_timestamp: int | float | str | None = None
    input_token_count: int | None = None
    cached_input_token_count: int | None = None
    cache_write_input_token_count: int | None = None
    output_token_count: int | None = None
    reasoning_token_count: int | None = None
    total_token_count: int | None = None
    response_status: str | None = None
    service_tier: str | None = None


class ModelProvider(Protocol):
    def invoke(self, request: ModelRequest) -> InvocationResult:
        """Invoke a model using only the provider-neutral request."""
        ...


@dataclass(slots=True)
class FakeProvider:
    """Deterministic offline provider that records exactly what it receives."""

    raw_output: str = ""
    error: str | None = None
    requests: list[ModelRequest] = field(default_factory=list, init=False)

    def invoke(self, request: ModelRequest) -> InvocationResult:
        self.requests.append(request)
        if self.error is not None:
            return InvocationResult("provider_error", error=self.error)
        return InvocationResult("success", raw_output=self.raw_output)


@dataclass(frozen=True, slots=True)
class OpenAIResponsesProvider:
    """Minimal Responses API adapter using credentials only from the environment."""

    api_key_environment_variable: str = "OPENAI_API_KEY"
    base_url_environment_variable: str = "OPENAI_BASE_URL"
    timeout_seconds: float = 120.0

    @property
    def is_configured(self) -> bool:
        return bool(os.environ.get(self.api_key_environment_variable))

    def invoke(self, request: ModelRequest) -> InvocationResult:
        api_key = os.environ.get(self.api_key_environment_variable)
        if not api_key:
            return InvocationResult(
                "provider_error",
                error=f"Missing environment variable: {self.api_key_environment_variable}",
            )
        base_url = os.environ.get(
            self.base_url_environment_variable, "https://api.openai.com/v1"
        ).rstrip("/")
        body: dict[str, object] = {
            "model": request.model,
            "input": request.prompt,
            "store": False,
            "service_tier": "default",
        }
        if request.reasoning_effort is not None:
            body["reasoning"] = {"effort": request.reasoning_effort}
        temperature = request.decoding_settings.get("temperature")
        if temperature is not None:
            body["temperature"] = temperature
        max_output_tokens = request.decoding_settings.get("max_output_tokens")
        if max_output_tokens is not None:
            body["max_output_tokens"] = max_output_tokens
        http_request = Request(
            f"{base_url}/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429:
                return InvocationResult(
                    "rate_limited", error="OpenAI Responses API rate limit (HTTP 429)"
                )
            return InvocationResult(
                "provider_error", error=f"OpenAI Responses API HTTP {error.code}"
            )
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            return InvocationResult(
                "provider_error", error=f"OpenAI Responses API failure: {type(error).__name__}"
            )

        if not isinstance(payload, dict):
            return InvocationResult(
                "provider_error", error="OpenAI Responses API returned a non-object"
            )

        metadata = _responses_metadata(payload)
        if payload.get("status") not in {None, "completed"}:
            return InvocationResult(
                "provider_error",
                error=f"OpenAI response status: {payload.get('status', 'unknown')}",
                **metadata,
            )
        refusal = _responses_refusal(payload)
        if refusal is not None:
            return InvocationResult(
                "refusal",
                raw_output=refusal,
                error="Provider refused the task",
                **metadata,
            )
        output_text = _responses_output_text(payload)
        return InvocationResult("success", raw_output=output_text, **metadata)


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _responses_metadata(payload: dict[str, object]) -> dict[str, object]:
    usage = payload.get("usage")
    usage_data = usage if isinstance(usage, dict) else {}
    input_details = usage_data.get("input_tokens_details")
    input_data = input_details if isinstance(input_details, dict) else {}
    output_details = usage_data.get("output_tokens_details")
    output_data = output_details if isinstance(output_details, dict) else {}
    timestamp = payload.get("created_at")
    return {
        "provider_returned_model": _optional_string(payload.get("model")),
        "response_id": _optional_string(payload.get("id")),
        "provider_timestamp": (
            timestamp
            if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool)
            else None
        ),
        "input_token_count": _optional_int(usage_data.get("input_tokens")),
        "cached_input_token_count": _optional_int(input_data.get("cached_tokens")),
        "cache_write_input_token_count": _optional_int(
            input_data.get("cache_write_tokens")
        ),
        "output_token_count": _optional_int(usage_data.get("output_tokens")),
        "reasoning_token_count": _optional_int(output_data.get("reasoning_tokens")),
        "total_token_count": _optional_int(usage_data.get("total_tokens")),
        "response_status": _optional_string(payload.get("status")),
        "service_tier": _optional_string(payload.get("service_tier")),
    }


def _responses_output_text(payload: dict[str, object]) -> str:
    """Collect output_text content without assuming the first output item is text."""
    texts: list[str] = []
    output = payload.get("output", [])
    if not isinstance(output, list):
        return ""
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content", [])
        if not isinstance(content, list):
            continue
        for part in content:
            if (
                isinstance(part, dict)
                and part.get("type") == "output_text"
                and isinstance(part.get("text"), str)
            ):
                texts.append(part["text"])
    return "\n".join(texts)


def _responses_refusal(payload: dict[str, object]) -> str | None:
    output = payload.get("output", [])
    if not isinstance(output, list):
        return None
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content", [])
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "refusal":
                refusal = part.get("refusal")
                if isinstance(refusal, str):
                    return refusal
    return None
