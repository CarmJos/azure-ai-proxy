"""aiohttp middleware: auth, logging, error handling, request-id."""

from __future__ import annotations

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

# Maximum bytes of request body to log (to avoid flooding output)
_MAX_BODY_LOG_BYTES = 2048

# Paths that always log full request details (model / deployment discovery only)
# Chat completions, embeddings, etc. are excluded to avoid flooding.
_DIAG_PATHS = ("/openai/models", "/openai/deployments", "/v1/models")
_DIAG_EXCLUDE = ("/chat/completions", "/embeddings", "/completions")


@web.middleware
async def logging_middleware(request: web.Request, handler: Any) -> web.StreamResponse:
    """Log every request and response.

    • **All** HTTP methods are logged (GET, POST, …).
    • When ``general.debug`` is ``true``, the POST body is also logged
      (truncated to ``_MAX_BODY_LOG_BYTES``).
    • Model / deployment listing endpoints are always logged at INFO
      level so that Copilot discovery traffic is visible even with
      ``debug: false``.
    """
    req_id = request.get("request_id", "-")
    debug = request.app["config"].debug

    # ── Collect request metadata ────────────────────────────────────
    ct = request.headers.get("Content-Type", request.headers.get("content-type", "-"))
    auth_present = "YES" if ("authorization" in request.headers or "api-key" in request.headers) else "NO"
    ua = request.headers.get("User-Agent", "-")
    accept = request.headers.get("Accept", "-")
    api_ver = ""
    if "?" in request.path_qs:
        from .utils import parse_api_version
        api_ver = parse_api_version(request.path_qs.split("?", 1)[1])

    _clean_path = request.path.rstrip("/")
    is_diag_path = (
        any(_clean_path == p or _clean_path.startswith(p + "/") for p in _DIAG_PATHS)
        and not any(_clean_path.endswith(ex) for ex in _DIAG_EXCLUDE)
    )

    # ── Log the request line ────────────────────────────────────────
    # Always log at least the request line for every incoming request.
    log.info("📡 [%s] REQ  %s %s  [api-ver: %s] [CT: %s] [UA: %s] [Auth: %s]",
             req_id, request.method, request.path_qs, api_ver or "-", ct, ua, auth_present)

    # ── Log request body ────────────────────────────────────────────
    # In debug mode, or for model/deployment discovery POSTs, dump the body.
    body_logged = False
    if request.method == "POST" and (debug or is_diag_path):
        try:
            raw_body = await request.read()
            if raw_body:
                truncated = raw_body[:_MAX_BODY_LOG_BYTES]
                body_preview = truncated.decode("utf-8", errors="replace")
                if len(raw_body) > _MAX_BODY_LOG_BYTES:
                    body_preview += f"… [{len(raw_body)} bytes total]"
                log.info("📥 [%s] BODY %s", req_id, body_preview)
                body_logged = True
            else:
                log.info("📥 [%s] BODY (empty)", req_id)
                body_logged = True
        except Exception:
            log.warning("📥 [%s] BODY (failed to read)", req_id)

    # ── Log full headers in debug mode ──────────────────────────────
    if debug:
        hdrs = {k: v for k, v in request.headers.items()
                if k.lower() not in ("authorization", "api-key")}
        log.info("📋 [%s] HEADERS %s", req_id, hdrs)

    try:
        resp = await handler(request)
    except web.HTTPException:
        raise
    except Exception:
        log.error("💥 [%s] Unhandled error: %s", req_id, traceback.format_exc())
        return web.json_response(
            to_azure_error("Internal proxy error", "500"),
            status=500,
        )

    elapsed = time.monotonic() - request.get("start_time", time.monotonic())
    status = resp.status if hasattr(resp, "status") else 0
    log.info("📤 [%s] RES  %s %s  %d  (%.3fs)", req_id, request.method, request.path, status, elapsed)

    # ── Log response body for model / deployment endpoints ──────────
    # This helps diagnose what Copilot sees when querying context length.
    if is_diag_path and hasattr(resp, "body") and resp.body:
        try:
            resp_preview = resp.body[:_MAX_BODY_LOG_BYTES].decode("utf-8", errors="replace")
            if len(resp.body) > _MAX_BODY_LOG_BYTES:
                resp_preview += f"… [{len(resp.body)} bytes total]"
            log.info("📋 [%s] RESP_BODY %s", req_id, resp_preview)
        except Exception:
            pass

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
    except Exception:
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
