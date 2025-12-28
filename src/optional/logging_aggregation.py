"""Enhanced logging system with aggregation and correlation capabilities."""

import logging
import json
import uuid
import time
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from pathlib import Path

class CorrelationContext:
    """Context for log correlation across requests/components."""

    def __init__(self, correlation_id: Optional[str] = None, parent_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.parent_id = parent_id
        self.start_time = time.time()
        self.metadata: Dict[str, Any] = {}

    def add_metadata(self, key: str, value: Any):
        """Add metadata to the correlation context."""
        self.metadata[key] = value

    def get_context(self) -> Dict[str, Any]:
        """Get the full correlation context."""
        return {
            "correlation_id": self.correlation_id,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "metadata": self.metadata
        }

# Thread-local storage for correlation context
_correlation_context = threading.local()

def get_correlation_context() -> Optional[CorrelationContext]:
    """Get the current correlation context."""
    return getattr(_correlation_context, 'context', None)

def set_correlation_context(context: CorrelationContext):
    """Set the current correlation context."""
    _correlation_context.context = context

def create_correlation_context(parent_id: Optional[str] = None) -> CorrelationContext:
    """Create a new correlation context."""
    context = CorrelationContext(parent_id=parent_id)
    set_correlation_context(context)
    return context

def clear_correlation_context():
    """Clear the current correlation context."""
    if hasattr(_correlation_context, 'context'):
        delattr(_correlation_context, 'context')

class StructuredLogger(logging.Logger):
    """Enhanced logger with structured logging and correlation support."""

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False):
        # Add correlation context to extra
        if extra is None:
            extra = {}

        correlation_ctx = get_correlation_context()
        if correlation_ctx:
            extra['correlation'] = correlation_ctx.get_context()

        # Add structured fields
        extra.update({
            'timestamp': datetime.utcnow().isoformat(),
            'level': logging.getLevelName(level),
            'component': getattr(self, '_component', 'unknown')
        })

        super()._log(level, msg, args, exc_info, extra, stack_info)

class LogAggregator:
    """Aggregates and correlates logs from different components."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
        self.max_logs = 10000  # Keep last 10k logs in memory
        self.lock = threading.Lock()
        self.correlation_index: Dict[str, List[Dict[str, Any]]] = {}

    def add_log_entry(self, log_entry: Dict[str, Any]):
        """Add a log entry to the aggregator."""
        with self.lock:
            # Add to main log list
            self.logs.append(log_entry)

            # Maintain max size
            if len(self.logs) > self.max_logs:
                removed_entry = self.logs.pop(0)
                # Remove from correlation index if needed
                if 'correlation' in removed_entry and removed_entry['correlation']:
                    corr_id = removed_entry['correlation'].get('correlation_id')
                    if corr_id and corr_id in self.correlation_index:
                        self.correlation_index[corr_id] = [
                            entry for entry in self.correlation_index[corr_id]
                            if entry is not removed_entry
                        ]
                        if not self.correlation_index[corr_id]:
                            del self.correlation_index[corr_id]

            # Add to correlation index
            if 'correlation' in log_entry and log_entry['correlation']:
                corr_id = log_entry['correlation'].get('correlation_id')
                if corr_id:
                    if corr_id not in self.correlation_index:
                        self.correlation_index[corr_id] = []
                    self.correlation_index[corr_id].append(log_entry)

    def get_logs_by_correlation(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get all logs for a specific correlation ID."""
        with self.lock:
            return self.correlation_index.get(correlation_id, []).copy()

    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent logs."""
        with self.lock:
            return self.logs[-limit:].copy()

    def get_logs_by_component(self, component: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs for a specific component."""
        with self.lock:
            component_logs = [log for log in self.logs if log.get('component') == component]
            return component_logs[-limit:]

    def get_logs_by_level(self, level: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs for a specific level."""
        with self.lock:
            level_logs = [log for log in self.logs if log.get('level') == level]
            return level_logs[-limit:]

    def search_logs(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search logs containing the query string."""
        with self.lock:
            matching_logs = []
            query_lower = query.lower()
            for log in reversed(self.logs):  # Search from most recent
                if len(matching_logs) >= limit:
                    break
                message = str(log.get('message', '')).lower()
                if query_lower in message:
                    matching_logs.append(log)
            return matching_logs

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        # Create the base log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'component': getattr(record, 'component', 'unknown')
        }

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # Add correlation context
        if hasattr(record, 'correlation'):
            log_entry['correlation'] = record.correlation

        # Add any extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, default=str)

class LogAggregatorHandler(logging.Handler):
    """Logging handler that sends logs to the aggregator."""

    def __init__(self, aggregator: LogAggregator):
        super().__init__()
        self.aggregator = aggregator

    def emit(self, record):
        try:
            # Format the record
            formatter = JSONFormatter()
            log_entry_str = formatter.format(record)

            # Parse back to dict for aggregation
            log_entry = json.loads(log_entry_str)

            # Add to aggregator
            self.aggregator.add_log_entry(log_entry)
        except Exception:
            # Don't let logging errors break the application
            pass

# Global log aggregator instance
_log_aggregator = None

def get_log_aggregator() -> LogAggregator:
    """Get the global log aggregator instance."""
    global _log_aggregator
    if _log_aggregator is None:
        _log_aggregator = LogAggregator()
    return _log_aggregator

def setup_structured_logging(component: str = "unknown") -> logging.Logger:
    """Set up structured logging for a component."""
    logger = logging.getLogger(f"repo_scanner.{component}")

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Set component
    logger._component = component

    # Create aggregator handler
    aggregator = get_log_aggregator()
    aggregator_handler = LogAggregatorHandler(aggregator)
    aggregator_handler.setLevel(logging.DEBUG)

    # Create console handler with JSON formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    console_handler.setLevel(logging.INFO)

    # Add handlers
    logger.addHandler(aggregator_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)

    return logger

def create_correlation_middleware():
    """Create middleware for adding correlation IDs to requests."""
    from fastapi import Request, Response
    import time

    async def correlation_middleware(request: Request, call_next):
        # Create correlation context for this request
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        context = CorrelationContext(correlation_id=correlation_id)
        context.add_metadata('method', request.method)
        context.add_metadata('path', str(request.url.path))
        context.add_metadata('user_agent', request.headers.get('User-Agent', 'unknown'))

        # Set context
        set_correlation_context(context)

        # Add correlation ID to response headers
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        response.headers['X-Correlation-ID'] = correlation_id
        response.headers['X-Request-Duration'] = str(duration)

        # Clear context
        clear_correlation_context()

        return response

    return correlation_middleware

# Context manager for correlation
class correlation_context:
    """Context manager for correlation contexts."""

    def __init__(self, correlation_id: Optional[str] = None, parent_id: Optional[str] = None):
        self.correlation_id = correlation_id
        self.parent_id = parent_id
        self.previous_context = None

    def __enter__(self):
        self.previous_context = get_correlation_context()
        context = CorrelationContext(
            correlation_id=self.correlation_id,
            parent_id=self.parent_id
        )
        set_correlation_context(context)
        return context

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.previous_context:
            set_correlation_context(self.previous_context)
        else:
            clear_correlation_context()