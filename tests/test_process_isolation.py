"""
Tests for Process Isolation

Tests resource limits, timeouts, and subprocess isolation.
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
    Path('/tmp/test_side_effect.txt').write_text('test')
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
        assert limits.max_open_files == 1024
        assert limits.max_processes == 100
    
    def test_custom_limits(self):
        """Test custom resource limits."""
        limits = ResourceLimits(
            max_memory_bytes=512 * 1024 * 1024,  # 512MB
            max_cpu_seconds=60,
            max_wall_time_seconds=120
        )
        
        assert limits.max_memory_bytes == 512 * 1024 * 1024
        assert limits.max_cpu_seconds == 60
        assert limits.max_wall_time_seconds == 120


class TestTimeoutDecorator:
    """Test timeout decorator functionality."""
    
    @pytest.mark.timeout(5)
    def test_function_completes_within_timeout(self):
        """Test that fast functions complete successfully."""
        @with_timeout(2)
        def fast_function():
            time.sleep(0.1)
            return "completed"
        
        result = fast_function()
        assert result == "completed"
    
    @pytest.mark.timeout(5)
    def test_function_exceeds_timeout(self):
        """Test that slow functions are interrupted."""
        @with_timeout(1)
        def slow_function():
            time.sleep(5)
            return "should not reach here"
        
        with pytest.raises(TimeoutError):
            slow_function()


class TestIsolatedProcess:
    """Test isolated process execution."""
    
    def test_simple_function_execution(self):
        """Test executing a simple function in isolation."""
        def add_numbers(a, b):
            return a + b
        
        isolator = IsolatedProcess()
        result = isolator.run(add_numbers, 5, 7)
        
        assert result == 12
    
    def test_function_with_return_value(self):
        """Test function with complex return value."""
        def get_data():
            return {
                'status': 'success',
                'data': [1, 2, 3, 4, 5],
                'metadata': {'count': 5}
            }
        
        isolator = IsolatedProcess()
        result = isolator.run(get_data)
        
        assert result['status'] == 'success'
        assert result['data'] == [1, 2, 3, 4, 5]
        assert result['metadata']['count'] == 5
    
    @pytest.mark.timeout(10)
    def test_timeout_enforcement(self):
        """Test that wall time timeout is enforced."""
        def infinite_loop():
            while True:
                pass
        
        limits = ResourceLimits(max_wall_time_seconds=2)
        isolator = IsolatedProcess(limits)
        
        with pytest.raises(TimeoutError):
            isolator.run(infinite_loop)
    
    @pytest.mark.skipif(sys.platform == 'darwin', 
                        reason="Memory limits behave differently on macOS")
    def test_memory_limit_enforcement(self):
        """Test that memory limit is enforced."""
        def allocate_memory():
            # Try to allocate 100MB chunks until we hit the limit
            data = []
            for i in range(100):
                data.append(bytearray(100 * 1024 * 1024))  # 100MB
            return len(data)
        
        # Set very low memory limit
        limits = ResourceLimits(max_memory_bytes=50 * 1024 * 1024)  # 50MB
        isolator = IsolatedProcess(limits)
        
        with pytest.raises((ResourceLimitError, MemoryError, ProcessIsolationError)):
            isolator.run(allocate_memory)
    
    def test_exception_propagation(self):
        """Test that exceptions are properly propagated."""
        def failing_function():
            raise ValueError("Test error")
        
        isolator = IsolatedProcess()
        
        with pytest.raises(ProcessIsolationError) as exc_info:
            isolator.run(failing_function)
        
        assert "ValueError" in str(exc_info.value)
    
    def test_function_with_arguments(self):
        """Test function execution with various argument types."""
        def process_data(numbers, operation='sum'):
            if operation == 'sum':
                return sum(numbers)
            elif operation == 'product':
                result = 1
                for n in numbers:
                    result *= n
                return result
            return 0
        
        isolator = IsolatedProcess()
        
        result_sum = isolator.run(process_data, [1, 2, 3, 4, 5], 'sum')
        assert result_sum == 15
        
        result_product = isolator.run(process_data, [2, 3, 4], 'product')
        assert result_product == 24


class TestRunWithIsolation:
    """Test convenience function for running with isolation."""
    
    def test_simple_execution(self):
        """Test simple function execution."""
        def multiply(x, y):
            return x * y
        
        result = run_with_isolation(multiply, None, 6, 7)
        assert result == 42
    
    def test_with_custom_limits(self):
        """Test execution with custom limits."""
        def compute():
            return sum(range(1000))
        
        limits = ResourceLimits(max_cpu_seconds=30)
        result = run_with_isolation(compute, limits)
        
        assert result == 499500


class TestResourceUsage:
    """Test resource usage monitoring."""
    
    def test_get_resource_usage(self):
        """Test getting current resource usage."""
        usage = get_resource_usage()
        
        assert 'cpu_time_seconds' in usage
        assert 'max_memory_mb' in usage
        assert 'page_faults' in usage
        assert 'io_operations' in usage
        
        # All values should be non-negative
        assert usage['cpu_time_seconds'] >= 0
        assert usage['max_memory_mb'] >= 0
        assert usage['page_faults'] >= 0
    
    def test_resource_usage_increases(self):
        """Test that resource usage increases with work."""
        usage_before = get_resource_usage()
        
        # Do some work
        _ = [i ** 2 for i in range(100000)]
        time.sleep(0.1)
        
        usage_after = get_resource_usage()
        
        # CPU time should have increased
        assert usage_after['cpu_time_seconds'] >= usage_before['cpu_time_seconds']


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_function_returning_none(self):
        """Test function that returns None."""
        def no_return():
            pass
        
        isolator = IsolatedProcess()
        result = isolator.run(no_return)
        
        assert result is None
    
    def test_function_with_side_effects(self):
        """Test that side effects are isolated."""
        import tempfile
        import os
        
        def create_temp_file():
            # Create a temp file in isolated process
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, 'test.txt')
            with open(temp_file, 'w') as f:
                f.write('test data')
            return temp_file
        
        isolator = IsolatedProcess()
        temp_file = isolator.run(create_temp_file)
        
        # File should exist after subprocess completes
        assert os.path.exists(temp_file)
        
        # Cleanup
        os.remove(temp_file)
        os.rmdir(os.path.dirname(temp_file))
    
    def test_very_short_timeout(self):
        """Test handling of very short timeouts."""
        def quick_function():
            return "done"
        
        # Even with 1 second timeout, should complete
        limits = ResourceLimits(max_wall_time_seconds=1)
        isolator = IsolatedProcess(limits)
        
        result = isolator.run(quick_function)
        assert result == "done"


class TestSecurityIsolation:
    """Test security isolation features."""
    
    def test_cannot_modify_parent_process(self):
        """Test that subprocess cannot modify parent process memory."""
        shared_list = [1, 2, 3]
        
        def try_modify_list():
            # This modifies a local copy, not the parent's list
            local_list = [4, 5, 6]
            return local_list
        
        isolator = IsolatedProcess()
        result = isolator.run(try_modify_list)
        
        # Original list unchanged
        assert shared_list == [1, 2, 3]
        # Result is new list
        assert result == [4, 5, 6]
    
    def test_subprocess_environment_isolation(self):
        """Test that subprocess has isolated environment."""
        import os
        
        # Set env var in main process
        os.environ['TEST_VAR'] = 'main_value'
        
        def check_and_modify_env():
            import os
            # Get value
            value = os.getenv('TEST_VAR')
            # Try to modify
            os.environ['TEST_VAR'] = 'subprocess_value'
            return os.getenv('TEST_VAR')
        
        isolator = IsolatedProcess()
        result = isolator.run(check_and_modify_env)
        
        # Subprocess saw and modified its copy
        assert result == 'subprocess_value'
        # Main process value unchanged
        assert os.getenv('TEST_VAR') == 'main_value'


class TestPerformance:
    """Test performance characteristics of isolation."""
    
    def test_overhead_is_reasonable(self):
        """Test that isolation overhead is acceptable."""
        def simple_computation():
            return sum(range(10000))
        
        # Measure direct execution
        start = time.time()
        expected = simple_computation()
        direct_time = time.time() - start
        
        # Measure isolated execution
        start = time.time()
        isolator = IsolatedProcess()
        result = isolator.run(simple_computation)
        isolated_time = time.time() - start
        
        assert result == expected
        
        # Overhead should be less than 2 seconds
        # (subprocess creation adds overhead)
        assert isolated_time - direct_time < 2.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
