"""
Monitoring, metrics, and structured logging utilities
"""

import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from functools import wraps

from fastapi import Request, Response
from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               generate_latest)
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


# Configure structured logging
class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON

        Args:
            record: Log record

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging():
    """
    Setup structured logging for the application
    """
    # Get root logger
    logger = logging.getLogger()

    # Set log level from settings
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()

    # Use JSON formatter if not in debug mode
    if not settings.DEBUG:
        console_handler.setFormatter(JSONFormatter())
    else:
        # Use simple format in debug
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get logger with structured logging

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger
    """
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs):
    """
    Log message with additional context

    Args:
        logger: Logger instance
        level: Log level (info, warning, error, etc.)
        message: Log message
        **kwargs: Additional context fields
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra=kwargs)


# Prometheus Metrics
if settings.ENABLE_METRICS:
    # Request metrics
    REQUEST_COUNT = Counter(
        "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
    )

    REQUEST_DURATION = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "endpoint"],
    )

    # RAG metrics
    RAG_QUERY_COUNT = Counter("rag_queries_total", "Total RAG queries", ["status"])

    RAG_QUERY_DURATION = Histogram(
        "rag_query_duration_seconds",
        "RAG query duration in seconds",
        buckets=[0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0],
    )

    RAG_RETRIEVAL_COUNT = Histogram(
        "rag_retrieval_chunks",
        "Number of chunks retrieved",
        buckets=[1, 5, 10, 15, 20, 30, 50],
    )

    RAG_TOKEN_COUNT = Histogram(
        "rag_tokens_used",
        "Number of tokens used in generation",
        buckets=[100, 500, 1000, 2000, 4000, 8000],
    )

    # Document metrics
    DOCUMENT_UPLOAD_COUNT = Counter(
        "documents_uploaded_total", "Total documents uploaded", ["file_type", "status"]
    )

    DOCUMENT_PROCESSING_DURATION = Histogram(
        "document_processing_duration_seconds",
        "Document processing duration in seconds",
        buckets=[1, 5, 10, 30, 60, 120, 300],
    )

    DOCUMENT_CHUNK_COUNT = Histogram(
        "document_chunks_created",
        "Number of chunks created per document",
        buckets=[10, 50, 100, 200, 500, 1000],
    )

    # System metrics
    ACTIVE_CONNECTIONS = Gauge(
        "active_websocket_connections", "Number of active WebSocket connections"
    )


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect HTTP metrics
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process request and collect metrics

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        if not settings.ENABLE_METRICS:
            return await call_next(request)

        # Skip metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)

        # Start timer
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).inc()

        REQUEST_DURATION.labels(
            method=request.method, endpoint=request.url.path
        ).observe(duration)

        return response


async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus metrics endpoint

    Args:
        request: FastAPI request

    Returns:
        Metrics in Prometheus format
    """
    if not settings.ENABLE_METRICS:
        return Response(content="Metrics disabled", status_code=404)

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Performance monitoring decorators
def monitor_performance(metric_name: str = "operation"):
    """
    Decorator to monitor function performance

    Args:
        metric_name: Name for logging

    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                log_with_context(
                    logger,
                    "info",
                    f"{metric_name} completed",
                    function=func.__name__,
                    duration=duration,
                    status="success",
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                log_with_context(
                    logger,
                    "error",
                    f"{metric_name} failed",
                    function=func.__name__,
                    duration=duration,
                    status="error",
                    error=str(e),
                )

                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                log_with_context(
                    logger,
                    "info",
                    f"{metric_name} completed",
                    function=func.__name__,
                    duration=duration,
                    status="success",
                )

                return result

            except Exception as e:
                duration = time.time() - start_time

                log_with_context(
                    logger,
                    "error",
                    f"{metric_name} failed",
                    function=func.__name__,
                    duration=duration,
                    status="error",
                    error=str(e),
                )

                raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


@asynccontextmanager
async def track_rag_query(query: str):
    """
    Context manager to track RAG query metrics

    Args:
        query: User query

    Yields:
        Metrics dictionary
    """
    start_time = time.time()
    metrics = {
        "query": query,
        "start_time": start_time,
        "chunks_retrieved": 0,
        "tokens_used": 0,
        "status": "success",
    }

    try:
        yield metrics

        # Record success metrics
        duration = time.time() - start_time

        if settings.ENABLE_METRICS:
            RAG_QUERY_COUNT.labels(status="success").inc()
            RAG_QUERY_DURATION.observe(duration)
            RAG_RETRIEVAL_COUNT.observe(metrics["chunks_retrieved"])
            RAG_TOKEN_COUNT.observe(metrics["tokens_used"])

        # Log
        logger = get_logger("rag")
        log_with_context(
            logger,
            "info",
            "RAG query completed",
            query_length=len(query),
            duration=duration,
            chunks_retrieved=metrics["chunks_retrieved"],
            tokens_used=metrics["tokens_used"],
        )

    except Exception as e:
        # Record failure metrics
        duration = time.time() - start_time

        if settings.ENABLE_METRICS:
            RAG_QUERY_COUNT.labels(status="error").inc()
            RAG_QUERY_DURATION.observe(duration)

        # Log error
        logger = get_logger("rag")
        log_with_context(
            logger,
            "error",
            "RAG query failed",
            query_length=len(query),
            duration=duration,
            error=str(e),
        )

        metrics["status"] = "error"
        raise


@asynccontextmanager
async def track_document_processing(document_id: int, filename: str):
    """
    Context manager to track document processing metrics

    Args:
        document_id: Document ID
        filename: Document filename

    Yields:
        Metrics dictionary
    """
    start_time = time.time()
    metrics = {
        "document_id": document_id,
        "filename": filename,
        "start_time": start_time,
        "chunks_created": 0,
        "status": "success",
    }

    try:
        yield metrics

        # Record success metrics
        duration = time.time() - start_time

        if settings.ENABLE_METRICS:
            file_ext = filename.split(".")[-1].lower()
            DOCUMENT_UPLOAD_COUNT.labels(file_type=file_ext, status="completed").inc()
            DOCUMENT_PROCESSING_DURATION.observe(duration)
            DOCUMENT_CHUNK_COUNT.observe(metrics["chunks_created"])

        # Log
        logger = get_logger("document_processing")
        log_with_context(
            logger,
            "info",
            "Document processing completed",
            document_id=document_id,
            filename=filename,
            duration=duration,
            chunks_created=metrics["chunks_created"],
        )

    except Exception as e:
        # Record failure metrics
        duration = time.time() - start_time

        if settings.ENABLE_METRICS:
            file_ext = filename.split(".")[-1].lower()
            DOCUMENT_UPLOAD_COUNT.labels(file_type=file_ext, status="failed").inc()

        # Log error
        logger = get_logger("document_processing")
        log_with_context(
            logger,
            "error",
            "Document processing failed",
            document_id=document_id,
            filename=filename,
            duration=duration,
            error=str(e),
        )

        metrics["status"] = "error"
        raise


def track_websocket_connection(connected: bool):
    """
    Track WebSocket connection state

    Args:
        connected: True if connecting, False if disconnecting
    """
    if not settings.ENABLE_METRICS:
        return

    if connected:
        ACTIVE_CONNECTIONS.inc()
    else:
        ACTIVE_CONNECTIONS.dec()


# Initialize logging on module import
logger = setup_logging()
