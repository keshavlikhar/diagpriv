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
    model_version: str
    decoding_settings: dict[str, float | int | str | bool | None]


@dataclass(frozen=True, slots=True)
class InvocationResult:
    status: Literal["success", "provider_error", "rate_limited"]
    raw_output: str = ""
    error: str | None = None


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
        }
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

        if payload.get("status") not in {None, "completed"}:
            return InvocationResult(
                "provider_error",
                error=f"OpenAI response status: {payload.get('status', 'unknown')}",
            )
        output_text = _responses_output_text(payload)
        return InvocationResult("success", raw_output=output_text)


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
