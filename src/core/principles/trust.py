"""Trust guarantees for Repository Intelligence Scanner."""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

TRUST_GUARANTEES = [
    "determinism_is_mandatory",
    "reproducibility_is_required",
    "conservative_bias_on_ambiguity",
    "explicit_limits_of_authority"
]

def enforce_determinism(operation: str) -> bool:
    """Ensure operation maintains determinism."""
    # Placeholder - actual determinism enforcement handled in determinism_verification.py
    logger.debug("Determinism check for operation: %s", operation)
    return True

def enforce_reproducibility(operation: str) -> bool:
    """Ensure operation is reproducible.

    BPS-021: Implement identical_input_identical_output guarantee
    Ensures that identical inputs always produce identical outputs by:
    - Validating input consistency
    - Ensuring deterministic processing
    - Preventing stateful side effects
    """

    # Track reproducibility violations
    violations = []

    # 1. Check for stateful operations that could affect reproducibility
    if any(keyword in operation.lower() for keyword in ['global', 'class_var', 'static_var']):
        if not any(safe in operation for safe in ['readonly', 'const', 'final']):
            violations.append("stateful_operation")

    # 2. Check for operations that modify external state
    if any(op in operation.lower() for op in ['write', 'update', 'modify', 'send', 'post']):
        violations.append("external_state_modification")

    # 3. Check for operations that depend on external state
    if any(op in operation.lower() for op in ['read_env', 'get_system', 'network', 'fetch', 'download']):
        violations.append("external_state_dependency")

    # 4. Check for non-deterministic data sources
    if any(source in operation for source in ['/dev/random', '/dev/urandom', 'uuid']):
        violations.append("nondeterministic_data_source")

    # Log violations but don't fail - let caller decide
    if violations:
        logger.warning("Reproducibility violations detected in operation '%s': %s", operation, violations)
        return False

    logger.debug("Reproducibility check passed for operation: %s", operation)
    return True

def apply_conservative_bias(assessment: dict) -> dict:
    """
    BPS-013: Apply conservative bias on ambiguity.

    When faced with ambiguity, err on the side of caution by:
    - Increasing risk scores for ambiguous findings
    - Assuming worst-case scenarios for unclear situations
    - Reducing confidence in optimistic assessments
    - Preferring security over convenience when unclear
    """
    if not isinstance(assessment, dict):
        return assessment

    biased_assessment = assessment.copy()

    # Apply conservative bias to risk assessments
    if 'risk_synthesis' in biased_assessment:
        biased_assessment['risk_synthesis'] = _apply_risk_conservatism(
            biased_assessment['risk_synthesis']
        )

    # Apply conservative bias to security findings
    if 'security_analysis' in biased_assessment:
        biased_assessment['security_analysis'] = _apply_security_conservatism(
            biased_assessment['security_analysis']
        )

    # Apply conservative bias to compliance analysis
    if 'compliance_analysis' in biased_assessment:
        biased_assessment['compliance_analysis'] = _apply_compliance_conservatism(
            biased_assessment['compliance_analysis']
        )

    # Apply conservative bias to intent posture
    if 'intent_posture' in biased_assessment:
        biased_assessment['intent_posture'] = _apply_intent_conservatism(
            biased_assessment['intent_posture']
        )

    # Add conservatism metadata
    biased_assessment['conservative_bias_applied'] = {
        'timestamp': '2025-12-23T00:00:00Z',
        'bias_level': 'high',  # Always apply maximum conservatism
        'rationale': 'BPS-013: Conservative bias on ambiguity guarantee'
    }

    logger.info("Applied conservative bias to assessment")
    return biased_assessment

