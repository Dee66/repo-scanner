#!/usr/bin/env python3
"""
Metrics Collection Integration Script
Integrates effectiveness metrics collection into the main analysis pipeline.
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.metrics.effectiveness import (
    EffectivenessMetricsCalculator,
    save_metrics_snapshot,
    load_historical_metrics_data
)
from core.sme_review.manager import SMEReviewManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and integrates effectiveness metrics into the analysis pipeline."""

    def __init__(self, metrics_dir: Path = Path("metrics")):
        self.metrics_dir = metrics_dir
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.calculator = EffectivenessMetricsCalculator()

    def collect_from_analysis_results(self, analysis_results: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Collect metrics from analysis results.

        Args:
            analysis_results: Results from the main analysis pipeline

        Returns:
            Collected metrics data or None if collection failed
        """
        try:
            # Extract predictions and ground truth from analysis results
            predictions = self._extract_predictions(analysis_results)
            ground_truth = self._extract_ground_truth(analysis_results)

            if not predictions:
                logger.warning("No predictions found in analysis results")
                return None

            # Load historical data for trend analysis
            historical_data = load_historical_metrics_data(self.metrics_dir)

            # Calculate comprehensive metrics
            metrics = self.calculator.calculate_comprehensive_metrics(
                predictions,
                ground_truth,
                historical_data
            )

            # Validate metrics
            validation = self.calculator.validate_accuracy_threshold(metrics)

            # Save metrics snapshot
            snapshot_path = save_metrics_snapshot(metrics, self.metrics_dir)

            result = {
                'metrics': metrics,
                'validation': validation,
                'snapshot_path': str(snapshot_path),
                'data_points': len(predictions),
                'ground_truth_points': len(ground_truth)
            }

            logger.info(f"Collected effectiveness metrics: accuracy={metrics.weighted_accuracy:.3f}, "
                       f"precision={metrics.precision:.3f}, recall={metrics.recall:.3f}")

            return result

        except Exception as e:
            logger.error(f"Failed to collect metrics from analysis results: {e}")
            return None

    def collect_from_sme_reviews(self) -> Optional[Dict[str, Any]]:
        """Collect metrics from SME review process.

        Returns:
            Collected metrics data or None if collection failed
        """
        try:
            manager = SMEReviewManager()
            review_metrics = manager.get_review_metrics()

            if not review_metrics.effectiveness_metrics:
                logger.warning("No effectiveness metrics available from SME reviews")
                return None

            metrics = review_metrics.effectiveness_metrics

            # Validate metrics
            validation = self.calculator.validate_accuracy_threshold(metrics)

            # Save metrics snapshot
            snapshot_path = save_metrics_snapshot(metrics, self.metrics_dir)

            result = {
                'metrics': metrics,
                'validation': validation,
                'snapshot_path': str(snapshot_path),
                'review_metrics': {
                    'total_cases': review_metrics.total_cases,
                    'completed_reviews': review_metrics.completed_reviews,
                    'weighted_review_score': review_metrics.weighted_review_score,
                    'review_consistency_score': review_metrics.review_consistency_score
                }
            }

            logger.info(f"Collected SME review metrics: accuracy={metrics.weighted_accuracy:.3f}")

            return result

        except Exception as e:
            logger.error(f"Failed to collect metrics from SME reviews: {e}")
            return None

    def integrate_with_pipeline_output(self, pipeline_output: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate metrics collection into pipeline output.

        Args:
            pipeline_output: Original pipeline output

        Returns:
            Enhanced pipeline output with metrics
        """
        enhanced_output = pipeline_output.copy()

        # Collect metrics from analysis results
        analysis_metrics = self.collect_from_analysis_results(pipeline_output)

        # Collect metrics from SME reviews
        sme_metrics = self.collect_from_sme_reviews()

        # Add metrics to output
        if analysis_metrics or sme_metrics:
            enhanced_output['effectiveness_metrics'] = {
                'analysis': analysis_metrics,
                'sme_reviews': sme_metrics,
                'collection_timestamp': str(self.calculator.calculator.calculated_at)
            }

            # Add validation status
            validation_status = {'passed': True, 'warnings': [], 'errors': []}

            for metrics_data in [analysis_metrics, sme_metrics]:
                if metrics_data and 'validation' in metrics_data:
                    val = metrics_data['validation']
                    if not val.get('passed', True):
                        validation_status['passed'] = False
                    validation_status['warnings'].extend(val.get('warnings', []))
                    validation_status['errors'].extend(val.get('errors', []))

            enhanced_output['effectiveness_validation'] = validation_status

            logger.info("Integrated effectiveness metrics into pipeline output")

        return enhanced_output

    def _extract_predictions(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract predictions from analysis results."""
        predictions = []

        # Extract from decision artifacts
        artifacts = analysis_results.get('decision_artifacts', {}).get('artifacts', [])
        for artifact in artifacts:
            prediction = {
                'id': artifact.get('id', f"pred_{len(predictions)}"),
                'category': artifact.get('category', 'unknown'),
                'severity': artifact.get('severity', 'MEDIUM'),
                'confidence': artifact.get('confidence', 0.8),
                'source': 'analysis_pipeline'
            }
            predictions.append(prediction)

        # Extract from evidence bundles
        evidence_bundles = analysis_results.get('evidence_bundles', [])
        for bundle in evidence_bundles:
            if bundle.get('confidence', 0) > 0.5:  # Only include reasonably confident findings
                prediction = {
                    'id': bundle.get('id', f"evidence_{len(predictions)}"),
                    'category': bundle.get('category', 'unknown'),
                    'severity': bundle.get('severity', 'MEDIUM'),
                    'confidence': bundle.get('confidence', 0.8),
                    'source': 'evidence_bundle'
                }
                predictions.append(prediction)

        return predictions

    def _extract_ground_truth(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract ground truth from analysis results (if available)."""
        ground_truth = []

        # This would typically come from validation data or golden datasets
        # For now, we'll use SME validations as ground truth
        try:
            validation_file = Path("validation_data/sme_validations.json")
            if validation_file.exists():
                with open(validation_file, 'r') as f:
                    validation_data = json.load(f)

                for validation in validation_data.get('sme_validations', []):
                    if validation.get('verified', False):
                        truth_item = {
                            'id': f"validation_{len(ground_truth)}",
                            'category': 'sme_validation',
                            'severity': 'HIGH' if validation.get('confidence', 0) > 0.8 else 'MEDIUM',
                            'verified': validation.get('verified', False),
                            'confidence': validation.get('confidence', 0.9)
                        }
                        ground_truth.append(truth_item)

        except Exception as e:
            logger.warning(f"Failed to extract ground truth from validations: {e}")

        return ground_truth

    def generate_metrics_report(self, output_path: Optional[Path] = None) -> Path:
        """Generate a comprehensive metrics report.

        Args:
            output_path: Path to save the report (optional)

        Returns:
            Path to generated report
        """
        if not output_path:
            output_path = self.metrics_dir / f"metrics_report_{self.calculator.calculator.calculated_at.strftime('%Y%m%d_%H%M%S')}.md"

        # Collect current metrics
        analysis_metrics = self.collect_from_analysis_results({})
        sme_metrics = self.collect_from_sme_reviews()

        # Load historical data for trends
        historical_data = load_historical_metrics_data(self.metrics_dir)

        # Generate report
        report_content = self._generate_report_content(analysis_metrics, sme_metrics, historical_data)

        with open(output_path, 'w') as f:
            f.write(report_content)

        logger.info(f"Generated metrics report: {output_path}")
        return output_path

    def _generate_report_content(self, analysis_metrics: Optional[Dict],
                               sme_metrics: Optional[Dict],
                               historical_data: List) -> str:
        """Generate report content."""
        lines = [
            "# Effectiveness Metrics Report",
            f"**Generated:** {self.calculator.calculator.calculated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Overview",
            "",
            f"- **Historical Data Points:** {len(historical_data)}",
            ""
        ]

        # Analysis metrics section
        if analysis_metrics and 'metrics' in analysis_metrics:
            metrics = analysis_metrics['metrics']
            validation = analysis_metrics.get('validation', {})

            lines.extend([
                "## Analysis Pipeline Metrics",
                "",
                "### Key Metrics",
                f"- **Weighted Accuracy:** {metrics.weighted_accuracy:.1%}",
                f"- **Precision:** {metrics.precision:.1%}",
                f"- **Recall:** {metrics.recall:.1%}",
                f"- **F1 Score:** {metrics.f1_score:.1%}",
                "",
                "### Validation Status",
                f"- **Passed:** {'✅ Yes' if validation.get('passed', False) else '❌ No'}",
                f"- **Warnings:** {len(validation.get('warnings', []))}",
                f"- **Errors:** {len(validation.get('errors', []))}",
                ""
            ])

        # SME metrics section
        if sme_metrics and 'metrics' in sme_metrics:
            metrics = sme_metrics['metrics']
            review_data = sme_metrics.get('review_metrics', {})

            lines.extend([
                "## SME Review Metrics",
                "",
                "### Effectiveness Metrics",
                f"- **Weighted Accuracy:** {metrics.weighted_accuracy:.1%}",
                f"- **Precision:** {metrics.precision:.1%}",
                f"- **Recall:** {metrics.recall:.1%}",
                f"- **F1 Score:** {metrics.f1_score:.1%}",
                "",
                "### Review Process Metrics",
                f"- **Total Cases:** {review_data.get('total_cases', 0)}",
                f"- **Completed Reviews:** {review_data.get('completed_reviews', 0)}",
                f"- **Weighted Review Score:** {review_data.get('weighted_review_score', 0):.1%}",
                f"- **Review Consistency:** {review_data.get('review_consistency_score', 0):.1%}",
                ""
            ])

        # Recommendations
        lines.extend([
            "## Recommendations",
            "",
            "Based on current metrics analysis:",
            ""
        ])

        all_warnings = []
        for metrics_data in [analysis_metrics, sme_metrics]:
            if metrics_data and 'validation' in metrics_data:
                all_warnings.extend(metrics_data['validation'].get('warnings', []))

        if all_warnings:
            lines.append("### Warnings to Address:")
            for warning in all_warnings[:5]:  # Show top 5
                lines.append(f"- {warning}")
            lines.append("")
        else:
            lines.append("- ✅ No critical warnings detected")
            lines.append("")

        lines.extend([
            "---",
            "*Report generated automatically by effectiveness metrics collection system*"
        ])

        return "\n".join(lines)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Collect and integrate effectiveness metrics")
    parser.add_argument('--pipeline-output', type=Path,
                       help='Path to pipeline output JSON file')
    parser.add_argument('--output', type=Path,
                       help='Path to save enhanced output')
    parser.add_argument('--generate-report', action='store_true',
                       help='Generate comprehensive metrics report')
    parser.add_argument('--report-output', type=Path,
                       help='Path to save metrics report')
    parser.add_argument('--metrics-dir', type=Path, default=Path('metrics'),
                       help='Directory for metrics storage (default: metrics)')

    args = parser.parse_args()

    collector = MetricsCollector(args.metrics_dir)

    if args.pipeline_output:
        # Load pipeline output
        with open(args.pipeline_output, 'r') as f:
            pipeline_output = json.load(f)

        # Integrate metrics
        enhanced_output = collector.integrate_with_pipeline_output(pipeline_output)

        # Save enhanced output
        output_path = args.output or args.pipeline_output.with_suffix('.enhanced.json')
        with open(output_path, 'w') as f:
            json.dump(enhanced_output, f, indent=2, default=str)

        print(f"Enhanced pipeline output saved to: {output_path}")

    if args.generate_report:
        # Generate metrics report
        report_path = collector.generate_metrics_report(args.report_output)
        print(f"Metrics report generated: {report_path}")

    # If no specific actions requested, collect from SME reviews
    if not args.pipeline_output and not args.generate_report:
        result = collector.collect_from_sme_reviews()
        if result:
            print("✅ Collected metrics from SME reviews")
            print(f"  Accuracy: {result['metrics'].weighted_accuracy:.1%}")
            print(f"  Snapshot: {result['snapshot_path']}")
        else:
            print("❌ Failed to collect metrics from SME reviews")


if __name__ == "__main__":
    main()