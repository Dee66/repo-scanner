"""Circuit Breaker Pattern Implementation for External Dependencies.

Provides resilience against cascading failures by temporarily stopping
calls to failing external services with automatic recovery mechanisms.
"""

import asyncio
import time
import logging
import threading
from enum import Enum
from typing import Dict, Any, Optional, Callable, Awaitable, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import functools

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before trying recovery
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures
    success_threshold: int = 3  # Successes needed to close circuit in half-open
    timeout: float = 30.0  # Request timeout
    name: str = "default"  # Circuit breaker name for logging


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker performance."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """Circuit breaker implementation with configurable behavior."""

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self.half_open_successes = 0
        self.last_state_change = time.time()
        self._lock = threading.RLock()

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        return (time.time() - self.last_state_change) >= self.config.recovery_timeout

    def _record_success(self):
        """Record a successful request."""
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.last_success_time = time.time()

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.half_open_successes += 1
                if self.half_open_successes >= self.config.success_threshold:
                    self._change_state(CircuitBreakerState.CLOSED)
                    self.half_open_successes = 0
            elif self.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success
                pass

    def _record_failure(self, exception: Exception):
        """Record a failed request."""
        with self._lock:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = time.time()

            if self.state == CircuitBreakerState.CLOSED:
                # Check if we should open the circuit
                if self.metrics.failed_requests >= self.config.failure_threshold:
                    self._change_state(CircuitBreakerState.OPEN)
            elif self.state == CircuitBreakerState.HALF_OPEN:
                # Any failure in half-open state sends us back to open
                self._change_state(CircuitBreakerState.OPEN)
                self.half_open_successes = 0

    def _change_state(self, new_state: CircuitBreakerState):
        """Change circuit breaker state."""
        with self._lock:
            old_state = self.state
            self.state = new_state
            self.last_state_change = time.time()
            self.metrics.state_changes += 1

            logger.info(f"Circuit breaker '{self.config.name}' state change: {old_state.value} -> {new_state.value}")

    def _call_with_circuit_breaker(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        # Check if circuit is open
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._change_state(CircuitBreakerState.HALF_OPEN)
            else:
                self.metrics.rejected_requests += 1
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.config.name}' is OPEN. "
                    f"Next retry in {self.config.recovery_timeout - (time.time() - self.last_state_change):.1f}s"
                )

        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.config.expected_exception as e:
            self._record_failure(e)
            raise

    async def _call_async_with_circuit_breaker(self, func: Callable[..., Awaitable], *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection."""
        # Check if circuit is open
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._change_state(CircuitBreakerState.HALF_OPEN)
            else:
                self.metrics.rejected_requests += 1
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.config.name}' is OPEN. "
                    f"Next retry in {self.config.recovery_timeout - (time.time() - self.last_state_change):.1f}s"
                )

        # Execute the function
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.config.expected_exception as e:
            self._record_failure(e)
            raise

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Synchronous call with circuit breaker protection."""
        return self._call_with_circuit_breaker(func, *args, **kwargs)

    async def call_async(self, func: Callable[..., Awaitable], *args, **kwargs) -> Any:
        """Asynchronous call with circuit breaker protection."""
        return await self._call_async_with_circuit_breaker(func, *args, **kwargs)

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        with self._lock:
            return {
                "name": self.config.name,
                "state": self.state.value,
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "recovery_timeout": self.config.recovery_timeout,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout
                },
                "metrics": {
                    "total_requests": self.metrics.total_requests,
                    "successful_requests": self.metrics.successful_requests,
                    "failed_requests": self.metrics.failed_requests,
                    "rejected_requests": self.metrics.rejected_requests,
                    "state_changes": self.metrics.state_changes,
                    "success_rate": (self.metrics.successful_requests / max(self.metrics.total_requests, 1)),
                    "last_failure_time": self.metrics.last_failure_time,
                    "last_success_time": self.metrics.last_success_time,
                    "time_since_last_state_change": time.time() - self.last_state_change
                }
            }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()

    def get_or_create(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Get existing circuit breaker or create new one."""
        with self._lock:
            if name not in self.breakers:
                config.name = name
                self.breakers[name] = CircuitBreaker(config)
            return self.breakers[name]

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        with self._lock:
            return {name: breaker.get_metrics() for name, breaker in self.breakers.items()}

    def reset_all(self):
        """Reset all circuit breakers to closed state."""
        with self._lock:
            for breaker in self.breakers.values():
                breaker.state = CircuitBreakerState.CLOSED
                breaker.metrics = CircuitBreakerMetrics()
                breaker.half_open_successes = 0
                breaker.last_state_change = time.time()


# Global registry instance
_circuit_breaker_registry = CircuitBreakerRegistry()

def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    return _circuit_breaker_registry


# Decorator for synchronous functions
def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """Decorator to apply circuit breaker to synchronous functions."""
    if config is None:
        config = CircuitBreakerConfig()

    def decorator(func: Callable) -> Callable:
        breaker = _circuit_breaker_registry.get_or_create(name, config)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        # Attach breaker for testing/debugging
        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator


# Decorator for asynchronous functions
def async_circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """Decorator to apply circuit breaker to asynchronous functions."""
    if config is None:
        config = CircuitBreakerConfig()

    def decorator(func: Callable[..., Awaitable]) -> Callable[..., Awaitable]:
        breaker = _circuit_breaker_registry.get_or_create(name, config)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call_async(func, *args, **kwargs)

        # Attach breaker for testing/debugging
        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator


# Context manager for manual circuit breaker usage
@asynccontextmanager
async def circuit_breaker_context(name: str, config: CircuitBreakerConfig = None):
    """Context manager for circuit breaker protection."""
    if config is None:
        config = CircuitBreakerConfig()

    breaker = _circuit_breaker_registry.get_or_create(name, config)

    # Check if circuit is open
    if breaker.state == CircuitBreakerState.OPEN:
        if breaker._should_attempt_reset():
            breaker._change_state(CircuitBreakerState.HALF_OPEN)
        else:
            breaker.metrics.rejected_requests += 1
            raise CircuitBreakerOpenException(
                f"Circuit breaker '{name}' is OPEN. "
                f"Next retry in {config.recovery_timeout - (time.time() - breaker.last_state_change):.1f}s"
            )

    try:
        yield breaker
    except config.expected_exception as e:
        breaker._record_failure(e)
        raise
    else:
        breaker._record_success()


# Pre-configured circuit breakers for common external dependencies
GIT_OPERATIONS_CONFIG = CircuitBreakerConfig(
    name="git_operations",
    failure_threshold=3,  # Git operations are more reliable, higher threshold
    recovery_timeout=120.0,  # 2 minutes recovery time
    timeout=300.0,  # 5 minutes for git operations
    expected_exception=(OSError, Exception)  # Git operations can raise various exceptions
)

HTTP_REQUESTS_CONFIG = CircuitBreakerConfig(
    name="http_requests",
    failure_threshold=5,  # HTTP requests can be flaky
    recovery_timeout=60.0,  # 1 minute recovery time
    timeout=30.0,  # 30 seconds for HTTP requests
    expected_exception=(Exception,)  # Broad exception catching for HTTP
)

API_CALLS_CONFIG = CircuitBreakerConfig(
    name="api_calls",
    failure_threshold=3,  # API calls are critical
    recovery_timeout=30.0,  # 30 seconds recovery time
    timeout=15.0,  # 15 seconds for API calls
    expected_exception=(Exception,)  # Broad exception catching for APIs
)
