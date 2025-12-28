"""Pytest configuration and fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


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