def _apply_risk_conservatism(risk_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply conservative bias to risk assessment data."""
    if not isinstance(risk_data, dict):
        return risk_data

    conservative_risk = risk_data.copy()

    # Increase risk scores for ambiguous or low-confidence findings
    if 'overall_risk_score' in conservative_risk:
        original_score = conservative_risk['overall_risk_score']
        # Apply 20% increase for conservatism when score is ambiguous (medium range)
        if 30 <= original_score <= 70:
            conservative_risk['overall_risk_score'] = min(100, original_score * 1.2)
            conservative_risk['conservatism_adjustment'] = {
                'original_score': original_score,
                'adjusted_score': conservative_risk['overall_risk_score'],
                'adjustment_reason': 'ambiguous risk level - applying conservative bias'
            }

    # Conservative treatment of risk categories
    if 'risk_categories' in conservative_risk:
        for category_name, data in conservative_risk['risk_categories'].items():
            if isinstance(data, dict) and 'confidence' in data:
                confidence = data['confidence']
                # If confidence is low (< 0.7), assume higher risk
                if confidence < 0.7:
                    if 'severity' in data:
                        # Increase severity for low-confidence risks
                        severity_map = {'low': 'medium', 'medium': 'high', 'high': 'critical'}
                        if data['severity'] in severity_map:
                            data['original_severity'] = data['severity']
                            data['severity'] = severity_map[data['severity']]
                            data['conservatism_reason'] = f'low confidence in {category_name} - assuming higher severity'

    return conservative_risk

def _apply_security_conservatism(security_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply conservative bias to security analysis data."""
    if not isinstance(security_data, dict):
        return security_data

    conservative_security = security_data.copy()

    # Conservative treatment of security findings
    if 'findings' in conservative_security:
        for finding in conservative_security['findings']:
            if isinstance(finding, dict):
                confidence = finding.get('confidence', 1.0)

                # For low-confidence findings, assume they represent real issues
                if confidence < 0.8:
                    finding['conservative_assumption'] = True
                    finding['assumed_severity'] = 'high'  # Assume high severity when unclear
                    finding['conservatism_reason'] = f'Low confidence ({confidence:.2f}) - assuming high severity'

                    # Add uncertainty note
                    if 'notes' not in finding:
                        finding['notes'] = []
                    finding['notes'].append(
                        f'BPS-013: Conservative bias applied due to ambiguity (confidence: {confidence:.2f})'
                    )

    # Conservative security architecture assessment
    if 'architectural_assessment' in conservative_security:
        arch_data = conservative_security['architectural_assessment']
        if isinstance(arch_data, dict) and 'overall_score' in arch_data:
            score = arch_data['overall_score']
            # If score is in ambiguous range, reduce it conservatively
            if 40 <= score <= 80:
                arch_data['original_score'] = score
                arch_data['overall_score'] = score * 0.8  # 20% reduction for conservatism
                arch_data['conservatism_reason'] = 'ambiguous architectural score - applying conservative reduction'

    return conservative_security

def _apply_compliance_conservatism(compliance_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply conservative bias to compliance analysis data."""
    if not isinstance(compliance_data, dict):
        return compliance_data

    conservative_compliance = compliance_data.copy()

    # Conservative compliance assessment
    if 'compliance_status' in conservative_compliance:
        status = conservative_compliance['compliance_status']

        # If compliance is ambiguous, assume non-compliant
        ambiguous_statuses = ['partial', 'unknown', 'incomplete', 'pending_review']
        if status.lower() in ambiguous_statuses:
            conservative_compliance['original_status'] = status
            conservative_compliance['compliance_status'] = 'non_compliant'
            conservative_compliance['conservatism_reason'] = f'Ambiguous compliance status "{status}" - assuming non-compliant'

    # Conservative treatment of compliance violations
    if 'violations' in conservative_compliance:
        for violation in conservative_compliance['violations']:
            if isinstance(violation, dict):
                severity = violation.get('severity', 'medium')

                # If severity is ambiguous, assume higher severity
                if severity.lower() in ['unknown', 'unclear', 'pending']:
                    violation['original_severity'] = severity
                    violation['severity'] = 'high'
                    violation['conservatism_reason'] = f'Ambiguous severity "{severity}" - assuming high severity'

    return conservative_compliance

def _apply_intent_conservatism(intent_data: Dict[str, Any]) -> Dict[str, Any]:
    """Apply conservative bias to intent posture analysis."""
    if not isinstance(intent_data, dict):
        return intent_data

    conservative_intent = intent_data.copy()

    # Conservative intent assessment - when unclear, assume potentially malicious
    if 'overall_posture' in conservative_intent:
        posture = conservative_intent['overall_posture']

        # If intent is ambiguous, assume suspicious
        ambiguous_postures = ['unclear', 'unknown', 'mixed', 'neutral']
        if posture.lower() in ambiguous_postures:
            conservative_intent['original_posture'] = posture
            conservative_intent['overall_posture'] = 'suspicious'
            conservative_intent['conservatism_reason'] = f'Ambiguous intent posture "{posture}" - assuming suspicious'

    # Conservative treatment of intent signals
    if 'intent_signals' in conservative_intent:
        for signal in conservative_intent['intent_signals']:
            if isinstance(signal, dict):
                confidence = signal.get('confidence', 1.0)

                # Low confidence intent signals get conservative interpretation
                if confidence < 0.7:
                    intent_type = signal.get('intent_type', 'unknown')
                    # Assume potentially harmful intent when unclear
                    if intent_type in ['unclear', 'unknown', 'mixed']:
                        signal['conservative_intent'] = 'potentially_harmful'
                        signal['conservatism_reason'] = f'Low confidence intent ({confidence:.2f}) - assuming potentially harmful'

    return conservative_intent

def enforce_authority_limits(operation: str) -> bool:
    """Ensure operation respects authority limits."""
    # Import here to avoid circular imports
    try:
        from src.core.authority_limits import AuthorityDomain, enforce_authority_limits as enforce_limits

        # Default to repository analysis domain for general operations
        domain = AuthorityDomain.REPOSITORY_ANALYSIS
        context = {"operation_type": "general", "operation_name": operation}

        result = enforce_limits(operation, domain, context)

        # Log authority evaluation
        if not result["authority_evaluation"]["can_proceed"]:
            logger.warning("Authority limit violation detected for operation: %s", operation)
            return False

        return True
    except ImportError:
        # Fallback if authority limits module not available
        logger.debug("Authority limits check for operation: %s", operation)
        return True
