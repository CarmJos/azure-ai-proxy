"""Route registration for all Azure AI and OpenAI-compatible endpoints."""

from __future__ import annotations

from aiohttp import web

from .handlers.chat import handle_chat
from .handlers.completions import handle_completions
from .handlers.deployments import (
    handle_deployment_detail,
    handle_deployment_models,
    handle_deployments_list,
)
from .handlers.embeddings import handle_embeddings
from .handlers.health import handle_catch_all, handle_health, handle_logs
from .handlers.models import (
    handle_model_detail,
    handle_models_list,
    handle_v1_model_detail,
    handle_v1_models_list,
)


def register_routes(app: web.Application) -> None:
    """Register all routes on the aiohttp application."""

    # ── Azure Deployments API ──────────────────────────────────────
    app.router.add_route("GET", "/openai/deployments", handle_deployments_list)
    app.router.add_route("GET", "/openai/deployments/", handle_deployments_list)
    app.router.add_route("GET", "/openai/deployments/{name}", handle_deployment_detail)
    app.router.add_route("GET", "/openai/deployments/{name}/", handle_deployment_detail)

    # ── Azure deployment models ────────────────────────────────────
    app.router.add_route("GET", "/openai/deployments/{name}/models", handle_deployment_models)
    app.router.add_route("GET", "/openai/deployments/{name}/models/", handle_deployment_models)

    # ── Chat Completions ───────────────────────────────────────────
    app.router.add_route("*", "/openai/deployments/{name}/chat/completions", handle_chat)
    app.router.add_route("*", "/openai/deployments/{name}/chat/completions/", handle_chat)

    # ── Embeddings ─────────────────────────────────────────────────
    app.router.add_route("*", "/openai/deployments/{name}/embeddings", handle_embeddings)
    app.router.add_route("*", "/openai/deployments/{name}/embeddings/", handle_embeddings)

    # ── Legacy Completions ─────────────────────────────────────────
    app.router.add_route("*", "/openai/deployments/{name}/completions", handle_completions)
    app.router.add_route("*", "/openai/deployments/{name}/completions/", handle_completions)

    # ── Azure model catalog ────────────────────────────────────────
    app.router.add_route("GET", "/openai/models", handle_models_list)
    app.router.add_route("GET", "/openai/models/", handle_models_list)
    app.router.add_route("GET", "/openai/models/{name}", handle_model_detail)
    app.router.add_route("GET", "/openai/models/{name}/", handle_model_detail)

    # ── OpenAI-compatible models endpoint ──────────────────────────
    app.router.add_route("GET", "/v1/models", handle_v1_models_list)
    app.router.add_route("GET", "/v1/models/", handle_v1_models_list)
    app.router.add_route("GET", "/v1/models/{name}", handle_v1_model_detail)

    # ── Health / debug ─────────────────────────────────────────────
    app.router.add_route("GET", "/", handle_health)
    app.router.add_route("GET", "/health", handle_health)
    app.router.add_route("GET", "/logs", handle_logs)

    # ── Catch-all (must be last) ───────────────────────────────────
    app.router.add_route("*", "/{tail:.*}", handle_catch_all)
