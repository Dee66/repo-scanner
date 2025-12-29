"""Request timeouts and resource limits for operational stability."""

import os
import signal
import time
import threading
import logging
from contextlib import contextmanager
from typing import Optional, Callable, Any
import psutil
import resource

from .resource_manager import get_resource_manager, start_global_resource_monitoring, stop_global_resource_monitoring

logger = logging.getLogger(__name__)

# Timeout and resource limit configuration
TIMEOUT_CONFIG = {
    "git_clone_timeout": int(os.getenv("REPO_SCANNER_GIT_CLONE_TIMEOUT", "300")),  # 5 minutes
    "analysis_timeout": int(os.getenv("REPO_SCANNER_ANALYSIS_TIMEOUT", "600")),   # 10 minutes
    "api_request_timeout": int(os.getenv("REPO_SCANNER_API_TIMEOUT", "60")),      # 1 minute
    "health_check_timeout": int(os.getenv("REPO_SCANNER_HEALTH_TIMEOUT", "30")),  # 30 seconds
}

RESOURCE_LIMITS = {
    "max_memory_mb": int(os.getenv("REPO_SCANNER_MAX_MEMORY_MB", "2048")),  # 2GB
    "max_cpu_percent": int(os.getenv("REPO_SCANNER_MAX_CPU_PERCENT", "80")),  # 80%
    "max_file_descriptors": int(os.getenv("REPO_SCANNER_MAX_FD", "1024")),    # 1024 files
}

class TimeoutError(Exception):
    """Exception raised when an operation times out."""
    pass

class ResourceLimitError(Exception):
    """Exception raised when resource limits are exceeded."""
    pass

def set_process_limits():
    """Set resource limits for the current process."""
    try:
        # Set memory limit (soft limit)
        memory_bytes = RESOURCE_LIMITS["max_memory_mb"] * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes * 2))

        # Set file descriptor limit
        resource.setrlimit(resource.RLIMIT_NOFILE, (RESOURCE_LIMITS["max_file_descriptors"],
                                                   RESOURCE_LIMITS["max_file_descriptors"] * 2))

        # Set CPU time limit (prevent infinite loops)
        cpu_seconds = TIMEOUT_CONFIG["analysis_timeout"] * 2  # Allow 2x analysis time
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds * 2))

    except (OSError, ValueError) as e:
        # Resource limits may not be available on all platforms
        pass

def check_resource_usage() -> dict:
    """Check current resource usage against limits."""
    try:
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=1.0)

        return {
            "memory_mb": memory_mb,
            "cpu_percent": cpu_percent,
            "memory_limit_exceeded": memory_mb > RESOURCE_LIMITS["max_memory_mb"],
            "cpu_limit_exceeded": cpu_percent > RESOURCE_LIMITS["max_cpu_percent"],
        }
    except Exception:
        return {
            "memory_mb": 0,
            "cpu_percent": 0,
            "memory_limit_exceeded": False,
            "cpu_limit_exceeded": False,
        }

@contextmanager
def timeout_context(seconds: int, operation_name: str = "operation"):
    """Context manager for operation timeouts."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"{operation_name} timed out after {seconds} seconds")

    # Check if we're in the main thread - signals only work there
    if threading.current_thread() is threading.main_thread():
        # Use signal-based timeout for main thread
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(seconds)

        try:
            yield
        finally:
            # Clean up the timeout
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # For worker threads, we need a different approach since signals don't work well
        # Use a flag-based approach with periodic checking
        timeout_reached = threading.Event()
        exception_raised = threading.Event()

        def trigger_timeout():
            timeout_reached.set()
            # Since we can't interrupt the thread directly, we'll set a flag
            # The calling code should check this flag periodically
            # For now, we'll just set the flag and let the context manager handle it

        timer = threading.Timer(seconds, trigger_timeout)
        timer.start()

        try:
            yield
            # After yielding, check if timeout was reached
            if timeout_reached.is_set():
                raise TimeoutError(f"{operation_name} timed out after {seconds} seconds")
        finally:
            timer.cancel()

def with_timeout(timeout_seconds: int, operation_name: str = "operation"):
    """Decorator to add timeout to functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with timeout_context(timeout_seconds, operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def with_resource_limits(operation_name: str = "operation"):
    """Decorator to enforce resource limits during execution with graceful degradation."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Set process limits
            set_process_limits()

            # Start resource monitoring
            resource_manager = get_resource_manager()
            start_global_resource_monitoring()

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Check final resource usage
                final_usage = resource_manager.get_resource_usage()

                # Log completion with resource stats
                logger.info(f"{operation_name} completed - "
                          f"Peak memory: {final_usage['memory_mb']:.1f}MB, "
                          f"Peak CPU: {final_usage['cpu_percent']:.1f}%, "
                          f"Final degradation level: {final_usage['degradation_level']}")

                # If limits were exceeded, log warning but don't fail (graceful degradation)
                if final_usage["memory_limit_exceeded"] or final_usage["cpu_limit_exceeded"]:
                    logger.warning(f"{operation_name} exceeded resource limits but completed via graceful degradation - "
                                 f"Memory: {final_usage['memory_limit_percent']:.1f}%, "
                                 f"CPU: {final_usage['cpu_limit_percent']:.1f}%")

                return result

            finally:
                # Stop resource monitoring
                stop_global_resource_monitoring()

        return wrapper
    return decorator

# Specific timeout decorators for common operations
git_clone_timeout = with_timeout(TIMEOUT_CONFIG["git_clone_timeout"], "git_clone")
analysis_timeout = with_timeout(TIMEOUT_CONFIG["analysis_timeout"], "analysis")
api_timeout = with_timeout(TIMEOUT_CONFIG["api_request_timeout"], "api_request")
health_check_timeout = with_timeout(TIMEOUT_CONFIG["health_check_timeout"], "health_check")

# Resource limit decorators
git_clone_limits = with_resource_limits("git_clone")
analysis_limits = with_resource_limits("analysis")
api_limits = with_resource_limits("api_request")