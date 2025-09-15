"""OpenTelemetry utilities for distributed tracing and metrics."""

from .otel import (
    get_meter,
    get_tracer,
    init_metrics,
    init_tracing,
    setup_telemetry,
)

__all__ = [
    "init_tracing",
    "init_metrics",
    "setup_telemetry",
    "get_tracer",
    "get_meter",
]
