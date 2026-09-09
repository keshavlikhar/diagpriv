"""Provider-independent model invocation contracts and an offline fake."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class ModelRequest:
    prompt: str
    model: str
    model_version: str
    decoding_settings: dict[str, float | int | str | bool | None]


@dataclass(frozen=True, slots=True)
class InvocationResult:
    status: Literal["success", "provider_error"]
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

