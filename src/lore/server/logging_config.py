"""Structured JSON logging configuration for Lore server."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JsonFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields (request_id, org_id, latency_ms, etc.)
        for key in ("request_id", "org_id", "latency_ms", "method", "path", "status"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val

        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """Configure logging based on LOG_FORMAT and LOG_LEVEL env vars."""
    from lore.server.config import settings

    root = logging.getLogger()

    # Avoid duplicate setup
    if getattr(root, "_lore_configured", False):
        return
    root._lore_configured = True  # type: ignore[attr-defined]

    level = getattr(logging, settings.log_level, logging.INFO)
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    if settings.log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
        )

    # Clear existing handlers to avoid duplicates
    root.handlers.clear()
    root.addHandler(handler)
