"""Pytest configuration and fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path
import os
import json
from collections import defaultdict
from datetime import datetime
import multiprocessing
import xml.etree.ElementTree as ET
from typing import Dict, List, Any

# Use absolute path based on conftest.py location
_conf_dir = Path(__file__).parent

# Global flakiness tracking
_flakiness_data = defaultdict(lambda: {"passes": 0, "failures": 0, "last_result": None})
_flakiness_file = _conf_dir / ".pytest_cache" / "flakiness.json"

# Test results aggregation
_test_results_history = []
_results_file = _conf_dir / ".pytest_cache" / "test_results_history.json"

# Global aggregation state
_current_session_results = None

# Flaky test quarantine
_quarantined_tests = set()
_quarantine_file = _conf_dir / ".pytest_cache" / "quarantined_tests.json"

# Performance benchmarking
_performance_baselines = {}
_performance_history = []
_performance_file = _conf_dir / ".pytest_cache" / "performance_baselines.json"
_performance_threshold = 0.10  # 10% performance regression threshold

# Test coverage analysis
_coverage_data_file = _conf_dir / ".pytest_cache" / "coverage_data.json"
_coverage_report_file = _conf_dir / ".pytest_cache" / "coverage_report.xml"
_coverage_thresholds = {
    "overall": 85.0,  # 85% overall coverage required
    "core": 90.0,     # 90% coverage for core modules
    "services": 85.0, # 85% coverage for services
    "adapters": 80.0, # 80% coverage for adapters
}

# Advanced parallelization configuration
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


def load_test_results_history():
    """Load test results history from cache file."""
    if _results_file.exists():
        try:
            with open(_results_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def load_quarantined_tests():
    """Load quarantined tests from cache file."""
    if _quarantine_file.exists():
        try:
            with open(_quarantine_file, 'r') as f:
                data = json.load(f)
                return set(data.get("quarantined_tests", []))
        except (json.JSONDecodeError, IOError):
            pass
    return set()


def save_quarantined_tests():
    """Save quarantined tests to cache file."""
    _quarantine_file.parent.mkdir(exist_ok=True)
    with open(_quarantine_file, 'w') as f:
        json.dump({
            "quarantined_tests": list(_quarantined_tests),
            "quarantine_timestamp": datetime.now().isoformat()
        }, f, indent=2)


def load_performance_baselines():
    """Load performance baselines from cache file."""
    if _performance_file.exists():
        try:
            with open(_performance_file, 'r') as f:
                data = json.load(f)
                return data.get("baselines", {}), data.get("history", [])
        except (json.JSONDecodeError, IOError):
            pass
    return {}, []


def save_performance_baselines():
    """Save performance baselines to cache file."""
    _performance_file.parent.mkdir(exist_ok=True)
    with open(_performance_file, 'w') as f:
        json.dump({
            "baselines": _performance_baselines,
            "history": _performance_history[-50:],  # Keep last 50 runs
            "last_updated": datetime.now().isoformat()
        }, f, indent=2, default=str)


def save_test_results_history():
    """Save test results history to cache file."""
    _results_file.parent.mkdir(exist_ok=True)
    with open(_results_file, 'w') as f:
        json.dump(_test_results_history, f, indent=2, default=str)


@pytest.fixture(scope="session", autouse=True)
def aggregate_test_results():
    """Aggregate test results across the session."""
    global _current_session_results
    session_results = {
        "start_time": None,
        "end_time": None,
        "total_tests": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "xfailed": 0,
        "duration": 0,
        "test_details": []
    }
    _current_session_results = session_results

    yield session_results

    # Save aggregated results
    global _test_results_history
    _test_results_history.append(session_results)
    # Keep only last 10 runs
    _test_results_history = _test_results_history[-10:]
    save_test_results_history()


def load_flakiness_data():
    """Load flakiness data from cache file."""
    if _flakiness_file.exists():
        try:
            with open(_flakiness_file, 'r') as f:
                return defaultdict(lambda: {"passes": 0, "failures": 0, "last_result": None}, json.load(f))
        except (json.JSONDecodeError, IOError):
            pass
    return _flakiness_data


def save_flakiness_data():
    """Save flakiness data to cache file."""
    _flakiness_file.parent.mkdir(exist_ok=True)
    with open(_flakiness_file, 'w') as f:
        json.dump(dict(_flakiness_data), f, indent=2)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Hook to track test results for flakiness detection and aggregation."""
    if call.when == "call":
        test_id = f"{item.parent.name}::{item.name}"
        outcome = call.excinfo is None

        if outcome:
            _flakiness_data[test_id]["passes"] += 1
            _flakiness_data[test_id]["last_result"] = "passed"
        else:
            _flakiness_data[test_id]["failures"] += 1
            _flakiness_data[test_id]["last_result"] = "failed"

        save_flakiness_data()

        # Aggregate results
        global _current_session_results
        if _current_session_results is not None:
            if outcome:
                _current_session_results["passed"] += 1
            else:
                _current_session_results["failed"] += 1

            _current_session_results["total_tests"] += 1
            _current_session_results["test_details"].append({
                "test_id": test_id,
                "outcome": "passed" if outcome else "failed",
                "duration": call.duration,
                "nodeid": item.nodeid
            })

        # Performance tracking for benchmarked tests
        if hasattr(item, "_benchmark_data"):
            benchmark_data = item._benchmark_data
            benchmark_data["outcome"] = "passed" if outcome else "failed"
            benchmark_data["timestamp"] = datetime.now().isoformat()
            benchmark_data["duration"] = call.duration  # Use pytest's measured duration

            # Add CPU and memory metrics if available
            try:
                import psutil
                import os
                process = psutil.Process(os.getpid())
                benchmark_data["memory_mb"] = process.memory_info().rss / 1024 / 1024
                benchmark_data["cpu_percent"] = psutil.cpu_percent(interval=None)
            except ImportError:
                benchmark_data["memory_mb"] = 0
                benchmark_data["cpu_percent"] = 0

            # Check for performance regression
            baseline = _performance_baselines.get(test_id)
            if baseline:
                regression = (benchmark_data["duration"] - baseline["duration"]) / baseline["duration"]
                benchmark_data["regression"] = regression
                benchmark_data["regression_threshold"] = _performance_threshold

                if abs(regression) > _performance_threshold:
                    benchmark_data["performance_alert"] = "REGRESSION" if regression > 0 else "IMPROVEMENT"

            _performance_history.append(benchmark_data)

            # Update baseline if this is a passing test
            if outcome:
                # Always update baseline for first run or if performance improved
                should_update = (test_id not in _performance_baselines or
                               benchmark_data["duration"] < _performance_baselines[test_id]["duration"])

                if should_update:
                    _performance_baselines[test_id] = {
                        "duration": benchmark_data["duration"],
                        "cpu_percent": benchmark_data["cpu_percent"],
                        "memory_mb": benchmark_data["memory_mb"],
                        "timestamp": benchmark_data["timestamp"]
                    }
                    save_performance_baselines()


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """Hook to skip quarantined tests unless explicitly requested."""
    test_id = f"{item.parent.name}::{item.name}"

    # Skip quarantined tests unless --run-quarantined is specified
    if test_id in _quarantined_tests and not item.config.getoption("--run-quarantined", False):
        pytest.skip(f"Test {test_id} is quarantined due to flakiness")
    # Set up benchmark data collection for benchmark tests
    if item.get_closest_marker("benchmark"):
        item._benchmark_data = {
            "test_id": test_id,
            "start_time": datetime.now().isoformat()
        }

