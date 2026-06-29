"""Health check, logs, and catch-all handlers."""

from __future__ import annotations

from aiohttp import web

from ..config import AppConfig
from ..logging_setup import get_log_buffer, get_logger
from ..utils import to_azure_error

log = get_logger("handlers.health")

PROXY_NAME = "azure-ai-proxy"


async def handle_health(request: web.Request) -> web.Response:
    """GET /health — simple health check."""
    cfg: AppConfig = request.app["config"]
    return web.json_response({
        "status": "ok",
        "proxy": PROXY_NAME,
        "models": cfg.model_names,
    })


async def handle_logs(request: web.Request) -> web.Response:
    """GET /logs — return recent log buffer as JSON."""
    return web.json_response({
        "lines": get_log_buffer(),
    })


async def handle_catch_all(request: web.Request) -> web.Response:
    """Catch-all handler for any unmatched routes."""
    log.warning("⚠️ UNMATCHED  %s %s  [UA: %s] [CT: %s] [Accept: %s]",
                request.method,
                request.path_qs,
                request.headers.get("User-Agent", "-"),
                request.headers.get("Content-Type", "-"),
                request.headers.get("Accept", "-"))
    return web.json_response(
        to_azure_error(f"Not found: {request.method} {request.path}", "404"),
        status=404,
    )

