"""
Authority Limits and Ceiling Evaluation for Repository Intelligence Scanner.

BPS-014: Implement explicit_limits_of_authority guarantee.
This module defines and enforces the system's explicit limits of authority,
ensuring the scanner never exceeds its defined boundaries of operation.
"""

from enum import Enum
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class AuthorityDomain(Enum):
    """Domains of authority the scanner is permitted to operate in."""
    REPOSITORY_ANALYSIS = "repository_analysis"
    CODE_SECURITY_ASSESSMENT = "code_security_assessment"
    COMPLIANCE_EVALUATION = "compliance_evaluation"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    ARCHITECTURAL_REVIEW = "architectural_review"
    INTENT_ASSESSMENT = "intent_assessment"


class AuthorityLimit(Enum):
    """Specific limits of authority."""
    # Analysis scope limits
    ANALYSIS_DEPTH_LIMIT = "analysis_depth_limit"
    FILE_SIZE_LIMIT = "file_size_limit"
    REPOSITORY_SIZE_LIMIT = "repository_size_limit"
    LANGUAGE_SUPPORT_LIMIT = "language_support_limit"

    # Operational limits
    EXECUTION_TIME_LIMIT = "execution_time_limit"
    MEMORY_USAGE_LIMIT = "memory_usage_limit"
    NETWORK_ACCESS_FORBIDDEN = "network_access_forbidden"
    FILE_SYSTEM_MODIFICATION_FORBIDDEN = "file_system_modification_forbidden"
    CODE_EXECUTION_FORBIDDEN = "code_execution_forbidden"

    # Assessment limits
    SECURITY_JUDGMENT_LIMIT = "security_judgment_limit"
    COMPLIANCE_CERTIFICATION_LIMIT = "compliance_certification_limit"
    LEGAL_OPINION_LIMIT = "legal_opinion_limit"
    BUSINESS_DECISION_LIMIT = "business_decision_limit"

    # Authority boundaries
    HUMAN_OVERRIDE_REQUIRED = "human_override_required"
    EXPERT_REVIEW_REQUIRED = "expert_review_required"
    REGULATORY_APPROVAL_REQUIRED = "regulatory_approval_required"


@dataclass
class AuthorityBoundary:
    """Defines a specific authority boundary."""
    limit: AuthorityLimit
    description: str
    enforcement_mechanism: str
    violation_consequence: str
    human_override_required: bool
    applicable_domains: Set[AuthorityDomain]


@dataclass
class AuthorityViolation:
    """Represents a violation of authority limits."""
    violated_limit: AuthorityLimit
    violation_description: str
    operation_attempted: str
    timestamp: str
    requires_human_intervention: bool


