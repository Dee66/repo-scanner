"""Quality bar validation for Repository Intelligence Scanner outputs."""

import logging
import re
from typing import Dict, Any, List, Optional

from ..quality.assurance import QUALITY_BAR

logger = logging.getLogger(__name__)


class QualityBarEvaluator:
    """Evaluates generated outputs against quality bar standards."""

    def __init__(self):
        self.quality_bar = QUALITY_BAR
        self.rejection_patterns = self._compile_rejection_patterns()

    def _compile_rejection_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for detecting rejection conditions."""
        return {
            "generic_advice": [
                re.compile(r"\b(?:you should|you must|always|never|generally|typically)\b", re.IGNORECASE),
                re.compile(r"\b(?:best practice|industry standard|common approach)\b", re.IGNORECASE),
                re.compile(r"\b(?:consider using|try to|think about)\b", re.IGNORECASE),
            ],
            "vanity_metrics": [
                re.compile(r"\b(?:score|rating|grade|percentage|metric)\b.*\b(?:out of|over|above)\b", re.IGNORECASE),
                re.compile(r"\b(?:excellent|good|fair|poor|average)\b.*\b(?:quality|performance|health)\b", re.IGNORECASE),
                re.compile(r"\b\d+(?:\.\d+)?\s*(?:/|out of)\s*\d+(?:\.\d+)?\b"),
            ],
            "unjustified_opinions": [
                re.compile(r"\b(?:clearly|obviously|evidently|undoubtedly|definitely)\b", re.IGNORECASE),
                re.compile(r"\b(?:I think|I believe|in my opinion|seems like)\b", re.IGNORECASE),
                re.compile(r"\b(?:very|extremely|highly|quite|really)\b.*\b(?:important|critical|essential)\b", re.IGNORECASE),
            ],
            "action_bias": [
                re.compile(r"\b(?:must|should|need to|have to|required to)\b.*\b(?:fix|change|update|modify|implement)\b", re.IGNORECASE),
                re.compile(r"\b(?:immediately|urgently|as soon as possible|right away)\b", re.IGNORECASE),
                re.compile(r"\b(?:critical|urgent|emergency|priority)\b.*\b(?:action|fix|change)\b", re.IGNORECASE),
            ],
            "hidden_uncertainty": [
                re.compile(r"\b(?:might|may|could|possibly|perhaps|maybe)\b.*\b(?:be|have|contain|include)\b", re.IGNORECASE),
                re.compile(r"\b(?:potential|possible|likely|probable)\b.*\b(?:issue|problem|risk|vulnerability)\b", re.IGNORECASE),
                re.compile(r"\b(?:appears to|seems to|looks like|resembles)\b", re.IGNORECASE),
            ]
        }

    def evaluate_quality_bar(self, primary_report: str, machine_readable_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate outputs against quality bar standards.

        Args:
            primary_report: The generated primary report (markdown)
            machine_readable_output: The generated machine-readable output (JSON)

        Returns:
            Dict containing quality evaluation with pass/fail status and violations
        """
        evaluation = {
            "passes_quality_bar": True,
            "minimum_standard": self.quality_bar["minimum_standard"],
            "violations": [],
            "violation_details": {}
        }

        # Evaluate primary report
        report_violations = self._evaluate_text_output(primary_report, "primary_report")
        if report_violations:
            evaluation["violations"].extend(report_violations)
            evaluation["violation_details"]["primary_report"] = report_violations

        # Evaluate machine-readable output (check text fields)
        machine_violations = self._evaluate_machine_output(machine_readable_output)
        if machine_violations:
            evaluation["violations"].extend(machine_violations)
            evaluation["violation_details"]["machine_readable_output"] = machine_violations

        # Determine if output passes quality bar
        if evaluation["violations"]:
            evaluation["passes_quality_bar"] = False
            logger.warning("Quality bar failed: %d violations detected", len(evaluation["violations"]))
        else:
            logger.info("Quality bar passed: outputs meet decision-grade standards")

        return evaluation

    def _evaluate_text_output(self, text: str, source: str) -> List[Dict[str, Any]]:
        """
        Evaluate text content against rejection conditions.

        Args:
            text: Text content to evaluate
            source: Source identifier for violations

        Returns:
            List of violation dictionaries
        """
        violations = []

        for condition, patterns in self.rejection_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    violations.append({
                        "condition": condition,
                        "source": source,
                        "pattern": pattern.pattern,
                        "matches": matches[:5],  # Limit to first 5 matches
                        "severity": self._get_condition_severity(condition)
                    })

        return violations

    def _evaluate_machine_output(self, machine_output: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluate machine-readable output for quality violations.

        Focuses on text fields that might contain subjective content.
        """
        violations = []

        # Check executive verdict
        if "executive_verdict" in machine_output:
            verdict_text = str(machine_output["executive_verdict"])
            verdict_violations = self._evaluate_text_output(verdict_text, "machine_readable_output.executive_verdict")
            violations.extend(verdict_violations)

        # Check risk gap ledger entries
        if "risk_gap_ledger" in machine_output:
            for i, entry in enumerate(machine_output["risk_gap_ledger"]):
                if "description" in entry:
                    desc_violations = self._evaluate_text_output(
                        str(entry["description"]),
                        f"machine_readable_output.risk_gap_ledger[{i}].description"
                    )
                    violations.extend(desc_violations)

        # Check evidence index entries
        if "evidence_index" in machine_output:
            for i, entry in enumerate(machine_output["evidence_index"]):
                if "description" in entry:
                    desc_violations = self._evaluate_text_output(
                        str(entry["description"]),
                        f"machine_readable_output.evidence_index[{i}].description"
                    )
                    violations.extend(desc_violations)

        return violations

    def _get_condition_severity(self, condition: str) -> str:
        """Get severity level for a rejection condition."""
        severity_map = {
            "generic_advice": "medium",
            "vanity_metrics": "high",
            "unjustified_opinions": "high",
            "action_bias": "critical",
            "hidden_uncertainty": "medium"
        }
        return severity_map.get(condition, "medium")

    def get_quality_bar_summary(self, evaluation: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of quality bar evaluation.

        Args:
            evaluation: Quality bar evaluation results

        Returns:
            Formatted summary string
        """
        if evaluation["passes_quality_bar"]:
            return f"✅ Quality Bar Passed: Outputs meet {evaluation['minimum_standard']} standards"

        summary = f"❌ Quality Bar Failed: {len(evaluation['violations'])} violations detected\n\n"

        # Group violations by condition
        by_condition = {}
        for violation in evaluation["violations"]:
            condition = violation["condition"]
            if condition not in by_condition:
                by_condition[condition] = []
            by_condition[condition].append(violation)

        for condition, violations in by_condition.items():
            summary += f"**{condition.replace('_', ' ').title()}** ({len(violations)} instances):\n"
            for violation in violations[:3]:  # Show first 3 examples
                summary += f"  - {violation['source']}: {violation['matches'][:2]}\n"
            if len(violations) > 3:
                summary += f"  - ... and {len(violations) - 3} more\n"
            summary += "\n"

        return summary.strip()


def evaluate_quality_bar(primary_report: str, machine_readable_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to evaluate outputs against quality bar.

    Args:
        primary_report: Generated primary report
        machine_readable_output: Generated machine-readable output

    Returns:
        Quality bar evaluation results
    """
    evaluator = QualityBarEvaluator()
    return evaluator.evaluate_quality_bar(primary_report, machine_readable_output)