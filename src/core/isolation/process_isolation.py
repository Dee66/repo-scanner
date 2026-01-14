"""
Process Isolation for Safe Repository Scanning

Provides resource limits and timeouts to protect against:
- Infinite loops
- Memory bombs
- CPU exhaustion
- Hanging operations
"""

import os
import sys
import signal
import resource
import multiprocessing
import logging
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from functools import wraps
import time

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits for scan processes."""
    max_memory_bytes: int = 2 * 1024 * 1024 * 1024  # 2GB
    max_cpu_seconds: int = 600  # 10 minutes
    max_wall_time_seconds: int = 900  # 15 minutes
    max_open_files: int = 1024
    max_processes: int = 100


class ProcessIsolationError(Exception):
    """Raised when process isolation fails or limits are exceeded."""
    pass


class TimeoutError(ProcessIsolationError):
    """Raised when operation exceeds time limit."""
    pass


class ResourceLimitError(ProcessIsolationError):
    """Raised when resource limit is exceeded."""
    pass


def _isolated_runner(q, limits_obj, func, args, kwargs):
    """
    Isolated runner function that sets limits and executes function.
    Must be at module level for pickling with spawn.
    
    Args:
        q: Queue for results
        limits_obj: ResourceLimits to apply
        func: Function to execute
        args: Positional arguments
        kwargs: Keyword arguments
    """
    try:
        # Set resource limits in subprocess
        _set_resource_limits(limits_obj)
        
        # Execute function
        result = func(*args, **kwargs)
        
        # Send result back
        q.put({'success': True, 'result': result})
        
    except MemoryError as e:
        q.put({
            'success': False,
            'error': 'ResourceLimitError',
            'message': f'Memory limit exceeded: {e}'
        })
    except Exception as e:
        q.put({
            'success': False,
            'error': type(e).__name__,
            'message': str(e)
        })


def _set_resource_limits(limits: ResourceLimits):
    """
    Set resource limits for current process.
    Must be called before scan starts.
    """
    try:
        # Memory limit (address space)
        if sys.platform != 'darwin':  # Not supported on macOS
            resource.setrlimit(
                resource.RLIMIT_AS,
                (limits.max_memory_bytes, limits.max_memory_bytes)
            )
        else:
            # On macOS, limit data segment instead
            resource.setrlimit(
                resource.RLIMIT_DATA,
                (limits.max_memory_bytes, limits.max_memory_bytes)
            )
        
        # CPU time limit
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (limits.max_cpu_seconds, limits.max_cpu_seconds)
        )
        
        # Open files limit
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (limits.max_open_files, limits.max_open_files)
        )
        
        # Process limit
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (limits.max_processes, limits.max_processes)
        )
                   
    except (ValueError, resource.error) as e:
        # Continue anyway - limits are best effort
        pass


def _timeout_handler(signum, frame):
    """Signal handler for timeout."""
    raise TimeoutError("Operation exceeded time limit")


def with_timeout(seconds: int):
    """
    Decorator to add timeout to a function.
    
    Args:
        seconds: Maximum execution time in seconds
        
    Usage:
        @with_timeout(300)
        def long_operation():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Set alarm signal
            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # Cancel alarm
                return result
            finally:
                signal.signal(signal.SIGALRM, old_handler)
        
        return wrapper
    return decorator


