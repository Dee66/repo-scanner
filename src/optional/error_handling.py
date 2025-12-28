"""Comprehensive Error Handling and Recovery Framework.

Provides robust error handling, retry mechanisms, recovery strategies,
and graceful degradation for 99.999% operational reliability.
"""

import asyncio
import time
import logging
import functools
import random
from enum import Enum
from typing import Dict, List, Any, Optional, Callable, Awaitable, Type, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import traceback

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for classification and handling."""
    LOW = "low"          # Minor issues, can continue
    MEDIUM = "medium"    # Significant issues, may need recovery
    HIGH = "high"        # Critical issues, may need system intervention
    CRITICAL = "critical"  # System-threatening, immediate action required


class ErrorCategory(Enum):
    """Error categories for targeted handling strategies."""
    NETWORK = "network"              # Network connectivity issues
    EXTERNAL_API = "external_api"     # External service failures
    FILESYSTEM = "filesystem"         # File/directory operations
    CONFIGURATION = "configuration"   # Configuration issues
    VALIDATION = "validation"         # Input validation failures
    RESOURCE = "resource"             # Resource exhaustion
    TIMEOUT = "timeout"               # Operation timeouts
    PERMISSION = "permission"         # Access/permission issues
    CORRUPTION = "corruption"         # Data corruption
    UNKNOWN = "unknown"               # Unclassified errors


@dataclass
class ErrorContext:
    """Context information for error handling and recovery."""
    operation: str
    component: str
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.UNKNOWN
    retry_count: int = 0
    max_retries: int = 3
    recoverable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay between retries
    backoff_factor: float = 2.0  # Exponential backoff multiplier
    jitter: bool = True  # Add random jitter to prevent thundering herd
    retry_on: tuple = (Exception,)  # Exceptions to retry on


@dataclass
class RecoveryStrategy:
    """Strategy for recovering from errors."""
    name: str
    description: str
    can_recover: Callable[[Exception, ErrorContext], bool]
    recovery_action: Callable[[Exception, ErrorContext], Any]
    fallback_action: Optional[Callable[[Exception, ErrorContext], Any]] = None


class ErrorHandler:
    """Centralized error handling and recovery system."""

    def __init__(self):
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}
        self.error_counts: Dict[str, int] = {}
        self.error_history: List[Dict[str, Any]] = []
        self.max_history_size = 1000

    def register_recovery_strategy(self, strategy: RecoveryStrategy):
        """Register a recovery strategy."""
        self.recovery_strategies[strategy.name] = strategy
        logger.info(f"Registered recovery strategy: {strategy.name}")

    def classify_error(self, exception: Exception, context: ErrorContext) -> ErrorContext:
        """Classify error and update context with appropriate handling information."""
        from src.core.exceptions import (
            RepositoryDiscoveryError, AnalysisError, OutputGenerationError,
            ValidationError, ConfigurationError, FileAccessError, GitError
        )

        # Classify by exception type
        if isinstance(exception, (RepositoryDiscoveryError, GitError)):
            context.category = ErrorCategory.FILESYSTEM
            context.severity = ErrorSeverity.HIGH
        elif isinstance(exception, (ValidationError, ConfigurationError)):
            context.category = ErrorCategory.VALIDATION
            context.severity = ErrorSeverity.MEDIUM
        elif isinstance(exception, (FileAccessError, PermissionError, OSError)):
            context.category = ErrorCategory.PERMISSION
            context.severity = ErrorSeverity.HIGH
        elif isinstance(exception, (TimeoutError, asyncio.TimeoutError)):
            context.category = ErrorCategory.TIMEOUT
            context.severity = ErrorSeverity.MEDIUM
        elif isinstance(exception, ConnectionError):
            context.category = ErrorCategory.NETWORK
            context.severity = ErrorSeverity.HIGH
        elif hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
            # HTTP-related errors
            context.category = ErrorCategory.EXTERNAL_API
            if exception.response.status_code >= 500:
                context.severity = ErrorSeverity.HIGH
            else:
                context.severity = ErrorSeverity.MEDIUM
        else:
            context.category = ErrorCategory.UNKNOWN
            context.severity = ErrorSeverity.MEDIUM

        # Update recoverability based on classification
        context.recoverable = self._is_recoverable(context.category, context.severity)

        return context

    def _is_recoverable(self, category: ErrorCategory, severity: ErrorSeverity) -> bool:
        """Determine if an error is recoverable based on category and severity."""
        # Critical errors are never recoverable
        if severity == ErrorSeverity.CRITICAL:
            return False

        # Some categories are inherently recoverable
        recoverable_categories = {
            ErrorCategory.NETWORK,
            ErrorCategory.TIMEOUT,
            ErrorCategory.EXTERNAL_API,
        }

        return category in recoverable_categories

    def log_error(self, exception: Exception, context: ErrorContext):
        """Log error with appropriate level and context."""
        error_info = {
            "timestamp": context.timestamp,
            "operation": context.operation,
            "component": context.component,
            "severity": context.severity.value,
            "category": context.category.value,
            "retry_count": context.retry_count,
            "recoverable": context.recoverable,
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "metadata": context.metadata
        }

        # Add to history
        self.error_history.append(error_info)
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)

        # Update error counts
        error_key = f"{context.component}:{context.category.value}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # Log with appropriate level
        log_message = f"Error in {context.component}.{context.operation}: {exception}"
        if context.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=error_info)
        elif context.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=error_info)
        elif context.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=error_info)
        else:
            logger.info(log_message, extra=error_info)

    def attempt_recovery(self, exception: Exception, context: ErrorContext) -> Any:
        """Attempt to recover from an error using registered strategies."""
        if not context.recoverable:
            logger.warning(f"Error not recoverable: {context.category.value}")
            raise exception

        # Find applicable recovery strategy
        for strategy in self.recovery_strategies.values():
            if strategy.can_recover(exception, context):
                logger.info(f"Attempting recovery with strategy: {strategy.name}")
                try:
                    result = strategy.recovery_action(exception, context)
                    logger.info(f"Recovery successful with strategy: {strategy.name}")
                    return result
                except Exception as recovery_error:
                    logger.warning(f"Recovery strategy {strategy.name} failed: {recovery_error}")
                    if strategy.fallback_action:
                        try:
                            result = strategy.fallback_action(exception, context)
                            logger.info(f"Fallback recovery successful with strategy: {strategy.name}")
                            return result
                        except Exception as fallback_error:
                            logger.error(f"Fallback recovery failed: {fallback_error}")
                    continue

        # No recovery strategy worked
        logger.error(f"No recovery strategy succeeded for error: {exception}")
        raise exception

    def get_error_metrics(self) -> Dict[str, Any]:
        """Get error handling metrics."""
        return {
            "total_errors": len(self.error_history),
            "error_counts_by_category": dict(self.error_counts),
            "recent_errors": self.error_history[-10:] if self.error_history else [],
            "recovery_strategies": list(self.recovery_strategies.keys())
        }


# Global error handler instance
_error_handler = ErrorHandler()

def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    return _error_handler


class RetryMechanism:
    """Retry mechanism with exponential backoff and jitter."""

    def __init__(self, config: RetryConfig):
        self.config = config

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt number."""
        delay = min(self.config.base_delay * (self.config.backoff_factor ** attempt), self.config.max_delay)

        if self.config.jitter:
            # Add random jitter (±25% of delay)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if we should retry based on exception and attempt count."""
        if attempt >= self.config.max_attempts:
            return False

        return isinstance(exception, self.config.retry_on)

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(self.config.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if not self.should_retry(e, attempt):
                    break

                if attempt < self.config.max_attempts:
                    delay = self.calculate_delay(attempt)
                    logger.info(f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1}/{self.config.max_attempts + 1})")
                    time.sleep(delay)

        # All retries exhausted
        raise last_exception

    async def execute_with_retry_async(self, func: Callable[..., Awaitable], *args, **kwargs) -> Any:
        """Execute async function with retry logic."""
        last_exception = None

        for attempt in range(self.config.max_attempts + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if not self.should_retry(e, attempt):
                    break

                if attempt < self.config.max_attempts:
                    delay = self.calculate_delay(attempt)
                    logger.info(f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1}/{self.config.max_attempts + 1})")
                    await asyncio.sleep(delay)

        # All retries exhausted
        raise last_exception


