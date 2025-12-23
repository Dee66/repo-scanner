"""Accuracy Validation Framework for Algora Bounty Hunting.

Backtesting and validation framework to ensure 99.999% SME accuracy
in bounty solving predictions through historical data analysis.
"""

from typing import Dict, List, Optional, Tuple
import json
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BountyValidationCase:
    """Represents a single bounty validation case."""
    bounty_id: str
    repository_url: str
    bounty_data: Dict
    predicted_profitability: float
    predicted_merge_confidence: float
    actual_outcome: bool  # True if merged, False if rejected
    actual_merge_time: Optional[int]  # days to merge
    validation_timestamp: datetime
    confidence_score: float


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for bounty predictions."""
    total_predictions: int
    correct_predictions: int
    false_positives: int
    false_negatives: int
    accuracy_percentage: float
    precision: float
    recall: float
    f1_score: float
    confidence_distribution: Dict[str, int]


class BountyAccuracyValidator:
    """Validator for bounty prediction accuracy with 99.999% target."""

    def __init__(self, validation_data_path: str = "validation_data"):
        self.validation_data_path = Path(validation_data_path)
        self.validation_data_path.mkdir(exist_ok=True)
        self.target_accuracy = 0.99999  # 99.999%
        self.validation_cases: List[BountyValidationCase] = []
        self.load_validation_data()

    def load_validation_data(self) -> None:
        """Load existing validation data from disk."""
        validation_file = self.validation_data_path / "bounty_validation_cases.json"
        if validation_file.exists():
            try:
                with open(validation_file, 'r') as f:
                    data = json.load(f)
                    for case_data in data.get('cases', []):
                        case = BountyValidationCase(
                            bounty_id=case_data['bounty_id'],
                            repository_url=case_data['repository_url'],
                            bounty_data=case_data['bounty_data'],
                            predicted_profitability=case_data['predicted_profitability'],
                            predicted_merge_confidence=case_data['predicted_merge_confidence'],
                            actual_outcome=case_data['actual_outcome'],
                            actual_merge_time=case_data.get('actual_merge_time'),
                            validation_timestamp=datetime.fromisoformat(case_data['validation_timestamp']),
                            confidence_score=case_data['confidence_score']
                        )
                        self.validation_cases.append(case)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load validation data: {e}")

    def save_validation_data(self) -> None:
        """Save validation data to disk."""
        validation_file = self.validation_data_path / "bounty_validation_cases.json"
        data = {
            'cases': [
                {
                    'bounty_id': case.bounty_id,
                    'repository_url': case.repository_url,
                    'bounty_data': case.bounty_data,
                    'predicted_profitability': case.predicted_profitability,
                    'predicted_merge_confidence': case.predicted_merge_confidence,
                    'actual_outcome': case.actual_outcome,
                    'actual_merge_time': case.actual_merge_time,
                    'validation_timestamp': case.validation_timestamp.isoformat(),
                    'confidence_score': case.confidence_score
                }
                for case in self.validation_cases
            ],
            'last_updated': datetime.now().isoformat()
        }

        with open(validation_file, 'w') as f:
            json.dump(data, f, indent=2)

    def add_validation_case(self, bounty_id: str, repository_url: str,
                          bounty_data: Dict, predicted_profitability: float,
                          predicted_merge_confidence: float, actual_outcome: bool,
                          actual_merge_time: Optional[int] = None,
                          confidence_score: float = 1.0) -> None:
        """Add a new validation case."""
        case = BountyValidationCase(
            bounty_id=bounty_id,
            repository_url=repository_url,
            bounty_data=bounty_data,
            predicted_profitability=predicted_profitability,
            predicted_merge_confidence=predicted_merge_confidence,
            actual_outcome=actual_outcome,
            actual_merge_time=actual_merge_time,
            validation_timestamp=datetime.now(),
            confidence_score=confidence_score
        )

        self.validation_cases.append(case)
        self.save_validation_data()

    def calculate_accuracy_metrics(self, min_confidence: float = 0.0) -> AccuracyMetrics:
        """Calculate comprehensive accuracy metrics."""
        # Filter cases by minimum confidence
        filtered_cases = [case for case in self.validation_cases
                         if case.confidence_score >= min_confidence]

        if not filtered_cases:
            return AccuracyMetrics(0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0, {})

        total_predictions = len(filtered_cases)
        correct_predictions = 0
        false_positives = 0  # Predicted merge but didn't merge
        false_negatives = 0  # Predicted no merge but did merge

        confidence_distribution = {
            'high': 0,  # > 0.8
            'medium': 0,  # 0.6-0.8
            'low': 0     # < 0.6
        }

        for case in filtered_cases:
            # Determine prediction (merge if profitability > 0.6 and confidence > 0.8)
            predicted_merge = (case.predicted_profitability > 0.6 and
                             case.predicted_merge_confidence > 0.8)

            # Calculate accuracy
            if predicted_merge == case.actual_outcome:
                correct_predictions += 1
            elif predicted_merge and not case.actual_outcome:
                false_positives += 1
            elif not predicted_merge and case.actual_outcome:
                false_negatives += 1

            # Confidence distribution
            if case.confidence_score > 0.8:
                confidence_distribution['high'] += 1
            elif case.confidence_score > 0.6:
                confidence_distribution['medium'] += 1
            else:
                confidence_distribution['low'] += 1

        # Calculate metrics
        accuracy_percentage = correct_predictions / total_predictions if total_predictions > 0 else 0.0
        precision = (correct_predictions / (correct_predictions + false_positives)
                    if (correct_predictions + false_positives) > 0 else 0.0)
        recall = (correct_predictions / (correct_predictions + false_negatives)
                 if (correct_predictions + false_negatives) > 0 else 0.0)
        f1_score = (2 * precision * recall / (precision + recall)
                   if (precision + recall) > 0 else 0.0)

        return AccuracyMetrics(
            total_predictions=total_predictions,
            correct_predictions=correct_predictions,
            false_positives=false_positives,
            false_negatives=false_negatives,
            accuracy_percentage=accuracy_percentage,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            confidence_distribution=confidence_distribution
        )

    def validate_accuracy_target(self) -> Dict:
        """Validate if current accuracy meets 99.999% target."""
        metrics = self.calculate_accuracy_metrics(min_confidence=0.9)  # High confidence only

        target_met = metrics.accuracy_percentage >= self.target_accuracy
        current_accuracy = metrics.accuracy_percentage

        # Calculate confidence interval
        if metrics.total_predictions > 0:
            # Wilson score interval for binomial proportion
            z = 3.291  # 99.9% confidence level (z-score)
            n = metrics.total_predictions
            p = current_accuracy

            denominator = 1 + z*z/n
            center = (p + z*z/(2*n)) / denominator
            margin = z * ((p*(1-p)/n + z*z/(4*n*n))**0.5) / denominator

            confidence_interval = {
                'lower': max(0.0, center - margin),
                'upper': min(1.0, center + margin)
            }
        else:
            confidence_interval = {'lower': 0.0, 'upper': 1.0}

        return {
            'target_accuracy': self.target_accuracy,
            'current_accuracy': current_accuracy,
            'target_met': target_met,
            'confidence_interval': confidence_interval,
            'total_validations': metrics.total_predictions,
            'recommendations': self._generate_accuracy_recommendations(metrics, target_met)
        }

    def _generate_accuracy_recommendations(self, metrics: AccuracyMetrics,
                                         target_met: bool) -> List[str]:
        """Generate recommendations based on accuracy analysis."""
        recommendations = []

        if not target_met:
            recommendations.append("Increase minimum confidence threshold for predictions")
            recommendations.append("Expand training data set with more validation cases")
            recommendations.append("Refine profitability scoring algorithm")

        if metrics.false_positives > metrics.false_negatives:
            recommendations.append("Adjust prediction threshold to reduce false positives")
        elif metrics.false_negatives > metrics.false_positives:
            recommendations.append("Lower prediction threshold to capture more viable bounties")

        if metrics.confidence_distribution.get('low', 0) > metrics.total_predictions * 0.1:
            recommendations.append("Improve confidence scoring mechanism")

        if metrics.total_predictions < 1000:
            recommendations.append("Collect more validation data for statistical significance")

        return recommendations

    def analyze_prediction_errors(self) -> Dict:
        """Analyze patterns in prediction errors."""
        errors = {
            'false_positives': [],
            'false_negatives': [],
            'error_patterns': {}
        }

        for case in self.validation_cases:
            predicted_merge = (case.predicted_profitability > 0.6 and
                             case.predicted_merge_confidence > 0.8)

            if predicted_merge and not case.actual_outcome:
                # False positive - predicted merge but didn't happen
                errors['false_positives'].append({
                    'bounty_id': case.bounty_id,
                    'profitability': case.predicted_profitability,
                    'confidence': case.predicted_merge_confidence,
                    'repository': case.repository_url
                })
            elif not predicted_merge and case.actual_outcome:
                # False negative - predicted no merge but did happen
                errors['false_negatives'].append({
                    'bounty_id': case.bounty_id,
                    'profitability': case.predicted_profitability,
                    'confidence': case.predicted_merge_confidence,
                    'repository': case.repository_url
                })

        # Analyze error patterns
        if errors['false_positives']:
            avg_profitability_fp = statistics.mean([e['profitability'] for e in errors['false_positives']])
            errors['error_patterns']['false_positive_avg_profitability'] = avg_profitability_fp

        if errors['false_negatives']:
            avg_profitability_fn = statistics.mean([e['profitability'] for e in errors['false_negatives']])
            errors['error_patterns']['false_negative_avg_profitability'] = avg_profitability_fn

        return errors

    def generate_accuracy_report(self) -> str:
        """Generate a comprehensive accuracy report."""
        metrics = self.calculate_accuracy_metrics()
        validation = self.validate_accuracy_target()
        errors = self.analyze_prediction_errors()

        report = f"""
