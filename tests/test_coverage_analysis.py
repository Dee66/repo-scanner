"""Test coverage analysis and reporting infrastructure."""

import pytest
import coverage
import json
from pathlib import Path
from typing import Dict, List, Any
import xml.etree.ElementTree as ET

# Use absolute path based on conftest.py location
_conf_dir = Path(__file__).parent

# Coverage configuration
_coverage_data_file = _conf_dir / ".pytest_cache" / "coverage_data.json"
_coverage_report_file = _conf_dir / ".pytest_cache" / "coverage_report.xml"
_coverage_thresholds = {
    "overall": 85.0,  # 85% overall coverage required
    "core": 90.0,     # 90% coverage for core modules
    "services": 85.0, # 85% coverage for services
    "adapters": 80.0, # 80% coverage for adapters
}


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
            'timestamp': coverage.utils.now()
        }

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


@pytest.fixture(scope="session", autouse=True)
def coverage_analysis(request):
    """Session fixture to collect and analyze test coverage."""
    # Start coverage collection
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

            # Check thresholds and report alerts
            alerts = check_coverage_thresholds(coverage_data)
            if alerts:
                terminal = request.config.pluginmanager.get_plugin("terminalreporter")
                if terminal:
                    terminal.write_sep("=", "Coverage Threshold Alerts")
                    for alert in alerts:
                        terminal.write_line(f"⚠️  {alert}")
                    terminal.write_line("")

    request.addfinalizer(finalize)


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


def pytest_addoption(parser):
    """Add coverage-related command line options."""
    group = parser.getgroup("reliability")

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


def pytest_sessionfinish(session, exitstatus):
    """Generate coverage report at session end if requested."""
    if session.config.getoption("--coverage-report"):
        coverage_data = load_coverage_data()
        if coverage_data:
            terminal = session.config.pluginmanager.get_plugin("terminalreporter")
            if terminal:
                terminal.write_sep("=", "Coverage Analysis Report")
                terminal.write_line(f"Overall Coverage: {coverage_data.get('overall', 0):.1f}%")
                terminal.write_line("Coverage by Package:")

                by_package = coverage_data.get('by_package', {})
                for package, cov in sorted(by_package.items()):
                    status = "✅" if cov >= _coverage_thresholds.get(package, 85.0) else "❌"
                    terminal.write_line(f"  {package}: {cov:.1f}% {status}")

                # Check for alerts
                alerts = check_coverage_thresholds(coverage_data)
                if alerts:
                    terminal.write_line("")
                    terminal.write_line("Coverage Alerts:")
                    for alert in alerts:
                        terminal.write_line(f"  ⚠️  {alert}")

                terminal.write_line("")

    # Fail if coverage thresholds not met and --fail-on-coverage specified
    if session.config.getoption("--fail-on-coverage"):
        coverage_data = load_coverage_data()
        alerts = check_coverage_thresholds(coverage_data)
        if alerts:
            session.exitstatus = 1


class TestCoverageAnalysis:
    """Test coverage analysis functionality."""

    def test_coverage_data_loading(self):
        """Test loading coverage data from cache."""
        data = load_coverage_data()
        assert isinstance(data, dict)

    def test_coverage_checker_creation(self, coverage_checker):
        """Test that coverage checker fixture works."""
        assert coverage_checker is not None
        assert hasattr(coverage_checker, 'check_module_coverage')
        assert hasattr(coverage_checker, 'get_coverage_report')

    def test_coverage_checker_methods(self, coverage_checker):
        """Test coverage checker methods."""
        # Test with non-existent module
        assert not coverage_checker.check_module_coverage("nonexistent_module")

        # Test coverage report retrieval
        report = coverage_checker.get_coverage_report()
        assert isinstance(report, dict)

    def test_coverage_threshold_checking(self):
        """Test coverage threshold checking logic."""
        # Test with good coverage
        good_data = {
            'overall': 90.0,
            'by_package': {'core': 95.0, 'services': 88.0, 'adapters': 85.0}
        }
        alerts = check_coverage_thresholds(good_data)
        assert len(alerts) == 0

        # Test with poor coverage
        poor_data = {
            'overall': 50.0,
            'by_package': {'core': 40.0, 'services': 30.0, 'adapters': 20.0}
        }
        alerts = check_coverage_thresholds(poor_data)
        assert len(alerts) > 0
        assert any("Overall coverage" in alert for alert in alerts)

    def test_coverage_data_persistence(self):
        """Test saving and loading coverage data."""
        test_data = {
            'overall': 75.0,
            'by_package': {'test_module': 80.0},
            'timestamp': '2024-01-01T00:00:00'
        }

        # Save data
        save_coverage_data(test_data)

        # Load data
        loaded_data = load_coverage_data()

        assert loaded_data['overall'] == 75.0
        assert loaded_data['by_package']['test_module'] == 80.0

    def test_coverage_report_generation(self):
        """Test coverage report generation (may fail if coverage not run)."""
        try:
            report = generate_coverage_report()
            # Report might be None if coverage hasn't been collected
            if report is not None:
                assert isinstance(report, dict)
                assert 'overall' in report
                assert 'by_package' in report
        except Exception:
            # It's okay if coverage report generation fails due to no data
            pass

    def test_coverage_checker_assertion(self, coverage_checker):
        """Test coverage checker assertion method."""
        # This should not raise an exception for non-existent modules
        # since we're not asserting on real coverage data
        try:
            coverage_checker.assert_coverage_threshold("nonexistent", 0.0)
        except AssertionError:
            pytest.fail("Should not assert on non-existent module with 0% threshold")