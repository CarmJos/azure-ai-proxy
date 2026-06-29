"""Deployments list/detail handlers."""

from __future__ import annotations

from aiohttp import web

from ..azure_format import build_deployment_entry, build_model_entry
from ..config import AppConfig
from ..logging_setup import get_logger
from ..utils import to_azure_error

log = get_logger("handlers.deployments")


async def handle_deployments_list(request: web.Request) -> web.Response:
    """GET /openai/deployments — list all configured deployments."""
    cfg: AppConfig = request.app["config"]
    data_list = [build_deployment_entry(name, c) for name, c in cfg.models.items()]
    return web.json_response({"object": "list", "data": data_list})


async def handle_deployment_detail(request: web.Request) -> web.Response:
    """GET /openai/deployments/{name} — single deployment detail."""
    cfg: AppConfig = request.app["config"]
    name = request.match_info.get("name", "")
    model_cfg = cfg.models.get(name)
    if not model_cfg:
        return web.json_response(
            to_azure_error(f"Deployment '{name}' not found", "404"),
            status=404,
        )
    return web.json_response(build_deployment_entry(name, model_cfg))


async def handle_deployment_models(request: web.Request) -> web.Response:
    """GET /openai/deployments/{name}/models — model version info for a deployment."""
    cfg: AppConfig = request.app["config"]
    name = request.match_info.get("name", "")
    model_cfg = cfg.models.get(name)
    if not model_cfg:
        return web.json_response(
            to_azure_error(f"Deployment '{name}' not found", "404"),
            status=404,
        )
    entry = build_model_entry(name, model_cfg)
    return web.json_response({"object": "list", "data": [entry]})

