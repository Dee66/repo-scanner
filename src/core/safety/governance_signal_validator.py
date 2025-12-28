"""Governance Signal Validation for Repository Intelligence Scanner.

Validates governance signals for consistency and detects contradictions that
could indicate misleading or incorrect governance information.
"""

from typing import Dict, List, Set, Optional, Tuple
import re


class GovernanceSignalValidator:
    """Validates governance signals and detects contradictions."""

    def __init__(self):
        self.required_governance_signals = [
            "ownership_artifacts",
            "code_review_process",
            "testing_standards",
            "deployment_process",
            "security_requirements"
        ]

        self.contradiction_patterns = [
            {
                "name": "ownership_contradiction",
                "description": "Multiple conflicting ownership claims",
                "signals": ["owner_files", "codeowners_file", "readme_ownership"],
                "check_function": self._check_ownership_contradictions
            },
            {
                "name": "maturity_contradiction",
                "description": "Governance maturity indicators contradict each other",
                "signals": ["test_coverage", "code_review_rate", "deployment_frequency"],
                "check_function": self._check_maturity_contradictions
            },
            {
                "name": "security_contradiction",
                "description": "Security requirements conflict with implementation",
                "signals": ["security_policy", "vulnerability_scans", "dependency_management"],
                "check_function": self._check_security_contradictions
            }
        ]

    def validate_governance_signals(self, governance_signals: Dict) -> Dict:
        """Validate governance signals for completeness and consistency.

        Returns a dict with:
        - valid: bool - whether governance signals are valid
        - completeness_score: float - fraction of required signals present (0-1)
        - contradictions: List[Dict] - any detected contradictions
        - confidence_score: float - confidence in the validation (0-1)
        - recommendations: List[str] - suggested improvements
        """
        completeness_score = self._calculate_completeness(governance_signals)
        contradictions = self._detect_contradictions(governance_signals)
        confidence_score = self._calculate_confidence(governance_signals, contradictions)

        valid = completeness_score >= 0.7 and len(contradictions) == 0
        recommendations = self._generate_recommendations(governance_signals, contradictions)

        return {
            "valid": valid,
            "completeness_score": completeness_score,
            "contradictions": contradictions,
            "confidence_score": confidence_score,
            "recommendations": recommendations
        }

    def _calculate_completeness(self, signals: Dict) -> float:
        """Calculate completeness score based on required signals."""
        present_signals = 0
        total_signals = len(self.required_governance_signals)

        for required_signal in self.required_governance_signals:
            if required_signal in signals and signals[required_signal]:
                present_signals += 1

        return present_signals / total_signals if total_signals > 0 else 0

    def _detect_contradictions(self, signals: Dict) -> List[Dict]:
        """Detect contradictions in governance signals."""
        contradictions = []

        for pattern in self.contradiction_patterns:
            contradiction = pattern["check_function"](signals)
            if contradiction:
                contradictions.append({
                    "type": pattern["name"],
                    "description": pattern["description"],
                    "severity": contradiction.get("severity", "medium"),
                    "details": contradiction.get("details", ""),
                    "affected_signals": pattern["signals"]
                })

        return contradictions

    def _check_ownership_contradictions(self, signals: Dict) -> Optional[Dict]:
        """Check for ownership contradictions."""
        ownership_sources = []

        # Check for different ownership files/sources
        if signals.get("owner_files"):
            ownership_sources.append("owner_files")
        if signals.get("codeowners_file"):
            ownership_sources.append("codeowners_file")
        if signals.get("readme_ownership"):
            ownership_sources.append("readme_ownership")

        if len(ownership_sources) > 1:
            # Check if they specify different owners
            owners = set()
            for source in ownership_sources:
                source_owners = signals.get(source, [])
                if isinstance(source_owners, list):
                    owners.update(source_owners)
                elif isinstance(source_owners, str):
                    owners.add(source_owners)

            if len(owners) > 1:
                return {
                    "severity": "high",
                    "details": f"Multiple ownership sources specify different owners: {', '.join(owners)}"
                }

        return None

    def _check_maturity_contradictions(self, signals: Dict) -> Optional[Dict]:
        """Check for maturity level contradictions."""
        test_coverage = signals.get("test_coverage", 0)
        code_review_rate = signals.get("code_review_rate", 0)
        deployment_frequency = signals.get("deployment_frequency", "unknown")

        contradictions = []

        # High test coverage but low code review rate
        if test_coverage > 80 and code_review_rate < 50:
            contradictions.append("High test coverage contradicts low code review rate")

        # Frequent deployments but low test coverage
        if deployment_frequency in ["daily", "weekly"] and test_coverage < 60:
            contradictions.append("Frequent deployments contradict low test coverage")

        if contradictions:
            return {
                "severity": "medium",
                "details": "; ".join(contradictions)
            }

        return None

    def _check_security_contradictions(self, signals: Dict) -> Optional[Dict]:
        """Check for security requirement contradictions."""
        has_security_policy = bool(signals.get("security_policy"))
        has_vulnerability_scans = bool(signals.get("vulnerability_scans"))
        dependency_management = signals.get("dependency_management", {})

        contradictions = []

        # Security policy exists but no vulnerability scanning
        if has_security_policy and not has_vulnerability_scans:
            contradictions.append("Security policy exists but no vulnerability scanning")

        # Dependency management claims security but no updates
        if dependency_management.get("security_focused") and not dependency_management.get("auto_updates"):
            contradictions.append("Security-focused dependency management but no automatic updates")

        if contradictions:
            return {
                "severity": "high",
                "details": "; ".join(contradictions)
            }

        return None

    def _calculate_confidence(self, signals: Dict, contradictions: List[Dict]) -> float:
        """Calculate confidence in governance signal validation."""
        confidence = 0.5  # Base confidence

        # Increase confidence based on signal quality
        if signals.get("signal_sources"):
            confidence += 0.2

        if signals.get("last_updated"):
            confidence += 0.1

        if signals.get("audit_trail"):
            confidence += 0.2

        # Decrease confidence for contradictions
        confidence -= len(contradictions) * 0.1

        return max(0, min(1, confidence))

    def _generate_recommendations(self, signals: Dict, contradictions: List[Dict]) -> List[str]:
        """Generate recommendations for improving governance signals."""
        recommendations = []

        # Completeness recommendations
        completeness = self._calculate_completeness(signals)
        if completeness < 0.7:
            missing_signals = []
            for required in self.required_governance_signals:
                if required not in signals or not signals[required]:
                    missing_signals.append(required.replace("_", " ").title())
            if missing_signals:
                recommendations.append(f"Add missing governance signals: {', '.join(missing_signals)}")

        # Contradiction recommendations
        for contradiction in contradictions:
            if contradiction["type"] == "ownership_contradiction":
                recommendations.append("Consolidate ownership information into a single authoritative source")
            elif contradiction["type"] == "maturity_contradiction":
                recommendations.append("Align maturity indicators (test coverage, code review, deployment frequency)")
            elif contradiction["type"] == "security_contradiction":
                recommendations.append("Ensure security policies are implemented and monitored")

        # General recommendations
        if not signals.get("audit_trail"):
            recommendations.append("Implement audit trail for governance signal changes")

        if not signals.get("automated_validation"):
            recommendations.append("Add automated validation of governance signal accuracy")

        return recommendations


def validate_governance_consistency(governance_signals: Dict) -> Dict:
    """High-level function to validate governance signal consistency."""
    validator = GovernanceSignalValidator()
    return validator.validate_governance_signals(governance_signals)


def governance_signals_require_attention(validation_result: Dict) -> bool:
    """Check if governance signals require human attention."""
    return not validation_result.get("valid", False) or len(validation_result.get("contradictions", [])) > 0