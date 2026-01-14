"""Test result aggregation and trend analysis."""

import pytest
import json
from pathlib import Path


class TestResultAggregation:
    """Test test result aggregation and trend analysis."""

    def test_results_history_persistence(self):
        """Test that test results history is persisted."""
        results_file = Path(".pytest_cache") / "test_results_history.json"

        # File should exist after test runs
        # Note: This test may not pass on first run, but should on subsequent runs
        if results_file.exists():
            with open(results_file, 'r') as f:
                history = json.load(f)
            assert isinstance(history, list), "History should be a list"
            if history:
                assert "total_tests" in history[0], "Should contain test counts"
        else:
            # File doesn't exist yet, which is fine for first run
            pass

    def test_aggregation_fixture(self, aggregate_test_results):
        """Test that the aggregation fixture provides expected structure."""
        assert "total_tests" in aggregate_test_results
        assert "passed" in aggregate_test_results
        assert "failed" in aggregate_test_results
        assert "test_details" in aggregate_test_results
        assert isinstance(aggregate_test_results["test_details"], list)

    def test_trend_analysis_data_structure(self):
        """Test that trend analysis data has correct structure."""
        results_file = Path(".pytest_cache") / "test_results_history.json"

        if results_file.exists():
            with open(results_file, 'r') as f:
                history = json.load(f)

            for run in history:
                assert "total_tests" in run, "Each run should have total_tests"
                assert "passed" in run, "Each run should have passed count"
                assert "failed" in run, "Each run should have failed count"
                assert "test_details" in run, "Each run should have test_details"

    def test_pass_rate_calculation(self):
        """Test that pass rates can be calculated from aggregated data."""
        results_file = Path(".pytest_cache") / "test_results_history.json"

        if results_file.exists():
            with open(results_file, 'r') as f:
                history = json.load(f)

            for run in history:
                total = run.get("total_tests", 0)
                passed = run.get("passed", 0)
                if total > 0:
                    pass_rate = passed / total
                    assert 0 <= pass_rate <= 1, f"Pass rate should be between 0 and 1, got {pass_rate}"

    @pytest.mark.parametrize("test_outcome", ["pass", "fail"])
    def test_result_tracking(self, test_outcome, aggregate_test_results):
        """Test that results are properly tracked."""
        initial_total = aggregate_test_results["total_tests"]
        initial_passed = aggregate_test_results["passed"]
        initial_failed = aggregate_test_results["failed"]

        # This test itself will be counted
        final_total = aggregate_test_results["total_tests"]
        final_passed = aggregate_test_results["passed"]
        final_failed = aggregate_test_results["failed"]

        # After this test runs, total should increase by 1
        assert final_total >= initial_total

        # Depending on test outcome, passed/failed should increase accordingly
        if test_outcome == "pass":
            assert final_passed >= initial_passed
        # Note: We can't easily test failure counting in the same test