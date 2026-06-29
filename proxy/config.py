"""Configuration loading and management."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Environment variable resolver ──────────────────────────────────

def _resolve_env(value: Any) -> str:
    """Resolve ``os.environ/KEY`` references to real env values."""
    if isinstance(value, str) and value.startswith("os.environ/"):
        key = value.split("/", 1)[1]
        return os.environ.get(key, "")
    return str(value) if value else ""


# ── Model configuration ────────────────────────────────────────────

@dataclass
class ProxyConfig:
    """Represents a single backend model as defined in config.yaml."""

    name: str
    provider: str = "openai"
    model: str = ""
    api_base: str = ""
    api_key: str = ""
    supports_vision: bool = False
    supports_function_calling: bool = False
    supports_reasoning: bool = False
    supports_tool_choice: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    max_input_tokens: int | None = None
    max_output_tokens: int | None = None
    timeout: int = 120
    extra_headers: dict[str, str] = field(default_factory=dict)
    base_model: str | None = None

    def __post_init__(self) -> None:
        if not self.model:
            self.model = self.name

    @classmethod
    def from_dict(cls, name: str, params: dict[str, Any]) -> ProxyConfig:
        """Create from a config dict (litellm_params section)."""
        return cls(
            name=name,
            provider=str(params.get("provider", "openai")),
            model=str(params.get("model", name)),
            api_base=_resolve_env(params.get("api_base", "")),
            api_key=_resolve_env(params.get("api_key", "")),
            supports_vision=bool(params.get("supports_vision", False)),
            supports_function_calling=bool(params.get("supports_function_calling", False)),
            supports_reasoning=bool(params.get("supports_reasoning", False)),
            supports_tool_choice=bool(params.get("supports_tool_choice", False)),
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
            max_input_tokens=params.get("max_input_tokens"),
            max_output_tokens=params.get("max_output_tokens"),
            timeout=int(params.get("timeout", 120)),
            extra_headers=params.get("extra_headers", {}) or {},
            base_model=params.get("base_model"),
        )

    @property
    def display_model_name(self) -> str:
        """Model name to report in Azure responses."""
        return self.base_model or self.name

    def to_litellm_kwargs(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build kwargs dict for litellm.acompletion() / aembedding()."""
        k: dict[str, Any] = {"timeout": self.timeout}
        if self.temperature is not None:
            k["temperature"] = self.temperature
        if self.max_tokens is not None:
            k["max_tokens"] = self.max_tokens
        if self.max_input_tokens is not None:
            k["max_input_tokens"] = self.max_input_tokens
        if self.max_output_tokens is not None:
            k["max_output_tokens"] = self.max_output_tokens
        if self.extra_headers:
            k["extra_headers"] = self.extra_headers
        if extra:
            # Filter out config-level fields that must NOT come from client
            safe_extra = {k_: v for k_, v in extra.items()
                         if k_ not in ("model", "api_base", "api_key")}
            k.update(safe_extra)
        # Config-level fields are set LAST so they cannot be overridden by client
        k["model"] = self.model
        if self.api_base:
            k["api_base"] = self.api_base
        if self.api_key:
            k["api_key"] = self.api_key
        return k


# ── Application configuration ──────────────────────────────────────

@dataclass
class AppConfig:
    """Top-level application configuration."""

    # Server
    host: str = "0.0.0.0"
    port: int = 4000
    timeout: int = 120
    debug: bool = False
    api_key: str = ""

    # Logging
    log_level: str = "INFO"
    log_file: str = ""

    # Streaming
    max_stream_timeout: int = 300
    keepalive_interval: int = 15

    # Models
    models: dict[str, ProxyConfig] = field(default_factory=dict)

    @property
    def model_names(self) -> list[str]:
        return list(self.models.keys())


# ── Config loader ──────────────────────────────────────────────────

def load_config(path: str | Path) -> AppConfig:
    """Parse config.yaml and return an AppConfig instance."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # -- Parse models --
    models: dict[str, ProxyConfig] = {}
    for entry in raw.get("models", raw.get("model_list", [])):
        name = entry.get("model_name", entry.get("name", ""))
        if not name:
            continue
        params = entry.get("litellm_params", entry.get("params", entry))
        models[name] = ProxyConfig.from_dict(name, params if isinstance(params, dict) else {})

    # -- Parse general settings --
    settings = raw.get("general", raw.get("general_settings", raw.get("settings", {}))) or {}

    cfg = AppConfig(
        host=str(settings.get("host", "0.0.0.0")),
        port=int(settings.get("port", raw.get("port", 4000))),
        timeout=int(settings.get("timeout", raw.get("request_timeout", 120))),
        debug=bool(settings.get("debug", False)),
        api_key=str(settings.get("api-key", "")).strip(),
        log_level=str(settings.get("log-level", "INFO")).upper(),
        log_file=str(settings.get("log-file", "")),
        max_stream_timeout=int(settings.get("max-stream-timeout", 300)),
        keepalive_interval=int(settings.get("keepalive-interval", 15)),
        models=models,
    )

    # -- Validate --
    if not cfg.models:
        raise ValueError("No models defined in config file.")

    # -- Warn about missing token limits --
    for _name, _mc in cfg.models.items():
        if _mc.max_input_tokens is None or _mc.max_output_tokens is None:
            import logging as _log_mod
            _log_mod.getLogger("azure_ai_proxy.config").warning(
                "⚠️  Model '%s' is missing max_input_tokens / max_output_tokens in config. "
                "Defaults (%d / %d) will be used in API responses. "
                "Set these in config.yaml for accurate context-window reporting in clients.",
                _name, 128000, 16384,
            )

    return cfg
