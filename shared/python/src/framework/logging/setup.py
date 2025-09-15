# Context variables for correlation and trace IDs
import contextvars
import logging
import sys

import structlog
from pythonjsonlogger import jsonlogger
from structlog.stdlib import LoggerFactory


def setup_logging(
    service_name: str,
    level: str = "INFO",
    format_type: str = "json",  # "json" or "console"
    correlation_id_header: str = "X-Correlation-ID",
    trace_id_header: str = "X-Trace-ID",
) -> None:
    """
    Set up structured logging for the service

    Args:
        service_name: Name of the service for log context
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        format_type: "json" for production, "console" for development
        correlation_id_header: Header name for correlation ID
        trace_id_header: Header name for trace ID
    """

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )

    # Configure processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_service_context(service_name),
        add_correlation_context(),
    ]

    if format_type == "console":
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )

    # Set up JSON logging for non-structlog loggers
    if format_type == "json":
        pass  # python-json-logger handles JSON formatting via handler below

        # Configure root logger with JSON formatter
        root_logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        handler.setFormatter(formatter)
        root_logger.handlers = [handler]


def add_service_context(service_name: str):
    """Add service context to all log entries"""

    def processor(logger, method_name, event_dict):
        event_dict["service"] = service_name
        return event_dict

    return processor


def add_correlation_context():
    """Add correlation and trace IDs from context"""

    def processor(logger, method_name, event_dict):
        # Try to get context from various sources

        # Check for correlation ID context variable
        try:
            correlation_id = _correlation_id_var.get()
            if correlation_id:
                event_dict["correlation_id"] = correlation_id
        except LookupError:
            pass

        # Check for trace ID context variable
        try:
            trace_id = _trace_id_var.get()
            if trace_id:
                event_dict["trace_id"] = trace_id
        except LookupError:
            pass

        return event_dict

    return processor


_correlation_id_var = contextvars.ContextVar("correlation_id", default=None)
_trace_id_var = contextvars.ContextVar("trace_id", default=None)


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context"""
    _correlation_id_var.set(correlation_id)


def set_trace_id(trace_id: str) -> None:
    """Set trace ID in context"""
    _trace_id_var.set(trace_id)


def get_correlation_id() -> str | None:
    """Get correlation ID from context"""
    try:
        return _correlation_id_var.get()
    except LookupError:
        return None


def get_trace_id() -> str | None:
    """Get trace ID from context"""
    try:
        return _trace_id_var.get()
    except LookupError:
        return None


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class CorrelationMiddleware:
    """Middleware to extract and set correlation/trace IDs from HTTP headers"""

    def __init__(
        self,
        app,
        correlation_header: str = "X-Correlation-ID",
        trace_header: str = "X-Trace-ID",
        generate_correlation: bool = True,
    ):
        self.app = app
        self.correlation_header = correlation_header.lower()
        self.trace_header = trace_header.lower()
        self.generate_correlation = generate_correlation

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import uuid

        # Extract headers from ASGI scope
        headers = {name.decode(): value.decode() for name, value in scope.get("headers", [])}
        correlation_id = headers.get(self.correlation_header)
        trace_id = headers.get(self.trace_header)

        # Generate correlation ID if missing and requested
        if not correlation_id and self.generate_correlation:
            correlation_id = str(uuid.uuid4())

        # Set context variables
        if correlation_id:
            set_correlation_id(correlation_id)
        if trace_id:
            set_trace_id(trace_id)

        await self.app(scope, receive, send)


def create_request_logger(request) -> structlog.BoundLogger:
    """Create a logger bound with request context"""
    logger = get_logger()

    # Add request information
    logger = logger.bind(
        method=request.method,
        path=request.url.path,
        query=str(request.url.query) if request.url.query else None,
        user_agent=request.headers.get("user-agent"),
        remote_addr=request.client.host if request.client else None,
    )

    # Add correlation context if available
    correlation_id = get_correlation_id()
    if correlation_id:
        logger = logger.bind(correlation_id=correlation_id)

    trace_id = get_trace_id()
    if trace_id:
        logger = logger.bind(trace_id=trace_id)

    return logger
