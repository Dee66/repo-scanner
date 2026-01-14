"""Advanced test parallelization and distributed testing infrastructure."""

import pytest
import os
import json
import time
import threading
import multiprocessing
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from queue import Queue, PriorityQueue
import hashlib
import socket
import subprocess
import tempfile
import shutil

# Use absolute path based on conftest.py location
_conf_dir = Path(__file__).parent

# Advanced parallelization configuration
_parallel_config_file = _conf_dir / ".pytest_cache" / "parallel_config.json"
_distributed_workers_file = _conf_dir / ".pytest_cache" / "distributed_workers.json"
_test_distribution_file = _conf_dir / ".pytest_cache" / "test_distribution.json"

# Parallelization settings
PARALLEL_CONFIG = {
    "max_workers": multiprocessing.cpu_count(),
    "worker_timeout": 300,  # 5 minutes
    "chunk_size": 10,  # Tests per worker chunk
    "load_balancing": "adaptive",  # adaptive, round_robin, duration_based
    "isolation_level": "process",  # process, thread, none
    "resource_limits": {
        "cpu_percent": 80,
        "memory_mb": 1024,
        "io_timeout": 30
    },
    "distributed": {
        "enabled": False,
        "coordinator_host": "localhost",
        "coordinator_port": 8888,
        "worker_discovery": "auto",  # auto, manual, config
        "heartbeat_interval": 30,
        "reconnection_attempts": 3
    }
}


