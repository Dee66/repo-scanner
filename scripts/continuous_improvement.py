#!/usr/bin/env python3
"""
Continuous Improvement Integration Script

Integrates SME feedback loops for continuous system improvements.
Processes completed SME reviews and applies changes to analysis rules,
configurations, and patterns.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.sme_review.manager import SMEReviewManager
from core.validation_data_manager import get_validation_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ContinuousImprovementIntegrator:
    """Integrates SME feedback for continuous system improvements."""

    def __init__(self):
        self.review_manager = SMEReviewManager()
        self.validation_manager = get_validation_manager()

    def run_continuous_improvement_cycle(self) -> Dict[str, Any]:
        """
        Run a complete continuous improvement cycle.

        Returns:
            Summary of improvements made
        """
        logger.info("Starting continuous improvement cycle")

        improvements = {
            "feedback_processed": 0,
            "rules_updated": 0,
            "patterns_added": 0,
            "config_changes": 0,
            "validation_datasets_updated": 0,
            "errors": []
        }

        try:
            # Step 1: Process SME feedback loops
            logger.info("Processing SME feedback loops")
            feedback_changes = self.review_manager.process_feedback_loops()
            improvements.update({
                "rules_updated": feedback_changes.get("rules_updated", 0),
                "patterns_added": feedback_changes.get("patterns_added", 0),
                "config_changes": feedback_changes.get("config_changes", 0),
                "feedback_processed": sum(feedback_changes.get(k, 0) for k in
                                        ["rules_updated", "patterns_added", "config_changes"]
                                        if k != "errors")
            })
            if feedback_changes.get("errors"):
                improvements["errors"].extend(feedback_changes["errors"])

            # Step 2: Update validation datasets based on feedback
            logger.info("Updating validation datasets")
            validation_updates = self._update_validation_datasets()
            improvements["validation_datasets_updated"] = validation_updates

            # Step 3: Generate improvement report
            logger.info("Generating improvement report")
            self._generate_improvement_report(improvements)

            # Step 4: Clean up old data
            logger.info("Cleaning up old validation data versions")
            cleanup_results = self._cleanup_old_versions()
            improvements["cleanup_results"] = cleanup_results

            logger.info(f"Continuous improvement cycle completed: {improvements}")

        except Exception as e:
            error_msg = f"Error in continuous improvement cycle: {str(e)}"
            logger.error(error_msg)
            improvements["errors"].append(error_msg)

        return improvements

    def _update_validation_datasets(self) -> int:
        """Update validation datasets based on recent SME feedback."""
        updates_made = 0

        try:
            # Get recent feedback from SME reviews
            feedback = self.review_manager._load_all_feedback()

            if not feedback:
                return 0

            # Group feedback by category
            category_insights = {}
            for fb in feedback:
                case = next((c for c in self.review_manager._load_all_cases() if c.id == fb.case_id), None)
                if not case:
                    continue

                category = case.category.value
                if category not in category_insights:
                    category_insights[category] = []

                category_insights[category].append({
                    "findings": fb.findings,
                    "recommendations": fb.recommendations,
                    "confidence": fb.confidence_level
                })

            # Update validation datasets with insights
            for category, insights in category_insights.items():
                if len(insights) >= 3:  # Only update if we have multiple insights
                    dataset_name = f"sme_insights_{category}"

                    # Get existing dataset or create new one
                    try:
                        existing_data = self.validation_manager.get_version(dataset_name)
                    except:
                        existing_data = {"insights": []}

                    # Add new insights
                    for insight in insights:
                        if insight not in existing_data["insights"]:
                            existing_data["insights"].append(insight)
                            updates_made += 1

                    # Create new version
                    self.validation_manager.create_version(
                        dataset_name,
                        existing_data,
                        f"Updated with {len(insights)} new SME insights",
                        "continuous-improvement"
                    )

        except Exception as e:
            logger.error(f"Error updating validation datasets: {e}")

        return updates_made

    def _generate_improvement_report(self, improvements: Dict[str, Any]):
        """Generate a report of improvements made."""
        report = {
            "timestamp": "2025-12-31T00:00:00Z",  # Would use datetime.now() in real implementation
            "cycle_type": "continuous_improvement",
            "improvements": improvements,
            "recommendations": self._generate_recommendations(improvements)
        }

        # Save report
        reports_dir = Path("reports/continuous_improvement")
        reports_dir.mkdir(exist_ok=True)

        report_file = reports_dir / "latest_improvement_report.json"
        with open(report_file, 'w') as f:
            import json
            json.dump(report, f, indent=2)

        logger.info(f"Improvement report saved to {report_file}")

    def _generate_recommendations(self, improvements: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on improvements made."""
        recommendations = []

        if improvements.get("rules_updated", 0) > 0:
            recommendations.append("Review updated analysis rules for accuracy")

        if improvements.get("patterns_added", 0) > 0:
            recommendations.append("Validate new detection patterns against test datasets")

        if improvements.get("config_changes", 0) > 0:
            recommendations.append("Test configuration changes in staging environment")

        if improvements.get("validation_datasets_updated", 0) > 0:
            recommendations.append("Run validation pipeline with updated datasets")

        if not recommendations:
            recommendations.append("Monitor system performance for potential improvements")

        return recommendations

    def _cleanup_old_versions(self) -> Dict[str, Any]:
        """Clean up old versions of validation datasets."""
        cleanup_results = {
            "datasets_cleaned": 0,
            "space_freed": 0
        }

        try:
            # Clean up SME insights datasets
            for dataset_name in ["sme_insights_analysis_accuracy", "sme_insights_security_concern",
                               "sme_insights_performance_issue", "sme_insights_enterprise_complexity"]:
                result = self.validation_manager.cleanup_old_versions(dataset_name, keep_versions=5)
                if result["deleted_versions"] > 0:
                    cleanup_results["datasets_cleaned"] += 1
                    cleanup_results["space_freed"] += result["freed_space"]

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        return cleanup_results


def main():
    """Main entry point for continuous improvement integration."""
    parser = argparse.ArgumentParser(description="Continuous Improvement Integration")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    integrator = ContinuousImprovementIntegrator()

    if args.dry_run:
        logger.info("Running in dry-run mode - no changes will be made")
        # Could implement dry-run logic here
        return

    results = integrator.run_continuous_improvement_cycle()

    # Print summary
    print("Continuous Improvement Cycle Results:")
    print(f"- Feedback processed: {results.get('feedback_processed', 0)}")
    print(f"- Rules updated: {results.get('rules_updated', 0)}")
    print(f"- Patterns added: {results.get('patterns_added', 0)}")
    print(f"- Config changes: {results.get('config_changes', 0)}")
    print(f"- Validation datasets updated: {results.get('validation_datasets_updated', 0)}")

    if results.get("errors"):
        print(f"- Errors: {len(results['errors'])}")
        for error in results["errors"]:
            print(f"  - {error}")

    # Exit with error code if there were errors
    if results.get("errors"):
        sys.exit(1)


if __name__ == "__main__":
    main()