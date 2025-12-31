#!/usr/bin/env python3
"""
Effectiveness Metrics CI Validation Script
Validates that effectiveness metrics meet accuracy thresholds for CI/CD pipeline.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.metrics.effectiveness import (
    EffectivenessMetrics,
    EffectivenessMetricsCalculator,
    load_historical_metrics_data
)
from core.sme_review.manager import SMEReviewManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EffectivenessCIValidator:
    """CI validator for effectiveness metrics thresholds."""

    def __init__(self, accuracy_threshold: float = 0.95, alert_threshold: float = 0.90):
        self.accuracy_threshold = accuracy_threshold
        self.alert_threshold = alert_threshold
        self.calculator = EffectivenessMetricsCalculator()

    def validate_current_metrics(self, metrics_file: Optional[Path] = None) -> Dict[str, Any]:
        """Validate current effectiveness metrics against thresholds.

        Args:
            metrics_file: Path to metrics file, if None uses latest from SME review manager

        Returns:
            Validation results dictionary
        """
        result = {
            'passed': True,
            'blocked': False,
            'warnings': [],
            'errors': [],
            'metrics': {},
            'recommendations': []
        }

        try:
            if metrics_file and metrics_file.exists():
                # Load from file
                with open(metrics_file, 'r') as f:
                    metrics_data = json.load(f)
                # Convert back to EffectivenessMetrics object
                metrics = self._dict_to_effectiveness_metrics(metrics_data)
            else:
                # Get from SME review manager
                manager = SMEReviewManager()
                review_metrics = manager.get_review_metrics()
                metrics = review_metrics.effectiveness_metrics

            if not metrics:
                result['errors'].append("No effectiveness metrics available for validation")
                result['passed'] = False
                result['blocked'] = True
                return result

            result['metrics'] = {
                'weighted_accuracy': metrics.weighted_accuracy,
                'precision': metrics.precision,
                'recall': metrics.recall,
                'f1_score': metrics.f1_score,
                'false_positive_rate': metrics.false_positive_rate,
                'false_negative_rate': metrics.false_negative_rate
            }

            # Validate accuracy threshold
            if metrics.weighted_accuracy < self.accuracy_threshold:
                result['passed'] = False
                result['blocked'] = True
                result['errors'].append(
                    f"❌ ACCURACY BLOCKER: Weighted accuracy {metrics.weighted_accuracy:.3f} "
                    f"below required threshold {self.accuracy_threshold:.3f}"
                )

            # Check for alert threshold
            elif metrics.weighted_accuracy < self.alert_threshold:
                result['warnings'].append(
                    f"⚠️  ACCURACY ALERT: Weighted accuracy {metrics.weighted_accuracy:.3f} "
                    f"below alert threshold {self.alert_threshold:.3f}"
                )

            # Validate precision
            if metrics.precision < 0.90:
                result['warnings'].append(
                    f"⚠️  PRECISION WARNING: Precision {metrics.precision:.3f} below recommended 0.90"
                )

            # Validate recall
            if metrics.recall < 0.85:
                result['warnings'].append(
                    f"⚠️  RECALL WARNING: Recall {metrics.recall:.3f} below recommended 0.85"
                )

            # Check false positive rate
            if metrics.false_positive_rate > 0.10:
                result['warnings'].append(
                    f"⚠️  FALSE POSITIVE WARNING: False positive rate {metrics.false_positive_rate:.3f} "
                    f"above recommended 0.10"
                )

            # Generate recommendations
            result['recommendations'] = self._generate_recommendations(metrics, result)

        except Exception as e:
            result['errors'].append(f"Failed to validate metrics: {str(e)}")
            result['passed'] = False
            result['blocked'] = True

        return result

    def validate_trend_analysis(self, metrics_dir: Path, min_data_points: int = 5) -> Dict[str, Any]:
        """Validate metrics trends to detect degradation.

        Args:
            metrics_dir: Directory containing historical metrics
            min_data_points: Minimum data points required for trend analysis

        Returns:
            Trend validation results
        """
        result = {
            'trend_stable': True,
            'degradation_detected': False,
            'trend_analysis': {},
            'warnings': []
        }

        try:
            historical_data = load_historical_metrics_data(metrics_dir)

            if len(historical_data) < min_data_points:
                result['warnings'].append(
                    f"Insufficient historical data: {len(historical_data)} points, "
                    f"need at least {min_data_points}"
                )
                return result

            # Analyze accuracy trend
            accuracies = []
            timestamps = []

            for ts, preds, truths in historical_data[-30:]:  # Last 30 data points
                try:
                    metrics = self.calculator.calculate_comprehensive_metrics(preds, truths)
                    accuracies.append(metrics.weighted_accuracy)
                    timestamps.append(ts)
                except Exception:
                    continue

            if len(accuracies) < 3:
                result['warnings'].append("Insufficient valid metrics data points for trend analysis")
                return result

            # Calculate trend using linear regression
            import numpy as np
            x = np.arange(len(accuracies))
            y = np.array(accuracies)

            # Simple linear regression
            slope = np.polyfit(x, y, 1)[0]
            trend_direction = "improving" if slope > 0 else "degrading" if slope < -0.001 else "stable"

            result['trend_analysis'] = {
                'data_points': len(accuracies),
                'slope': slope,
                'direction': trend_direction,
                'avg_accuracy': np.mean(accuracies),
                'accuracy_std': np.std(accuracies),
                'min_accuracy': np.min(accuracies),
                'max_accuracy': np.max(accuracies)
            }

            # Check for significant degradation
            recent_avg = np.mean(accuracies[-5:]) if len(accuracies) >= 5 else np.mean(accuracies)
            overall_avg = np.mean(accuracies)

            if recent_avg < overall_avg * 0.95:  # 5% degradation
                result['degradation_detected'] = True
                result['warnings'].append(
                    f"⚠️  TREND DEGRADATION: Recent accuracy ({recent_avg:.3f}) "
                    f"5% below overall average ({overall_avg:.3f})"
                )

            result['trend_stable'] = not result['degradation_detected']

        except Exception as e:
            result['warnings'].append(f"Failed to analyze trends: {str(e)}")

        return result

    def _dict_to_effectiveness_metrics(self, data: Dict[str, Any]) -> EffectivenessMetrics:
        """Convert dictionary to EffectivenessMetrics object."""
        from core.metrics.effectiveness import EffectivenessMetrics

        # Create a basic metrics object from dict
        metrics = EffectivenessMetrics()
        metrics.weighted_accuracy = data.get('weighted_accuracy', 0.0)
        metrics.precision = data.get('precision', 0.0)
        metrics.recall = data.get('recall', 0.0)
        metrics.f1_score = data.get('f1_score', 0.0)
        metrics.false_positive_rate = data.get('false_positive_rate', 0.0)
        metrics.false_negative_rate = data.get('false_negative_rate', 0.0)
        metrics.high_confidence_accuracy = data.get('high_confidence_accuracy', 0.0)
        metrics.low_confidence_accuracy = data.get('low_confidence_accuracy', 0.0)
        metrics.confidence_accuracy_correlation = data.get('confidence_accuracy_correlation', 0.0)

        return metrics

    def _generate_recommendations(self, metrics: EffectivenessMetrics, validation_result: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on metrics analysis."""
        recommendations = []

        # Accuracy recommendations
        if metrics.weighted_accuracy < 0.90:
            recommendations.append("🔧 Implement additional training data for low-accuracy categories")
            recommendations.append("🔧 Review and improve confidence scoring algorithms")

        # Precision recommendations
        if metrics.precision < 0.85:
            recommendations.append("🔧 Reduce false positives by tightening detection thresholds")
            recommendations.append("🔧 Implement additional validation steps for high-risk findings")

        # Recall recommendations
        if metrics.recall < 0.80:
            recommendations.append("🔧 Expand detection coverage for missed issue types")
            recommendations.append("🔧 Review and enhance pattern matching algorithms")

        # False positive recommendations
        if metrics.false_positive_rate > 0.15:
            recommendations.append("🔧 Implement false positive reduction techniques (e.g., additional heuristics)")
            recommendations.append("🔧 Add manual review workflow for borderline cases")

        # Confidence correlation recommendations
        if abs(metrics.confidence_accuracy_correlation) < 0.3:
            recommendations.append("🔧 Improve confidence calibration to better reflect actual accuracy")
            recommendations.append("🔧 Review confidence scoring methodology")

        # General recommendations
        if not validation_result['passed']:
            recommendations.append("🚫 BLOCKED: Address critical accuracy issues before deployment")
        elif validation_result['warnings']:
            recommendations.append("⚠️  MONITOR: Address accuracy warnings to prevent future issues")

        return recommendations


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Validate effectiveness metrics for CI/CD")
    parser.add_argument('--metrics-file', type=Path, help='Path to metrics JSON file')
    parser.add_argument('--accuracy-threshold', type=float, default=0.95,
                       help='Required accuracy threshold (default: 0.95)')
    parser.add_argument('--alert-threshold', type=float, default=0.90,
                       help='Alert threshold for warnings (default: 0.90)')
    parser.add_argument('--check-trends', action='store_true',
                       help='Also perform trend analysis')
    parser.add_argument('--metrics-dir', type=Path, default=Path('metrics'),
                       help='Directory for historical metrics (default: metrics)')
    parser.add_argument('--output-format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')

    args = parser.parse_args()

    validator = EffectivenessCIValidator(
        accuracy_threshold=args.accuracy_threshold,
        alert_threshold=args.alert_threshold
    )

    # Validate current metrics
    current_result = validator.validate_current_metrics(args.metrics_file)

    # Validate trends if requested
    trend_result = {}
    if args.check_trends:
        trend_result = validator.validate_trend_analysis(args.metrics_dir)

    # Combine results
    combined_result = {**current_result, 'trend_analysis': trend_result}

    # Output results
    if args.output_format == 'json':
        print(json.dumps(combined_result, indent=2, default=str))
    else:
        # Text output
        print("🔍 Effectiveness Metrics CI Validation")
        print("=" * 50)

        if current_result['passed']:
            print("✅ PASSED: All accuracy thresholds met")
        else:
            print("❌ FAILED: Accuracy requirements not met")
            if current_result['blocked']:
                print("🚫 BLOCKED: Critical issues prevent deployment")

        print(f"\n📊 Current Metrics:")
        for key, value in current_result['metrics'].items():
            print(f"  {key}: {value:.3f}")

        if current_result['errors']:
            print(f"\n❌ Errors ({len(current_result['errors'])}):")
            for error in current_result['errors']:
                print(f"  {error}")

        if current_result['warnings']:
            print(f"\n⚠️  Warnings ({len(current_result['warnings'])}):")
            for warning in current_result['warnings']:
                print(f"  {warning}")

        if args.check_trends and trend_result:
            print(f"\n📈 Trend Analysis:")
            if trend_result.get('trend_stable'):
                print("✅ Trends stable")
            else:
                print("⚠️  Trend degradation detected")

            trend_data = trend_result.get('trend_analysis', {})
            if trend_data:
                print(f"  Direction: {trend_data.get('direction', 'unknown')}")
                print(f"  Data points: {trend_data.get('data_points', 0)}")
                print(f"  Avg accuracy: {trend_data.get('avg_accuracy', 0):.3f}")

        recommendations = current_result.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Recommendations ({len(recommendations)}):")
            for rec in recommendations:
                print(f"  {rec}")

    # Exit with appropriate code
    exit_code = 0
    if not current_result['passed']:
        exit_code = 1  # Fail CI
    elif current_result['warnings']:
        exit_code = 0  # Pass but with warnings

    sys.exit(exit_code)


if __name__ == "__main__":
    main()