class IsolatedProcess:
    """
    Run a function in an isolated subprocess with resource limits.
    
    This provides true isolation - if the subprocess hangs or consumes
    too many resources, it can be killed without affecting the parent.
    """
    
    def __init__(self, limits: Optional[ResourceLimits] = None):
        """
        Initialize isolated process executor.
        
        Args:
            limits: Resource limits to enforce
        """
        self.limits = limits or ResourceLimits()
        
    def run(self, func: Callable, *args, **kwargs) -> Any:
        """
        Run function in isolated subprocess with resource limits.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function return value
            
        Raises:
            TimeoutError: If operation exceeds time limit
            ResourceLimitError: If operation exceeds resource limits
            ProcessIsolationError: If subprocess fails
        """
        # Use multiprocessing to create isolated subprocess
        # Use 'fork' context for better compatibility with dynamic functions
        # Note: 'fork' is more compatible but less isolated than 'spawn'
        if sys.platform != 'win32':
            ctx = multiprocessing.get_context('fork')
        else:
            ctx = multiprocessing.get_context('spawn')
        
        queue = ctx.Queue()
        
        def run_in_subprocess():
            """Wrapper to run in subprocess."""
            try:
                _set_resource_limits(self.limits)
                result = func(*args, **kwargs)
                queue.put({'success': True, 'result': result})
            except MemoryError as e:
                queue.put({
                    'success': False,
                    'error': 'ResourceLimitError',
                    'message': f'Memory limit exceeded: {e}'
                })
            except Exception as e:
                queue.put({
                    'success': False,
                    'error': type(e).__name__,
                    'message': str(e)
                })
        
        # Start subprocess
        process = ctx.Process(target=run_in_subprocess)
        start_time = time.time()
        process.start()
        
        # Wait for completion with timeout
        process.join(timeout=self.limits.max_wall_time_seconds)
        
        if process.is_alive():
            # Process exceeded time limit - kill it
            logger.error("Process exceeded time limit (%ds) - terminating",
                        self.limits.max_wall_time_seconds)
            process.terminate()
            process.join(timeout=5)
            
            if process.is_alive():
                # Still alive - force kill
                process.kill()
                process.join()
            
            raise TimeoutError(
                f"Operation exceeded time limit ({self.limits.max_wall_time_seconds}s)"
            )
        
        # Check exit code
        if process.exitcode != 0:
            logger.error("Process exited with code %d", process.exitcode)
            
            # Try to get error from queue
            try:
                result = queue.get(timeout=1)
                if not result['success']:
                    error_type = result.get('error', 'ProcessIsolationError')
                    message = result.get('message', 'Unknown error')
                    
                    if error_type == 'ResourceLimitError':
                        raise ResourceLimitError(message)
                    else:
                        raise ProcessIsolationError(f"{error_type}: {message}")
            except:
                pass
            
            # Generic error if we couldn't get specifics
            if process.exitcode == -9:
                raise ResourceLimitError("Process killed (likely memory limit exceeded)")
            elif process.exitcode == -11:
                raise ProcessIsolationError("Process segfaulted")
            else:
                raise ProcessIsolationError(f"Process failed with exit code {process.exitcode}")
        
        # Get result from queue
        try:
            result = queue.get(timeout=5)
            
            if result['success']:
                elapsed = time.time() - start_time
                logger.info("Isolated execution completed in %.2fs", elapsed)
                return result['result']
            else:
                error_type = result.get('error', 'ProcessIsolationError')
                message = result.get('message', 'Unknown error')
                
                if error_type == 'ResourceLimitError':
                    raise ResourceLimitError(message)
                else:
                    raise ProcessIsolationError(f"{error_type}: {message}")
                    
        except Exception as e:
            if isinstance(e, (TimeoutError, ResourceLimitError, ProcessIsolationError)):
                raise
            raise ProcessIsolationError(f"Failed to get result from subprocess: {e}")


def run_with_isolation(func: Callable, limits: Optional[ResourceLimits] = None,
                      *args, **kwargs) -> Any:
    """
    Convenience function to run function with isolation.
    
    Args:
        func: Function to execute
        limits: Resource limits (uses defaults if None)
        *args: Positional arguments for function
        **kwargs: Keyword arguments for function
        
    Returns:
        Function return value
        
    Example:
        result = run_with_isolation(
            scan_repository,
            ResourceLimits(max_memory_bytes=1024*1024*1024),
            repo_path="/path/to/repo"
        )
    """
    isolator = IsolatedProcess(limits)
    return isolator.run(func, *args, **kwargs)


class ScanIsolationWrapper:
    """
    Wrapper for scanning operations with automatic isolation.
    
    Provides a context manager for isolated scanning.
    """
    
    def __init__(self, repository_path: str, limits: Optional[ResourceLimits] = None):
        """
        Initialize scan isolation wrapper.
        
        Args:
            repository_path: Path to repository being scanned
            limits: Resource limits to enforce
        """
        self.repository_path = repository_path
        self.limits = limits or ResourceLimits()
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        """Enter isolation context."""
        self.start_time = time.time()
        logger.info("Starting isolated scan of %s", self.repository_path)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit isolation context."""
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        
        if exc_type is None:
            logger.info("Isolated scan completed in %.2fs", elapsed)
        elif exc_type == TimeoutError:
            logger.error("Scan exceeded time limit (%.2fs)", elapsed)
        elif exc_type == ResourceLimitError:
            logger.error("Scan exceeded resource limits (%.2fs)", elapsed)
        else:
            logger.error("Scan failed with %s: %s (%.2fs)", 
                        exc_type.__name__, exc_val, elapsed)
        
        return False  # Don't suppress exceptions
    
    def execute_scan(self, scan_func: Callable, *args, **kwargs) -> Any:
        """
        Execute scan function with isolation.
        
        Args:
            scan_func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Scan results
        """
        isolator = IsolatedProcess(self.limits)
        return isolator.run(scan_func, *args, **kwargs)


def get_resource_usage() -> Dict[str, Any]:
    """
    Get current resource usage statistics.
    
    Returns:
        Dictionary with resource usage metrics
    """
    usage = resource.getrusage(resource.RUSAGE_SELF)
    
    return {
        'cpu_time_seconds': usage.ru_utime + usage.ru_stime,
        'max_memory_mb': usage.ru_maxrss / 1024 / 1024,  # Convert to MB
        'page_faults': usage.ru_majflt,
        'io_operations': usage.ru_inblock + usage.ru_oublock,
        'voluntary_context_switches': usage.ru_nvcsw,
        'involuntary_context_switches': usage.ru_nivcsw
    }


def log_resource_usage(prefix: str = ""):
    """
    Log current resource usage.
    
    Args:
        prefix: Prefix for log message
    """
    usage = get_resource_usage()
    logger.info("%sResource usage: CPU=%.2fs, Memory=%.1fMB, PageFaults=%d",
               prefix,
               usage['cpu_time_seconds'],
               usage['max_memory_mb'],
               usage['page_faults'])
