"""Distributed tracing utilities for Repository Intelligence Scanner."""

import os
import logging
from typing import Optional

# Optional tracing imports
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False

logger = logging.getLogger(__name__)

def setup_distributed_tracing(service_name: str = "repo-scanner") -> bool:
    """
    Set up distributed tracing with OpenTelemetry.

    Returns True if tracing was successfully configured, False otherwise.
    """
    if not TRACING_AVAILABLE:
        logger.debug("OpenTelemetry not available, tracing disabled")
        return False

    if os.getenv('REPO_SCANNER_ENABLE_TRACING', 'false').lower() != 'true':
        logger.debug("Tracing not enabled via environment variable")
        return False

    try:
        # Set up tracing
        trace.set_tracer_provider(TracerProvider())
        tracer_provider = trace.get_tracer_provider()

        # Configure exporter based on environment
        exporter_type = os.getenv('REPO_SCANNER_TRACING_EXPORTER', 'console').lower()

        if exporter_type == 'jaeger':
            jaeger_host = os.getenv('JAEGER_HOST', 'localhost')
            jaeger_port = int(os.getenv('JAEGER_PORT', '14268'))
            exporter = JaegerExporter(
                agent_host_name=jaeger_host,
                agent_port=jaeger_port,
            )
            logger.info(f"Configured Jaeger exporter: {jaeger_host}:{jaeger_port}")
        elif exporter_type == 'console':
            exporter = ConsoleSpanExporter()
            logger.info("Configured console exporter for tracing")
        else:
            logger.warning(f"Unknown tracing exporter: {exporter_type}, using console")
            exporter = ConsoleSpanExporter()

        # Add span processor
        span_processor = BatchSpanProcessor(exporter)
        tracer_provider.add_span_processor(span_processor)

        # Set service name
        resource = trace.get_tracer_provider().resource
        if hasattr(resource, 'attributes'):
            resource.attributes.update({"service.name": service_name})

        logger.info(f"Distributed tracing enabled with {exporter_type} exporter")
        return True

    except Exception as e:
        logger.error(f"Failed to set up distributed tracing: {e}")
        return False

def get_tracer(name: str) -> Optional[object]:
    """Get a tracer instance if tracing is available and enabled."""
    if not TRACING_AVAILABLE or not os.getenv('REPO_SCANNER_ENABLE_TRACING', 'false').lower() == 'true':
        return None

    return trace.get_tracer(name)

def instrument_fastapi_app(app) -> bool:
    """Instrument a FastAPI app for tracing if available."""
    if not TRACING_AVAILABLE or not os.getenv('REPO_SCANNER_ENABLE_TRACING', 'false').lower() == 'true':
        return False

    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI app instrumented for tracing")
        return True
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI app: {e}")
        return False