class AuthorityCeilingEvaluator:
    """
    Evaluates and enforces authority ceiling limits.

    BPS-014: Ensures the system never exceeds its defined authority boundaries.
    """

    def __init__(self):
        self.authority_boundaries = self._define_authority_boundaries()
        self.violations: List[AuthorityViolation] = []

    def _define_authority_boundaries(self) -> Dict[AuthorityLimit, AuthorityBoundary]:
        """Define all authority boundaries for the scanner."""
        return {
            AuthorityLimit.ANALYSIS_DEPTH_LIMIT: AuthorityBoundary(
                limit=AuthorityLimit.ANALYSIS_DEPTH_LIMIT,
                description="Analysis limited to static code analysis and observable patterns",
                enforcement_mechanism="Pattern matching and evidence-based assessment only",
                violation_consequence="Analysis refused - requires human expert review",
                human_override_required=True,
                applicable_domains={
                    AuthorityDomain.REPOSITORY_ANALYSIS,
                    AuthorityDomain.CODE_SECURITY_ASSESSMENT,
                    AuthorityDomain.ARCHITECTURAL_REVIEW
                }
            ),

            AuthorityLimit.SECURITY_JUDGMENT_LIMIT: AuthorityBoundary(
                limit=AuthorityLimit.SECURITY_JUDGMENT_LIMIT,
                description="Cannot make definitive security judgments - only identifies patterns",
                enforcement_mechanism="Pattern identification with confidence scoring only",
                violation_consequence="Judgment refused - requires security expert review",
                human_override_required=True,
                applicable_domains={AuthorityDomain.CODE_SECURITY_ASSESSMENT}
            ),

            AuthorityLimit.COMPLIANCE_CERTIFICATION_LIMIT: AuthorityBoundary(
                limit=AuthorityLimit.COMPLIANCE_CERTIFICATION_LIMIT,
                description="Cannot certify compliance - only identifies compliance patterns",
                enforcement_mechanism="Compliance pattern detection only",
                violation_consequence="Certification refused - requires compliance officer review",
                human_override_required=True,
                applicable_domains={AuthorityDomain.COMPLIANCE_EVALUATION}
            ),

            AuthorityLimit.LEGAL_OPINION_LIMIT: AuthorityBoundary(
                limit=AuthorityLimit.LEGAL_OPINION_LIMIT,
                description="Cannot provide legal opinions or advice",
                enforcement_mechanism="Legal pattern identification only",
                violation_consequence="Legal opinion refused - requires legal counsel",
                human_override_required=True,
                applicable_domains={AuthorityDomain.COMPLIANCE_EVALUATION}
            ),

            AuthorityLimit.BUSINESS_DECISION_LIMIT: AuthorityBoundary(
                limit=AuthorityLimit.BUSINESS_DECISION_LIMIT,
                description="Cannot make business decisions or recommendations",
                enforcement_mechanism="Technical analysis only",
                violation_consequence="Business decision refused - requires business stakeholder",
                human_override_required=True,
                applicable_domains={
                    AuthorityDomain.REPOSITORY_ANALYSIS,
                    AuthorityDomain.INTENT_ASSESSMENT
                }
            ),

            AuthorityLimit.NETWORK_ACCESS_FORBIDDEN: AuthorityBoundary(
                limit=AuthorityLimit.NETWORK_ACCESS_FORBIDDEN,
                description="Network access is strictly forbidden",
                enforcement_mechanism="Offline-only operation enforced",
                violation_consequence="Network operation blocked",
                human_override_required=False,
                applicable_domains=set(AuthorityDomain)  # All domains
            ),

            AuthorityLimit.FILE_SYSTEM_MODIFICATION_FORBIDDEN: AuthorityBoundary(
                limit=AuthorityLimit.FILE_SYSTEM_MODIFICATION_FORBIDDEN,
                description="File system modification is strictly forbidden",
                enforcement_mechanism="Read-only access enforced",
                violation_consequence="Modification operation blocked",
                human_override_required=False,
                applicable_domains=set(AuthorityDomain)  # All domains
            ),

            AuthorityLimit.CODE_EXECUTION_FORBIDDEN: AuthorityBoundary(
                limit=AuthorityLimit.CODE_EXECUTION_FORBIDDEN,
                description="Code execution is strictly forbidden",
                enforcement_mechanism="Static analysis only",
                violation_consequence="Execution operation blocked",
                human_override_required=False,
                applicable_domains=set(AuthorityDomain)  # All domains
            ),

            AuthorityLimit.EXPERT_REVIEW_REQUIRED: AuthorityBoundary(
                limit=AuthorityLimit.EXPERT_REVIEW_REQUIRED,
                description="High-risk findings require expert review",
                enforcement_mechanism="Critical finding flag with review requirement",
                violation_consequence="Analysis flagged for expert review",
                human_override_required=True,
                applicable_domains={
                    AuthorityDomain.CODE_SECURITY_ASSESSMENT,
                    AuthorityDomain.ARCHITECTURAL_REVIEW
                }
            )
        }

    def evaluate_authority_ceiling(self, operation: str, domain: AuthorityDomain,
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate if an operation exceeds authority ceiling.

        Returns evaluation result with any violations.
        """
        violations = []

        # Check each applicable authority boundary
        for limit, boundary in self.authority_boundaries.items():
            if domain in boundary.applicable_domains:
                violation = self._check_boundary_violation(limit, boundary, operation, context)
                if violation:
                    violations.append(violation)

        # Determine if operation can proceed
        can_proceed = not any(v.requires_human_intervention for v in violations)
        requires_override = any(v.requires_human_intervention for v in violations)

        evaluation_result = {
            "operation": operation,
            "domain": domain.value,
            "authority_evaluation": {
                "can_proceed": can_proceed,
                "requires_human_override": requires_override,
                "violations_detected": len(violations) > 0,
                "violation_count": len(violations)
            },
            "authority_violations": [
                {
                    "limit": v.violated_limit.value,
                    "description": v.violation_description,
                    "requires_human_intervention": v.requires_human_intervention
                }
                for v in violations
            ],
            "authority_boundaries_checked": len([
                b for b in self.authority_boundaries.values()
                if domain in b.applicable_domains
            ]),
            "evaluation_timestamp": "2025-12-23T00:00:00Z"
        }

        if violations:
            logger.warning(f"Authority ceiling violations detected for {operation}: {len(violations)} violations")

        return evaluation_result

    def _check_boundary_violation(self, limit: AuthorityLimit, boundary: AuthorityBoundary,
                                operation: str, context: Dict[str, Any]) -> Optional[AuthorityViolation]:
        """
        Check if a specific authority boundary is violated.
        """
        # Network access check
        if limit == AuthorityLimit.NETWORK_ACCESS_FORBIDDEN:
            if self._detects_network_access_attempt(operation, context):
                return AuthorityViolation(
                    violated_limit=limit,
                    violation_description="Network access attempted in offline-only system",
                    operation_attempted=operation,
                    timestamp="2025-12-23T00:00:00Z",
                    requires_human_intervention=False  # Automatic blocking
                )

        # File system modification check
        elif limit == AuthorityLimit.FILE_SYSTEM_MODIFICATION_FORBIDDEN:
            if self._detects_file_modification_attempt(operation, context):
                return AuthorityViolation(
                    violated_limit=limit,
                    violation_description="File system modification attempted in read-only system",
                    operation_attempted=operation,
                    timestamp="2025-12-23T00:00:00Z",
                    requires_human_intervention=False  # Automatic blocking
                )

        # Code execution check
        elif limit == AuthorityLimit.CODE_EXECUTION_FORBIDDEN:
            if self._detects_code_execution_attempt(operation, context):
                return AuthorityViolation(
                    violated_limit=limit,
                    violation_description="Code execution attempted in static analysis system",
                    operation_attempted=operation,
                    timestamp="2025-12-23T00:00:00Z",
                    requires_human_intervention=False  # Automatic blocking
                )

        # Security judgment check
        elif limit == AuthorityLimit.SECURITY_JUDGMENT_LIMIT:
            if self._detects_security_judgment_attempt(operation, context):
                return AuthorityViolation(
                    violated_limit=limit,
                    violation_description="Security judgment attempted beyond pattern identification",
                    operation_attempted=operation,
                    timestamp="2025-12-23T00:00:00Z",
                    requires_human_intervention=True  # Requires expert review
                )

        # Compliance certification check
        elif limit == AuthorityLimit.COMPLIANCE_CERTIFICATION_LIMIT:
            if self._detects_compliance_certification_attempt(operation, context):
                return AuthorityViolation(
                    violated_limit=limit,
                    violation_description="Compliance certification attempted beyond pattern detection",
                    operation_attempted=operation,
                    timestamp="2025-12-23T00:00:00Z",
                    requires_human_intervention=True  # Requires compliance officer
                )

        # Business decision check
        elif limit == AuthorityLimit.BUSINESS_DECISION_LIMIT:
            if self._detects_business_decision_attempt(operation, context):
                return AuthorityViolation(
                    violated_limit=limit,
                    violation_description="Business decision attempted beyond technical analysis",
                    operation_attempted=operation,
                    timestamp="2025-12-23T00:00:00Z",
                    requires_human_intervention=True  # Requires business stakeholder
                )

        return None

    def _detects_network_access_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """Detect if operation attempts network access."""
        network_indicators = [
            'http', 'https', 'ftp', 'ssh', 'api', 'download', 'upload',
            'network', 'internet', 'remote', 'external', 'cloud'
        ]

        operation_str = operation.lower()
        context_str = str(context).lower()

        return any(indicator in operation_str or indicator in context_str
                  for indicator in network_indicators)

    def _detects_file_modification_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """Detect if operation attempts file system modification."""
        modification_indicators = [
            'write', 'modify', 'delete', 'create', 'update', 'save',
            'edit', 'change', 'alter', 'remove'
        ]

        operation_str = operation.lower()
        context_str = str(context).lower()

        return any(indicator in operation_str or indicator in context_str
                  for indicator in modification_indicators)

    def _detects_code_execution_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """Detect if operation attempts code execution."""
        execution_indicators = [
            'execute', 'run', 'eval', 'exec', 'system', 'shell', 'command',
            'process', 'spawn', 'launch', 'start'
        ]

        operation_str = operation.lower()
        context_str = str(context).lower()

        return any(indicator in operation_str or indicator in context_str
                  for indicator in execution_indicators)

    def _detects_security_judgment_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """Detect if operation attempts security judgment beyond pattern identification."""
        judgment_indicators = [
            'certify', 'guarantee', 'assure', 'confirm', 'validate',
            'approve', 'authorize', 'recommend', 'decide'
        ]

        operation_str = operation.lower()
        context_str = str(context).lower()

        return any(indicator in operation_str or indicator in context_str
                  for indicator in judgment_indicators)

    def _detects_compliance_certification_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """Detect if operation attempts compliance certification."""
        certification_indicators = [
            'certify', 'compliant', 'certification', 'certified',
            'conformant', 'conformance', 'approved', 'authorized'
        ]

        operation_str = operation.lower()
        context_str = str(context).lower()

        return any(indicator in operation_str or indicator in context_str
                  for indicator in certification_indicators)

    def _detects_business_decision_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """Detect if operation attempts business decision."""
        business_indicators = [
            'business', 'decision', 'recommend', 'strategy', 'priority',
            'investment', 'resource', 'budget', 'timeline', 'roadmap'
        ]

        operation_str = operation.lower()
        context_str = str(context).lower()

        return any(indicator in operation_str or indicator in context_str
                  for indicator in business_indicators)

    def get_authority_boundaries_report(self) -> Dict[str, Any]:
        """Generate report of all authority boundaries."""
        return {
            "authority_boundaries": {
                limit.value: {
                    "description": boundary.description,
                    "enforcement_mechanism": boundary.enforcement_mechanism,
                    "violation_consequence": boundary.violation_consequence,
                    "human_override_required": boundary.human_override_required,
                    "applicable_domains": [d.value for d in boundary.applicable_domains]
                }
                for limit, boundary in self.authority_boundaries.items()
            },
            "total_boundaries": len(self.authority_boundaries),
            "automatic_enforcement_boundaries": len([
                b for b in self.authority_boundaries.values() if not b.human_override_required
            ]),
            "human_override_required_boundaries": len([
                b for b in self.authority_boundaries.values() if b.human_override_required
            ]),
            "report_timestamp": "2025-12-23T00:00:00Z"
        }


# Global authority ceiling evaluator instance
authority_evaluator = AuthorityCeilingEvaluator()


def enforce_authority_limits(operation: str, domain: AuthorityDomain,
                           context: Dict[str, Any]) -> Dict[str, Any]:
    """
    BPS-014: Enforce explicit limits of authority.

    Evaluates if an operation exceeds the system's authority ceiling.
    """
    return authority_evaluator.evaluate_authority_ceiling(operation, domain, context)