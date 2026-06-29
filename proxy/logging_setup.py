"""Logging system with emoji-style formatting and request tracking."""

from __future__ import annotations

import collections
import logging
import sys
import threading
from typing import Any


# ── Log buffer for /logs endpoint ──────────────────────────────────

_LOG_BUFFER: collections.deque[str] = collections.deque(maxlen=5000)
_LOG_LOCK = threading.Lock()


def get_log_buffer() -> list[str]:
    """Return a snapshot of recent log lines."""
    with _LOG_LOCK:
        return list(_LOG_BUFFER)[-200:]


# ── Custom formatter ───────────────────────────────────────────────

class EmojiFormatter(logging.Formatter):
    """Formatter that preserves the emoji-prefix style from the original proxy."""

    LEVEL_EMOJI = {
        logging.DEBUG:    "🔍",
        logging.INFO:     "📋",
        logging.WARNING:  "⚠️",
        logging.ERROR:    "❌",
        logging.CRITICAL: "💥",
    }

    def format(self, record: logging.LogRecord) -> str:
        emoji = self.LEVEL_EMOJI.get(record.levelno, "📋")
        # If the message already starts with a known emoji, don't double-prefix
        msg = record.getMessage()
        known_emojis = {"📡", "⚡", "🔐", "🔓", "🚀", "🌐", "🏷️", "📋", "🔑",
                        "🖼️", "📊", "⏱️", "🚫", "💥", "❌", "⚠️", "🔍", "✅",
                        "🔄", "📥", "📤", "🗑️"}
        if msg and msg[:2] in known_emojis:
            emoji = ""
        prefix = f"{emoji} " if emoji else ""
        return f"{prefix}{msg}"


# ── Setup function ─────────────────────────────────────────────────

class _BufferHandler(logging.Handler):
    """Handler that stores log records in the shared buffer."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            with _LOG_LOCK:
                _LOG_BUFFER.append(msg)
        except Exception:
            self.handleError(record)


def setup_logging(level: str = "INFO", log_file: str = "", debug: bool = False) -> logging.Logger:
    """Configure and return the application root logger.

    Args:
        level: Log level string (DEBUG / INFO / WARNING / ERROR).
        log_file: Optional file path for log output.
        debug: If True, force DEBUG level regardless of *level*.
    """
    if debug:
        level = "DEBUG"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger("azure_ai_proxy")
    root_logger.setLevel(numeric_level)

    # Remove any pre-existing handlers
    root_logger.handlers.clear()

    formatter = EmojiFormatter()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(numeric_level)
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root_logger.addHandler(file_handler)

    # Buffer handler (for /logs endpoint)
    buf_handler = _BufferHandler()
    buf_handler.setLevel(logging.DEBUG)  # capture everything in buffer
    buf_handler.setFormatter(formatter)
    root_logger.addHandler(buf_handler)

    # Suppress noisy third-party loggers
    for name in ("aiohttp.access", "litellm", "httpx", "openai", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the ``azure_ai_proxy`` namespace."""
    return logging.getLogger(f"azure_ai_proxy.{name}")

