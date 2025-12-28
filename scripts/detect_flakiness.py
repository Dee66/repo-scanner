#!/usr/bin/env python3
"""Flakiness detection script for test suite.

Runs tests multiple times to detect flaky tests that pass/fail intermittently.
"""

import subprocess
import sys
import json
from pathlib import Path
from collections import defaultdict


def run_tests_once(run_id: int) -> dict:
    """Run the test suite once and return results."""
    print(f"Starting test run {run_id}...")

    cmd = [sys.executable, "-m", "pytest", "--tb=no", "-q"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        # Parse the last line for results
        last_line = result.stdout.strip().split('\n')[-1] if result.stdout.strip() else ""
        passed = "passed" in last_line and "failed" not in last_line
        return {
            "run_id": run_id,
            "returncode": result.returncode,
            "passed": passed,
            "summary": last_line
        }
    except subprocess.TimeoutExpired:
        return {
            "run_id": run_id,
            "returncode": -1,
            "stdout": "",
            "stderr": "Timeout",
            "passed": False
        }


def analyze_flakiness(results: list) -> dict:
    """Analyze test results for flakiness."""
    flaky_tests = []
    consistent_failures = []
    consistent_passes = []

    # For now, we'll analyze at the suite level
    # In a more advanced version, we'd parse individual test results

    total_runs = len(results)
    passed_runs = sum(1 for r in results if r["passed"])
    failed_runs = total_runs - passed_runs

    if failed_runs > 0 and passed_runs > 0:
        flakiness_rate = failed_runs / total_runs
        return {
            "flaky": True,
            "flakiness_rate": flakiness_rate,
            "passed_runs": passed_runs,
            "failed_runs": failed_runs,
            "total_runs": total_runs,
            "flaky_tests": ["suite-level-flakiness-detected"],
            "consistent_failures": [],
            "consistent_passes": []
        }
    else:
        return {
            "flaky": False,
            "flakiness_rate": 0.0,
            "passed_runs": passed_runs,
            "failed_runs": failed_runs,
            "total_runs": total_runs,
            "flaky_tests": [],
            "consistent_failures": [],
            "consistent_passes": []
        }


def main():
    """Main flakiness detection function."""
    num_runs = 5  # Run tests 5 times to detect flakiness

    print(f"Running flakiness detection with {num_runs} test runs...")
    print("=" * 50)

    results = []
    for i in range(1, num_runs + 1):
        result = run_tests_once(i)
        results.append(result)
        status = "PASSED" if result["passed"] else "FAILED"
        print(f"Run {i}: {status}")

    print("=" * 50)

    analysis = analyze_flakiness(results)

    if analysis["flaky"]:
        print("❌ FLAKY TESTS DETECTED!")
        print(".2f")
        print(f"Passed runs: {analysis['passed_runs']}")
        print(f"Failed runs: {analysis['failed_runs']}")
        print(f"Flaky tests: {', '.join(analysis['flaky_tests'])}")
        return 1
    else:
        print("✅ NO FLAKY TESTS DETECTED")
        print(f"All {analysis['total_runs']} runs {'passed' if analysis['passed_runs'] > 0 else 'failed'} consistently")
        return 0


if __name__ == "__main__":
    sys.exit(main())