"""Enhanced Effectiveness Metrics Calculation Module.

Provides comprehensive metrics calculation with precision/recall analysis,
weighted scoring, and accuracy validation for the Repository Intelligence Scanner.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class EffectivenessMetrics:
    """Comprehensive effectiveness metrics with precision/recall analysis."""

    # Basic metrics
    total_predictions: int = 0
    total_correct: int = 0
    total_incorrect: int = 0

    # Precision/Recall metrics
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0

    # Weighted scoring
    weighted_accuracy: float = 0.0
    severity_weights: Dict[str, float] = field(default_factory=lambda: {
        'CRITICAL': 1.0,
        'HIGH': 0.8,
        'MEDIUM': 0.6,
        'LOW': 0.4,
        'INFO': 0.2
    })

    # Category-specific metrics
    category_precision: Dict[str, float] = field(default_factory=dict)
    category_recall: Dict[str, float] = field(default_factory=dict)
    category_f1: Dict[str, float] = field(default_factory=dict)

    # Temporal metrics
    accuracy_trend: List[Tuple[datetime, float]] = field(default_factory=list)
    rolling_accuracy_7d: float = 0.0
    rolling_accuracy_30d: float = 0.0

    # Confidence metrics
    confidence_accuracy_correlation: float = 0.0
    high_confidence_accuracy: float = 0.0
    low_confidence_accuracy: float = 0.0

    # Performance metrics
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    true_positive_rate: float = 0.0
    true_negative_rate: float = 0.0

    # Metadata
    calculated_at: datetime = field(default_factory=datetime.now)
    data_points: int = 0
    time_window_days: int = 30


@dataclass
class WeightedScoringConfig:
    """Configuration for weighted scoring system."""

    severity_weights: Dict[str, float] = field(default_factory=lambda: {
        'CRITICAL': 1.0,
        'HIGH': 0.8,
        'MEDIUM': 0.6,
        'LOW': 0.4,
        'INFO': 0.2
    })

    category_weights: Dict[str, float] = field(default_factory=lambda: {
        'security': 1.0,
        'performance': 0.9,
        'reliability': 0.9,
        'maintainability': 0.7,
        'compatibility': 0.6
    })

    confidence_multiplier: float = 0.1  # Additional weight for high confidence


class EffectivenessMetricsCalculator:
    """Calculator for comprehensive effectiveness metrics."""

    def __init__(self, config: Optional[WeightedScoringConfig] = None):
        self.config = config or WeightedScoringConfig()
        self.logger = logging.getLogger(__name__)

    def calculate_precision_recall(self,
                                 true_positives: int,
                                 false_positives: int,
                                 false_negatives: int) -> Tuple[float, float, float]:
        """Calculate precision, recall, and F1-score.

        Args:
            true_positives: Correct positive predictions
            false_positives: Incorrect positive predictions
            false_negatives: Missed positive cases

        Returns:
            Tuple of (precision, recall, f1_score)
        """
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return precision, recall, f1_score

    def calculate_weighted_accuracy(self,
                                  predictions: List[Dict[str, Any]],
                                  ground_truth: List[Dict[str, Any]]) -> float:
        """Calculate weighted accuracy based on severity and category.

        Args:
            predictions: List of predicted findings
            ground_truth: List of actual findings

        Returns:
            Weighted accuracy score (0.0 to 1.0)
        """
        if not predictions and not ground_truth:
            return 1.0  # Perfect score if no findings

        total_weight = 0.0
        weighted_correct = 0.0

        # Create lookup dictionaries
        pred_lookup = {(p.get('id'), p.get('severity', 'MEDIUM')): p for p in predictions}
        truth_lookup = {(t.get('id'), t.get('severity', 'MEDIUM')): t for t in ground_truth}

        # Check all ground truth items
        for (item_id, severity), truth_item in truth_lookup.items():
            weight = self.config.severity_weights.get(severity.upper(), 0.5)
            category = truth_item.get('category', 'unknown')
            category_weight = self.config.category_weights.get(category.lower(), 0.5)
            combined_weight = weight * category_weight

            total_weight += combined_weight

            # Check if this item was correctly predicted
            if (item_id, severity) in pred_lookup:
                pred_item = pred_lookup[(item_id, severity)]
                confidence = pred_item.get('confidence', 0.5)
                confidence_bonus = confidence * self.config.confidence_multiplier

                # Consider it correct if predicted with reasonable confidence
                if confidence >= 0.7:
                    weighted_correct += combined_weight * (1.0 + confidence_bonus)
                else:
                    weighted_correct += combined_weight * 0.5  # Partial credit

        # Check for false positives (predictions not in ground truth)
        for (item_id, severity), pred_item in pred_lookup.items():
            if (item_id, severity) not in truth_lookup:
                weight = self.config.severity_weights.get(severity.upper(), 0.5)
                category = pred_item.get('category', 'unknown')
                category_weight = self.config.category_weights.get(category.lower(), 0.5)
                combined_weight = weight * category_weight

                total_weight += combined_weight
                # Penalize false positives
                weighted_correct += combined_weight * 0.1  # Small penalty

        return weighted_correct / total_weight if total_weight > 0 else 0.0

    def calculate_category_metrics(self,
                                 predictions: List[Dict[str, Any]],
                                 ground_truth: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Calculate precision/recall metrics by category.

        Args:
            predictions: List of predicted findings
            ground_truth: List of actual findings

        Returns:
            Dictionary with category-specific metrics
        """
        categories = set()
        for item in predictions + ground_truth:
            if 'category' in item:
                categories.add(item['category'])

        category_metrics = {}

        for category in categories:
            cat_predictions = [p for p in predictions if p.get('category') == category]
            cat_truth = [t for t in ground_truth if t.get('category') == category]

            if not cat_predictions and not cat_truth:
                continue

            # Calculate true/false positives/negatives for this category
            pred_ids = {p.get('id') for p in cat_predictions}
            truth_ids = {t.get('id') for t in cat_truth}

            tp = len(pred_ids & truth_ids)
            fp = len(pred_ids - truth_ids)
            fn = len(truth_ids - pred_ids)

            precision, recall, f1 = self.calculate_precision_recall(tp, fp, fn)

            category_metrics[category] = {
                'precision': precision,
                'recall': recall,
                'f1_score': f1,
                'true_positives': tp,
                'false_positives': fp,
                'false_negatives': fn
            }

        return category_metrics

    def calculate_temporal_trends(self,
                                 historical_data: List[Tuple[datetime, List[Dict], List[Dict]]],
                                 window_days: int = 30) -> List[Tuple[datetime, float]]:
        """Calculate accuracy trends over time.

        Args:
            historical_data: List of (timestamp, predictions, ground_truth) tuples
            window_days: Rolling window size in days

        Returns:
            List of (timestamp, accuracy) tuples
        """
        if not historical_data:
            return []

        # Sort by timestamp
        historical_data.sort(key=lambda x: x[0])

        trends = []
        for i, (timestamp, predictions, ground_truth) in enumerate(historical_data):
            # Calculate rolling accuracy
            window_start = timestamp - timedelta(days=window_days)
            window_data = [d for d in historical_data[:i+1] if d[0] >= window_start]

            if len(window_data) >= 3:  # Need minimum data points
                accuracies = []
                for ts, preds, truths in window_data:
                    acc = self.calculate_weighted_accuracy(preds, truths)
                    accuracies.append(acc)

                rolling_accuracy = np.mean(accuracies)
                trends.append((timestamp, rolling_accuracy))

        return trends

    def calculate_confidence_correlation(self,
                                       predictions: List[Dict[str, Any]],
                                       ground_truth: List[Dict[str, Any]]) -> float:
        """Calculate correlation between confidence scores and accuracy.

        Args:
            predictions: List of predicted findings with confidence scores
            ground_truth: List of actual findings

        Returns:
            Pearson correlation coefficient (-1 to 1)
        """
        if not predictions:
            return 0.0

        truth_ids = {t.get('id') for t in ground_truth}

        confidences = []
        accuracies = []

        for pred in predictions:
            confidence = pred.get('confidence', 0.5)
            is_correct = pred.get('id') in truth_ids

            confidences.append(confidence)
            accuracies.append(1.0 if is_correct else 0.0)

        if len(confidences) < 2:
            return 0.0

        return np.corrcoef(confidences, accuracies)[0, 1]

    def calculate_comprehensive_metrics(self,
                                      predictions: List[Dict[str, Any]],
                                      ground_truth: List[Dict[str, Any]],
                                      historical_data: Optional[List[Tuple[datetime, List[Dict], List[Dict]]]] = None) -> EffectivenessMetrics:
        """Calculate comprehensive effectiveness metrics.

        Args:
            predictions: Current prediction results
            ground_truth: Ground truth data
            historical_data: Optional historical data for trend analysis

        Returns:
            Comprehensive EffectivenessMetrics object
        """
        metrics = EffectivenessMetrics()

        # Basic counts
        pred_ids = {p.get('id') for p in predictions}
        truth_ids = {t.get('id') for t in ground_truth}

        tp = len(pred_ids & truth_ids)
        fp = len(pred_ids - truth_ids)
        fn = len(truth_ids - pred_ids)
        tn = 0  # True negatives not easily calculable without full universe

        metrics.total_predictions = len(predictions)
        metrics.total_correct = tp
        metrics.total_incorrect = fp + fn

        # Precision/Recall metrics
        metrics.precision, metrics.recall, metrics.f1_score = self.calculate_precision_recall(tp, fp, fn)

        # Weighted accuracy
        metrics.weighted_accuracy = self.calculate_weighted_accuracy(predictions, ground_truth)

        # Category-specific metrics
        category_data = self.calculate_category_metrics(predictions, ground_truth)
        metrics.category_precision = {cat: data['precision'] for cat, data in category_data.items()}
        metrics.category_recall = {cat: data['recall'] for cat, data in category_data.items()}
        metrics.category_f1 = {cat: data['f1_score'] for cat, data in category_data.items()}

        # Performance metrics
        total_positives = tp + fn
        total_negatives = fp + tn if tn > 0 else fp

        metrics.true_positive_rate = tp / total_positives if total_positives > 0 else 0.0
        metrics.false_positive_rate = fp / total_negatives if total_negatives > 0 else 0.0
        metrics.false_negative_rate = fn / total_positives if total_positives > 0 else 0.0
        metrics.true_negative_rate = tn / total_negatives if total_negatives > 0 else 0.0

        # Confidence analysis
        metrics.confidence_accuracy_correlation = self.calculate_confidence_correlation(predictions, ground_truth)

        # Split by confidence levels
        high_conf_predictions = [p for p in predictions if p.get('confidence', 0.5) >= 0.8]
        low_conf_predictions = [p for p in predictions if p.get('confidence', 0.5) < 0.8]

        if high_conf_predictions:
            metrics.high_confidence_accuracy = self.calculate_weighted_accuracy(high_conf_predictions, ground_truth)
        if low_conf_predictions:
            metrics.low_confidence_accuracy = self.calculate_weighted_accuracy(low_conf_predictions, ground_truth)

        # Temporal trends
        if historical_data:
            metrics.accuracy_trend = self.calculate_temporal_trends(historical_data)

            # Calculate rolling accuracies
            recent_trends = [acc for _, acc in metrics.accuracy_trend[-7:]]  # Last 7 data points
            if recent_trends:
                metrics.rolling_accuracy_7d = np.mean(recent_trends)

            recent_trends_30 = [acc for _, acc in metrics.accuracy_trend[-30:]]  # Last 30 data points
            if recent_trends_30:
                metrics.rolling_accuracy_30d = np.mean(recent_trends_30)

        # Metadata
        metrics.data_points = len(predictions) + len(ground_truth)

        self.logger.info(f"Calculated effectiveness metrics: precision={metrics.precision:.3f}, "
                        f"recall={metrics.recall:.3f}, weighted_accuracy={metrics.weighted_accuracy:.3f}")

        return metrics

    def validate_accuracy_threshold(self, metrics: EffectivenessMetrics, threshold: float = 0.95) -> Dict[str, Any]:
        """Validate that metrics meet accuracy thresholds.

        Args:
            metrics: Calculated effectiveness metrics
            threshold: Minimum accuracy threshold (default 0.95)

        Returns:
            Validation result with pass/fail status and details
        """
        result = {
            'passed': True,
            'violations': [],
            'warnings': [],
            'overall_accuracy': metrics.weighted_accuracy,
            'threshold': threshold
        }

        # Check overall accuracy
        if metrics.weighted_accuracy < threshold:
            result['passed'] = False
            result['violations'].append({
                'metric': 'weighted_accuracy',
                'value': metrics.weighted_accuracy,
                'threshold': threshold,
                'message': f'Overall accuracy {metrics.weighted_accuracy:.3f} below threshold {threshold:.3f}'
            })

        # Check precision
        if metrics.precision < 0.90:  # 90% precision threshold
            result['warnings'].append({
                'metric': 'precision',
                'value': metrics.precision,
                'threshold': 0.90,
                'message': f'Precision {metrics.precision:.3f} below recommended 0.90'
            })

        # Check recall
        if metrics.recall < 0.85:  # 85% recall threshold
            result['warnings'].append({
                'metric': 'recall',
                'value': metrics.recall,
                'threshold': 0.85,
                'message': f'Recall {metrics.recall:.3f} below recommended 0.85'
            })

        # Check F1 score
        if metrics.f1_score < 0.87:  # 87% F1 threshold
            result['warnings'].append({
                'metric': 'f1_score',
                'value': metrics.f1_score,
                'threshold': 0.87,
                'message': f'F1 score {metrics.f1_score:.3f} below recommended 0.87'
            })

        # Check for concerning false positive/negative rates
        if metrics.false_positive_rate > 0.10:  # >10% false positive rate
            result['warnings'].append({
                'metric': 'false_positive_rate',
                'value': metrics.false_positive_rate,
                'threshold': 0.10,
                'message': f'False positive rate {metrics.false_positive_rate:.3f} above recommended 0.10'
            })

        return result


