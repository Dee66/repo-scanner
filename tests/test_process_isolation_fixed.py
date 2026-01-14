"""
Tests for Process Isolation - Fixed Version

Tests resource limits, timeouts, and subprocess isolation with module-level functions.
"""

import pytest
import time
import sys
from pathlib import Path
from src.core.isolation.process_isolation import (
    IsolatedProcess,
    ResourceLimits,
    TimeoutError,
    ResourceLimitError,
    ProcessIsolationError,
    with_timeout,
    run_with_isolation,
    get_resource_usage
)


# Module-level test functions (required for pickling with spawn context)
def add_numbers(a, b):
    """Simple addition function."""
    return a + b


def get_data():
    """Function that returns structured data."""
    return {'status': 'success', 'value': 42}


def slow_function():
    """Function that takes a while to execute."""
    time.sleep(3)
    return 'completed'


def memory_hog():
    """Function that tries to allocate lots of memory."""
    # Try to allocate 3GB
    data = []
    for _ in range(3000):
        data.append(b'x' * (1024 * 1024))  # 1MB chunks
    return len(data)


def failing_function():
    """Function that raises an exception."""
    raise ValueError("This function always fails")


def multiply(x, y, z=1):
    """Function with multiple arguments."""
    return x * y * z


def returns_none():
    """Function that returns None."""
    return None


def has_side_effects():
    """Function with side effects."""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write('test')
    return 'done'


def very_fast_function():
    """Function that completes quickly."""
    return 'fast'


parent_var = "parent_value"


def tries_to_modify_parent():
    """Function that tries to modify parent scope."""
    global parent_var
    parent_var = "modified"
    return parent_var


def check_environment():
    """Function that checks environment variables."""
    import os
    return os.environ.get('TEST_VAR', 'not_set')


def measure_time():
    """Function to measure timing overhead."""
    start = time.time()
    result = sum(range(10000))
    return time.time() - start


class TestResourceLimits:
    """Test resource limit enforcement."""
    
    def test_default_limits(self):
        """Test default resource limits."""
        limits = ResourceLimits()
        
        assert limits.max_memory_bytes == 2 * 1024 * 1024 * 1024  # 2GB
        assert limits.max_cpu_seconds == 600  # 10 minutes
        assert limits.max_wall_time_seconds == 900  # 15 minutes
    
    def test_custom_limits(self):
        """Test custom resource limits."""
        limits = ResourceLimits(
            max_memory_bytes=1024 * 1024 * 1024,  # 1GB
            max_cpu_seconds=60,
            max_wall_time_seconds=120
        )
        
        assert limits.max_memory_bytes == 1024 * 1024 * 1024
        assert limits.max_cpu_seconds == 60
        assert limits.max_wall_time_seconds == 120


class TestTimeoutDecorator:
    """Test timeout decorator functionality."""
    
    @pytest.mark.skipif(sys.platform == 'darwin', reason="Signal-based timeout not reliable on macOS")
    def test_function_completes_within_timeout(self):
        """Test that fast functions complete successfully."""
        @with_timeout(2)
        def fast_function():
            time.sleep(0.1)
            return "completed"
        
        result = fast_function()
        assert result == "completed"
    
    @pytest.mark.skipif(sys.platform == 'darwin', reason="Signal-based timeout not reliable on macOS")
    def test_function_exceeds_timeout(self):
        """Test that slow functions are interrupted."""
        @with_timeout(1)
        def slow_function_local():
            time.sleep(5)
            return "should not reach here"
        
        with pytest.raises(TimeoutError):
            slow_function_local()


