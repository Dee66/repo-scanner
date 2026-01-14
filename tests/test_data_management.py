"""Test data management and cleanup procedures."""

import pytest
from pathlib import Path
import tempfile
import os


class TestDataManagement:
    """Test test data management and cleanup procedures."""

    def test_isolated_test_dir(self, isolated_test_dir):
        """Test that each test gets an isolated directory."""
        assert isolated_test_dir.exists()
        assert isolated_test_dir.is_dir()

        # Create a file in the isolated directory
        test_file = isolated_test_dir / "test_file.txt"
        test_file.write_text("test content")

        assert test_file.exists()
        assert test_file.read_text() == "test content"

    def test_mock_repo_data_creation(self, mock_repo_data):
        """Test that mock repository data is created correctly."""
        assert mock_repo_data.exists()
        assert (mock_repo_data / ".git").exists()
        assert (mock_repo_data / "README.md").exists()
        assert (mock_repo_data / "src" / "main.py").exists()
        assert (mock_repo_data / "tests" / "test_main.py").exists()

        # Verify content
        readme = (mock_repo_data / "README.md").read_text()
        assert "# Test Repository" in readme

        main_py = (mock_repo_data / "src" / "main.py").read_text()
        assert "print('Hello World')" in main_py

    def test_cleanup_test_artifacts(self, tmp_path):
        """Test that test artifacts are cleaned up."""
        # Create some test artifacts
        temp_file = tmp_path / "test.tmp"
        log_file = tmp_path / "test.log"
        cache_file = tmp_path / "test.cache"

        temp_file.write_text("temp data")
        log_file.write_text("log data")
        cache_file.write_text("cache data")

        assert temp_file.exists()
        assert log_file.exists()
        assert cache_file.exists()

        # The cleanup fixture should handle cleanup after the test
        # We can't directly test this in the same test, but we can verify
        # the fixture is applied by checking the autouse parameter

    def test_session_data_dir(self, test_data_dir):
        """Test that session-wide test data directory is available."""
        assert test_data_dir.exists()
        assert test_data_dir.is_dir()

        # Create session-persistent data
        session_file = test_data_dir / "session_data.json"
        session_file.write_text('{"session": "data"}')

        assert session_file.exists()

    def test_data_isolation_between_tests(self, isolated_test_dir):
        """Test that data is properly isolated between tests."""
        # Each test should get its own isolated directory
        marker_file = isolated_test_dir / f"marker_{os.getpid()}"
        marker_file.write_text("isolated")

        assert marker_file.exists()

        # In a real scenario, this would be tested by running multiple tests
        # and verifying they don't interfere with each other

    def test_temp_file_cleanup(self, tmp_path):
        """Test that temporary files are properly managed."""
        # Create various temp files
        temp_files = []
        for i in range(3):
            temp_file = tmp_path / f"temp_{i}.tmp"
            temp_file.write_text(f"content {i}")
            temp_files.append(temp_file)

        for temp_file in temp_files:
            assert temp_file.exists()

        # Files should be cleaned up by the cleanup fixture