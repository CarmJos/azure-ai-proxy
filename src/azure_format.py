"""Azure AI format builders for deployments, models, and error responses."""

from __future__ import annotations

import json
import time
from typing import Any

from .config import ProxyConfig


def build_deployment_entry(name: str, cfg: ProxyConfig) -> dict[str, Any]:
    """Build a single Azure-format deployment entry.

    Follows the real Azure OpenAI API response structure.
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
            {"key": "tokens", "renewal_period": "PT1M", "count": cfg.max_input_tokens or 1000000},
        ],
        # Token-limit fields
        "max_tokens": cfg.max_tokens,
        "max_input_tokens": cfg.max_input_tokens,
        "max_output_tokens": cfg.max_output_tokens,
        "max_context_tokens": cfg.max_input_tokens,
        "max_input_context_tokens": cfg.max_input_tokens,
        "context_window": cfg.max_input_tokens,
        "max_model_tokens": cfg.max_input_tokens,
    }


def build_model_entry(name: str, cfg: ProxyConfig) -> dict[str, Any]:
    """Build an entry for the Azure /openai/models endpoint (model catalog)."""
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

    return {
        "id": model_name,
        "object": "models",
        "status": "succeeded",
        "created_at": now,
        "owned_by": "organization-owner",
        "capabilities": caps,
        "lifecycle_status": "ga",
        "deprecation": {
            "fine_tune": None,
            "inference": None,
        },
        "max_tokens": cfg.max_tokens,
        "max_input_tokens": cfg.max_input_tokens,
        "max_output_tokens": cfg.max_output_tokens,
        "max_context_tokens": cfg.max_input_tokens,
        "max_input_context_tokens": cfg.max_input_tokens,
        "context_window": cfg.max_input_tokens,
        "max_model_tokens": cfg.max_input_tokens,
    }


def build_v1_model_entry(name: str, cfg: ProxyConfig) -> dict[str, Any]:
    """Build an OpenAI-compatible /v1/models entry."""
    return {
        "id": name,
        "object": "model",
        "created": int(time.time()),
        "owned_by": "organization-owner",
        "root": name,
        "parent": None,
        "max_tokens": cfg.max_tokens,
        "max_input_tokens": cfg.max_input_tokens,
        "max_output_tokens": cfg.max_output_tokens,
        "max_context_tokens": cfg.max_input_tokens,
        "context_window": cfg.max_input_tokens,
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