def load_historical_metrics_data(metrics_dir: Path) -> List[Tuple[datetime, List[Dict], List[Dict]]]:
    """Load historical metrics data from storage.

    Args:
        metrics_dir: Directory containing historical metrics files

    Returns:
        List of (timestamp, predictions, ground_truth) tuples
    """
    historical_data = []

    if not metrics_dir.exists():
        return historical_data

    for metrics_file in metrics_dir.glob("metrics_*.json"):
        try:
            with open(metrics_file, 'r') as f:
                data = json.load(f)

            timestamp = datetime.fromisoformat(data['timestamp'])
            predictions = data.get('predictions', [])
            ground_truth = data.get('ground_truth', [])

            historical_data.append((timestamp, predictions, ground_truth))

        except Exception as e:
            logger.warning(f"Failed to load historical metrics from {metrics_file}: {e}")
            continue

    return sorted(historical_data, key=lambda x: x[0])


def save_metrics_snapshot(metrics: EffectivenessMetrics, output_dir: Path) -> Path:
    """Save a snapshot of calculated metrics.

    Args:
        metrics: Metrics to save
        output_dir: Directory to save metrics

    Returns:
        Path to saved metrics file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = metrics.calculated_at.strftime("%Y%m%d_%H%M%S")
    filename = f"effectiveness_metrics_{timestamp}.json"
    filepath = output_dir / filename

    # Convert to serializable format
    data = {
        'timestamp': metrics.calculated_at.isoformat(),
        'total_predictions': metrics.total_predictions,
        'total_correct': metrics.total_correct,
        'total_incorrect': metrics.total_incorrect,
        'precision': metrics.precision,
        'recall': metrics.recall,
        'f1_score': metrics.f1_score,
        'weighted_accuracy': metrics.weighted_accuracy,
        'severity_weights': metrics.severity_weights,
        'category_precision': metrics.category_precision,
        'category_recall': metrics.category_recall,
        'category_f1': metrics.category_f1,
        'rolling_accuracy_7d': metrics.rolling_accuracy_7d,
        'rolling_accuracy_30d': metrics.rolling_accuracy_30d,
        'confidence_accuracy_correlation': metrics.confidence_accuracy_correlation,
        'high_confidence_accuracy': metrics.high_confidence_accuracy,
        'low_confidence_accuracy': metrics.low_confidence_accuracy,
        'false_positive_rate': metrics.false_positive_rate,
        'false_negative_rate': metrics.false_negative_rate,
        'true_positive_rate': metrics.true_positive_rate,
        'true_negative_rate': metrics.true_negative_rate,
        'data_points': metrics.data_points,
        'time_window_days': metrics.time_window_days
    }

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    logger.info(f"Saved effectiveness metrics snapshot to {filepath}")
    return filepath