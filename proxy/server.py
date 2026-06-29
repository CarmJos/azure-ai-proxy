"""Main server — application factory and entry point."""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from pathlib import Path

from aiohttp import web

from . import __version__
from .bridge import LiteLLMBridge
from .config import AppConfig, load_config
from .logging_setup import get_logger, setup_logging
from .middleware import (
    auth_middleware,
    cors_middleware,
    error_handling_middleware,
    logging_middleware,
    request_id_middleware,
)
from .routes import register_routes

log = get_logger("server")


def create_app(config_path: str | Path) -> web.Application:
    """Build and return the aiohttp Application with all middleware and routes."""

    # Load config
    cfg = load_config(config_path)

    # Setup logging
    setup_logging(level=cfg.log_level, log_file=cfg.log_file, debug=cfg.debug)

    # Create app
    app = web.Application(
        middlewares=[
            cors_middleware,
            request_id_middleware,
            auth_middleware,
            logging_middleware,
            error_handling_middleware,
        ],
    )

    # Store shared objects
    app["config"] = cfg
    app["bridge"] = LiteLLMBridge(cfg)

    # Register routes
    register_routes(app)

    # Startup / shutdown hooks
    app.on_startup.append(_on_startup)
    app.on_shutdown.append(_on_shutdown)
    app.on_cleanup.append(_on_cleanup)

    return app


async def _on_startup(app: web.Application) -> None:
    """Log startup information."""
    cfg: AppConfig = app["config"]
    log.info("🚀 azure-ai-proxy v%s starting", __version__)
    log.info("📋 config loaded — %d model(s)", len(cfg.models))
    if cfg.api_key:
        log.info("🔑 api-key: *** (%d chars)", len(cfg.api_key))
    else:
        log.info("🔓 api-key: <none> — accepting all keys")
    for name, mc in cfg.models.items():
        if mc.base_model:
            log.info("🏷️    %s  →  \"%s\" (base_model)", name, mc.base_model)
        else:
            log.info("🏷️    %s  →  \"%s\"", name, mc.model)
    log.info("🌐 listening on http://%s:%d", cfg.host, cfg.port)
    if cfg.debug:
        log.info("🔍 debug mode ON")


async def _on_shutdown(app: web.Application) -> None:
    log.info("🛑 shutting down...")


async def _on_cleanup(app: web.Application) -> None:
    log.info("✅ cleanup complete")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="azure-ai-proxy — Azure AI API compatible proxy powered by LiteLLM",
    )
    parser.add_argument(
        "--config", default="config.yaml",
        help="Path to YAML config (default: config.yaml)",
    )
    parser.add_argument(
        "--port", type=int, default=0,
        help="Override port (default: from config)",
    )
    parser.add_argument(
        "--host", default="",
        help="Override bind address (default: from config)",
    )
    args = parser.parse_args(argv)

    # Resolve config path
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent.parent / config_path
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    # Load config to get host/port overrides
    try:
        cfg = load_config(str(config_path))
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}", file=sys.stderr)
        sys.exit(1)

    host = args.host or cfg.host
    port = args.port or cfg.port

    # Create app
    app = create_app(str(config_path))

    # Try to use uvloop for performance (optional)
    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except ImportError:
        pass

    # Run
    web.run_app(
        app,
        host=host,
        port=port,
        print=lambda *_: None,  # suppress aiohttp's default banner; we log our own
    )


if __name__ == "__main__":
    main()

