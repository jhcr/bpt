import os
from typing import Optional
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.boto3sqs import Boto3SQSInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


def init_tracing(
    service_name: str,
    service_version: str = "1.0.0",
    endpoint: Optional[str] = None,
    resource_attributes: Optional[dict] = None
) -> None:
    """
    Initialize OpenTelemetry tracing
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        endpoint: OTLP endpoint URL
        resource_attributes: Additional resource attributes
    """
    
    # Get endpoint from environment if not provided
    if not endpoint:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    if not endpoint:
        # No endpoint configured, use no-op tracer
        trace.set_tracer_provider(trace.NoOpTracerProvider())
        return
    
    # Create resource
    resource_attrs = {
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENV", "development"),
    }
    
    if resource_attributes:
        resource_attrs.update(resource_attributes)
    
    resource = Resource.create(resource_attrs)
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    
    # Add OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=endpoint,
        insecure=endpoint.startswith("http://"),
    )
    
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Set as global tracer provider
    trace.set_tracer_provider(tracer_provider)


def init_metrics(
    service_name: str,
    service_version: str = "1.0.0",
    endpoint: Optional[str] = None,
    resource_attributes: Optional[dict] = None,
    export_interval: int = 60
) -> None:
    """
    Initialize OpenTelemetry metrics
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        endpoint: OTLP endpoint URL
        resource_attributes: Additional resource attributes
        export_interval: Metrics export interval in seconds
    """
    
    # Get endpoint from environment if not provided
    if not endpoint:
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    if not endpoint:
        return
    
    # Create resource
    resource_attrs = {
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENV", "development"),
    }
    
    if resource_attributes:
        resource_attrs.update(resource_attributes)
    
    resource = Resource.create(resource_attrs)
    
    # Create metric exporter
    metric_exporter = OTLPMetricExporter(
        endpoint=endpoint,
        insecure=endpoint.startswith("http://"),
    )
    
    # Create metric reader
    metric_reader = PeriodicExportingMetricReader(
        exporter=metric_exporter,
        export_interval_millis=export_interval * 1000,
    )
    
    # Create meter provider
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    
    # Set as global meter provider
    metrics.set_meter_provider(meter_provider)


def init_instrumentation(
    app = None,
    instrument_fastapi: bool = True,
    instrument_httpx: bool = True,
    instrument_psycopg2: bool = True,
    instrument_redis: bool = True,
    instrument_boto3: bool = True,
    instrument_requests: bool = True,
) -> None:
    """
    Initialize automatic instrumentation for common libraries
    
    Args:
        app: FastAPI app instance to instrument
        instrument_*: Flags to enable/disable specific instrumentations
    """
    
    if instrument_fastapi and app:
        FastAPIInstrumentor.instrument_app(app)
    
    if instrument_httpx:
        HTTPXClientInstrumentor().instrument()
    
    if instrument_psycopg2:
        Psycopg2Instrumentor().instrument()
    
    if instrument_redis:
        RedisInstrumentor().instrument()
    
    if instrument_boto3:
        Boto3SQSInstrumentor().instrument()
    
    if instrument_requests:
        RequestsInstrumentor().instrument()


def get_tracer(name: Optional[str] = None) -> trace.Tracer:
    """Get a tracer instance"""
    return trace.get_tracer(name or __name__)


def get_meter(name: Optional[str] = None) -> metrics.Meter:
    """Get a meter instance"""
    return metrics.get_meter(name or __name__)


class TracingMiddleware:
    """Custom tracing middleware for additional context"""
    
    def __init__(self, app, service_name: str):
        self.app = app
        self.service_name = service_name
        self.tracer = get_tracer(service_name)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request info
        method = scope["method"]
        path = scope["path"]
        
        # Create span
        with self.tracer.start_as_current_span(
            f"{method} {path}",
            kind=trace.SpanKind.SERVER
        ) as span:
            # Add span attributes
            span.set_attribute("http.method", method)
            span.set_attribute("http.url", path)
            span.set_attribute("service.name", self.service_name)
            
            # Add correlation ID if present
            headers = dict(scope.get("headers", []))
            correlation_id = headers.get(b"x-correlation-id")
            if correlation_id:
                span.set_attribute("correlation_id", correlation_id.decode())
            
            # Process request
            try:
                await self.app(scope, receive, send)
                span.set_status(trace.Status(trace.StatusCode.OK))
            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise


def setup_telemetry(
    service_name: str,
    service_version: str = "1.0.0",
    app = None,
    enable_tracing: bool = True,
    enable_metrics: bool = True,
    enable_instrumentation: bool = True,
) -> None:
    """
    Setup complete telemetry stack
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        app: FastAPI app to instrument
        enable_tracing: Enable tracing
        enable_metrics: Enable metrics
        enable_instrumentation: Enable auto-instrumentation
    """
    
    if enable_tracing:
        init_tracing(service_name, service_version)
    
    if enable_metrics:
        init_metrics(service_name, service_version)
    
    if enable_instrumentation:
        init_instrumentation(
            app=app,
            instrument_fastapi=bool(app),
        )