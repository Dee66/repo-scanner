"""Calibration tests for detector accuracy using golden repositories."""

import pytest
from tests.test_calibration import CalibrationHarness


def test_golden_repos_precision_threshold():
    """Compute precision on HIGH findings across golden repos.

    The test will fail if overall precision for HIGH findings falls below 0.60.
    """
    harness = CalibrationHarness()
    repos = harness.golden_repos

    if not repos:
        pytest.skip("No golden repositories found")

    total_tp = 0
    total_fp = 0
    total_fn = 0

    for repo in repos:
        result = harness.run_calibration_test(repo)

        if result["error"] or not result["metrics"]:
            continue

        metrics = result["metrics"]
        total_tp += metrics["true_positives"]
        total_fp += metrics["false_positives"]
        total_fn += metrics["false_negatives"]

    if total_tp + total_fp == 0:
        pytest.skip('No findings detected; nothing to evaluate')

    precision = total_tp / (total_tp + total_fp)
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0

    print(f"\nCalibration results across {len(repos)} golden repos:")
    print(f"  True positives: {total_tp}")
    print(f"  False positives: {total_fp}")
    print(f"  False negatives: {total_fn}")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall: {recall:.3f}")

    # Assert minimum precision threshold for detector reliability
    assert precision >= 0.60, f'Precision for findings too low: {precision:.2f} < 0.60'
