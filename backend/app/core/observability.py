"""Observability helpers: correlation IDs, structured logs and lightweight metrics.

Design constraints:
- NO clinical content is ever written to logs. Only identifiers, action names,
  durations and status codes.
- Metrics are in-process and dependency-free (a real deployment would export to
  Prometheus/OpenTelemetry; the interface here is deliberately small).
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar

# Correlation id propagated across a request's lifetime.
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")

logger = logging.getLogger("sunudoctor")


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log line (12-factor friendly)."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "correlation_id": correlation_id.get(),
        }
        for key in ("method", "path", "status", "duration_ms", "ip"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("sunudoctor")
    root.handlers = [handler]
    root.setLevel(level)
    root.propagate = False


def new_correlation_id() -> str:
    cid = uuid.uuid4().hex[:16]
    correlation_id.set(cid)
    return cid


class Metrics:
    """Minimal in-process counters and latency histograms."""

    def __init__(self) -> None:
        self.counters: dict[str, int] = defaultdict(int)
        self.latency_ms: dict[str, list[float]] = defaultdict(list)
        self.started_at = time.time()

    def incr(self, key: str, amount: int = 1) -> None:
        self.counters[key] += amount

    def observe(self, key: str, value_ms: float) -> None:
        bucket = self.latency_ms[key]
        bucket.append(value_ms)
        if len(bucket) > 1000:  # bound memory
            del bucket[: len(bucket) - 1000]

    @staticmethod
    def _percentile(values: list[float], pct: float) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        idx = min(len(ordered) - 1, round(pct / 100 * (len(ordered) - 1)))
        return round(ordered[idx], 2)

    def snapshot(self) -> dict:
        return {
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "counters": dict(self.counters),
            "latency_ms": {
                key: {
                    "count": len(vals),
                    "p50": self._percentile(vals, 50),
                    "p95": self._percentile(vals, 95),
                    "p99": self._percentile(vals, 99),
                }
                for key, vals in self.latency_ms.items()
            },
        }


metrics = Metrics()