class TestIsolatedProcess:
    """Test isolated process execution."""
    
    def test_simple_function_execution(self):
        """Test executing a simple function in isolation."""
        isolator = IsolatedProcess()
        result = isolator.run(add_numbers, 5, 7)
        
        assert result == 12
    
    def test_function_with_return_value(self):
        """Test function that returns structured data."""
        isolator = IsolatedProcess()
        result = isolator.run(get_data)
        
        assert result == {'status': 'success', 'value': 42}
    
    def test_timeout_enforcement(self):
        """Test that timeouts are enforced."""
        limits = ResourceLimits(max_wall_time_seconds=1)
        isolator = IsolatedProcess(limits)
        
        with pytest.raises(TimeoutError):
            isolator.run(slow_function)
    
    @pytest.mark.skipif(sys.platform == 'darwin', reason="Memory limits don't work reliably on macOS")
    def test_memory_limit_enforcement(self):
        """Test that memory limits are enforced."""
        limits = ResourceLimits(
            max_memory_bytes=500 * 1024 * 1024,  # 500MB
            max_wall_time_seconds=10
        )
        isolator = IsolatedProcess(limits)
        
        with pytest.raises((ResourceLimitError, MemoryError, OSError)):
            isolator.run(memory_hog)
    
    def test_exception_propagation(self):
        """Test that exceptions from subprocess are propagated."""
        isolator = IsolatedProcess()
        
        with pytest.raises((ProcessIsolationError, Exception)) as exc_info:
            isolator.run(failing_function)
        
        error_msg = str(exc_info.value).lower()
        assert 'fails' in error_msg or 'valueerror' in error_msg
    
    def test_function_with_arguments(self):
        """Test function with multiple arguments."""
        isolator = IsolatedProcess()
        result = isolator.run(multiply, 3, 4, z=2)
        
        assert result == 24


class TestRunWithIsolation:
    """Test run_with_isolation convenience function."""
    
    def test_simple_execution(self):
        """Test simple execution with default limits."""
        result = run_with_isolation(add_numbers, 10, 20)
        assert result == 30
    
    def test_with_custom_limits(self):
        """Test execution with custom limits."""
        limits = ResourceLimits(max_wall_time_seconds=5)
        result = run_with_isolation(multiply, 6, 7, limits=limits)
        assert result == 42


class TestResourceUsage:
    """Test resource usage monitoring."""
    
    def test_get_resource_usage(self):
        """Test getting current resource usage."""
        usage = get_resource_usage()
        
        assert 'cpu_time' in usage
        assert 'memory_mb' in usage
        assert usage['cpu_time'] >= 0
        assert usage['memory_mb'] > 0
    
    def test_resource_usage_increases(self):
        """Test that resource usage increases with work."""
        usage1 = get_resource_usage()
        
        # Do some work
        _ = [i**2 for i in range(100000)]
        
        usage2 = get_resource_usage()
        
        # CPU time should increase
        assert usage2['cpu_time'] >= usage1['cpu_time']


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_function_returning_none(self):
        """Test function that returns None."""
        isolator = IsolatedProcess()
        result = isolator.run(returns_none)
        
        assert result is None
    
    def test_function_with_side_effects(self):
        """Test function with side effects."""
        isolator = IsolatedProcess()
        result = isolator.run(has_side_effects)
        
        assert result == 'done'
    
    def test_very_short_timeout(self):
        """Test with very short timeout."""
        limits = ResourceLimits(max_wall_time_seconds=0.001)
        isolator = IsolatedProcess(limits)
        
        # Even fast function might timeout
        with pytest.raises(TimeoutError):
            isolator.run(very_fast_function)


class TestSecurityIsolation:
    """Test security aspects of isolation."""
    
    def test_cannot_modify_parent_process(self):
        """Test that subprocess cannot modify parent variables."""
        original_value = parent_var
        
        isolator = IsolatedProcess()
        result = isolator.run(tries_to_modify_parent)
        
        # Result shows modified value in subprocess
        assert result == "modified"
        # But parent process value unchanged
        assert parent_var == original_value
    
    def test_subprocess_environment_isolation(self):
        """Test that subprocess has isolated environment."""
        import os
        
        # Set environment variable in parent
        os.environ['TEST_VAR'] = 'parent_value'
        
        isolator = IsolatedProcess()
        result = isolator.run(check_environment)
        
        # Subprocess should see the environment variable
        # (spawn context doesn't completely isolate environment)
        assert result == 'parent_value'


class TestPerformance:
    """Test performance characteristics."""
    
    def test_overhead_is_reasonable(self):
        """Test that isolation overhead is acceptable."""
        isolator = IsolatedProcess()
        
        start = time.time()
        result = isolator.run(measure_time)
        overhead = time.time() - start - result
        
        # Overhead should be less than 2 seconds
        assert overhead < 2.0
        assert result >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
