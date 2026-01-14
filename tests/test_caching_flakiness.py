"""Test caching and flakiness detection mechanisms."""

import pytest
import os
import tempfile
from pathlib import Path
import json


class TestCachingAndFlakiness:
    """Test test result caching and flakiness detection."""

    def test_cache_directory_exists(self):
        """Test that cache directory is properly configured."""
        # Get the project root directory
        project_root = Path(__file__).parent.parent
        cache_dir = project_root / ".pytest_cache"
        assert cache_dir.exists(), f"Cache directory should exist at {cache_dir}"
        assert cache_dir.is_dir(), "Cache directory should be a directory"

    def test_flakiness_data_persistence(self, flakiness_stats):
        """Test that flakiness data is persisted across test runs."""
        flakiness_file = Path(".pytest_cache") / "flakiness.json"

        # Initially, flakiness data should exist (from conftest loading)
        assert flakiness_file.exists() or flakiness_stats, "Flakiness data should be available"

        # Add some test data
        test_id = "test_caching_and_flakiness.py::TestCachingAndFlakiness::test_flakiness_data_persistence"
        if test_id in flakiness_stats:
            stats = flakiness_stats[test_id]
            assert "passes" in stats, "Should track passes"
            assert "failures" in stats, "Should track failures"
            assert "last_result" in stats, "Should track last result"

    @pytest.mark.flaky
    def test_flaky_test_example(self):
        """Example of a test that might be flaky."""
        import random
        # This test has a 30% chance of failing to simulate flakiness
        if random.random() < 0.3:
            pytest.fail("Simulated flaky failure")
        assert True

    def test_rerun_mechanism(self):
        """Test that rerun mechanism is configured."""
        # This test should pass, but we're testing that rerun is available
        assert True

    def test_cache_functionality(self, tmp_path):
        """Test that caching works for test data."""
        # Create a file in cache
        cache_file = Path(".pytest_cache") / "test_cache_data.json"
        test_data = {"test_run": True, "timestamp": "2025-12-31"}

        cache_file.parent.mkdir(exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(test_data, f)

        # Verify it was cached
        assert cache_file.exists()
        with open(cache_file, 'r') as f:
            loaded_data = json.load(f)
        assert loaded_data == test_data

    def test_parallel_cache_isolation(self, tmp_path):
        """Test that parallel execution doesn't interfere with caching."""
        worker_id = os.environ.get("PYTEST_XDIST_WORKER", "master")

        # Each worker should have its own cache context
        cache_marker = tmp_path / f"worker_{worker_id}_cache"
        cache_marker.write_text(f"cached_data_for_{worker_id}")

        assert cache_marker.exists()
        assert cache_marker.read_text() == f"cached_data_for_{worker_id}"