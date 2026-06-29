"""Legacy Completions handler."""

from __future__ import annotations

import asyncio
import json
import time
import traceback
from typing import Any

from aiohttp import web
try:
    from aiohttp.client_exceptions import ClientConnectionResetError
except ImportError:
    ClientConnectionResetError = ConnectionResetError  # type: ignore[assignment,misc]

from ..bridge import LiteLLMError, LiteLLMBridge
from ..config import AppConfig, ProxyConfig
from ..logging_setup import get_logger
from ..models import CompletionRequest
from ..utils import extract_deployment, to_azure_error
from ..azure_format import format_stream_chunk_sse

log = get_logger("handlers.completions")


async def handle_completions(request: web.Request) -> web.StreamResponse:
    """POST /openai/deployments/{name}/completions"""
    cfg: AppConfig = request.app["config"]
    bridge: LiteLLMBridge = request.app["bridge"]
    req_id: str = request.get("request_id", "-")

    # Resolve deployment
    deployment = extract_deployment(request.path)
    if not deployment:
        return web.json_response(
            to_azure_error("Unrecognized Azure deployment URL.", "404"),
            status=404,
        )

    model_cfg: ProxyConfig | None = cfg.models.get(deployment)
    if not model_cfg:
        return web.json_response(
            to_azure_error(f"Unknown deployment: {deployment}", "404"),
            status=404,
        )

    log.info("📝 [%s] %s %s  ->  %s", req_id, request.method, request.path_qs, deployment)

    # Parse body
    try:
        body = await request.read()
        data: dict[str, Any] = json.loads(body) if body else {}
    except json.JSONDecodeError as e:
        return web.json_response(to_azure_error(f"Invalid JSON: {e}", "400"), status=400)

    comp_req = CompletionRequest.from_dict(data)
    params = comp_req.to_litellm_params()
    prompt = params.pop("prompt", comp_req.prompt)

    try:
        if comp_req.stream:
            return await _stream_legacy_completion(request, bridge, model_cfg, prompt, params)
        else:
            result = await bridge.legacy_completion(model_cfg, prompt, **params)
            resp = web.json_response(result)
            resp.headers["x-request-id"] = req_id
            return resp
    except LiteLLMError as e:
        return web.json_response(to_azure_error(str(e), e.error_code), status=e.status)


async def _stream_legacy_completion(
    request: web.Request,
    bridge: LiteLLMBridge,
    model_cfg: ProxyConfig,
    prompt: Any,
    params: dict[str, Any],
) -> web.StreamResponse:
    """Stream legacy completions with keepalive and disconnect handling."""
    cfg: AppConfig = request.app["config"]
    req_id: str = request.get("request_id", "-")

    resp = web.StreamResponse(status=200)
    resp.headers["Content-Type"] = "text/event-stream"
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Connection"] = "keep-alive"
    resp.headers["X-Request-Id"] = req_id
    await resp.prepare(request)

    chunk_count = 0
    total_bytes = 0
    start_time = time.monotonic()
    last_chunk_time = start_time
    interrupted = False

    keepalive_stop = asyncio.Event()

    async def _keepalive() -> None:
        while not keepalive_stop.is_set():
            try:
                await asyncio.wait_for(keepalive_stop.wait(), timeout=cfg.keepalive_interval)
            except asyncio.TimeoutError:
                pass
            if keepalive_stop.is_set():
                break
            try:
                await resp.write(b": keepalive\n\n")
            except Exception:
                break

    keepalive_task = asyncio.create_task(_keepalive())

    try:
        stream = bridge.legacy_completion_stream(model_cfg, prompt, **params)
        async for chunk in stream:
            if request.transport is not None and request.transport.is_closing():
                interrupted = True
                break
            now = time.monotonic()
            if now - last_chunk_time > cfg.max_stream_timeout:
                interrupted = True
                break
            data = format_stream_chunk_sse(chunk)
            await asyncio.wait_for(resp.write(data), timeout=10)
            chunk_count += 1
            total_bytes += len(data)
            last_chunk_time = time.monotonic()
    except asyncio.CancelledError:
        interrupted = True
    except ClientConnectionResetError:
        interrupted = True
    except LiteLLMError as e:
        try:
            await resp.write(format_stream_chunk_sse(
                {"error": {"message": str(e), "type": e.error_code, "code": e.error_code}}))
        except Exception:
            interrupted = True
    except Exception as e:
        log.error("💥 [%s] stream error: %s", req_id, traceback.format_exc())
        try:
            await resp.write(format_stream_chunk_sse({"error": {"message": str(e)}}))
        except Exception:
            interrupted = True
    finally:
        keepalive_stop.set()
        keepalive_task.cancel()
        try:
            await keepalive_task
        except asyncio.CancelledError:
            pass

    if not interrupted:
        try:
            await resp.write(b"data: [DONE]\n\n")
            await resp.write_eof()
        except (ClientConnectionResetError, ConnectionResetError):
            pass

    elapsed = time.monotonic() - start_time
    log.info("📊 [%s] legacy stream done: %d chunks, %d bytes, %.1fs", req_id, chunk_count, total_bytes, elapsed)
    return resp

