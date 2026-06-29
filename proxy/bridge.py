"""LiteLLM bridge — translates Azure requests to LiteLLM calls and normalizes responses."""

from __future__ import annotations

import asyncio
import json
import time
import traceback
from typing import Any, AsyncIterator

import litellm

from .config import AppConfig, ProxyConfig
from .logging_setup import get_logger
from .utils import safe_json, sanitize_response_tool_calls, sanitize_stream_chunk_tool_calls

log = get_logger("bridge")


class LiteLLMError(Exception):
    """Raised when a LiteLLM call fails. Carries HTTP status code."""

    def __init__(self, message: str, status: int = 500, error_code: str = "500") -> None:
        super().__init__(message)
        self.status = status
        self.error_code = error_code


class LiteLLMBridge:
    """Thin wrapper around litellm that builds kwargs from ProxyConfig
    and normalises responses to Azure-compatible dicts."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    # ── Chat completion (non-stream) ───────────────────────────────

    async def chat_completion(
        self,
        cfg: ProxyConfig,
        messages: list[dict[str, Any]],
        **params: Any,
    ) -> dict[str, Any]:
        kwargs = cfg.to_litellm_kwargs({"messages": messages, **params})
        try:
            result = await litellm.acompletion(**kwargs)
            payload = safe_json(result)
            payload["model"] = cfg.display_model_name
            sanitize_response_tool_calls(payload)
            return payload
        except litellm.exceptions.AuthenticationError as e:
            raise LiteLLMError(f"Backend auth error: {e}", 401, "401") from e
        except litellm.exceptions.InvalidRequestError as e:
            raise LiteLLMError(f"Invalid request: {e}", 400, "400") from e
        except litellm.exceptions.RateLimitError as e:
            raise LiteLLMError(f"Rate limited: {e}", 429, "429") from e
        except litellm.exceptions.APIConnectionError as e:
            raise LiteLLMError(f"Backend connection error: {e}", 503, "503") from e
        except litellm.exceptions.Timeout as e:
            raise LiteLLMError(f"Backend timeout: {e}", 504, "504") from e
        except litellm.exceptions.APIError as e:
            raise LiteLLMError(f"Backend API error: {e}", 502, "502") from e
        except LiteLLMError:
            raise
        except Exception as e:
            log.error("Unexpected error in chat_completion: %s", traceback.format_exc())
            raise LiteLLMError(f"Internal proxy error: {e}", 500, "500") from e

    # ── Chat completion (stream) ───────────────────────────────────

    async def chat_completion_stream(
        self,
        cfg: ProxyConfig,
        messages: list[dict[str, Any]],
        **params: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        kwargs = cfg.to_litellm_kwargs({"messages": messages, **params})
        display_model = cfg.display_model_name
        try:
            completion = await litellm.acompletion(stream=True, **kwargs)
            async for chunk in completion:
                payload = safe_json(chunk)
                payload["model"] = display_model
                sanitize_stream_chunk_tool_calls(payload)
                yield payload
        except litellm.exceptions.AuthenticationError as e:
            raise LiteLLMError(f"Backend auth error: {e}", 401, "401") from e
        except litellm.exceptions.InvalidRequestError as e:
            raise LiteLLMError(f"Invalid request: {e}", 400, "400") from e
        except litellm.exceptions.RateLimitError as e:
            raise LiteLLMError(f"Rate limited: {e}", 429, "429") from e
        except litellm.exceptions.APIConnectionError as e:
            raise LiteLLMError(f"Backend connection error: {e}", 503, "503") from e
        except litellm.exceptions.Timeout as e:
            raise LiteLLMError(f"Backend timeout: {e}", 504, "504") from e
        except litellm.exceptions.APIError as e:
            raise LiteLLMError(f"Backend API error: {e}", 502, "502") from e
        except LiteLLMError:
            raise
        except Exception as e:
            log.error("Unexpected error in chat_completion_stream: %s", traceback.format_exc())
            raise LiteLLMError(f"Stream error: {e}", 500, "500") from e

    # ── Embeddings ─────────────────────────────────────────────────

    async def embedding(
        self,
        cfg: ProxyConfig,
        input_data: Any,
        **params: Any,
    ) -> dict[str, Any]:
        kwargs = cfg.to_litellm_kwargs({"input": input_data, **params})
        try:
            result = await litellm.aembedding(**kwargs)
            payload = safe_json(result)
            return payload
        except litellm.exceptions.AuthenticationError as e:
            raise LiteLLMError(f"Backend auth error: {e}", 401, "401") from e
        except litellm.exceptions.InvalidRequestError as e:
            raise LiteLLMError(f"Invalid request: {e}", 400, "400") from e
        except litellm.exceptions.RateLimitError as e:
            raise LiteLLMError(f"Rate limited: {e}", 429, "429") from e
        except litellm.exceptions.APIConnectionError as e:
            raise LiteLLMError(f"Backend connection error: {e}", 503, "503") from e
        except litellm.exceptions.Timeout as e:
            raise LiteLLMError(f"Backend timeout: {e}", 504, "504") from e
        except litellm.exceptions.APIError as e:
            raise LiteLLMError(f"Backend API error: {e}", 502, "502") from e
        except LiteLLMError:
            raise
        except Exception as e:
            log.error("Unexpected error in embedding: %s", traceback.format_exc())
            raise LiteLLMError(f"Internal proxy error: {e}", 500, "500") from e

    # ── Legacy completions (non-stream) ────────────────────────────

    async def legacy_completion(
        self,
        cfg: ProxyConfig,
        prompt: Any,
        **params: Any,
    ) -> dict[str, Any]:
        kwargs = cfg.to_litellm_kwargs({"prompt": prompt, **params})
        try:
            result = await litellm.atext_completion(**kwargs)
            payload = safe_json(result)
            payload["model"] = cfg.display_model_name
            return payload
        except litellm.exceptions.AuthenticationError as e:
            raise LiteLLMError(f"Backend auth error: {e}", 401, "401") from e
        except litellm.exceptions.InvalidRequestError as e:
            raise LiteLLMError(f"Invalid request: {e}", 400, "400") from e
        except litellm.exceptions.RateLimitError as e:
            raise LiteLLMError(f"Rate limited: {e}", 429, "429") from e
        except litellm.exceptions.APIConnectionError as e:
            raise LiteLLMError(f"Backend connection error: {e}", 503, "503") from e
        except litellm.exceptions.Timeout as e:
            raise LiteLLMError(f"Backend timeout: {e}", 504, "504") from e
        except litellm.exceptions.APIError as e:
            raise LiteLLMError(f"Backend API error: {e}", 502, "502") from e
        except LiteLLMError:
            raise
        except Exception as e:
            log.error("Unexpected error in legacy_completion: %s", traceback.format_exc())
            raise LiteLLMError(f"Internal proxy error: {e}", 500, "500") from e

    # ── Legacy completions (stream) ────────────────────────────────

    async def legacy_completion_stream(
        self,
        cfg: ProxyConfig,
        prompt: Any,
        **params: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        kwargs = cfg.to_litellm_kwargs({"prompt": prompt, **params})
        display_model = cfg.display_model_name
        try:
            completion = await litellm.atext_completion(stream=True, **kwargs)
            async for chunk in completion:
                payload = safe_json(chunk)
                payload["model"] = display_model
                yield payload
        except litellm.exceptions.AuthenticationError as e:
            raise LiteLLMError(f"Backend auth error: {e}", 401, "401") from e
        except litellm.exceptions.InvalidRequestError as e:
            raise LiteLLMError(f"Invalid request: {e}", 400, "400") from e
        except litellm.exceptions.RateLimitError as e:
            raise LiteLLMError(f"Rate limited: {e}", 429, "429") from e
        except litellm.exceptions.APIConnectionError as e:
            raise LiteLLMError(f"Backend connection error: {e}", 503, "503") from e
        except litellm.exceptions.Timeout as e:
            raise LiteLLMError(f"Backend timeout: {e}", 504, "504") from e
        except litellm.exceptions.APIError as e:
            raise LiteLLMError(f"Backend API error: {e}", 502, "502") from e
        except LiteLLMError:
            raise
        except Exception as e:
            log.error("Unexpected error in legacy_completion_stream: %s", traceback.format_exc())
            raise LiteLLMError(f"Stream error: {e}", 500, "500") from e
