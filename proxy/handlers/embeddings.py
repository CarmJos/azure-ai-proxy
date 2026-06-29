"""Embeddings handler."""

from __future__ import annotations

import json
from typing import Any

from aiohttp import web

from ..bridge import LiteLLMError, LiteLLMBridge
from ..config import AppConfig, ProxyConfig
from ..logging_setup import get_logger
from ..models import EmbeddingsRequest
from ..utils import extract_deployment, to_azure_error

log = get_logger("handlers.embeddings")


async def handle_embeddings(request: web.Request) -> web.Response:
    """POST /openai/deployments/{name}/embeddings"""
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

    log.info("📥 [%s] %s %s  ->  %s", req_id, request.method, request.path_qs, deployment)

    # Parse body
    try:
        body = await request.read()
        data: dict[str, Any] = json.loads(body) if body else {}
    except json.JSONDecodeError as e:
        return web.json_response(to_azure_error(f"Invalid JSON: {e}", "400"), status=400)

    emb_req = EmbeddingsRequest.from_dict(data)
    if emb_req.input is None:
        return web.json_response(
            to_azure_error("'input' field is required.", "400"),
            status=400,
        )

    params = emb_req.to_litellm_params()
    input_data = params.pop("input", emb_req.input)

    try:
        result = await bridge.embedding(model_cfg, input_data, **params)
        resp = web.json_response(result)
        resp.headers["x-request-id"] = req_id
        return resp
    except LiteLLMError as e:
        return web.json_response(to_azure_error(str(e), e.error_code), status=e.status)

