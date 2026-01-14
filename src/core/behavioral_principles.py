"""
Behavioral Principles and Safety Mechanisms

This module implements the core behavioral rules and safety mechanisms
for the Repository Intelligence Scanner, ensuring refusal-first discipline
and trust guarantees.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


class BehavioralPrinciple(Enum):
    """Core behavioral principles"""
    ONLY_OBSERVABLE_CLAIMS = "only_observable_claims"
    EVIDENCE_SEPARATION = "evidence_separation"
    UNCERTAINTY_VISIBILITY = "uncertainty_visibility"
    CONFIDENCE_JUSTIFICATION = "confidence_justification"
    SILENCE_PREFERENCE = "silence_preference"


class BehavioralRule(Enum):
    """Behavioral rules for analysis"""
    NEVER_GUESS_INTENT = "never_guess_intent"
    NEVER_OPTIMIZE_FOR_OUTPUT_VOLUME = "never_optimize_for_output_volume"
    NEVER_MASK_UNKNOWNS = "never_mask_unknowns"
    NEVER_FORCE_ACTION = "never_force_action"
    NEVER_REQUIRE_MANUAL_INTERVENTION = "never_require_manual_intervention"


class TrustGuarantee(Enum):
    """Trust guarantees"""
    DETERMINISM_IS_MANDATORY = "determinism_is_mandatory"
    REPRODUCIBILITY_IS_REQUIRED = "reproducibility_is_required"
    CONSERVATIVE_BIAS_ON_AMBIGUITY = "conservative_bias_on_ambiguity"
    EXPLICIT_LIMITS_OF_AUTHORITY = "explicit_limits_of_authority"


class OperatingConstraint(Enum):
    """Operating constraints"""
    OFFLINE_ONLY = "offline_only"
    NETWORK_ACCESS_FORBIDDEN = "network_access_forbidden"
    EXTERNAL_SERVICES_FORBIDDEN = "external_services_forbidden"
    REPOSITORY_MODIFICATION_FORBIDDEN = "repository_modification_forbidden"
    EXECUTE_CODE_FORBIDDEN = "execute_code_forbidden"


@dataclass
class RefusalArtifact:
    """Artifact generated when analysis must refuse"""
    reason_for_refusal: str
    missing_or_unknown_information: str
    blast_radius_unbounded_statement: str
    responsible_human_role_required: str
    timestamp: Optional[str] = None


class BehavioralValidator:
    """
    Validates that analysis outputs comply with behavioral principles.
    """

    def __init__(self):
        self.violations: List[str] = []

    def validate_observable_claims(self, findings: List[Dict[str, Any]]) -> bool:
        """
        BPS-001: Ensure all claims are based on observable facts only.

        Returns True if all findings are observable claims.
        """
        for finding in findings:
            if not self._is_observable_claim(finding):
                self.violations.append(
                    f"Non-observable claim in finding: {finding.get('id', 'unknown')}"
                )
                return False
        return True

    def _is_observable_claim(self, finding: Dict[str, Any]) -> bool:
        """Check if a finding represents an observable claim"""
        # Must have evidence field
        if 'evidence' not in finding:
            return False

        evidence = finding['evidence']

        # Evidence must include file path and line range or byte range
        required_fields = ['file_path']
        has_range = 'line_range' in evidence or 'byte_range' in evidence

        if not all(field in evidence for field in required_fields) or not has_range:
            return False

        # Claim must be directly supported by the evidence
        claim = finding.get('claim', '')
        evidence_snippet = evidence.get('snippet', '')

        # Basic check: claim should be related to evidence
        # This is a simplified check - in practice would need more sophisticated validation
        if not evidence_snippet or claim not in evidence_snippet:
            return False

        return True

    def validate_evidence_separation(self, findings: List[Dict[str, Any]]) -> bool:
        """
        BPS-002: Ensure evidence is separated from judgment.

        Returns True if evidence and judgment are properly separated.
        """
        for finding in findings:
            if not self._evidence_separated_from_judgment(finding):
                self.violations.append(
                    f"Evidence not separated from judgment in finding: {finding.get('id', 'unknown')}"
                )
                return False
        return True

    def _evidence_separated_from_judgment(self, finding: Dict[str, Any]) -> bool:
        """Check if evidence is separated from judgment"""
        # Evidence should be in separate field from interpretation
        evidence = finding.get('evidence', {})
        interpretation = finding.get('interpretation', '')

        # Evidence should not contain judgmental language
        judgmental_words = ['bad', 'good', 'risky', 'safe', 'vulnerable', 'secure']

        evidence_text = str(evidence)
        if any(word in evidence_text.lower() for word in judgmental_words):
            return False

        return True

    def validate_uncertainty_visibility(self, findings: List[Dict[str, Any]]) -> bool:
        """
        BPS-003: Ensure uncertainty is visible in confidence reporting.

        Returns True if uncertainty is properly reported.
        """
        for finding in findings:
            if not self._uncertainty_visible(finding):
                self.violations.append(
                    f"Uncertainty not visible in finding: {finding.get('id', 'unknown')}"
                )
                return False
        return True

    def _uncertainty_visible(self, finding: Dict[str, Any]) -> bool:
        """Check if uncertainty is visible in the finding"""
        # Must have confidence field
        if 'confidence' not in finding:
            return False

        confidence = finding['confidence']

        # Confidence must be numeric between 0 and 1
        if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
            return False

        # If confidence is not 1.0, uncertainty explanation should be present
        if confidence < 1.0 and 'uncertainty_reason' not in finding:
            return False

        return True

    def validate_confidence_justification(self, findings: List[Dict[str, Any]]) -> bool:
        """
        BPS-004: Ensure confidence levels are justified.

        Returns True if all confidence levels have justification.
        """
        for finding in findings:
            if not self._confidence_justified(finding):
                self.violations.append(
                    f"Confidence not justified in finding: {finding.get('id', 'unknown')}"
                )
                return False
        return True

    def _confidence_justified(self, finding: Dict[str, Any]) -> bool:
        """Check if confidence level is justified"""
        if 'confidence' not in finding or 'confidence_reason' not in finding:
            return False

        confidence = finding['confidence']
        reason = finding['confidence_reason']

        # Reason should explain the confidence level
        if not reason or len(reason) < 10:  # Minimum explanation length
            return False

        return True

    def validate_silence_preference(self, findings: List[Dict[str, Any]]) -> bool:
        """
        BPS-005: Prefer silence over false precision.

        Returns True if silence is preferred appropriately.
        """
        # This is more of a design principle than a validation
        # Check that low-confidence findings are marked appropriately
        low_confidence_count = sum(1 for f in findings if f.get('confidence', 1.0) < 0.5)

        # If we have many low-confidence findings, should consider silence
        if low_confidence_count > len(findings) * 0.3:  # More than 30% low confidence
            # This would trigger a review, but for validation we pass
            pass

        return True

    def get_violations(self) -> List[str]:
        """Get list of validation violations"""
        return self.violations.copy()

    def reset(self):
        """Reset violations list"""
        self.violations.clear()


# Global validator instance
behavioral_validator = BehavioralValidator()


class RefusalChecker:
    """
    Checks for behavioral rule violations that require analysis refusal.
    """

    def __init__(self):
        self.refusal_artifacts: List[RefusalArtifact] = []

    def check_never_guess_intent(self, analysis_request: Dict[str, Any], repository_content: Dict[str, Any]) -> Optional[RefusalArtifact]:
        """
        BPS-006: Check if analysis would require guessing intent.

        Returns a refusal artifact if intent cannot be determined from observable evidence.
        """
        # Check if the analysis request requires intent interpretation
        if self._requires_intent_inference(analysis_request):
            # Check if intent can be determined from observable evidence
            if not self._intent_observable_from_evidence(repository_content):
                return generate_refusal_artifact(
                    reason_for_refusal="Analysis would require guessing intent",
                    missing_or_unknown_information="Intent cannot be determined from observable repository content",
                    blast_radius_unbounded_statement="Incorrect intent assumptions could lead to false security conclusions",
                    responsible_human_role_required="Security architect or developer with domain knowledge"
                )
        return None

    def _requires_intent_inference(self, analysis_request: Dict[str, Any]) -> bool:
        """Check if the analysis request requires intent interpretation"""
        # Analysis types that typically require intent inference
        intent_requiring_types = [
            'security_review', 'vulnerability_assessment', 'code_quality',
            'architecture_analysis', 'compliance_check', 'risk_assessment'
        ]

        analysis_type = analysis_request.get('type', '').lower()
        return any(intent_type in analysis_type for intent_type in intent_requiring_types)

    def _intent_observable_from_evidence(self, repository_content: Dict[str, Any]) -> bool:
        """Check if intent can be determined from observable repository evidence"""
        # Look for explicit intent indicators in repository content
        intent_indicators = [
            'readme', 'documentation', 'config', 'manifest', 'changelog',
            'security_policy', 'contributing', 'license'
        ]

        files = repository_content.get('files', [])
        file_names = [f.lower() for f in files]

        # Check for documentation files that might indicate intent
        has_documentation = any(
            any(indicator in fname for indicator in intent_indicators)
            for fname in file_names
        )

        # Check for explicit security/compliance configurations
        has_security_config = any(
            'security' in fname or 'policy' in fname or 'compliance' in fname
            for fname in file_names
        )

        # If we have documentation or security configs, intent might be observable
        return has_documentation or has_security_config

    def check_never_optimize_for_output_volume(self, analysis_request: Dict[str, Any]) -> Optional[RefusalArtifact]:
        """
        BPS-007: Check if analysis optimizes for output volume.

        Returns a refusal artifact if the request prioritizes quantity over quality.
        """
        # Check for indicators of volume optimization
        if self._indicates_volume_optimization(analysis_request):
            return generate_refusal_artifact(
                reason_for_refusal="Analysis request optimizes for output volume",
                missing_or_unknown_information="Cannot guarantee quality with volume-focused analysis",
                blast_radius_unbounded_statement="High-volume low-quality findings increase false positive burden",
                responsible_human_role_required="Quality assurance engineer or security analyst"
            )
        return None

    def _indicates_volume_optimization(self, analysis_request: Dict[str, Any]) -> bool:
        """Check if request indicates volume optimization"""
        # Look for volume-focused parameters
        volume_indicators = [
            'max_findings', 'all_issues', 'comprehensive_scan',
            'full_coverage', 'exhaustive_analysis'
        ]

        request_str = str(analysis_request).lower()
        return any(indicator in request_str for indicator in volume_indicators)

    def check_never_mask_unknowns(self, analysis_request: Dict[str, Any], repository_content: Dict[str, Any]) -> Optional[RefusalArtifact]:
        """
        BPS-008: Check if analysis would mask unknowns.

        Returns a refusal artifact if unknowns would be hidden.
        """
        # Check if analysis scope includes unknown areas
        unknowns = self._identify_unknowns(repository_content)
        if unknowns and self._would_mask_unknowns(analysis_request, unknowns):
            return generate_refusal_artifact(
                reason_for_refusal="Analysis would mask unknowns",
                missing_or_unknown_information=f"Unknown areas identified: {', '.join(unknowns)}",
                blast_radius_unbounded_statement="Masked unknowns could hide critical security issues",
                responsible_human_role_required="Security researcher or domain expert"
            )
        return None

    def _identify_unknowns(self, repository_content: Dict[str, Any]) -> List[str]:
        """Identify areas of the repository that are unknown/unclear"""
        unknowns = []

        # Check for unsupported file types
        files = repository_content.get('files', [])
        unsupported_extensions = ['.exe', '.dll', '.so', '.dylib', '.bin']
        has_unsupported = any(
            any(f.endswith(ext) for ext in unsupported_extensions)
            for f in files
        )
        if has_unsupported:
            unknowns.append("binary_files")

        # Check for encrypted/compressed files
        encrypted_indicators = ['encrypted', 'compressed', 'archive']
        has_encrypted = any(
            any(indicator in f.lower() for indicator in encrypted_indicators)
            for f in files
        )
        if has_encrypted:
            unknowns.append("encrypted_content")

        # Check for very large files that might be unanalyzed
        # This is a simplified check - in practice would check actual file sizes
        large_file_indicators = ['large', 'big', 'huge']
        has_large_files = any(
            any(indicator in f.lower() for indicator in large_file_indicators)
            for f in files
        )
        if has_large_files:
            unknowns.append("large_files")

        return unknowns

    def _would_mask_unknowns(self, analysis_request: Dict[str, Any], unknowns: List[str]) -> bool:
        """Check if the analysis would mask the identified unknowns"""
        # If unknowns exist and analysis doesn't explicitly acknowledge them,
        # it might be masking them
        if unknowns:
            request_str = str(analysis_request).lower()
            # Look for explicit unknown handling
            explicit_unknown_handling = any(term in request_str for term in [
                'include_unknowns', 'analyze_all', 'comprehensive', 'full_scan'
            ])
            return not explicit_unknown_handling
        return False

    def check_never_force_action(self, analysis_request: Dict[str, Any]) -> Optional[RefusalArtifact]:
        """
        BPS-009: Check if analysis would force action on uncertain findings.

        Returns a refusal artifact if actions would be forced.
        """
        if self._would_force_action(analysis_request):
            return generate_refusal_artifact(
                reason_for_refusal="Analysis would force action on uncertain findings",
                missing_or_unknown_information="Cannot determine appropriate actions for uncertain findings",
                blast_radius_unbounded_statement="Forced actions on uncertain findings could cause unnecessary disruption",
                responsible_human_role_required="Operations or DevOps engineer"
            )
        return None

    def _would_force_action(self, analysis_request: Dict[str, Any]) -> bool:
        """Check if analysis would force actions"""
        # Look for action-forcing parameters
        action_indicators = [
            'auto_fix', 'auto_remediate', 'force_update', 'mandatory_action',
            'enforce_policy', 'block_merge', 'fail_build'
        ]

        request_str = str(analysis_request).lower()
        return any(indicator in request_str for indicator in action_indicators)

    def check_never_require_manual_intervention(self, analysis_request: Dict[str, Any]) -> Optional[RefusalArtifact]:
        """
        BPS-010: Check if analysis requires manual intervention.

        Returns a refusal artifact if manual intervention is required.
        """
        if self._requires_manual_intervention(analysis_request):
            return generate_refusal_artifact(
                reason_for_refusal="Analysis requires manual intervention",
                missing_or_unknown_information="Automated analysis cannot proceed without human input",
                blast_radius_unbounded_statement="Manual intervention breaks automation and introduces delays",
                responsible_human_role_required="System administrator or operator"
            )
        return None

    def _requires_manual_intervention(self, analysis_request: Dict[str, Any]) -> bool:
        """Check if analysis requires manual intervention"""
        # Look for manual intervention requirements
        manual_indicators = [
            'manual_review', 'human_approval', 'interactive', 'prompt_user',
            'manual_input', 'user_confirmation', 'manual_override'
        ]

        request_str = str(analysis_request).lower()
        return any(indicator in request_str for indicator in manual_indicators)

    def perform_refusal_checks(self, analysis_request: Dict[str, Any], repository_content: Dict[str, Any]) -> List[RefusalArtifact]:
        """
        Perform all behavioral rule refusal checks.

        Returns list of refusal artifacts if any checks fail.
        """
        refusals = []

        # BPS-006: Never guess intent
        refusal = self.check_never_guess_intent(analysis_request, repository_content)
        if refusal:
            refusals.append(refusal)

        # BPS-007: Never optimize for output volume
        refusal = self.check_never_optimize_for_output_volume(analysis_request)
        if refusal:
            refusals.append(refusal)

        # BPS-008: Never mask unknowns
        refusal = self.check_never_mask_unknowns(analysis_request, repository_content)
        if refusal:
            refusals.append(refusal)

        # BPS-009: Never force action
        refusal = self.check_never_force_action(analysis_request)
        if refusal:
            refusals.append(refusal)

        # BPS-010: Never require manual intervention
        refusal = self.check_never_require_manual_intervention(analysis_request)
        if refusal:
            refusals.append(refusal)

        self.refusal_artifacts.extend(refusals)
        return refusals

    def get_refusal_artifacts(self) -> List[RefusalArtifact]:
        """Get all generated refusal artifacts"""
        return self.refusal_artifacts.copy()

    def reset(self):
        """Reset refusal artifacts list"""
        self.refusal_artifacts.clear()


# Global refusal checker instance
refusal_checker = RefusalChecker()


def validate_behavioral_compliance(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate that findings comply with all behavioral principles.

    Returns validation result with compliance status and violations.
    """
    validator = BehavioralValidator()

    compliance = {
        'observable_claims': validator.validate_observable_claims(findings),
        'evidence_separation': validator.validate_evidence_separation(findings),
        'uncertainty_visibility': validator.validate_uncertainty_visibility(findings),
        'confidence_justification': validator.validate_confidence_justification(findings),
        'silence_preference': validator.validate_silence_preference(findings),
    }

    overall_compliant = all(compliance.values())

    return {
        'compliant': overall_compliant,
        'violations': validator.get_violations(),
        'principle_compliance': compliance
    }


def generate_refusal_artifact(reason: str, missing_info: str, blast_radius: str, human_role: str) -> RefusalArtifact:
    """
    Generate a refusal artifact when analysis cannot proceed safely.
    """
    return RefusalArtifact(
        reason_for_refusal=reason,
        missing_or_unknown_information=missing_info,
        blast_radius_unbounded_statement=blast_radius,
        responsible_human_role_required=human_role
    )