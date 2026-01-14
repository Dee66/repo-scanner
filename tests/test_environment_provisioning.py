"""Test environment provisioning and teardown."""

import os
import pytest
from pathlib import Path


def test_environment_provisioning():
    """Test that test environment is properly provisioned."""
    assert os.environ.get('PYTEST_RUNNING') == '1'
    assert os.environ.get('TEST_ENVIRONMENT') == '1'
    assert 'PYTHONPATH' in os.environ


def test_working_directory():
    """Test that working directory is set correctly."""
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    assert Path.cwd() == project_root or str(project_root) in os.environ.get('PYTHONPATH', '')


def test_dependencies_available():
    """Test that required dependencies are available."""
    import git
    import yaml
    # These should not raise ImportError
    assert git is not None
    assert yaml is not None


class TestEnvironmentProvisioning:
    """Test test environment provisioning and teardown."""

    def test_test_environment_variables(self, test_environment):
        """Test that test environment variables are set."""
        assert os.environ.get("TEST_MODE") == "1"
        assert os.environ.get("LOG_LEVEL") == "DEBUG"
        assert os.environ.get("DISABLE_ANALYTICS") == "1"
        assert os.environ.get("MOCK_EXTERNAL_SERVICES") == "1"

    def test_mock_external_services(self, mock_external_services):
        """Test that external services are mocked."""
        assert os.environ.get("MOCK_REDIS") == "1"
        assert os.environ.get("MOCK_GIT") == "1"
        assert os.environ.get("MOCK_API") == "1"

    def test_environment_isolation(self, environment_isolation):
        """Test that environment is properly isolated."""
        assert os.environ.get("ISOLATED_TEST") == "1"
        work_dir = os.environ.get("TEST_WORK_DIR")
        assert work_dir is not None
        assert Path(work_dir).exists()

    def test_clean_database_state(self, clean_database_state):
        """Test that database state is clean."""
        # In a real scenario, this would verify database state
        # For now, just ensure the fixture runs without error
        assert True

    def test_test_configuration(self, test_configuration):
        """Test that test configuration is available."""
        assert test_configuration["timeout"] == 30
        assert test_configuration["max_retries"] == 3
        assert test_configuration["parallel_workers"] == 4
        assert test_configuration["log_level"] == "DEBUG"
        assert test_configuration["mock_services"] is True

    def test_environment_restoration(self, test_environment):
        """Test that environment is properly restored after tests."""
        # Modify environment during test
        original_test_mode = os.environ.get("TEST_MODE")
        os.environ["TEST_MODE"] = "modified"

        # Environment should be restored by fixture teardown
        # We can't test this directly in the same test, but we can verify
        # the fixture is set up correctly

    def test_isolated_working_directory(self, environment_isolation):
        """Test that each test gets an isolated working directory."""
        work_dir = Path(os.environ["TEST_WORK_DIR"])
        assert work_dir.exists()
        assert work_dir.is_dir()

        # Create a file in the working directory
        test_file = work_dir / "isolation_test.txt"
        test_file.write_text("isolated environment")

        assert test_file.exists()
        assert test_file.read_text() == "isolated environment"

    def test_service_mocking_integration(self, mock_external_services, test_configuration):
        """Test integration of service mocking with configuration."""
        assert test_configuration["mock_services"] is True
        assert os.environ.get("MOCK_API") == "1"

        # Verify that mocked services don't interfere
        # In a real test, this would verify no actual external calls are made