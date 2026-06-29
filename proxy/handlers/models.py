"""Models list/detail handlers (Azure and OpenAI formats)."""

from __future__ import annotations

import time

from aiohttp import web

from ..azure_format import build_model_entry, build_v1_model_entry
from ..config import AppConfig
from ..logging_setup import get_logger
from ..utils import to_azure_error

log = get_logger("handlers.models")


async def handle_models_list(request: web.Request) -> web.Response:
    """GET /openai/models — Azure model catalog."""
    cfg: AppConfig = request.app["config"]
    data_list = [build_model_entry(name, c) for name, c in cfg.models.items()]
    return web.json_response({"object": "list", "data": data_list})


async def handle_model_detail(request: web.Request) -> web.Response:
    """GET /openai/models/{name} — single model detail (Azure format)."""
    cfg: AppConfig = request.app["config"]
    name = request.match_info.get("name", "")
    model_cfg = cfg.models.get(name)
    if not model_cfg:
        return web.json_response(
            to_azure_error(f"Model '{name}' not found", "404"),
            status=404,
        )
    return web.json_response(build_model_entry(name, model_cfg))


async def handle_v1_models_list(request: web.Request) -> web.Response:
    """GET /v1/models — OpenAI-compatible model list."""
    cfg: AppConfig = request.app["config"]
    data_list = [build_v1_model_entry(name, c) for name, c in cfg.models.items()]
    return web.json_response({"object": "list", "data": data_list})


async def handle_v1_model_detail(request: web.Request) -> web.Response:
    """GET /v1/models/{name} — single model detail (OpenAI format)."""
    cfg: AppConfig = request.app["config"]
    name = request.match_info.get("name", "")
    model_cfg = cfg.models.get(name)
    if not model_cfg:
        return web.json_response(
            {"error": {"message": f"Model '{name}' not found", "type": "not_found"}},
            status=404,
        )
    return web.json_response(build_v1_model_entry(name, model_cfg))