@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items):
    """Automatically quarantine flaky tests based on reliability metrics."""
    if config.getoption("--list-quarantined"):
        if _quarantined_tests:
            terminalreporter = config.pluginmanager.get_plugin("terminalreporter")
            if terminalreporter:
                terminalreporter.write_sep("=", "Quarantined Tests")
                for test_id in sorted(_quarantined_tests):
                    stats = _flakiness_data.get(test_id, {"passes": 0, "failures": 0})
                    total_runs = stats["passes"] + stats["failures"]
                    failure_rate = stats["failures"] / max(total_runs, 1)
                    reliability = 1.0 - failure_rate
                    terminalreporter.write_line(f"{test_id}: {reliability:.1%} reliable ({stats['failures']}/{total_runs} failures)")
                terminalreporter.write_line("")
        pytest.exit("Listed quarantined tests", returncode=0)

    # Filter to benchmark tests only if requested
    if config.getoption("--perf-only"):
        benchmark_items = []
        for item in items:
            if item.get_closest_marker("benchmark"):
                benchmark_items.append(item)
        items[:] = benchmark_items

    # Update performance threshold from command line
    global _performance_threshold
    _performance_threshold = config.getoption("--performance-threshold", 0.10)

    if not config.getoption("--auto-quarantine", True):
        return

    quarantined_count = 0
    for item in items:
        test_id = f"{item.parent.name}::{item.name}"
        stats = _flakiness_data.get(test_id, {"passes": 0, "failures": 0})

        total_runs = stats["passes"] + stats["failures"]
        if total_runs >= 5:  # Need at least 5 runs to assess reliability
            failure_rate = stats["failures"] / total_runs
            reliability_score = 1.0 - failure_rate

            # Quarantine if reliability is below 80% and has failed recently
            if reliability_score < 0.8 and stats["last_result"] == "failed":
                if test_id not in _quarantined_tests:
                    _quarantined_tests.add(test_id)
                    quarantined_count += 1

    if quarantined_count > 0:
        save_quarantined_tests()
        terminalreporter = config.pluginmanager.get_plugin("terminalreporter")
        if terminalreporter:
            terminalreporter.write_line(f"Quarantined {quarantined_count} flaky tests due to low reliability (<80%)")