# Decorator for synchronous functions
def with_error_handling(operation: str, component: str, retry_config: Optional[RetryConfig] = None):
    """Decorator to add comprehensive error handling to synchronous functions."""
    def decorator(func: Callable) -> Callable:
        error_handler = get_error_handler()
        retry_mechanism = RetryMechanism(retry_config or RetryConfig())

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = ErrorContext(operation=operation, component=component)

            try:
                # Execute with retry if configured
                return retry_mechanism.execute_with_retry(func, *args, **kwargs)
            except Exception as e:
                # Classify and log error
                context = error_handler.classify_error(e, context)
                error_handler.log_error(e, context)

                # Attempt recovery
                try:
                    return error_handler.attempt_recovery(e, context)
                except Exception:
                    # Recovery failed, re-raise original exception
                    raise e

        return wrapper

    return decorator


# Decorator for asynchronous functions
def async_with_error_handling(operation: str, component: str, retry_config: Optional[RetryConfig] = None):
    """Decorator to add comprehensive error handling to asynchronous functions."""
    def decorator(func: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        error_handler = get_error_handler()
        retry_mechanism = RetryMechanism(retry_config or RetryConfig())

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            context = ErrorContext(operation=operation, component=component)

            try:
                # Execute with retry if configured
                return await retry_mechanism.execute_with_retry_async(func, *args, **kwargs)
            except Exception as e:
                # Classify and log error
                context = error_handler.classify_error(e, context)
                error_handler.log_error(e, context)

                # Attempt recovery
                try:
                    return error_handler.attempt_recovery(e, context)
                except Exception:
                    # Recovery failed, re-raise original exception
                    raise e

        return wrapper

    return decorator


# Context manager for manual error handling
@asynccontextmanager
async def error_handling_context(operation: str, component: str, retry_config: Optional[RetryConfig] = None):
    """Context manager for comprehensive error handling."""
    error_handler = get_error_handler()
    context = ErrorContext(operation=operation, component=component)

    try:
        yield context
    except Exception as e:
        # Classify and log error
        context = error_handler.classify_error(e, context)
        error_handler.log_error(e, context)

        # Attempt recovery
        try:
            # For context managers, we can't return a value, so we just log success
            error_handler.attempt_recovery(e, context)
        except Exception:
            # Recovery failed, re-raise original exception
            raise e


# Pre-configured retry configurations for common scenarios
NETWORK_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    max_delay=30.0,
    backoff_factor=2.0,
    retry_on=(ConnectionError, TimeoutError, OSError)
)

API_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=20.0,
    backoff_factor=1.5,
    retry_on=(Exception,)  # Broad retry for API calls
)
FILESYSTEM_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    base_delay=0.5,
    max_delay=5.0,
    backoff_factor=2.0,
    retry_on=(OSError, PermissionError)
)
