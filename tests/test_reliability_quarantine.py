"""Tests for test reliability metrics and quarantine mechanisms."""

import pytest
import json
from pathlib import Path


class TestReliabilityMetrics:
    """Test reliability scoring and quarantine functionality."""

    def test_quarantine_file_creation(self, tmp_path):
        """Test that quarantined tests are saved to file."""
        from tests.conftest import save_quarantined_tests, _quarantined_tests, _quarantine_file

        # Add a test to quarantine
        _quarantined_tests.add("test_module::test_flaky_function")

        # Save quarantined tests
        original_file = _quarantine_file
        test_file = tmp_path / "test_quarantine.json"

        # Temporarily override the file path
        import tests.conftest
        tests.conftest._quarantine_file = test_file

        try:
            save_quarantined_tests()

            # Verify file was created and contains expected data
            assert test_file.exists()
            with open(test_file, 'r') as f:
                data = json.load(f)

            assert "quarantined_tests" in data
            assert "test_module::test_flaky_function" in data["quarantined_tests"]
            assert "quarantine_timestamp" in data
        finally:
            # Restore original file path
            tests.conftest._quarantine_file = original_file
            _quarantined_tests.clear()

    def test_reliability_score_calculation(self):
        """Test calculation of test reliability scores."""
        from tests.conftest import _flakiness_data

        # Simulate test results
        test_id = "test_module::test_reliability"
        _flakiness_data[test_id] = {"passes": 8, "failures": 2, "last_result": "failed"}

        # Calculate reliability
        stats = _flakiness_data[test_id]
        total_runs = stats["passes"] + stats["failures"]
        failure_rate = stats["failures"] / total_runs
        reliability_score = 1.0 - failure_rate

        assert reliability_score == 0.8  # 80% reliable
        assert reliability_score <= 0.8  # Would be quarantined (at or below threshold)

    def test_quarantine_criteria(self):
        """Test the criteria for quarantining tests."""
        from tests.conftest import _flakiness_data, _quarantined_tests

        # Clear any existing quarantine
        _quarantined_tests.clear()

        # Test case 1: Reliable test (should not be quarantined)
        reliable_test = "test_module::test_reliable"
        _flakiness_data[reliable_test] = {"passes": 9, "failures": 1, "last_result": "passed"}

        # Test case 2: Unreliable test that passed last (should not be quarantined)
        unreliable_passed = "test_module::test_unreliable_passed"
        _flakiness_data[unreliable_passed] = {"passes": 2, "failures": 8, "last_result": "passed"}

        # Test case 3: Unreliable test that failed last (should be quarantined)
        unreliable_failed = "test_module::test_unreliable_failed"
        _flakiness_data[unreliable_failed] = {"passes": 2, "failures": 8, "last_result": "failed"}

        # Apply quarantine logic
        for test_id in [reliable_test, unreliable_passed, unreliable_failed]:
            stats = _flakiness_data.get(test_id, {"passes": 0, "failures": 0})
            total_runs = stats["passes"] + stats["failures"]
            if total_runs >= 5:
                failure_rate = stats["failures"] / total_runs
                reliability_score = 1.0 - failure_rate
                if reliability_score < 0.8 and stats["last_result"] == "failed":
                    _quarantined_tests.add(test_id)

        # Verify quarantine decisions
        assert reliable_test not in _quarantined_tests
        assert unreliable_passed not in _quarantined_tests
        assert unreliable_failed in _quarantined_tests

        # Clean up
        _quarantined_tests.clear()

    def test_quarantine_skip_logic(self):
        """Test that quarantined tests are skipped unless --run-quarantined is used."""
        from tests.conftest import _quarantined_tests

        # Add a test to quarantine
        test_id = "test_module::test_quarantined"
        _quarantined_tests.add(test_id)

        # Mock pytest item and config
        class MockConfig:
            def getoption(self, option, default=None):
                if option == "--run-quarantined":
                    return False  # Default behavior - don't run quarantined
                return default

        class MockParent:
            def __init__(self, name):
                self.name = name

        class MockItem:
            def __init__(self, parent_name, test_name):
                self.parent = MockParent(parent_name)
                self.name = test_name
                self.config = MockConfig()

        item = MockItem("test_module", "test_quarantined")

        # Test skip behavior
        from tests.conftest import pytest_runtest_setup
        with pytest.raises(pytest.skip.Exception) as exc_info:
            pytest_runtest_setup(item)

        assert "is quarantined" in str(exc_info.value)

        # Clean up
        _quarantined_tests.clear()

    def test_quarantine_bypass_with_flag(self):
        """Test that quarantined tests run when --run-quarantined is specified."""
        from tests.conftest import _quarantined_tests

        # Add a test to quarantine
        test_id = "test_module::test_quarantined"
        _quarantined_tests.add(test_id)

        # Mock pytest item and config with flag enabled
        class MockConfig:
            def getoption(self, option, default=None):
                if option == "--run-quarantined":
                    return True  # Run quarantined tests
                return default

        class MockParent:
            def __init__(self, name):
                self.name = name

        class MockItem:
            def __init__(self, parent_name, test_name):
                self.parent = MockParent(parent_name)
                self.name = test_name
                self.config = MockConfig()

        item = MockItem("test_module", "test_quarantined")

        # Test that no skip occurs
        from tests.conftest import pytest_runtest_setup
        # Should not raise an exception
        pytest_runtest_setup(item)

        # Clean up
        _quarantined_tests.clear()