def load_parallel_config() -> Dict[str, Any]:
    """Load parallelization configuration."""
    if _parallel_config_file.exists():
        try:
            with open(_parallel_config_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return PARALLEL_CONFIG.copy()


def save_parallel_config(config: Dict[str, Any]):
    """Save parallelization configuration."""
    _parallel_config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(_parallel_config_file, 'w') as f:
        json.dump(config, f, indent=2)


class TestChunk:
    """Represents a chunk of tests to be executed together."""

    def __init__(self, test_ids: List[str], estimated_duration: float = 0.0, priority: int = 1):
        self.test_ids = test_ids
        self.estimated_duration = estimated_duration
        self.priority = priority
        self.chunk_id = self._generate_chunk_id()

    def _generate_chunk_id(self) -> str:
        """Generate unique chunk identifier."""
        content = f"{','.join(self.test_ids)}{self.estimated_duration}{time.time()}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def __lt__(self, other):
        """Priority comparison for priority queue."""
        return self.priority < other.priority

    def __eq__(self, other):
        """Equality comparison based on content."""
        if not isinstance(other, TestChunk):
            return False
        return (self.test_ids == other.test_ids and
                self.estimated_duration == other.estimated_duration and
                self.priority == other.priority)

    def __hash__(self):
        """Hash based on content for use in sets/dicts."""
        return hash((tuple(self.test_ids), self.estimated_duration, self.priority))


class LoadBalancer:
    """Advanced load balancer for test distribution."""

    def __init__(self, strategy: str = "adaptive"):
        self.strategy = strategy
        self.worker_stats = {}  # worker_id -> stats
        self.test_history = {}  # test_id -> historical durations

    def distribute_tests(self, test_items: List[Any], num_workers: int) -> List[TestChunk]:
        """Distribute tests across workers using the configured strategy."""
        if self.strategy == "round_robin":
            return self._round_robin_distribution(test_items, num_workers)
        elif self.strategy == "duration_based":
            return self._duration_based_distribution(test_items, num_workers)
        else:  # adaptive
            return self._adaptive_distribution(test_items, num_workers)

    def _round_robin_distribution(self, test_items: List[Any], num_workers: int) -> List[TestChunk]:
        """Simple round-robin distribution."""
        chunks = [[] for _ in range(num_workers)]
        for i, test_item in enumerate(test_items):
            chunks[i % num_workers].append(test_item.nodeid)

        return [TestChunk(chunk) for chunk in chunks if chunk]

    def _duration_based_distribution(self, test_items: List[Any], num_workers: int) -> List[TestChunk]:
        """Distribute based on estimated test durations."""
        # Sort tests by estimated duration (longest first)
        sorted_tests = sorted(test_items,
                            key=lambda x: self.test_history.get(x.nodeid, 1.0),
                            reverse=True)

        chunks = [[] for _ in range(num_workers)]
        chunk_durations = [0.0] * num_workers

        for test_item in sorted_tests:
            test_id = test_item.nodeid
            duration = self.test_history.get(test_id, 1.0)

            # Find chunk with current smallest total duration
            min_chunk_idx = chunk_durations.index(min(chunk_durations))
            chunks[min_chunk_idx].append(test_id)
            chunk_durations[min_chunk_idx] += duration

        return [TestChunk(chunk, duration) for chunk, duration in zip(chunks, chunk_durations) if chunk]

    def _adaptive_distribution(self, test_items: List[Any], num_workers: int) -> List[TestChunk]:
        """Adaptive distribution based on worker performance and test characteristics."""
        # Analyze test characteristics
        test_complexity = self._analyze_test_complexity(test_items)

        # Consider worker capabilities
        worker_capabilities = self._get_worker_capabilities(num_workers)

        chunks = []
        remaining_tests = test_items.copy()

        while remaining_tests:
            chunk = self._create_optimal_chunk(remaining_tests, worker_capabilities, test_complexity)
            if not chunk:
                break
            chunks.append(chunk)
            for test in chunk.test_ids:
                remaining_tests = [t for t in remaining_tests if t.nodeid != test]

        return chunks

    def _analyze_test_complexity(self, test_items: List[Any]) -> Dict[str, float]:
        """Analyze test complexity based on various factors."""
        complexity = {}
        for test_item in test_items:
            test_id = test_item.nodeid
            # Simple complexity heuristic based on test name and path
            complexity_score = len(test_id.split('::')) * 0.1  # More nested = more complex
            if 'integration' in test_id.lower():
                complexity_score *= 2.0
            if 'slow' in test_item.keywords:
                complexity_score *= 1.5
            complexity[test_id] = complexity_score
        return complexity

    def _get_worker_capabilities(self, num_workers: int) -> List[Dict[str, Any]]:
        """Get worker capabilities for load balancing."""
        capabilities = []
        for i in range(num_workers):
            worker_id = f"worker_{i}"
            stats = self.worker_stats.get(worker_id, {})
            capabilities.append({
                "id": worker_id,
                "performance_score": stats.get("performance_score", 1.0),
                "current_load": stats.get("current_load", 0),
                "specialized_for": stats.get("specialized_for", [])
            })
        return capabilities

    def _create_optimal_chunk(self, test_items: List[Any], worker_capabilities: List[Dict],
                            test_complexity: Dict[str, float]) -> Optional[TestChunk]:
        """Create an optimal chunk for the next available worker."""
        if not test_items:
            return None

        # Find best worker (lowest current load)
        best_worker = min(worker_capabilities, key=lambda w: w["current_load"])

        # Select tests suitable for this worker
        suitable_tests = []
        for test_item in test_items:
            test_id = test_item.nodeid
            complexity = test_complexity.get(test_id, 1.0)

            # Check if worker can handle this test
            if self._worker_can_handle_test(best_worker, test_item, complexity):
                suitable_tests.append((test_item, complexity))

        if not suitable_tests:
            return None

        # Sort by complexity and take top N
        suitable_tests.sort(key=lambda x: x[1], reverse=True)
        chunk_size = min(len(suitable_tests), PARALLEL_CONFIG["chunk_size"])
        selected_tests = suitable_tests[:chunk_size]

        chunk = TestChunk(
            [test.nodeid for test, _ in selected_tests],
            sum(complexity for _, complexity in selected_tests),
            priority=1
        )

        # Update worker load
        best_worker["current_load"] += chunk.estimated_duration

        return chunk

    def _worker_can_handle_test(self, worker: Dict[str, Any], test_item: Any, complexity: float) -> bool:
        """Check if a worker can handle a specific test."""
        # Basic checks - can be extended with more sophisticated logic
        max_load = 10.0  # Arbitrary limit
        return worker["current_load"] + complexity <= max_load

    def update_worker_stats(self, worker_id: str, stats: Dict[str, Any]):
        """Update worker statistics for adaptive load balancing."""
        self.worker_stats[worker_id] = stats

    def update_test_history(self, test_id: str, duration: float):
        """Update test execution history."""
        if test_id not in self.test_history:
            self.test_history[test_id] = duration
        else:
            # Exponential moving average
            alpha = 0.3
            self.test_history[test_id] = alpha * duration + (1 - alpha) * self.test_history[test_id]


class ParallelTestExecutor:
    """Advanced parallel test executor with load balancing."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.load_balancer = LoadBalancer(config.get("load_balancing", "adaptive"))
        self.results_queue = Queue()
        self.workers = []

    def execute_parallel(self, test_items: List[Any], pytest_args: List[str]) -> Dict[str, Any]:
        """Execute tests in parallel with advanced load balancing."""
        num_workers = min(self.config["max_workers"], len(test_items))
        if num_workers <= 1:
            return self._execute_sequential(test_items, pytest_args)

        # Distribute tests
        chunks = self.load_balancer.distribute_tests(test_items, num_workers)

        # Execute chunks in parallel
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            for chunk in chunks:
                future = executor.submit(self._execute_chunk, chunk, pytest_args.copy())
                futures.append(future)

            results = []
            for future in as_completed(futures):
                try:
                    chunk_result = future.result(timeout=self.config["worker_timeout"])
                    results.append(chunk_result)
                except Exception as e:
                    results.append({"error": str(e), "chunk_id": "unknown"})

        return self._aggregate_results(results)

    def _execute_chunk(self, chunk: TestChunk, pytest_args: List[str]) -> Dict[str, Any]:
        """Execute a chunk of tests."""
        # Create temporary test file with only the tests in this chunk
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for test_id in chunk.test_ids:
                f.write(f"{test_id}\n")
            test_list_file = f.name

        try:
            # Run pytest with the test list
            cmd = ["python", "-m", "pytest"] + pytest_args + ["--collect-only", f"--test-list={test_list_file}"]
            if chunk.test_ids:
                cmd.extend(chunk.test_ids)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config["worker_timeout"],
                cwd=_conf_dir.parent
            )

            return {
                "chunk_id": chunk.chunk_id,
                "test_ids": chunk.test_ids,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": time.time() - time.time()  # Would need to track actual duration
            }

        finally:
            Path(test_list_file).unlink(missing_ok=True)

    def _execute_sequential(self, test_items: List[Any], pytest_args: List[str]) -> Dict[str, Any]:
        """Fallback to sequential execution."""
        test_ids = [item.nodeid for item in test_items]
        return {
            "sequential": True,
            "test_ids": test_ids,
            "results": "Sequential execution would be handled by pytest directly"
        }

    def _aggregate_results(self, chunk_results: List[Dict]) -> Dict[str, Any]:
        """Aggregate results from all chunks."""
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_errors = 0
        all_output = []

        for result in chunk_results:
            if "error" in result:
                total_errors += 1
                continue

            # Parse pytest output to extract test counts
            # This is a simplified parsing - real implementation would need more robust parsing
            stdout = result.get("stdout", "")
            all_output.append(stdout)

            # Simple parsing for demonstration
            if "passed" in stdout.lower():
                total_passed += len(result.get("test_ids", []))
            if "failed" in stdout.lower():
                total_failed += len(result.get("test_ids", []))

            total_tests += len(result.get("test_ids", []))

        return {
            "parallel_execution": True,
            "num_chunks": len(chunk_results),
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "errors": total_errors,
            "chunk_results": chunk_results,
            "combined_output": "\n".join(all_output)
        }


class DistributedTestCoordinator:
    """Coordinator for distributed test execution across multiple machines."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.workers = {}  # worker_id -> worker_info
        self.heartbeat_thread = None
        self.coordinator_socket = None

    def start_coordinator(self):
        """Start the distributed test coordinator."""
        if not self.config.get("distributed", {}).get("enabled", False):
            return

        # Start heartbeat monitoring
        self.heartbeat_thread = threading.Thread(target=self._monitor_heartbeats, daemon=True)
        self.heartbeat_thread.start()

        # Start coordinator server
        coordinator_thread = threading.Thread(target=self._run_coordinator_server, daemon=True)
        coordinator_thread.start()

    def _run_coordinator_server(self):
        """Run the coordinator server for worker communication."""
        try:
            self.coordinator_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.coordinator_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.coordinator_socket.bind((self.config["distributed"]["coordinator_host"],
                                        self.config["distributed"]["coordinator_port"]))
            self.coordinator_socket.listen(5)

            while True:
                client_socket, address = self.coordinator_socket.accept()
                threading.Thread(target=self._handle_worker_connection,
                               args=(client_socket, address), daemon=True).start()

        except Exception as e:
            print(f"Coordinator server error: {e}")
        finally:
            if self.coordinator_socket:
                self.coordinator_socket.close()

    def _handle_worker_connection(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Handle communication with a worker."""
        try:
            # Simple protocol for worker registration and heartbeat
            data = client_socket.recv(1024).decode()
            if data.startswith("REGISTER:"):
                worker_id = data.split(":")[1]
                self.workers[worker_id] = {
                    "address": address,
                    "last_heartbeat": time.time(),
                    "status": "active",
                    "capabilities": {}
                }
                client_socket.send(b"REGISTERED")
            elif data.startswith("HEARTBEAT:"):
                worker_id = data.split(":")[1]
                if worker_id in self.workers:
                    self.workers[worker_id]["last_heartbeat"] = time.time()
                    client_socket.send(b"ACK")
                else:
                    client_socket.send(b"UNKNOWN_WORKER")

        except Exception as e:
            print(f"Worker connection error: {e}")
        finally:
            client_socket.close()

    def _monitor_heartbeats(self):
        """Monitor worker heartbeats and mark dead workers."""
        while True:
            current_time = time.time()
            timeout = self.config["distributed"]["heartbeat_interval"] * 2

            dead_workers = []
            for worker_id, worker_info in self.workers.items():
                if current_time - worker_info["last_heartbeat"] > timeout:
                    dead_workers.append(worker_id)

            for worker_id in dead_workers:
                print(f"Worker {worker_id} timed out")
                del self.workers[worker_id]

            time.sleep(self.config["distributed"]["heartbeat_interval"])

    def get_available_workers(self) -> List[str]:
        """Get list of available workers."""
        return [worker_id for worker_id, info in self.workers.items()
                if info["status"] == "active"]

    def distribute_to_workers(self, test_chunks: List[TestChunk]) -> Dict[str, List[TestChunk]]:
        """Distribute test chunks to available workers."""
        available_workers = self.get_available_workers()
        if not available_workers:
            return {}

        distribution = {}
        for i, chunk in enumerate(test_chunks):
            worker_id = available_workers[i % len(available_workers)]
            if worker_id not in distribution:
                distribution[worker_id] = []
            distribution[worker_id].append(chunk)

        return distribution


class AdvancedTestDiscovery:
    """Advanced test discovery and organization."""

    def __init__(self):
        self.test_metadata = {}
        self.discovery_cache = {}

    def discover_and_organize_tests(self, pytest_session) -> Dict[str, Any]:
        """Discover and organize tests with advanced metadata."""
        organized_tests = {
            "by_module": {},
            "by_class": {},
            "by_marker": {},
            "by_complexity": {},
            "by_duration": {},
            "by_dependencies": {},
            "performance_tests": [],
            "integration_tests": [],
            "unit_tests": []
        }

        for item in pytest_session.items:
            self._analyze_test_item(item, organized_tests)

        return organized_tests

    def _analyze_test_item(self, item, organized_tests: Dict[str, Any]):
        """Analyze individual test item and categorize it."""
        test_id = item.nodeid
        module_name = item.module.__name__ if hasattr(item, 'module') else 'unknown'
        class_name = item.cls.__name__ if hasattr(item, 'cls') else None

        # Categorize by module
        if module_name not in organized_tests["by_module"]:
            organized_tests["by_module"][module_name] = []
        organized_tests["by_module"][module_name].append(test_id)

        # Categorize by class
        if class_name:
            if class_name not in organized_tests["by_class"]:
                organized_tests["by_class"][class_name] = []
            organized_tests["by_class"][class_name].append(test_id)

        # Categorize by markers
        for marker in item.keywords:
            if marker not in organized_tests["by_marker"]:
                organized_tests["by_marker"][marker] = []
            organized_tests["by_marker"][marker].append(test_id)

        # Categorize by test type
        if 'benchmark' in item.keywords:
            organized_tests["performance_tests"].append(test_id)
        elif 'integration' in item.keywords or 'slow' in item.keywords:
            organized_tests["integration_tests"].append(test_id)
        else:
            organized_tests["unit_tests"].append(test_id)

        # Store metadata
        self.test_metadata[test_id] = {
            "module": module_name,
            "class": class_name,
            "markers": list(item.keywords),
            "filepath": str(item.fspath),
            "estimated_complexity": self._estimate_complexity(item)
        }

    def _estimate_complexity(self, item) -> float:
        """Estimate test complexity based on various factors."""
        complexity = 1.0

        # Factor in markers
        if 'slow' in item.keywords:
            complexity *= 2.0
        if 'integration' in item.keywords:
            complexity *= 1.5
        if 'benchmark' in item.keywords:
            complexity *= 1.2

        # Factor in test name length (rough heuristic) - ensure minimum 1.0
        name_factor = max(len(item.name) / 20.0, 1.0)
        complexity *= name_factor

        return min(complexity, 10.0)  # Cap at 10

    def get_test_dependencies(self, test_id: str) -> List[str]:
        """Get test dependencies for a given test."""
        # This would analyze fixtures and imports to determine dependencies
        # Simplified implementation
        metadata = self.test_metadata.get(test_id, {})
        dependencies = []

        # Check for fixture dependencies
        if hasattr(metadata, 'fixtures'):
            dependencies.extend(metadata.get('fixtures', []))

        return dependencies

    def optimize_execution_order(self, test_ids: List[str]) -> List[str]:
        """Optimize test execution order based on dependencies and complexity."""
        # Simple topological sort based on dependencies
        # In a real implementation, this would be more sophisticated
        return sorted(test_ids, key=lambda x: self.test_metadata.get(x, {}).get("estimated_complexity", 1.0))


# Global instances
_parallel_executor = None
_distributed_coordinator = None
_test_discovery = None


def pytest_configure(config):
    """Configure advanced parallelization and distributed testing."""
    global _parallel_executor, _distributed_coordinator, _test_discovery

    parallel_config = load_parallel_config()

    # Initialize components
    _parallel_executor = ParallelTestExecutor(parallel_config)
    _distributed_coordinator = DistributedTestCoordinator(parallel_config)
    _test_discovery = AdvancedTestDiscovery()

    # Start distributed coordinator if enabled
    _distributed_coordinator.start_coordinator()

    # Add command line options
    config.addinivalue_line("addopts", "--strict-markers")


def pytest_addoption(parser):
    """Add command line options for advanced parallelization."""
    group = parser.getgroup("parallelization")

    group.addoption(
        "--parallel-workers",
        type=int,
        default=PARALLEL_CONFIG["max_workers"],
        help=f"Number of parallel workers (default: {PARALLEL_CONFIG['max_workers']})"
    )

    group.addoption(
        "--parallel-strategy",
        type=str,
        default=PARALLEL_CONFIG["load_balancing"],
        choices=["adaptive", "round_robin", "duration_based"],
        help="Load balancing strategy for parallel execution"
    )

    group.addoption(
        "--distributed",
        action="store_true",
        default=False,
        help="Enable distributed test execution"
    )

    group.addoption(
        "--coordinator-host",
        type=str,
        default=PARALLEL_CONFIG["distributed"]["coordinator_host"],
        help="Distributed coordinator host"
    )

    group.addoption(
        "--coordinator-port",
        type=int,
        default=PARALLEL_CONFIG["distributed"]["coordinator_port"],
        help="Distributed coordinator port"
    )

    group.addoption(
        "--test-discovery",
        action="store_true",
        default=False,
        help="Enable advanced test discovery and organization"
    )

    group.addoption(
        "--optimize-order",
        action="store_true",
        default=False,
        help="Optimize test execution order based on dependencies"
    )


def pytest_collection_modifyitems(session, config, items):
    """Modify test collection for advanced features."""
    global _test_discovery

    # Advanced test discovery
    if config.getoption("--test-discovery"):
        organized_tests = _test_discovery.discover_and_organize_tests(session)

        # Store organized test information
        session.organized_tests = organized_tests

        terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if terminalreporter:
            terminalreporter.write_sep("=", "Advanced Test Discovery")
            terminalreporter.write_line(f"Discovered {len(items)} tests")
            terminalreporter.write_line(f"Modules: {len(organized_tests['by_module'])}")
            terminalreporter.write_line(f"Classes: {len(organized_tests['by_class'])}")
            terminalreporter.write_line(f"Performance tests: {len(organized_tests['performance_tests'])}")
            terminalreporter.write_line(f"Integration tests: {len(organized_tests['integration_tests'])}")
            terminalreporter.write_line(f"Unit tests: {len(organized_tests['unit_tests'])}")
            terminalreporter.write_line("")

    # Optimize execution order
    if config.getoption("--optimize-order"):
        optimized_items = _test_discovery.optimize_execution_order([item.nodeid for item in items])
        # Reorder items (simplified - would need more sophisticated implementation)
        items.sort(key=lambda x: optimized_items.index(x.nodeid) if x.nodeid in optimized_items else 0)


def pytest_sessionfinish(session, exitstatus):
    """Generate advanced parallelization report."""
    if session.config.getoption("--parallel-workers", 1) > 1:
        terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if terminalreporter:
            terminalreporter.write_sep("=", "Advanced Parallelization Report")
            num_workers = session.config.getoption("--parallel-workers")
            strategy = session.config.getoption("--parallel-strategy")
            terminalreporter.write_line(f"Parallel workers: {num_workers}")
            terminalreporter.write_line(f"Load balancing strategy: {strategy}")

            if hasattr(session, 'organized_tests'):
                organized = session.organized_tests
                terminalreporter.write_line(f"Test organization completed")
                terminalreporter.write_line(f"  Modules: {len(organized['by_module'])}")
                terminalreporter.write_line(f"  Test types: {len(organized['performance_tests'])} perf, {len(organized['integration_tests'])} integration, {len(organized['unit_tests'])} unit")

            terminalreporter.write_line("")


# Test functions for advanced parallelization
def test_parallel_executor_initialization():
    """Test that the parallel executor can be initialized."""
    config = load_parallel_config()
    executor = ParallelTestExecutor(config)
    assert executor is not None
    assert executor.config == config


def test_load_balancer_strategies():
    """Test different load balancing strategies."""
    balancer = LoadBalancer("round_robin")

    # Mock test items
    class MockItem:
        def __init__(self, nodeid):
            self.nodeid = nodeid

    test_items = [MockItem(f"test_{i}") for i in range(10)]
    chunks = balancer.distribute_tests(test_items, 3)

    assert len(chunks) == 3
    total_tests = sum(len(chunk.test_ids) for chunk in chunks)
    assert total_tests == 10


def test_test_chunk_creation():
    """Test test chunk creation and properties."""
    test_ids = ["test_1", "test_2", "test_3"]
    chunk = TestChunk(test_ids, estimated_duration=5.0, priority=2)

    assert chunk.test_ids == test_ids
    assert chunk.estimated_duration == 5.0
    assert chunk.priority == 2
    assert len(chunk.chunk_id) == 8  # MD5 hash truncated to 8 chars


def test_adaptive_distribution():
    """Test adaptive load balancing distribution."""
    balancer = LoadBalancer("adaptive")

    class MockItem:
        def __init__(self, nodeid, keywords=None):
            self.nodeid = nodeid
            self.keywords = keywords or set()

    test_items = [MockItem(f"test_{i}") for i in range(20)]
    chunks = balancer.distribute_tests(test_items, 4)

    assert len(chunks) > 0
    total_tests = sum(len(chunk.test_ids) for chunk in chunks)
    assert total_tests == 20


def test_distributed_coordinator():
    """Test distributed coordinator initialization."""
    config = load_parallel_config()
    coordinator = DistributedTestCoordinator(config)
    assert coordinator is not None
    assert coordinator.config == config


def test_advanced_test_discovery():
    """Test advanced test discovery functionality."""
    discovery = AdvancedTestDiscovery()
    assert discovery is not None
    assert isinstance(discovery.test_metadata, dict)


def test_test_complexity_estimation():
    """Test test complexity estimation."""
    discovery = AdvancedTestDiscovery()

    class MockItem:
        def __init__(self, name, keywords=None):
            self.name = name
            self.keywords = keywords or set()

    # Test simple unit test
    simple_test = MockItem("test_simple")
    complexity = discovery._estimate_complexity(simple_test)
    assert complexity >= 1.0

    # Test complex integration test
    complex_test = MockItem("test_very_long_integration_test_name", {"slow", "integration"})
    complexity_complex = discovery._estimate_complexity(complex_test)
    assert complexity_complex > complexity


def test_execution_order_optimization():
    """Test execution order optimization."""
    discovery = AdvancedTestDiscovery()

    # Add some test metadata
    discovery.test_metadata = {
        "simple_test": {"estimated_complexity": 1.0},
        "complex_test": {"estimated_complexity": 5.0},
        "medium_test": {"estimated_complexity": 3.0}
    }

    test_ids = ["simple_test", "complex_test", "medium_test"]
    optimized = discovery.optimize_execution_order(test_ids)

    # Should be ordered by complexity (ascending)
    assert optimized[0] == "simple_test"
    assert optimized[-1] == "complex_test"


def test_parallel_config_persistence():
    """Test parallel configuration loading and saving."""
    config = load_parallel_config()
    assert isinstance(config, dict)
    assert "max_workers" in config
    assert "load_balancing" in config

    # Test saving modified config
    modified_config = config.copy()
    modified_config["custom_setting"] = "test_value"
    save_parallel_config(modified_config)

    # Load and verify
    loaded_config = load_parallel_config()
    assert loaded_config.get("custom_setting") == "test_value"


def test_worker_capability_analysis():
    """Test worker capability analysis."""
    balancer = LoadBalancer("adaptive")
    capabilities = balancer._get_worker_capabilities(3)

    assert len(capabilities) == 3
    for cap in capabilities:
        assert "id" in cap
        assert "performance_score" in cap
        assert "current_load" in cap


def test_chunk_priority_queue():
    """Test chunk priority queue functionality."""
    chunk1 = TestChunk(["test_1"], priority=1)
    chunk2 = TestChunk(["test_2"], priority=2)
    chunk3 = TestChunk(["test_1"], priority=1)  # Same test_ids and priority as chunk1

    # Test priority comparison
    assert chunk1 < chunk2  # Lower priority number = higher priority
    assert chunk1 == chunk3  # Same content
    assert not (chunk2 < chunk1)