"""Chat Completions handler — the primary proxy endpoint."""

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
from ..models import ChatCompletionRequest
from ..utils import extract_deployment, strip_image_url, to_azure_error
from ..azure_format import format_stream_chunk_sse

log = get_logger("handlers.chat")


async def handle_chat(request: web.Request) -> web.StreamResponse:
    """POST /openai/deployments/{name}/chat/completions"""
    cfg: AppConfig = request.app["config"]
    bridge: LiteLLMBridge = request.app["bridge"]
    req_id: str = request.get("request_id", "-")

    # ── Resolve deployment ─────────────────────────────────────────
    deployment = extract_deployment(request.path)
    if not deployment:
        return web.json_response(
            to_azure_error(
                "Unrecognized Azure deployment URL. "
                "Expected /openai/deployments/{model}/chat/completions", "404"),
            status=404,
        )

    model_cfg: ProxyConfig | None = cfg.models.get(deployment)
    if not model_cfg:
        return web.json_response(
            to_azure_error(f"Unknown deployment: {deployment}", "404"),
            status=404,
        )

    log.info("⚡ [%s] %s %s  ->  %s", req_id, request.method, request.path_qs, deployment)

    # ── Parse body ─────────────────────────────────────────────────
    try:
        body = await request.read()
        data: dict[str, Any] = json.loads(body) if body else {}
    except json.JSONDecodeError as e:
        return web.json_response(to_azure_error(f"Invalid JSON: {e}", "400"), status=400)

    chat_req = ChatCompletionRequest.from_dict(data)

    # Strip image_url if backend doesn't support vision
    if not model_cfg.supports_vision and chat_req.messages:
        orig = len(chat_req.messages)
        chat_req.messages = strip_image_url(chat_req.messages)
        if dropped := orig - len(chat_req.messages):
            log.info("🖼️ [%s] dropped %d image-only message(s)", req_id, dropped)

    params = chat_req.to_litellm_params()
    params.pop("messages", None)  # messages passed separately

    # ── Dispatch ───────────────────────────────────────────────────
    try:
        if chat_req.stream:
            return await _stream_response(request, bridge, model_cfg, chat_req.messages, params)
        else:
            result = await bridge.chat_completion(model_cfg, chat_req.messages, **params)
            resp = web.json_response(result)
            resp.headers["x-request-id"] = req_id
            return resp
    except LiteLLMError as e:
        return web.json_response(to_azure_error(str(e), e.error_code), status=e.status)


async def _stream_response(
    request: web.Request,
    bridge: LiteLLMBridge,
    model_cfg: ProxyConfig,
    messages: list[dict[str, Any]],
    params: dict[str, Any],
) -> web.StreamResponse:
    """Enhanced streaming with keepalive, timeout protection, and graceful disconnect."""
    cfg: AppConfig = request.app["config"]
    req_id: str = request.get("request_id", "-")

    resp = web.StreamResponse(status=200)
    resp.headers["Content-Type"] = "text/event-stream"
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Connection"] = "keep-alive"
    resp.headers["X-Request-Id"] = req_id
    await resp.prepare(request)

    # Stats
    chunk_count = 0
    total_bytes = 0
    start_time = time.monotonic()
    last_chunk_time = start_time
    interrupted = False

    # Keepalive task
    keepalive_stop = asyncio.Event()

    async def _keepalive() -> None:
        """Send SSE comments to prevent client timeout."""
        while not keepalive_stop.is_set():
            try:
                await asyncio.wait_for(
                    keepalive_stop.wait(),
                    timeout=cfg.keepalive_interval,
                )
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
        stream = bridge.chat_completion_stream(model_cfg, messages, **params)
        async for chunk in stream:
            # Check client disconnect
            if request.transport is not None and request.transport.is_closing():
                log.info("🚫 [%s] client disconnected during stream", req_id)
                interrupted = True
                break

            # Timeout protection per chunk
            now = time.monotonic()
            if now - last_chunk_time > cfg.max_stream_timeout:
                log.warning("⏱️ [%s] stream timeout — no chunk for %ds", req_id, cfg.max_stream_timeout)
                interrupted = True
                break

            # Write chunk
            data = format_stream_chunk_sse(chunk)
            await asyncio.wait_for(resp.write(data), timeout=10)
            chunk_count += 1
            total_bytes += len(data)
            last_chunk_time = time.monotonic()

    except asyncio.CancelledError:
        log.info("🚫 [%s] stream cancelled", req_id)
        interrupted = True
    except ClientConnectionResetError:
        log.info("🚫 [%s] client disconnected", req_id)
        interrupted = True
    except LiteLLMError as e:
        log.error("💥 [%s] stream LiteLLM error: %s", req_id, e)
        try:
            err_data = format_stream_chunk_sse(
                {"error": {"message": str(e), "type": e.error_code, "code": e.error_code}}
            )
            await resp.write(err_data)
        except Exception:
            interrupted = True
    except Exception as e:
        log.error("💥 [%s] stream error: %s", req_id, traceback.format_exc())
        try:
            err_data = format_stream_chunk_sse(
                {"error": {"message": str(e), "type": "stream_error"}}
            )
            await resp.write(err_data)
        except Exception:
            interrupted = True
    finally:
        keepalive_stop.set()
        keepalive_task.cancel()
        try:
            await keepalive_task
        except asyncio.CancelledError:
            pass

    # Send [DONE] and close
    if not interrupted:
        try:
            await resp.write(b"data: [DONE]\n\n")
            await resp.write_eof()
        except (ClientConnectionResetError, ConnectionResetError):
            log.info("🚫 [%s] client disconnected before [DONE]", req_id)

    elapsed = time.monotonic() - start_time
    log.info("📊 [%s] stream done: %d chunks, %d bytes, %.1fs", req_id, chunk_count, total_bytes, elapsed)
    return resp