@pytest.fixture
def performance_timer():
    """Provide a performance timer for measuring test execution time."""
    import time
    start_time = time.perf_counter()
    yield lambda: time.perf_counter() - start_time
    # Timer automatically stops when fixture goes out of scope


@pytest.fixture
def benchmark_test(request):
    """Fixture for benchmarking test performance."""
    import time
    import psutil
    import os

    start_time = time.perf_counter()
    start_cpu = psutil.cpu_percent(interval=None)
    process = psutil.Process(os.getpid())
    start_memory = process.memory_info().rss / 1024 / 1024  # MB

    def get_metrics():
        end_time = time.perf_counter()
        end_cpu = psutil.cpu_percent(interval=None)
        end_memory = process.memory_info().rss / 1024 / 1024  # MB

        return {
            "duration": end_time - start_time,
            "cpu_percent": end_cpu - start_cpu,
            "memory_mb": end_memory - start_memory,
            "test_id": f"{request.node.parent.name}::{request.node.name}"
        }

    yield get_metrics


@pytest.fixture(scope="session", autouse=True)
def coverage_analysis(request):
    """Session fixture to collect and analyze test coverage."""
    try:
        import coverage
        cov = coverage.Coverage(
            source=['core', 'services', 'adapters'],
            omit=['*/tests/*', '*/test_*', '*/conftest.py']
        )
        cov.start()

        def finalize():
            cov.stop()
            cov.save()

            # Generate and analyze coverage report
            coverage_data = generate_coverage_report()
            if coverage_data:
                save_coverage_data(coverage_data)

        request.addfinalizer(finalize)
    except ImportError:
        # Coverage not available, skip
        pass


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Create a session-wide test data directory."""
    data_dir = tmp_path_factory.mktemp("test_data")
    return data_dir


@pytest.fixture
def isolated_test_dir(tmp_path):
    """Provide an isolated directory for each test."""
    test_dir = tmp_path / "test_isolation"
    test_dir.mkdir()
    return test_dir


@pytest.fixture
def mock_repo_data(isolated_test_dir):
    """Create mock repository data for testing."""
    # Create a mock git repository structure
    repo_dir = isolated_test_dir / "mock_repo"
    repo_dir.mkdir()

    # Create basic repo structure
    (repo_dir / ".git").mkdir()
    (repo_dir / "README.md").write_text("# Test Repository\n")
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "main.py").write_text("print('Hello World')\n")
    (repo_dir / "tests").mkdir()
    (repo_dir / "tests" / "test_main.py").write_text("def test_hello(): pass\n")

    return repo_dir


@pytest.fixture(autouse=True)
def cleanup_test_artifacts(tmp_path):
    """Clean up test artifacts after each test."""
    yield

    # Clean up any temporary files created during test
    for pattern in ["*.tmp", "*.log", "*.cache"]:
        for file in tmp_path.rglob(pattern):
            try:
                if file.is_file():
                    file.unlink()
            except (OSError, PermissionError):
                pass  # Ignore cleanup errors


@pytest.fixture(scope="session", autouse=True)
def session_cleanup():
    """Clean up session-wide test artifacts."""
    yield

    # Clean up any global test artifacts
    import tempfile
    temp_base = Path(tempfile.gettempdir())

    # Clean up test-related temp directories
    for pattern in ["pytest-*", "test_*_data"]:
        for path in temp_base.glob(pattern):
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except (OSError, PermissionError):
                pass  # Ignore cleanup errors


@pytest.fixture(scope="session")
def test_environment():
    """Set up test environment variables and configuration."""
    # Store original environment
    original_env = {}

    # Set test environment variables
    test_env_vars = {
        "TEST_MODE": "1",
        "LOG_LEVEL": "DEBUG",
        "DISABLE_ANALYTICS": "1",
        "MOCK_EXTERNAL_SERVICES": "1",
    }

    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture
def mock_external_services(monkeypatch):
    """Mock external services for testing."""
    # Mock any external API calls, database connections, etc.
    monkeypatch.setenv("MOCK_REDIS", "1")
    monkeypatch.setenv("MOCK_GIT", "1")
    monkeypatch.setenv("MOCK_API", "1")

    yield

    # Cleanup would happen automatically via monkeypatch


@pytest.fixture
def clean_database_state():
    """Ensure clean database state for tests."""
    # In a real application, this would reset database state
    # For now, just ensure no persistent state
    yield

    # Reset any in-memory state
    pass


@pytest.fixture(scope="session")
def test_configuration():
    """Provide test configuration."""
    config = {
        "timeout": 30,
        "max_retries": 3,
        "parallel_workers": 4,
        "log_level": "DEBUG",
        "mock_services": True,
    }
    return config


@pytest.fixture(autouse=True)
def environment_isolation(monkeypatch, tmp_path):
    """Isolate environment for each test."""
    # Isolate any environment-specific state
    test_env_dir = tmp_path / ".test_env"
    test_env_dir.mkdir()

    # Set isolated paths
    monkeypatch.setenv("TEST_WORK_DIR", str(test_env_dir))
    monkeypatch.setenv("ISOLATED_TEST", "1")

    yield

    # Cleanup happens via tmp_path


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "flaky: marks tests that are known to be flaky and should be rerun on failure")
    config.addinivalue_line("markers", "benchmark: marks tests as performance benchmarks")

    # Add command line options for quarantine management
    config.addinivalue_line("addopts", "--strict-markers")
    config.addinivalue_line("addopts", "--strict-config")


def pytest_addoption(parser):
    """Add command line options for test reliability management."""
    group = parser.getgroup("reliability")
    group.addoption(
        "--run-quarantined",
        action="store_true",
        default=False,
        help="Run quarantined tests that would normally be skipped"
    )
    group.addoption(
        "--auto-quarantine",
        action="store_true",
        default=True,
        help="Automatically quarantine flaky tests based on reliability metrics"
    )
    group.addoption(
        "--list-quarantined",
        action="store_true",
        default=False,
        help="List all quarantined tests and exit"
    )

    # Performance benchmarking options
    group.addoption(
        "--perf-only",
        action="store_true",
        default=False,
        help="Run only performance benchmark tests"
    )
    group.addoption(
        "--performance-threshold",
        type=float,
        default=0.10,
        help="Performance regression threshold (default: 0.10 = 10%%)"
    )
    group.addoption(
        "--update-baselines",
        action="store_true",
        default=False,
        help="Update performance baselines with current run results"
    )

    # Coverage analysis options
    group.addoption(
        "--coverage-report",
        action="store_true",
        default=False,
        help="Generate detailed coverage report after test run"
    )
    group.addoption(
        "--coverage-threshold",
        type=float,
        default=85.0,
        help="Overall coverage threshold (default: 85.0%%)"
    )
    group.addoption(
        "--fail-on-coverage",
        action="store_true",
        default=False,
        help="Fail tests if coverage thresholds are not met"
    )

    # CI/CD pipeline options
    group.addoption(
        "--run-pipeline",
        action="store_true",
        default=False,
        help="Run the complete CI/CD pipeline"
    )
    group.addoption(
        "--ci-config",
        action="store_true",
        default=False,
        help="Show current CI configuration"
    )
    group.addoption(
        "--generate-ci",
        type=str,
        default="",
        help="Generate CI configuration for specified system (github_actions, gitlab_ci)"
    )
    group.addoption(
        "--pipeline-report",
        action="store_true",
        default=False,
        help="Show pipeline execution report"
    )

    # Security testing options
    group.addoption(
        "--security-scan",
        action="store_true",
        default=False,
        help="Perform security vulnerability scanning"
    )
    group.addoption(
        "--security-report",
        action="store_true",
        default=False,
        help="Generate detailed security assessment report"
    )
    group.addoption(
        "--fail-on-security",
        action="store_true",
        default=False,
        help="Fail tests if security vulnerabilities are found"
    )
    group.addoption(
        "--security-threshold",
        type=str,
        default="medium",
        choices=["low", "medium", "high", "critical"],
        help="Security severity threshold (default: medium)"
    )

    # Advanced reporting options
    group.addoption(
        "--advanced-report",
        action="store_true",
        default=False,
        help="Generate advanced analytics report with trends and risk assessment"
    )
    group.addoption(
        "--analytics-dashboard",
        action="store_true",
        default=False,
        help="Generate interactive analytics dashboard"
    )
    group.addoption(
        "--trend-analysis",
        action="store_true",
        default=False,
        help="Perform detailed trend analysis on test metrics"
    )
    group.addoption(
        "--risk-assessment",
        action="store_true",
        default=False,
        help="Generate comprehensive risk assessment report"
    )

    # Advanced parallelization options
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


def pytest_sessionstart(session):
    """Load flakiness data at session start."""
    global _flakiness_data, _test_results_history, _quarantined_tests, _performance_baselines, _performance_history
    _flakiness_data = load_flakiness_data()
    _test_results_history = load_test_results_history()
    _quarantined_tests = load_quarantined_tests()
    _performance_baselines, _performance_history = load_performance_baselines()


def load_coverage_data():
    """Load coverage data from cache file."""
    if _coverage_data_file.exists():
        try:
            with open(_coverage_data_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_coverage_data(data):
    """Save coverage data to cache file."""
    _coverage_data_file.parent.mkdir(parents=True, exist_ok=True)
    with open(_coverage_data_file, 'w') as f:
        json.dump(data, f, indent=2)


def generate_coverage_report():
    """Generate coverage report and check against thresholds."""
    try:
        import coverage
    except ImportError:
        return None

    try:
        cov = coverage.Coverage()
        cov.load()

        # Generate XML report
        cov.xml_report(outfile=str(_coverage_report_file))

        # Parse XML report for analysis
        if _coverage_report_file.exists():
            tree = ET.parse(_coverage_report_file)
            root = tree.getroot()

            coverage_by_package = {}
            overall_coverage = 0.0

            for package in root.findall(".//package"):
                name = package.get('name', '')
                line_rate = float(package.get('line-rate', 0))
                coverage_by_package[name] = line_rate * 100

            # Calculate overall coverage
            overall_line_rate = float(root.get('line-rate', 0))
            overall_coverage = overall_line_rate * 100

            return {
                'overall': overall_coverage,
                'by_package': coverage_by_package,
                'timestamp': datetime.now().isoformat()
            }
    except Exception:
        # Coverage report generation failed (no data, etc.)
        return None

    return None


def check_coverage_thresholds(coverage_data):
    """Check if coverage meets required thresholds."""
    if not coverage_data:
        return []

    alerts = []

    # Check overall coverage
    overall = coverage_data.get('overall', 0)
    if overall < _coverage_thresholds['overall']:
        alerts.append(f"Overall coverage {overall:.1f}% below threshold {_coverage_thresholds['overall']}%")

    # Check package-specific thresholds
    by_package = coverage_data.get('by_package', {})
    for package, threshold in _coverage_thresholds.items():
        if package != 'overall':
            package_coverage = by_package.get(package, 0)
            if package_coverage < threshold:
                alerts.append(f"{package} coverage {package_coverage:.1f}% below threshold {threshold}%")

    return alerts


@pytest.fixture
def coverage_checker():
    """Fixture to check coverage for specific modules during testing."""
    return CoverageChecker()


class CoverageChecker:
    """Helper class for coverage checking during tests."""

    def check_module_coverage(self, module_name: str, min_coverage: float = 80.0) -> bool:
        """Check if a specific module meets minimum coverage requirements."""
        coverage_data = load_coverage_data()
        by_package = coverage_data.get('by_package', {})
        module_coverage = by_package.get(module_name, 0)
        return module_coverage >= min_coverage

    def get_coverage_report(self) -> Dict[str, Any]:
        """Get the current coverage report data."""
        return load_coverage_data()

    def assert_coverage_threshold(self, module_name: str, threshold: float):
        """Assert that a module meets a coverage threshold."""
        coverage_data = load_coverage_data()
        by_package = coverage_data.get('by_package', {})
        actual = by_package.get(module_name, 0)
        assert actual >= threshold, f"{module_name} coverage {actual:.1f}% below threshold {threshold}%"


def pytest_sessionfinish(session, exitstatus):
    """Save final results and generate trend analysis at session end."""
    global _test_results_history

    if _test_results_history:
        # Generate trend analysis
        recent_runs = _test_results_history[-5:]  # Last 5 runs

        if len(recent_runs) >= 2:
            # Calculate trends
            pass_rates = [run.get("passed", 0) / max(run.get("total_tests", 1), 1) for run in recent_runs]
            avg_pass_rate = sum(pass_rates) / len(pass_rates)

            terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
            if terminalreporter:
                terminalreporter.write_sep("=", "Test Trend Analysis")
                terminalreporter.write_line(f"Average pass rate (last {len(recent_runs)} runs): {avg_pass_rate:.1%}")

                if len(pass_rates) >= 2:
                    trend = pass_rates[-1] - pass_rates[-2]
                    if trend > 0.05:
                        terminalreporter.write_line("📈 Pass rate improving")
                    elif trend < -0.05:
                        terminalreporter.write_line("📉 Pass rate declining")
                    else:
                        terminalreporter.write_line("➡️  Pass rate stable")

                terminalreporter.write_line("")


    # Generate coverage report if requested
    if session.config.getoption("--coverage-report"):
        coverage_data = generate_coverage_report()
        if coverage_data:
            save_coverage_data(coverage_data)

            terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
            if terminalreporter:
                terminalreporter.write_sep("=", "Coverage Analysis Report")
                terminalreporter.write_line(f"Overall Coverage: {coverage_data.get('overall', 0):.1f}%")
                terminalreporter.write_line("Coverage by Package:")

                by_package = coverage_data.get('by_package', {})
                for package, cov in sorted(by_package.items()):
                    status = "✅" if cov >= _coverage_thresholds.get(package, 85.0) else "❌"
                    terminalreporter.write_line(f"  {package}: {cov:.1f}% {status}")

                # Check for alerts
                alerts = check_coverage_thresholds(coverage_data)
                if alerts:
                    terminalreporter.write_line("")
                    terminalreporter.write_line("Coverage Alerts:")
                    for alert in alerts:
                        terminalreporter.write_line(f"  ⚠️  {alert}")

                terminalreporter.write_line("")

    # Fail if coverage thresholds not met and --fail-on-coverage specified
    if session.config.getoption("--fail-on-coverage"):
        coverage_data = generate_coverage_report()
        if coverage_data:
            save_coverage_data(coverage_data)
            alerts = check_coverage_thresholds(coverage_data)
            if alerts:
                session.exitstatus = 1

    # Run CI pipeline if requested
    if session.config.getoption("--run-pipeline"):
        print("\n🚀 Running CI/CD Pipeline...")
        try:
            from tests.test_ci_integration import run_test_pipeline
            pipeline_result = run_test_pipeline()

            terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
            if terminalreporter:
                terminalreporter.write_sep("=", "CI/CD Pipeline Results")
                terminalreporter.write_line(f"Overall Success: {'✅' if pipeline_result['overall_success'] else '❌'}")
                terminalreporter.write_line(f"Deployment Ready: {'✅' if pipeline_result['deployment_ready'] else '❌'}")
                terminalreporter.write_line(f"Total Duration: {pipeline_result['duration']:.1f}s")
                terminalreporter.write_line("")

                for step in pipeline_result['steps']:
                    status = "✅" if step['success'] else "❌"
                    terminalreporter.write_line(f"{status} {step['step_name']}: {step['duration']:.1f}s")

                terminalreporter.write_line("")
        except ImportError:
            print("CI integration module not available")

    # Show CI config if requested
    if session.config.getoption("--ci-config"):
        try:
            from tests.test_ci_integration import load_ci_config
            ci_config = load_ci_config()
            terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
            if terminalreporter:
                terminalreporter.write_sep("=", "CI Configuration")
                for key, value in ci_config.items():
                    terminalreporter.write_line(f"{key}: {value}")
                terminalreporter.write_line("")
        except ImportError:
            print("CI integration module not available")

    # Generate CI workflow if requested
    if session.config.getoption("--generate-ci"):
        try:
            from tests.test_ci_integration import generate_ci_config
            ci_system = session.config.getoption("--generate-ci")
            ci_config = generate_ci_config(ci_system)
            terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
            if terminalreporter:
                terminalreporter.write_sep("=", f"Generated {ci_system.upper()} CI Configuration")
                terminalreporter.write_line(ci_config)
                terminalreporter.write_line("")
        except ImportError:
            print("CI integration module not available")

    # Show pipeline report if requested
    if session.config.getoption("--pipeline-report"):
        try:
            from tests.test_ci_integration import load_pipeline_results
            pipeline_results = load_pipeline_results()
            if pipeline_results:
                last_pipeline = pipeline_results[-1]
                terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
                if terminalreporter:
                    terminalreporter.write_sep("=", "Pipeline Execution Report")
                    terminalreporter.write_line(f"Pipeline ID: {last_pipeline['pipeline_id']}")
                    terminalreporter.write_line(f"Timestamp: {last_pipeline['timestamp']}")
                    terminalreporter.write_line(f"Success: {last_pipeline['overall_success']}")
                    terminalreporter.write_line(f"Steps: {len(last_pipeline['steps'])}")
                    terminalreporter.write_line("")
            else:
                print("No pipeline results found.")
        except ImportError:
            print("CI integration module not available")

    # Run security assessment if requested
    if session.config.getoption("--security-scan"):
        try:
            from tests.test_security_assessment import run_security_assessment
            security_results = run_security_assessment()
            if security_results:
                terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
                if terminalreporter:
                    terminalreporter.write_sep("=", "Security Assessment Report")
                    terminalreporter.write_line(f"Security Score: {security_results.get('overall_score', 0):.1f}/100")
                    terminalreporter.write_line(f"Vulnerabilities Found: {len(security_results.get('vulnerabilities', []))}")
                    terminalreporter.write_line(f"Critical Issues: {security_results.get('critical_count', 0)}")
                    terminalreporter.write_line(f"High Issues: {security_results.get('high_count', 0)}")
                    terminalreporter.write_line("")
        except ImportError:
            print("Security assessment module not available")

    # Generate advanced analytics report if requested
    if session.config.getoption("--advanced-report") or session.config.getoption("--analytics-dashboard"):
        try:
            from tests.test_advanced_reporting import run_advanced_analytics
            analytics_results = run_advanced_analytics()
            if analytics_results:
                terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
                if terminalreporter:
                    terminalreporter.write_sep("=", "Advanced Analytics Report")
                    risk = analytics_results.get("trend_analysis", {}).get("risk_assessment", {})
                    terminalreporter.write_line(f"Overall Risk Level: {risk.get('overall_risk', 'unknown').upper()}")
                    terminalreporter.write_line(f"Risk Factors: {len(risk.get('risk_factors', []))}")

                    recommendations = analytics_results.get("trend_analysis", {}).get("recommendations", [])
                    if recommendations:
                        terminalreporter.write_line("Key Recommendations:")
                        for rec in recommendations[:3]:
                            terminalreporter.write_line(f"  • {rec}")

                    terminalreporter.write_line(f"Analytics Dashboard: .pytest_cache/advanced_reports/analytics_dashboard.html")
                    terminalreporter.write_line("")
        except ImportError:
            print("Advanced reporting module not available")

    # Generate advanced parallelization report
    if session.config.getoption("--parallel-workers", 1) > 1 or session.config.getoption("--test-discovery"):
        terminalreporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if terminalreporter:
            terminalreporter.write_sep("=", "Advanced Parallelization Report")
            num_workers = session.config.getoption("--parallel-workers")
            strategy = session.config.getoption("--parallel-strategy")
            terminalreporter.write_line(f"Parallel workers: {num_workers}")
            terminalreporter.write_line(f"Load balancing strategy: {strategy}")

            if session.config.getoption("--distributed"):
                terminalreporter.write_line("Distributed execution: enabled")
                coordinator_host = session.config.getoption("--coordinator-host")
                coordinator_port = session.config.getoption("--coordinator-port")
                terminalreporter.write_line(f"Coordinator: {coordinator_host}:{coordinator_port}")

            if session.config.getoption("--test-discovery"):
                terminalreporter.write_line("Advanced test discovery: enabled")
                if hasattr(session, 'organized_tests'):
                    organized = session.organized_tests
                    terminalreporter.write_line(f"Test organization completed")
                    terminalreporter.write_line(f"  Modules: {len(organized['by_module'])}")
                    terminalreporter.write_line(f"  Test types: {len(organized['performance_tests'])} perf, {len(organized['integration_tests'])} integration, {len(organized['unit_tests'])} unit")

            if session.config.getoption("--optimize-order"):
                terminalreporter.write_line("Test execution order optimization: enabled")

            terminalreporter.write_line("")


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Display flakiness summary at end of test session."""
    if _flakiness_data:
        terminalreporter.write_sep("=", "Flakiness Report")
        flaky_tests = []
        total_runs = 0
        total_failures = 0

        for test_id, stats in _flakiness_data.items():
            runs = stats["passes"] + stats["failures"]
            if runs > 1 and stats["failures"] > 0:
                failure_rate = stats["failures"] / runs
                if failure_rate > 0.1:  # More than 10% failure rate
                    flaky_tests.append((test_id, failure_rate, runs))
            total_runs += runs
            total_failures += stats["failures"]

        if flaky_tests:
            terminalreporter.write_line("Potentially flaky tests (>10% failure rate):")
            for test_id, rate, runs in sorted(flaky_tests, key=lambda x: x[1], reverse=True):
                quarantined_marker = " [QUARANTINED]" if test_id in _quarantined_tests else ""
                terminalreporter.write_line(".2%")
        else:
            terminalreporter.write_line("No flaky tests detected.")

        if total_runs > 0:
            overall_failure_rate = total_failures / total_runs
            terminalreporter.write_line(".2%")

        # Report quarantined tests
        if _quarantined_tests:
            terminalreporter.write_line(f"Quarantined tests: {len(_quarantined_tests)}")
            terminalreporter.write_line("Use --run-quarantined to execute quarantined tests")
        else:
            terminalreporter.write_line("No tests currently quarantined")

        terminalreporter.write_line("")

    # Performance benchmarking summary
    if _performance_history:
        terminalreporter.write_sep("=", "Performance Benchmarking Report")

        # Show recent benchmark results
        recent_benchmarks = [b for b in _performance_history[-10:] if "performance_alert" in b]

        if recent_benchmarks:
            terminalreporter.write_line("Performance alerts:")
            for benchmark in recent_benchmarks:
                alert_type = benchmark["performance_alert"]
                regression = benchmark.get("regression", 0)
                test_id = benchmark["test_id"]
                duration = benchmark["duration"]
                terminalreporter.write_line(".1f")
        else:
            terminalreporter.write_line("No performance regressions detected.")

        # Show baseline information
        if _performance_baselines:
            terminalreporter.write_line(f"Performance baselines established for {len(_performance_baselines)} tests")
            terminalreporter.write_line("Use --benchmark-only to run only benchmark tests")
        else:
            terminalreporter.write_line("No performance baselines established yet")

        terminalreporter.write_line("")


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment before any tests run."""
    import os
    import sys

    # Ensure we're in the right directory
    original_cwd = os.getcwd()
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Set up environment variables for testing
    test_env_vars = {
        "PYTEST_RUNNING": "1",
        "TEST_ENVIRONMENT": "1",
        "PYTHONPATH": str(project_root),
    }

    original_env = {}
    for key, value in test_env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    # Ensure test dependencies are available
    try:
        import pytest
        import git
        import yaml
    except ImportError as e:
        pytest.fail(f"Test dependency missing: {e}")

    yield

    # Cleanup: restore original environment
    for key, value in original_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    os.chdir(original_cwd)


@pytest.fixture(scope="session", autouse=True)
def teardown_test_environment():
    """Clean up after all tests have run."""
    yield

    # Post-test cleanup
    import gc
    import tempfile

    # Force garbage collection
    gc.collect()

    # Clean up any remaining temp files
    temp_base = Path(tempfile.gettempdir())
    for pattern in ["pytest-*", "test_*"]:
        for path in temp_base.glob(pattern):
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except (OSError, PermissionError):
                pass  # Ignore cleanup errors in teardown


@pytest.fixture(autouse=True)
def isolate_test_data(tmp_path, monkeypatch):
    """Isolate test data and ensure proper cleanup."""
    # Change to a temporary directory for each test
    monkeypatch.chdir(tmp_path)

    # Ensure temp directory is clean
    yield

    # Cleanup happens automatically via tmp_path fixture


@pytest.fixture
def clean_temp_dir(tmp_path):
    """Provide a clean temporary directory with guaranteed cleanup."""
    temp_dir = tmp_path / "clean_temp"
    temp_dir.mkdir()
    yield temp_dir
    # Cleanup happens automatically


@pytest.fixture(autouse=True)
def isolate_global_state(monkeypatch, tmp_path):
    """Isolate global state between tests for parallel execution."""
    # Reset system config global state
    try:
        from src.core.system_config import reset_system_config
        reset_system_config()
    except ImportError:
        pass  # Module may not be available

    # Isolate scanner cache directory per test
    scanner_cache_dir = tmp_path / ".scanner_cache"
    scanner_cache_dir.mkdir()
    monkeypatch.setenv("SCANNER_CACHE_DIR", str(scanner_cache_dir))

    # Isolate repository cache directory per test
    repo_cache_dir = tmp_path / ".repo_cache"
    repo_cache_dir.mkdir()
    monkeypatch.setenv("REPO_CACHE_DIR", str(repo_cache_dir))

    # Ensure no shared state from previous tests
    yield

    # Cleanup will happen automatically via tmp_path


@pytest.fixture(scope="session")
def worker_id():
    """Get the pytest-xdist worker ID for parallel test isolation."""
    import os
    return os.environ.get("PYTEST_XDIST_WORKER", "master")


@pytest.fixture(autouse=True)
def isolate_worker_cache(worker_id, tmp_path_factory, monkeypatch):
    """Isolate cache directories per pytest-xdist worker."""
    if worker_id != "master":
        # Create worker-specific cache directories
        worker_cache_base = tmp_path_factory.mktemp(f"worker_{worker_id}")
        worker_scanner_cache = worker_cache_base / ".scanner_cache"
        worker_repo_cache = worker_cache_base / ".repo_cache"

        worker_scanner_cache.mkdir()
        worker_repo_cache.mkdir()

        # Override environment variables for this worker
        monkeypatch.setenv("SCANNER_CACHE_DIR", str(worker_scanner_cache))
        monkeypatch.setenv("REPO_CACHE_DIR", str(worker_repo_cache))

        yield worker_cache_base
    else:
        yield None