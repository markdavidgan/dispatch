"""Structured logging — JSON in containers, pretty in local dev.

Detection: container if HOME=/home/dispatch (set by Dockerfile ENV).
"""
import logging
import os
import sys
import json
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    if os.environ.get("HOME") == "/home/dispatch":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
