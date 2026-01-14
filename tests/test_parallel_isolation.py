"""Test parallel execution isolation."""

import os
import pytest
from pathlib import Path


class TestParallelIsolation:
    """Test that parallel execution provides proper isolation."""

    def test_cache_directory_isolation(self, tmp_path):
        """Test that each test gets its own cache directories."""
        scanner_cache = os.environ.get("SCANNER_CACHE_DIR")
        repo_cache = os.environ.get("REPO_CACHE_DIR")

        # Verify environment variables are set
        assert scanner_cache is not None, "SCANNER_CACHE_DIR should be set"
        assert repo_cache is not None, "REPO_CACHE_DIR should be set"

        # Verify directories exist
        assert Path(scanner_cache).exists(), f"Scanner cache dir {scanner_cache} should exist"
        assert Path(repo_cache).exists(), f"Repo cache dir {repo_cache} should exist"

        # In parallel execution, cache dirs are either per-test (tmp_path) or per-worker
        # Both provide isolation, just at different levels
        cache_is_isolated = (
            str(tmp_path) in scanner_cache or  # Per-test isolation
            "worker_" in scanner_cache  # Per-worker isolation
        )
        assert cache_is_isolated, f"Cache dir {scanner_cache} should be isolated (per-test or per-worker)"

        # Create a test file in the cache to verify isolation
        test_file = Path(scanner_cache) / "isolation_test.txt"
        test_file.write_text(f"test_data_{tmp_path.name}")

        # Verify the file was created
        assert test_file.exists()
        assert test_file.read_text() == f"test_data_{tmp_path.name}"

    def test_global_state_reset(self):
        """Test that global state is properly reset between tests."""
        from src.core.system_config import get_system_config, reset_system_config

        # Get initial config
        config1 = get_system_config()
        original_name = config1.name

        # Modify config
        config1.name = "modified_for_test"

        # Reset config
        reset_system_config()

        # Get config again - should be reset
        config2 = get_system_config()
        assert config2.name == original_name, "Global config should be reset between tests"

    def test_worker_isolation(self, worker_id):
        """Test that worker-specific isolation is working."""
        if worker_id != "master":
            # In parallel execution, each worker should have its own environment
            scanner_cache = os.environ.get("SCANNER_CACHE_DIR")
            assert worker_id in scanner_cache, f"Worker {worker_id} should have worker-specific cache dir"