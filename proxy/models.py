"""Data models for parsed requests and proxy responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatCompletionRequest:
    """Parsed Azure chat completion request body."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: list[str] | None = None
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any = None
    seed: int | None = None
    response_format: dict[str, Any] | None = None
    user: str | None = None
    n: int | None = None
    logprobs: bool | None = None
    top_logprobs: int | None = None

    # Extra fields not explicitly listed
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChatCompletionRequest:
        known = {
            "messages", "temperature", "max_tokens", "top_p",
            "frequency_penalty", "presence_penalty", "stop",
            "stream", "tools", "tool_choice", "seed",
            "response_format", "user", "n", "logprobs", "top_logprobs",
        }
        extra = {k: v for k, v in data.items() if k not in known and v is not None}
        return cls(
            messages=data.get("messages", []),
            temperature=data.get("temperature"),
            max_tokens=data.get("max_tokens"),
            top_p=data.get("top_p"),
            frequency_penalty=data.get("frequency_penalty"),
            presence_penalty=data.get("presence_penalty"),
            stop=data.get("stop"),
            stream=bool(data.get("stream", False)),
            tools=data.get("tools"),
            tool_choice=data.get("tool_choice"),
            seed=data.get("seed"),
            response_format=data.get("response_format"),
            user=data.get("user"),
            n=data.get("n"),
            logprobs=data.get("logprobs"),
            top_logprobs=data.get("top_logprobs"),
            extra=extra,
        )

    def to_litellm_params(self) -> dict[str, Any]:
        """Return only non-None parameters suitable for litellm."""
        params: dict[str, Any] = {}
        if self.messages:
            params["messages"] = self.messages
        if self.temperature is not None:
            params["temperature"] = self.temperature
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            params["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            params["presence_penalty"] = self.presence_penalty
        if self.stop is not None:
            params["stop"] = self.stop
        if self.tools is not None:
            params["tools"] = self.tools
        if self.tool_choice is not None:
            params["tool_choice"] = self.tool_choice
        if self.seed is not None:
            params["seed"] = self.seed
        if self.response_format is not None:
            params["response_format"] = self.response_format
        if self.user is not None:
            params["user"] = self.user
        if self.n is not None:
            params["n"] = self.n
        if self.logprobs is not None:
            params["logprobs"] = self.logprobs
        if self.top_logprobs is not None:
            params["top_logprobs"] = self.top_logprobs
        params.update(self.extra)
        return params


@dataclass
class EmbeddingsRequest:
    """Parsed Azure embeddings request body."""

    input: Any = None
    encoding_format: str | None = None
    dimensions: int | None = None
    user: str | None = None

    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddingsRequest:
        known = {"input", "encoding_format", "dimensions", "user"}
        extra = {k: v for k, v in data.items() if k not in known and v is not None}
        return cls(
            input=data.get("input"),
            encoding_format=data.get("encoding_format"),
            dimensions=data.get("dimensions"),
            user=data.get("user"),
            extra=extra,
        )

    def to_litellm_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self.input is not None:
            params["input"] = self.input
        if self.encoding_format is not None:
            params["encoding_format"] = self.encoding_format
        if self.dimensions is not None:
            params["dimensions"] = self.dimensions
        if self.user is not None:
            params["user"] = self.user
        params.update(self.extra)
        return params


@dataclass
class CompletionRequest:
    """Parsed Azure legacy completions request body."""

    prompt: Any = None
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
    presence_penalty: float | None = None
    stop: list[str] | None = None
    stream: bool = False
    suffix: str | None = None
    echo: bool | None = None
    user: str | None = None

    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CompletionRequest:
        known = {
            "prompt", "temperature", "max_tokens", "top_p",
            "frequency_penalty", "presence_penalty", "stop",
            "stream", "suffix", "echo", "user",
        }
        extra = {k: v for k, v in data.items() if k not in known and v is not None}
        return cls(
            prompt=data.get("prompt", ""),
            temperature=data.get("temperature"),
            max_tokens=data.get("max_tokens"),
            top_p=data.get("top_p"),
            frequency_penalty=data.get("frequency_penalty"),
            presence_penalty=data.get("presence_penalty"),
            stop=data.get("stop"),
            stream=bool(data.get("stream", False)),
            suffix=data.get("suffix"),
            echo=data.get("echo"),
            user=data.get("user"),
            extra=extra,
        )

    def to_litellm_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if self.prompt is not None:
            params["prompt"] = self.prompt
        if self.temperature is not None:
            params["temperature"] = self.temperature
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            params["top_p"] = self.top_p
        if self.frequency_penalty is not None:
            params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            params["presence_penalty"] = self.presence_penalty
        if self.stop is not None:
            params["stop"] = self.stop
        if self.suffix is not None:
            params["suffix"] = self.suffix
        if self.echo is not None:
            params["echo"] = self.echo
        if self.user is not None:
            params["user"] = self.user
        params.update(self.extra)
        return params

