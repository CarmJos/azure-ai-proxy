"""General-purpose utility functions."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any


def extract_deployment(path: str) -> str | None:
    """Extract the deployment name from an Azure-style URL path."""
    parts = path.strip("/").split("/")
    try:
        idx = parts.index("deployments")
        if idx + 1 >= len(parts):
            return None
        name = parts[idx + 1]
        return name if name else None
    except (ValueError, IndexError):
        return None


def strip_image_url(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop every image_url content part."""
    out: list[dict[str, Any]] = []
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            out.append(msg)
            continue
        text_parts = [
            p for p in content
            if not (isinstance(p, dict) and p.get("type") == "image_url")
        ]
        if not text_parts:
            continue
        if (len(text_parts) == 1
            and isinstance(text_parts[0], dict)
            and text_parts[0].get("type") == "text"):
            msg = {**msg, "content": text_parts[0]["text"]}
        else:
            msg = {**msg, "content": text_parts}
        out.append(msg)
    return out


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return f"azure-proxy-{uuid.uuid4().hex[:12]}"


def to_azure_error(message: str, code: str = "500", error_type: str | None = None) -> dict[str, Any]:
    """Build an Azure-format error response body."""
    return {
        "error": {
            "message": message,
            "type": error_type or code,
            "code": code,
            "param": None,
        }
    }


def parse_api_version(query_string: str) -> str:
    """Extract api-version from a query string."""
    if not query_string:
        return ""
    for pair in query_string.split("&"):
        if pair.startswith("api-version="):
            return pair.split("=", 1)[1]
    return ""


def safe_json(obj: Any) -> dict:
    """Safely convert a litellm response object to a dict."""
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "json"):
        raw = obj.json()
        return raw if isinstance(raw, dict) else json.loads(raw)
    return dict(obj) if obj else {}


# --- JSON escape fix for tool call arguments ---

_INVALID_ESCAPE_RE = re.compile(r'\\(?!["\\/bfnrtu])')


def fix_json_escapes(s: str) -> str:
    """Fix unescaped backslashes in a JSON string."""
    return _INVALID_ESCAPE_RE.sub(r'\\\\', s)


def sanitize_tool_call_arguments(arguments: str) -> str:
    """Ensure tool call function.arguments is valid JSON."""
    if not arguments:
        return arguments
    try:
        json.loads(arguments)
        return arguments
    except (json.JSONDecodeError, ValueError):
        pass
    fixed = fix_json_escapes(arguments)
    try:
        json.loads(fixed)
        return fixed
    except (json.JSONDecodeError, ValueError):
        pass
    return json.dumps({"error": "malformed_arguments", "raw": arguments})


def sanitize_response_tool_calls(payload: dict[str, Any]) -> dict[str, Any]:
    """Walk a chat completion response and fix tool call arguments."""
    choices = payload.get("choices")
    if not choices:
        return payload
    for choice in choices:
        message = choice.get("message") or choice.get("delta")
        if not message:
            continue
        tool_calls = message.get("tool_calls")
        if not tool_calls:
            continue
        for tc in tool_calls:
            func = tc.get("function")
            if func and isinstance(func.get("arguments"), str):
                func["arguments"] = sanitize_tool_call_arguments(func["arguments"])
    return payload


def sanitize_stream_chunk_tool_calls(payload: dict[str, Any]) -> dict[str, Any]:
    """Fix tool call arguments in a streaming chunk (complete JSON objects only)."""
    choices = payload.get("choices")
    if not choices:
        return payload
    for choice in choices:
        delta = choice.get("delta")
        if not delta:
            continue
        tool_calls = delta.get("tool_calls")
        if not tool_calls:
            continue
        for tc in tool_calls:
            func = tc.get("function")
            if not func:
                continue
            args = func.get("arguments")
            if not isinstance(args, str):
                continue
            stripped = args.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                func["arguments"] = sanitize_tool_call_arguments(args)
    return payload
