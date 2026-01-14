"""Silence policy evaluation for Repository Intelligence Scanner."""

import logging
from typing import Dict, Any, Optional

from ..quality.assurance import SILENCE_POLICY

logger = logging.getLogger(__name__)


class SilencePolicyEvaluator:
    """Evaluates whether scanner should produce outputs or remain silent."""

    def __init__(self):
        self.policy = SILENCE_POLICY

    def evaluate_silence_conditions(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate analysis results against silence policy conditions.

        Args:
            analysis_results: Complete analysis pipeline results

        Returns:
            Dict containing silence evaluation with verdict and reasoning
        """
        evaluation = {
            "should_be_silent": False,
            "silence_conditions_met": [],
            "silence_verdict": None,
            "evaluation_reasoning": []
        }

        # Check for material findings
        material_findings = self._check_material_findings(analysis_results)
        if not material_findings:
            evaluation["silence_conditions_met"].append("no_material_findings")
            evaluation["evaluation_reasoning"].append(
                "No material findings identified that warrant action"
            )

        # Check for safe actions identified
        safe_actions = self._check_safe_actions_identified(analysis_results)
        if not safe_actions:
            evaluation["silence_conditions_met"].append("no_safe_action_identified")
            evaluation["evaluation_reasoning"].append(
                "No safe actions identified for recommendation"
            )

        # Determine if silence is appropriate
        required_conditions = set(self.policy["allowed_conditions"])
        met_conditions = set(evaluation["silence_conditions_met"])

        if required_conditions.issubset(met_conditions):
            evaluation["should_be_silent"] = True
            evaluation["silence_verdict"] = self.policy["explicit_silence_verdict"]
            logger.info("Silence policy triggered: %s", evaluation["silence_verdict"])
        else:
            missing_conditions = required_conditions - met_conditions
            evaluation["evaluation_reasoning"].append(
                f"Silence not appropriate - missing conditions: {missing_conditions}"
            )
            logger.info("Silence policy not triggered - proceeding with output generation")

        return evaluation

    def _check_material_findings(self, analysis_results: Dict[str, Any]) -> bool:
        """
        Check if analysis results contain material findings that warrant action.

        Material findings are those with:
        - High severity (critical, high)
        - Medium severity with clear evidence
        - Security vulnerabilities
        - Compliance violations
        """
        # Check risk synthesis results
        risk_synthesis = analysis_results.get("risk_and_gap_synthesis", {})
        if not risk_synthesis:
            return False

        risks = risk_synthesis.get("risks", [])
        gaps = risk_synthesis.get("gaps", [])

        # Check for high-severity risks
        high_severity_risks = [
            risk for risk in risks
            if risk.get("severity", "").lower() in ["critical", "high"]
        ]

        # Check for security-related risks
        security_risks = [
            risk for risk in risks
            if "security" in risk.get("category", "").lower() or
            "vulnerability" in risk.get("type", "").lower()
        ]

        # Check for compliance gaps
        compliance_gaps = [
            gap for gap in gaps
            if "compliance" in gap.get("category", "").lower()
        ]

        material_findings = (
            len(high_severity_risks) > 0 or
            len(security_risks) > 0 or
            len(compliance_gaps) > 0
        )

        if material_findings:
            logger.debug("Material findings detected: %d high-severity, %d security, %d compliance",
                        len(high_severity_risks), len(security_risks), len(compliance_gaps))

        return material_findings

    def _check_safe_actions_identified(self, analysis_results: Dict[str, Any]) -> bool:
        """
        Check if analysis results identify safe actions that can be recommended.

        Safe actions are those with:
        - Clear implementation path
        - Low risk of negative consequences
        - High confidence in effectiveness
        """
        # Check decision artifacts
        decision_artifacts = analysis_results.get("decision_artifact_generation", {})
        if not decision_artifacts:
            return False

        safe_changes = decision_artifacts.get("safe_changes", [])
        recommended_actions = decision_artifacts.get("recommended_actions", [])

        # Filter for actions with high confidence and low risk
        safe_actions = []
        for action in recommended_actions:
            confidence = action.get("confidence", 0.0)
            risk_level = action.get("risk_level", "unknown")

            if confidence >= 0.8 and risk_level.lower() in ["low", "minimal"]:
                safe_actions.append(action)

        # Include safe changes as they represent low-risk modifications
        total_safe_actions = len(safe_actions) + len(safe_changes)

        if total_safe_actions > 0:
            logger.debug("Safe actions identified: %d recommended actions, %d safe changes",
                        len(safe_actions), len(safe_changes))

        return total_safe_actions > 0


def evaluate_silence_policy(analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to evaluate silence policy against analysis results.

    Args:
        analysis_results: Complete analysis pipeline results

    Returns:
        Silence policy evaluation results
    """
    evaluator = SilencePolicyEvaluator()
    return evaluator.evaluate_silence_conditions(analysis_results)