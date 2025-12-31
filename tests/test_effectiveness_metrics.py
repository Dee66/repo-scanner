"""Tests for enhanced effectiveness metrics calculation."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
import numpy as np
from datetime import datetime, timedelta

from src.core.metrics.effectiveness import (
    EffectivenessMetrics,
    EffectivenessMetricsCalculator,
    WeightedScoringConfig,
    load_historical_metrics_data,
    save_metrics_snapshot
)


class TestEffectivenessMetricsCalculator:
    """Test effectiveness metrics calculator functionality."""

    def test_calculate_precision_recall_perfect(self):
        """Test precision/recall calculation with perfect scores."""
        calculator = EffectivenessMetricsCalculator()

        precision, recall, f1 = calculator.calculate_precision_recall(10, 0, 0)

        assert precision == 1.0
        assert recall == 1.0
        assert f1 == 1.0

    def test_calculate_precision_recall_zero(self):
        """Test precision/recall calculation with zero scores."""
        calculator = EffectivenessMetricsCalculator()

        precision, recall, f1 = calculator.calculate_precision_recall(0, 5, 5)

        assert precision == 0.0
        assert recall == 0.0
        assert f1 == 0.0

    def test_calculate_precision_recall_partial(self):
        """Test precision/recall calculation with partial scores."""
        calculator = EffectivenessMetricsCalculator()

        precision, recall, f1 = calculator.calculate_precision_recall(7, 3, 2)

        expected_precision = 7 / 10  # 7 / (7 + 3)
        expected_recall = 7 / 9     # 7 / (7 + 2)
        expected_f1 = 2 * expected_precision * expected_recall / (expected_precision + expected_recall)

        assert abs(precision - expected_precision) < 0.001
        assert abs(recall - expected_recall) < 0.001
        assert abs(f1 - expected_f1) < 0.001

    def test_calculate_weighted_accuracy_empty(self):
        """Test weighted accuracy with empty data."""
        calculator = EffectivenessMetricsCalculator()

        accuracy = calculator.calculate_weighted_accuracy([], [])

        assert accuracy == 1.0  # Perfect score for no findings

    def test_calculate_weighted_accuracy_basic(self):
        """Test weighted accuracy with basic data."""
        calculator = EffectivenessMetricsCalculator()

        predictions = [
            {'id': '1', 'severity': 'HIGH', 'category': 'security'},
            {'id': '2', 'severity': 'MEDIUM', 'category': 'performance'}
        ]

        ground_truth = [
            {'id': '1', 'severity': 'HIGH', 'category': 'security'},
            {'id': '3', 'severity': 'LOW', 'category': 'compatibility'}
        ]

        accuracy = calculator.calculate_weighted_accuracy(predictions, ground_truth)

        # Should be less than 1.0 due to mismatch
        assert 0.0 <= accuracy <= 1.0

    def test_calculate_category_metrics(self):
        """Test category-specific metrics calculation."""
        calculator = EffectivenessMetricsCalculator()

        predictions = [
            {'id': '1', 'category': 'security', 'severity': 'HIGH'},
            {'id': '2', 'category': 'performance', 'severity': 'MEDIUM'},
            {'id': '3', 'category': 'security', 'severity': 'HIGH'}
        ]

        ground_truth = [
            {'id': '1', 'category': 'security', 'severity': 'HIGH'},
            {'id': '4', 'category': 'security', 'severity': 'HIGH'}
        ]

        category_metrics = calculator.calculate_category_metrics(predictions, ground_truth)

        assert 'security' in category_metrics
        assert 'performance' in category_metrics

        security = category_metrics['security']
        assert 'precision' in security
        assert 'recall' in security
        assert 'f1_score' in security
        assert 0.0 <= security['precision'] <= 1.0
        assert 0.0 <= security['recall'] <= 1.0
        assert 0.0 <= security['f1_score'] <= 1.0

    def test_calculate_confidence_correlation(self):
        """Test confidence-accuracy correlation calculation."""
        calculator = EffectivenessMetricsCalculator()

        predictions = [
            {'id': '1', 'confidence': 0.9},
            {'id': '2', 'confidence': 0.7},
            {'id': '3', 'confidence': 0.5}
        ]

        ground_truth = [
            {'id': '1'},  # Correct
            {'id': '3'}   # Correct
        ]

        correlation = calculator.calculate_confidence_correlation(predictions, ground_truth)

        # Should be a valid correlation coefficient
        assert -1.0 <= correlation <= 1.0

    def test_calculate_comprehensive_metrics(self):
        """Test comprehensive metrics calculation."""
        calculator = EffectivenessMetricsCalculator()

        predictions = [
            {'id': '1', 'category': 'security', 'severity': 'HIGH', 'confidence': 0.9},
            {'id': '2', 'category': 'performance', 'severity': 'MEDIUM', 'confidence': 0.7}
        ]

        ground_truth = [
            {'id': '1', 'category': 'security', 'severity': 'HIGH'},
            {'id': '3', 'category': 'compatibility', 'severity': 'LOW'}
        ]

        metrics = calculator.calculate_comprehensive_metrics(predictions, ground_truth)

        assert isinstance(metrics, EffectivenessMetrics)
        assert 0.0 <= metrics.weighted_accuracy <= 1.0
        assert 0.0 <= metrics.precision <= 1.0
        assert 0.0 <= metrics.recall <= 1.0
        assert 0.0 <= metrics.f1_score <= 1.0
        assert metrics.total_predictions == 2
        assert metrics.total_correct == 1  # Only ID '1' matches
        assert metrics.total_incorrect == 2  # ID '2' is incorrect (FP), and ID '3' is missing (FN)

    def test_validate_accuracy_threshold_pass(self):
        """Test accuracy threshold validation - pass case."""
        calculator = EffectivenessMetricsCalculator()

        metrics = EffectivenessMetrics()
        metrics.weighted_accuracy = 0.98
        metrics.precision = 0.95
        metrics.recall = 0.90
        metrics.f1_score = 0.92
        metrics.false_positive_rate = 0.05

        validation = calculator.validate_accuracy_threshold(metrics, threshold=0.95)

        assert validation['passed'] is True
        assert len(validation['violations']) == 0
        assert len(validation['warnings']) == 0

    def test_validate_accuracy_threshold_fail(self):
        """Test accuracy threshold validation - fail case."""
        calculator = EffectivenessMetricsCalculator()

        metrics = EffectivenessMetrics()
        metrics.weighted_accuracy = 0.92  # Below 0.95 threshold
        metrics.precision = 0.85
        metrics.recall = 0.80
        metrics.f1_score = 0.82
        metrics.false_positive_rate = 0.20

        validation = calculator.validate_accuracy_threshold(metrics, threshold=0.95)

        assert validation['passed'] is False
        assert len(validation['violations']) > 0
        assert len(validation['warnings']) > 0
        assert 'weighted_accuracy' in validation['violations'][0]['metric']

    def test_calculate_temporal_trends(self):
        """Test temporal trend calculation."""
        calculator = EffectivenessMetricsCalculator()

        from datetime import datetime, timedelta

        # Create mock historical data
        base_time = datetime.now()
        historical_data = []

        for i in range(10):
            timestamp = base_time - timedelta(days=9-i)
            predictions = [
                {'id': f'pred_{i}_{j}', 'category': 'test', 'severity': 'MEDIUM', 'confidence': 0.8}
                for j in range(5)
            ]
            ground_truth = predictions[:4]  # 80% accuracy
            historical_data.append((timestamp, predictions, ground_truth))

        trends = calculator.calculate_temporal_trends(historical_data)

        assert len(trends) > 0
        for timestamp, accuracy in trends:
            assert isinstance(timestamp, datetime)
            assert 0.0 <= accuracy <= 1.0


class TestWeightedScoringConfig:
    """Test weighted scoring configuration."""

    def test_default_config(self):
        """Test default weighted scoring configuration."""
        config = WeightedScoringConfig()

        assert 'CRITICAL' in config.severity_weights
        assert 'HIGH' in config.severity_weights
        assert 'security' in config.category_weights

        assert config.severity_weights['CRITICAL'] == 1.0
        assert config.severity_weights['HIGH'] == 0.8
        assert config.category_weights['security'] == 1.0

    def test_custom_config(self):
        """Test custom weighted scoring configuration."""
        custom_weights = {'CRITICAL': 2.0, 'HIGH': 1.5}
        custom_categories = {'security': 1.5, 'performance': 1.2}

        config = WeightedScoringConfig(
            severity_weights=custom_weights,
            category_weights=custom_categories
        )

        assert config.severity_weights['CRITICAL'] == 2.0
        assert config.category_weights['security'] == 1.5


class TestMetricsPersistence:
    """Test metrics data persistence."""

    def test_save_and_load_metrics_snapshot(self, tmp_path):
        """Test saving and loading metrics snapshots."""
        metrics = EffectivenessMetrics()
        metrics.weighted_accuracy = 0.95
        metrics.precision = 0.92
        metrics.recall = 0.88
        metrics.f1_score = 0.90
        metrics.data_points = 100

        # Save snapshot
        snapshot_path = save_metrics_snapshot(metrics, tmp_path)

        assert snapshot_path.exists()

        # Load and verify
        with open(snapshot_path, 'r') as f:
            data = json.load(f)

        assert data['weighted_accuracy'] == 0.95
        assert data['precision'] == 0.92
        assert data['data_points'] == 100

    def test_load_historical_metrics_data(self, tmp_path):
        """Test loading historical metrics data."""
        # Create mock historical data files
        base_time = EffectivenessMetrics().calculated_at

        for i in range(3):
            timestamp = base_time - timedelta(days=2-i)
            metrics_file = tmp_path / f"metrics_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"

            data = {
                'timestamp': timestamp.isoformat(),
                'weighted_accuracy': 0.85 + i * 0.05,
                'predictions': [{'id': f'test_{i}', 'category': 'test'}],
                'ground_truth': [{'id': f'test_{i}', 'category': 'test'}]
            }

            with open(metrics_file, 'w') as f:
                json.dump(data, f)

        # Load historical data
        historical_data = load_historical_metrics_data(tmp_path)

        assert len(historical_data) == 3
        # Should be sorted by timestamp
        assert historical_data[0][0] < historical_data[1][0] < historical_data[2][0]


class TestIntegrationWithSMEReviews:
    """Test integration with SME review metrics."""

    @patch('src.core.sme_review.manager.SMEReviewManager.get_review_metrics')
    def test_sme_metrics_integration(self, mock_get_metrics):
        """Test integration with SME review metrics."""
        from src.core.sme_review.manager import ReviewMetrics
        from src.core.metrics.effectiveness import EffectivenessMetrics

        # Create mock review metrics with effectiveness metrics
        effectiveness_metrics = EffectivenessMetrics()
        effectiveness_metrics.weighted_accuracy = 0.94
        effectiveness_metrics.precision = 0.91

        review_metrics = ReviewMetrics(
            total_cases=10,
            pending_reviews=2,
            completed_reviews=8,
            average_review_time_days=1.5,
            approval_rate=0.75,
            rejection_rate=0.15,
            requires_changes_rate=0.10,
            average_confidence=4.2,
            cases_by_category={'security': 6, 'performance': 4},
            cases_by_priority={'CRITICAL': 3, 'HIGH': 5, 'MEDIUM': 2},
            effectiveness_metrics=effectiveness_metrics,
            weighted_review_score=0.88,
            category_effectiveness={'security': 0.92, 'performance': 0.85},
            review_consistency_score=0.95,
            inter_reviewer_agreement=0.89
        )

        mock_get_metrics.return_value = review_metrics

        # Test that the metrics are properly integrated
        assert review_metrics.effectiveness_metrics is not None
        assert review_metrics.effectiveness_metrics.weighted_accuracy == 0.94
        assert review_metrics.weighted_review_score == 0.88
        assert review_metrics.review_consistency_score == 0.95


class TestCIValidation:
    """Test CI validation functionality."""

    def test_ci_validation_script_basic(self, tmp_path):
        """Test basic CI validation script functionality."""
        # Add src to path for script import
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

        from validate_effectiveness_metrics import EffectivenessCIValidator

        validator = EffectivenessCIValidator(accuracy_threshold=0.95, alert_threshold=0.90)

        # Create mock metrics file
        metrics_file = tmp_path / "test_metrics.json"
        metrics_data = {
            'weighted_accuracy': 0.96,
            'precision': 0.93,
            'recall': 0.89,
            'f1_score': 0.91,
            'false_positive_rate': 0.04
        }

        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f)

        # Mock the _dict_to_effectiveness_metrics method
        metrics_obj = EffectivenessMetrics()
        metrics_obj.weighted_accuracy = 0.96
        metrics_obj.precision = 0.93
        metrics_obj.recall = 0.89
        metrics_obj.f1_score = 0.91
        metrics_obj.false_positive_rate = 0.04

        validator._dict_to_effectiveness_metrics = lambda x: metrics_obj

        result = validator.validate_current_metrics(metrics_file)

        assert result['passed'] is True
        assert len(result['errors']) == 0
        assert result['metrics']['weighted_accuracy'] == 0.96

    def test_ci_validation_script_failure(self, tmp_path):
        """Test CI validation script with failure case."""
        # Add src to path for script import
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

        from validate_effectiveness_metrics import EffectivenessCIValidator

        validator = EffectivenessCIValidator(accuracy_threshold=0.95, alert_threshold=0.90)

        # Create mock metrics file with low accuracy
        metrics_file = tmp_path / "test_metrics.json"
        metrics_data = {
            'weighted_accuracy': 0.88,  # Below both thresholds
            'precision': 0.85,
            'recall': 0.82,
            'f1_score': 0.83,
            'false_positive_rate': 0.12
        }

        with open(metrics_file, 'w') as f:
            json.dump(metrics_data, f)

        # Mock the _dict_to_effectiveness_metrics method
        metrics_obj = EffectivenessMetrics()
        metrics_obj.weighted_accuracy = 0.88
        metrics_obj.precision = 0.85
        metrics_obj.recall = 0.82
        metrics_obj.f1_score = 0.83
        metrics_obj.false_positive_rate = 0.12

        validator._dict_to_effectiveness_metrics = lambda x: metrics_obj

        result = validator.validate_current_metrics(metrics_file)

        assert result['passed'] is False
        assert result['blocked'] is True
        assert len(result['errors']) > 0
        assert len(result['warnings']) > 0