# Bounty Prediction Accuracy Report
Generated: {datetime.now().isoformat()}

## Target vs Current Performance
- Target Accuracy: {validation['target_accuracy']:.5%}
- Current Accuracy: {validation['current_accuracy']:.5%}
- Target Met: {'✅ YES' if validation['target_met'] else '❌ NO'}
- Confidence Interval: {validation['confidence_interval']['lower']:.5%} - {validation['confidence_interval']['upper']:.5%}

## Overall Metrics
- Total Predictions: {metrics.total_predictions}
- Correct Predictions: {metrics.correct_predictions}
- False Positives: {metrics.false_positives}
- False Negatives: {metrics.false_negatives}
- Precision: {metrics.precision:.4f}
- Recall: {metrics.recall:.4f}
- F1 Score: {metrics.f1_score:.4f}

## Confidence Distribution
- High Confidence (>0.8): {metrics.confidence_distribution.get('high', 0)}
- Medium Confidence (0.6-0.8): {metrics.confidence_distribution.get('medium', 0)}
- Low Confidence (<0.6): {metrics.confidence_distribution.get('low', 0)}

## Error Analysis
- False Positives: {len(errors['false_positives'])}
- False Negatives: {len(errors['false_negatives'])}

## Recommendations
{chr(10).join(f"- {rec}" for rec in validation['recommendations'])}
"""

        return report

    def calibrate_prediction_thresholds(self) -> Dict:
        """Calibrate prediction thresholds for optimal accuracy."""
        # Use validation data to find optimal thresholds
        best_accuracy = 0.0
        best_thresholds = {'profitability': 0.6, 'confidence': 0.8}

        # Grid search for optimal thresholds
        for profitability_threshold in [0.5, 0.6, 0.7, 0.8]:
            for confidence_threshold in [0.7, 0.8, 0.9]:
                correct = 0
                total = 0

                for case in self.validation_cases:
                    if case.confidence_score >= 0.8:  # Only use high-confidence validations
                        predicted = (case.predicted_profitability > profitability_threshold and
                                   case.predicted_merge_confidence > confidence_threshold)
                        if predicted == case.actual_outcome:
                            correct += 1
                        total += 1

                if total > 0:
                    accuracy = correct / total
                    if accuracy > best_accuracy:
                        best_accuracy = accuracy
                        best_thresholds = {
                            'profitability': profitability_threshold,
                            'confidence': confidence_threshold
                        }

        return {
            'optimal_thresholds': best_thresholds,
            'expected_accuracy': best_accuracy,
            'calibration_timestamp': datetime.now().isoformat()
        }


def validate_bounty_accuracy(validation_data_path: str = "validation_data") -> Dict:
    """Convenience function for bounty accuracy validation."""
    validator = BountyAccuracyValidator(validation_data_path)
    return {
        'metrics': validator.calculate_accuracy_metrics(),
        'validation': validator.validate_accuracy_target(),
        'errors': validator.analyze_prediction_errors(),
        'report': validator.generate_accuracy_report()
    }