"""Success criteria validation for Repository Intelligence Scanner."""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class SuccessCriteriaEvaluator:
    """Evaluates analysis pipeline against success criteria."""

    def __init__(self):
        self.success_criteria = [
            "deterministic_verification_passed",
            "refusal_possible_and_clean",
            "blast_radius_explicit",
            "authority_bounds_respected",
            "trust_maintained_over_output_volume"
        ]

    def evaluate_success_criteria(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate analysis results against success criteria.

        Args:
            analysis_results: Complete analysis pipeline results

        Returns:
            Dict containing success criteria evaluation with pass/fail status
        """
        evaluation = {
            "success_criteria_passed": True,
            "criteria_results": {},
            "failure_reasons": [],
            "overall_assessment": "success"
        }

        # Evaluate each success criterion
        criteria_results = {}

        # 1. Deterministic verification passed
        criteria_results["deterministic_verification_passed"] = self._evaluate_deterministic_verification(analysis_results)

        # 2. Refusal possible and clean
        criteria_results["refusal_possible_and_clean"] = self._evaluate_refusal_capability(analysis_results)

        # 3. Blast radius explicit
        criteria_results["blast_radius_explicit"] = self._evaluate_blast_radius_explicit(analysis_results)

        # 4. Authority bounds respected
        criteria_results["authority_bounds_respected"] = self._evaluate_authority_bounds(analysis_results)

        # 5. Trust maintained over output volume
        criteria_results["trust_maintained_over_output_volume"] = self._evaluate_trust_maintenance(analysis_results)

        evaluation["criteria_results"] = criteria_results

        # Determine overall success
        failed_criteria = [k for k, v in criteria_results.items() if not v["passed"]]
        if failed_criteria:
            evaluation["success_criteria_passed"] = False
            evaluation["failure_reasons"] = [criteria_results[k]["reason"] for k in failed_criteria]
            evaluation["overall_assessment"] = "failure"
            logger.warning("Success criteria failed: %d criteria not met", len(failed_criteria))
        else:
            logger.info("Success criteria passed: all operational excellence standards met")

        return evaluation

    def _evaluate_deterministic_verification(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate deterministic verification success."""
        determinism = results.get("determinism_verification", {})

        if not determinism:
            return {
                "passed": False,
                "reason": "Determinism verification not performed",
                "details": "No determinism verification results found"
            }

        # Check if determinism verification passed
        verification_passed = determinism.get("determinism_verification_passed", False)

        if verification_passed:
            return {
                "passed": True,
                "reason": "Deterministic verification passed",
                "details": f"Hash: {determinism.get('governance_hash', 'unknown')}"
            }
        else:
            return {
                "passed": False,
                "reason": "Determinism verification failed",
                "details": determinism.get("verification_errors", ["Unknown determinism issues"])
            }

    def _evaluate_refusal_capability(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate clean refusal capability."""
        silence_policy = results.get("silence_policy_evaluation", {})

        # Check if silence policy was properly evaluated
        if not silence_policy:
            return {
                "passed": False,
                "reason": "Silence policy not evaluated",
                "details": "No silence policy evaluation found"
            }

        # If outputs were generated, check if silence was appropriately not triggered
        outputs_generated = results.get("outputs_generated", False)
        should_be_silent = silence_policy.get("should_be_silent", False)

        if outputs_generated and not should_be_silent:
            # Outputs generated when silence not required - this is correct
            return {
                "passed": True,
                "reason": "Clean output generation when silence not required",
                "details": "System correctly produced outputs for material findings"
            }
        elif not outputs_generated and should_be_silent:
            # Silence triggered when appropriate - this is correct
            return {
                "passed": True,
                "reason": "Clean silence when no action required",
                "details": f"Silence verdict: {silence_policy.get('silence_verdict', 'unknown')}"
            }
        elif outputs_generated and should_be_silent:
            # Outputs generated despite silence being appropriate - this is wrong
            return {
                "passed": False,
                "reason": "Outputs generated despite silence being appropriate",
                "details": "System failed to remain silent when no action was required"
            }
        else:
            # No outputs but silence not triggered - this might be an error
            return {
                "passed": False,
                "reason": "No outputs generated but silence not triggered",
                "details": "System failed to produce outputs when findings exist"
            }

    def _evaluate_blast_radius_explicit(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if blast radius is explicitly stated."""
        decision_artifacts = results.get("decision_artifact_generation", {})
        risk_synthesis = results.get("risk_and_gap_synthesis", {})

        # Check if blast radius is mentioned in decision artifacts
        blast_radius_indicators = []
        recommended_actions = decision_artifacts.get("recommended_actions", [])

        for action in recommended_actions:
            if "blast_radius" in str(action.get("description", "")).lower():
                blast_radius_indicators.append("action_description")
            if "impact" in str(action.get("description", "")).lower():
                blast_radius_indicators.append("impact_mentioned")
            if action.get("risk_level"):
                blast_radius_indicators.append("risk_level_specified")

        # Check risk synthesis for blast radius information
        risks = risk_synthesis.get("risks", [])
        for risk in risks:
            if "blast_radius" in str(risk.get("description", "")).lower():
                blast_radius_indicators.append("risk_blast_radius")

        if blast_radius_indicators:
            return {
                "passed": True,
                "reason": "Blast radius explicitly stated",
                "details": f"Indicators found: {blast_radius_indicators}"
            }
        else:
            return {
                "passed": False,
                "reason": "Blast radius not explicitly stated",
                "details": "No clear indication of potential impact scope in recommendations or risk assessment"
            }

    def _evaluate_authority_bounds(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if authority bounds are respected."""
        authority_evaluation = results.get("authority_ceiling_evaluation", {})

        if not authority_evaluation:
            return {
                "passed": False,
                "reason": "Authority bounds not evaluated",
                "details": "No authority ceiling evaluation found"
            }

        # Check if authority bounds were respected
        bounds_respected = authority_evaluation.get("authority_bounds_respected", False)

        if bounds_respected:
            return {
                "passed": True,
                "reason": "Authority bounds respected",
                "details": f"Authority domain: {authority_evaluation.get('authority_domain', 'unknown')}"
            }
        else:
            violations = authority_evaluation.get("authority_violations", [])
            return {
                "passed": False,
                "reason": "Authority bounds violated",
                "details": f"Violations: {violations}"
            }

    def _evaluate_trust_maintenance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if trust is maintained over output volume."""
        quality_bar = results.get("quality_bar_evaluation", {})

        if not quality_bar:
            return {
                "passed": False,
                "reason": "Quality bar not evaluated",
                "details": "No quality bar evaluation found"
            }

        # Check if quality bar passed
        quality_passed = quality_bar.get("passes_quality_bar", False)

        if quality_passed:
            return {
                "passed": True,
                "reason": "Trust maintained through quality standards",
                "details": f"Quality standard: {quality_bar.get('minimum_standard', 'unknown')}"
            }
        else:
            violations = quality_bar.get("violations", [])
            return {
                "passed": False,
                "reason": "Trust compromised by quality violations",
                "details": f"Quality violations: {len(violations)} detected"
            }

    def get_success_criteria_summary(self, evaluation: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of success criteria evaluation.

        Args:
            evaluation: Success criteria evaluation results

        Returns:
            Formatted summary string
        """
        if evaluation["success_criteria_passed"]:
            return f"✅ Success Criteria Passed: All {len(self.success_criteria)} operational excellence standards met"

        # Count failed criteria
        failed_criteria = [k for k, v in evaluation["criteria_results"].items() if not v["passed"]]
        failure_reasons = evaluation.get("failure_reasons", [])

        summary = f"❌ Success Criteria Failed: {len(failed_criteria)} criteria not met\n\n"

        for criterion in self.success_criteria:
            result = evaluation["criteria_results"][criterion]
            status = "✅" if result["passed"] else "❌"
            summary += f"{status} **{criterion.replace('_', ' ').title()}**\n"
            if not result["passed"]:
                summary += f"   Reason: {result['reason']}\n"
                summary += f"   Details: {result['details']}\n"
            summary += "\n"

        return summary.strip()


def evaluate_success_criteria(analysis_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to evaluate success criteria against analysis results.

    Args:
        analysis_results: Complete analysis pipeline results

    Returns:
        Success criteria evaluation results
    """
    evaluator = SuccessCriteriaEvaluator()
    return evaluator.evaluate_success_criteria(analysis_results)