"""aiohttp middleware: auth, logging, error handling, request-id."""

from __future__ import annotations

import json
import time
import traceback
from typing import Any

from aiohttp import web

from .config import AppConfig
from .logging_setup import get_logger
from .utils import generate_request_id, to_azure_error

log = get_logger("middleware")


# ── Request-ID middleware ───────────────────────────────────────────

@web.middleware
async def request_id_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    """Attach a unique request ID to every request."""
    request["request_id"] = generate_request_id()
    request["start_time"] = time.monotonic()
    return await handler(request)


# ── Auth middleware ─────────────────────────────────────────────────

@web.middleware
async def auth_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    """Validate proxy-level API key if configured.

    Supports both ``api-key`` header (Azure style) and ``Authorization: Bearer`` (OpenAI style).
    """
    app_config: AppConfig = request.app["config"]
    if not app_config.api_key:
        return await handler(request)

    client_key = request.headers.get("api-key", "")
    if not client_key:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            client_key = auth_header[7:]

    if client_key != app_config.api_key:
        req_id = request.get("request_id", "-")
        log.warning("🔐 [%s] REJECTED %s %s — bad or missing api-key", req_id, request.method, request.path_qs)
        return web.json_response(
            to_azure_error("Invalid or missing api-key", "401"),
            status=401,
        )

    return await handler(request)


# ── Logging middleware ──────────────────────────────────────────────

@web.middleware
async def logging_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    """Log every request and response."""
    req_id = request.get("request_id", "-")
    debug = request.app["config"].debug

    # Log request
    ct = request.headers.get("Content-Type", request.headers.get("content-type", "-"))
    auth_present = "YES" if ("authorization" in request.headers or "api-key" in request.headers) else "NO"
    api_ver = ""
    if "?" in request.path_qs:
        from .utils import parse_api_version
        api_ver = parse_api_version(request.path_qs.split("?", 1)[1])

    if debug or request.method != "POST":
        log.info("📡 [%s] REQ  %s %s  [api-ver: %s] [CT: %s] [Auth: %s]",
                 req_id, request.method, request.path_qs, api_ver or "-", ct, auth_present)

    try:
        resp = await handler(request)
    except web.HTTPException:
        raise
    except Exception:
        log.error("💥 [%s] Unhandled exception:\n%s", req_id, traceback.format_exc())
        raise

    elapsed = time.monotonic() - request.get("start_time", time.monotonic())
    status = resp.status if hasattr(resp, "status") else 0
    log.info("📤 [%s] RES  %s %s  %d  (%.3fs)", req_id, request.method, request.path, status, elapsed)

    return resp


# ── Error handling middleware ───────────────────────────────────────

@web.middleware
async def error_handling_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    """Catch all unhandled exceptions and return Azure-format JSON errors."""
    req_id = request.get("request_id", "-")
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as e:
        log.error("💥 [%s] Unhandled error: %s", req_id, traceback.format_exc())
        return web.json_response(
            to_azure_error("Internal proxy error", "500"),
            status=500,
        )


# ── CORS middleware (optional) ─────────────────────────────────────

@web.middleware
async def cors_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    """Add permissive CORS headers. Useful for browser-based clients."""
    if request.method == "OPTIONS":
        resp = web.Response(status=204)
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, api-key"
    resp.headers["Access-Control-Max-Age"] = "86400"
    return resp

