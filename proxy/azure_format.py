"""Azure AI format builders for deployments, models, and error responses.

References:
  - Azure OpenAI API: https://learn.microsoft.com/en-us/azure/ai-services/openai/reference
  - Azure AI Foundry: https://learn.microsoft.com/en-us/azure/foundry/openai/reference
"""

from __future__ import annotations

import json
import time
from typing import Any

from .config import ProxyConfig

# ── Sensible fallback defaults for token limits ──────────────────────
# Used when config does not explicitly set a value, so the API response
# never contains ``null`` (which clients like JetBrains Copilot ignore).
_DEFAULT_MAX_INPUT_TOKENS = 128000
_DEFAULT_MAX_OUTPUT_TOKENS = 16384
_DEFAULT_MAX_TOKENS = _DEFAULT_MAX_INPUT_TOKENS + _DEFAULT_MAX_OUTPUT_TOKENS


def _safe_token(value: int | None, default: int) -> int:
    """Return *value* if not None, otherwise *default*."""
    return value if value is not None else default


def build_deployment_entry(name: str, cfg: ProxyConfig) -> dict[str, Any]:
    """Build a single Azure-format deployment entry.

    Follows the real Azure OpenAI API response structure as described at:
    https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#retrievedeployment
    """
    caps: dict[str, bool] = {"chat_completion": True}
    if cfg.supports_function_calling:
        caps["function_calling"] = True
    if cfg.supports_reasoning:
        caps["reasoning"] = True
    if cfg.supports_tool_choice:
        caps["tool_choice"] = True
    if cfg.supports_vision:
        caps["vision"] = True

    now = int(time.time())
    model_name = cfg.display_model_name

    max_input = _safe_token(cfg.max_input_tokens, _DEFAULT_MAX_INPUT_TOKENS)
    max_output = _safe_token(cfg.max_output_tokens, _DEFAULT_MAX_OUTPUT_TOKENS)
    max_tok = _safe_token(cfg.max_tokens, _DEFAULT_MAX_TOKENS)

    return {
        "id": name,
        "object": "deployment",
        "model": model_name,
        "owner": "organization-owner",
        "status": "succeeded",
        "created_at": now,
        "updated_at": now,
        "capabilities": caps,
        "scale_settings": {
            "scale_type": "standard",
            "capacity": None,
        },
        "version": "2025-01-01",
        "is_latest_version": True,
        "is_preview": False,
        "rate_limits": [
            {"key": "request", "renewal_period": "PT1M", "count": 100},
            {"key": "tokens", "renewal_period": "PT1M", "count": max_input},
        ],
        # Token-limit fields — multiple names for client compatibility
        "max_tokens": max_tok,
        "max_input_tokens": max_input,
        "max_output_tokens": max_output,
        "max_context_tokens": max_input,
        "max_input_context_tokens": max_input,
        "context_window": max_input,
        "max_model_tokens": max_input,
    }


def build_model_entry(name: str, cfg: ProxyConfig) -> dict[str, Any]:
    """Build an entry for the Azure /openai/models endpoint (model catalog).

    Follows the Azure OpenAI model response as described at:
    https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#retrieve模型
    """
    caps: dict[str, bool] = {"chat_completion": True}
    if cfg.supports_function_calling:
        caps["function_calling"] = True
    if cfg.supports_reasoning:
        caps["reasoning"] = True
    if cfg.supports_tool_choice:
        caps["tool_choice"] = True
    if cfg.supports_vision:
        caps["vision"] = True

    now = int(time.time())
    model_name = cfg.display_model_name

    max_input = _safe_token(cfg.max_input_tokens, _DEFAULT_MAX_INPUT_TOKENS)
    max_output = _safe_token(cfg.max_output_tokens, _DEFAULT_MAX_OUTPUT_TOKENS)
    max_tok = _safe_token(cfg.max_tokens, _DEFAULT_MAX_TOKENS)

    return {
        "id": model_name,
        "object": "model",   # singular — matches the Azure OpenAI spec
        "created": now,
        "owned_by": "azure-openai",
        "status": "succeeded",
        "permission": [],
        "root": model_name,
        "parent": None,
        "capabilities": caps,
        "lifecycle_status": "ga",
        "deprecation": {
            "fine_tune": None,
            "inference": None,
        },
        # Token-limit fields — multiple names for client compatibility
        "max_tokens": max_tok,
        "max_input_tokens": max_input,
        "max_output_tokens": max_output,
        "max_context_tokens": max_input,
        "max_input_context_tokens": max_input,
        "context_window": max_input,
        "max_model_tokens": max_input,
    }


def build_v1_model_entry(name: str, cfg: ProxyConfig) -> dict[str, Any]:
    """Build an OpenAI-compatible /v1/models entry."""
    max_input = _safe_token(cfg.max_input_tokens, _DEFAULT_MAX_INPUT_TOKENS)
    max_output = _safe_token(cfg.max_output_tokens, _DEFAULT_MAX_OUTPUT_TOKENS)
    max_tok = _safe_token(cfg.max_tokens, _DEFAULT_MAX_TOKENS)

    return {
        "id": name,
        "object": "model",
        "created": int(time.time()),
        "owned_by": "organization-owner",
        "root": name,
        "parent": None,
        "max_tokens": max_tok,
        "max_input_tokens": max_input,
        "max_output_tokens": max_output,
        "max_context_tokens": max_input,
        "context_window": max_input,
    }


def build_error_response(message: str, code: str = "500", error_type: str | None = None) -> dict[str, Any]:
    """Build an Azure-format error response body."""
    return {
        "error": {
            "message": message,
            "type": error_type or code,
            "code": code,
            "param": None,
        }
    }


def format_stream_chunk_sse(payload: dict[str, Any]) -> bytes:
    """Format a dict as an SSE data frame."""
    return f"data: {json.dumps(payload)}\n\n".encode("utf-8")
