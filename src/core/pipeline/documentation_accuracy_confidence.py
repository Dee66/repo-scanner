"""Documentation accuracy confidence metrics for documentation accuracy analysis."""

import logging
import math
from typing import Dict, List, Any, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentationAccuracyConfidenceMetrics:
    """Calculates confidence metrics for documentation accuracy assessments."""

    def __init__(self):
        self.confidence_thresholds = {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4,
            'very_low': 0.0
        }

    def calculate_confidence_metrics(self, documentation_claims: Dict[str, Any],
                                   implementation_patterns: Dict[str, Any],
                                   accuracy_scoring: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate confidence metrics for documentation accuracy assessment.

        Args:
            documentation_claims: Extracted claims from documentation
            implementation_patterns: Detected implementation patterns
            accuracy_scoring: Results from accuracy scoring analysis

        Returns:
            Dict containing confidence metrics and assessment
        """
        try:
            # Calculate base confidence from data quality
            data_quality_confidence = self._assess_data_quality_confidence(
                documentation_claims, implementation_patterns
            )

            # Calculate verification confidence from accuracy scoring
            verification_confidence = self._assess_verification_confidence(accuracy_scoring)

            # Calculate temporal confidence (documentation freshness)
            temporal_confidence = self._assess_temporal_confidence(documentation_claims)

            # Calculate consistency confidence across claims
            consistency_confidence = self._assess_consistency_confidence(
                documentation_claims, implementation_patterns
            )

            # Combine confidence metrics
            overall_confidence = self._calculate_overall_confidence(
                data_quality_confidence, verification_confidence,
                temporal_confidence, consistency_confidence
            )

            # Generate confidence insights
            insights = self._generate_confidence_insights(
                overall_confidence, data_quality_confidence, verification_confidence,
                temporal_confidence, consistency_confidence
            )

            return {
                'documentation_accuracy_confidence': {
                    'overall_confidence': overall_confidence,
                    'component_confidence': {
                        'data_quality': data_quality_confidence,
                        'verification': verification_confidence,
                        'temporal': temporal_confidence,
                        'consistency': consistency_confidence
                    },
                    'confidence_assessment': self._assess_confidence_level(overall_confidence),
                    'insights': insights,
                    'assessment_timestamp': self._get_timestamp()
                }
            }

        except Exception as e:
            logger.error(f"Error calculating confidence metrics: {e}")
            return {
                'documentation_accuracy_confidence': {
                    'error': str(e),
                    'assessment_timestamp': self._get_timestamp()
                }
            }

    def _assess_data_quality_confidence(self, documentation_claims: Dict[str, Any],
                                      implementation_patterns: Dict[str, Any]) -> float:
        """Assess confidence based on data quality and completeness."""
        confidence = 0.5  # Base confidence

        claims = documentation_claims.get('claims', [])
        patterns = implementation_patterns.get('patterns', [])

        # Factor 1: Documentation coverage
        if claims:
            confidence += 0.2  # Has some documentation
            if len(claims) > 5:
                confidence += 0.1  # Substantial documentation
        else:
            confidence -= 0.3  # No documentation found

        # Factor 2: Implementation pattern coverage
        if patterns:
            confidence += 0.2  # Has detectable patterns
            if len(patterns) > 10:
                confidence += 0.1  # Rich implementation
        else:
            confidence -= 0.2  # No patterns detected

        # Factor 3: Claim verification potential
        verifiable_claims = sum(1 for claim in claims if claim.get('verifiable', False))
        if claims:
            verification_ratio = verifiable_claims / len(claims)
            confidence += verification_ratio * 0.2

        return max(0.0, min(1.0, confidence))

    def _assess_verification_confidence(self, accuracy_scoring: Dict[str, Any]) -> float:
        """Assess confidence based on verification results."""
        confidence = 0.5  # Base confidence

        overall_accuracy = accuracy_scoring.get('overall_accuracy', {})
        score = overall_accuracy.get('overall_score', 0.0)

        # Higher accuracy scores increase confidence
        confidence += score * 0.4

        # Evidence quality affects confidence
        evidence_items = accuracy_scoring.get('accuracy_insights', [])
        if evidence_items:
            confidence += min(0.2, len(evidence_items) * 0.05)  # Up to 0.2 for evidence

        # Confidence assessment from scoring
        existing_confidence = accuracy_scoring.get('confidence_assessment', {}).get('confidence_level', 'unknown')
        if existing_confidence == 'high':
            confidence += 0.1
        elif existing_confidence == 'low':
            confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    def _assess_temporal_confidence(self, documentation_claims: Dict[str, Any]) -> float:
        """Assess confidence based on documentation freshness."""
        confidence = 0.5  # Base confidence

        # Check for last modified dates in claims
        claims = documentation_claims.get('claims', [])
        recent_claims = 0
        total_dated_claims = 0

        for claim in claims:
            last_modified = claim.get('last_modified')
            if last_modified:
                total_dated_claims += 1
                try:
                    # Parse date and check if within last year
                    mod_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                    days_since_modified = (datetime.now(mod_date.tzinfo) - mod_date).days
                    if days_since_modified < 365:
                        recent_claims += 1
                except (ValueError, AttributeError):
                    pass

        if total_dated_claims > 0:
            recency_ratio = recent_claims / total_dated_claims
            confidence += recency_ratio * 0.3
        else:
            # No dates available, slight penalty
            confidence -= 0.1

        return max(0.0, min(1.0, confidence))

    def _assess_consistency_confidence(self, documentation_claims: Dict[str, Any],
                                     implementation_patterns: Dict[str, Any]) -> float:
        """Assess confidence based on internal consistency."""
        confidence = 0.5  # Base confidence

        claims = documentation_claims.get('claims', [])
        patterns = implementation_patterns.get('patterns', [])

        # Check for contradictory claims
        contradictions = 0
        total_comparisons = 0

        # Simple contradiction detection (can be enhanced)
        claim_texts = [claim.get('text', '').lower() for claim in claims]
        for i, claim1 in enumerate(claim_texts):
            for j, claim2 in enumerate(claim_texts[i+1:], i+1):
                total_comparisons += 1
                # Look for obvious contradictions (simplified)
                if ('not' in claim1 and claim1.replace('not', '') in claim2) or \
                   ('not' in claim2 and claim2.replace('not', '') in claim1):
                    contradictions += 1

        if total_comparisons > 0:
            contradiction_ratio = contradictions / total_comparisons
            confidence -= contradiction_ratio * 0.4  # Penalty for contradictions

        # Pattern consistency
        if patterns:
            # Check if patterns are consistent with each other
            pattern_types = set(pattern.get('type', '') for pattern in patterns)
            if len(pattern_types) > 1:
                confidence += 0.1  # Multiple pattern types suggest thorough analysis

        return max(0.0, min(1.0, confidence))

    def _calculate_overall_confidence(self, data_quality: float, verification: float,
                                    temporal: float, consistency: float) -> float:
        """Calculate overall confidence from component confidences."""
        # Weighted average of components
        weights = {
            'data_quality': 0.3,
            'verification': 0.4,
            'temporal': 0.15,
            'consistency': 0.15
        }

        overall = (data_quality * weights['data_quality'] +
                  verification * weights['verification'] +
                  temporal * weights['temporal'] +
                  consistency * weights['consistency'])

        return round(overall, 3)

    def _assess_confidence_level(self, overall_confidence: float) -> Dict[str, Any]:
        """Assess the confidence level based on overall score."""
        if overall_confidence >= self.confidence_thresholds['high']:
            level = 'high'
            description = 'High confidence in documentation accuracy assessment'
        elif overall_confidence >= self.confidence_thresholds['medium']:
            level = 'medium'
            description = 'Moderate confidence in documentation accuracy assessment'
        elif overall_confidence >= self.confidence_thresholds['low']:
            level = 'low'
            description = 'Low confidence in documentation accuracy assessment'
        else:
            level = 'very_low'
            description = 'Very low confidence in documentation accuracy assessment'

        return {
            'confidence_level': level,
            'description': description,
            'confidence_score': overall_confidence,
            'thresholds_used': self.confidence_thresholds
        }

    def _generate_confidence_insights(self, overall: float, data_quality: float,
                                    verification: float, temporal: float,
                                    consistency: float) -> List[Dict[str, Any]]:
        """Generate insights about confidence assessment."""
        insights = []

        # Overall confidence insight
        if overall >= self.confidence_thresholds['high']:
            insights.append({
                'type': 'positive',
                'category': 'overall_confidence',
                'message': f"High overall confidence ({overall:.1%}) in documentation accuracy assessment",
                'severity': 'info'
            })
        elif overall < self.confidence_thresholds['low']:
            insights.append({
                'type': 'warning',
                'category': 'overall_confidence',
                'message': f"Low overall confidence ({overall:.1%}) - results should be interpreted cautiously",
                'severity': 'warning'
            })

        # Component-specific insights
        components = [
            ('data_quality', data_quality, 'Data quality confidence'),
            ('verification', verification, 'Verification confidence'),
            ('temporal', temporal, 'Temporal confidence'),
            ('consistency', consistency, 'Consistency confidence')
        ]

        for name, score, description in components:
            if score < 0.4:
                insights.append({
                    'type': 'warning',
                    'category': f'{name}_confidence',
                    'message': f"Low {description.lower()} ({score:.1%}) may affect assessment reliability",
                    'severity': 'info'
                })

        return insights

    def _get_timestamp(self) -> str:
        """Get current timestamp for assessment."""
        return datetime.utcnow().isoformat()


def calculate_documentation_accuracy_confidence(documentation_claims: Dict[str, Any],
                                              implementation_patterns: Dict[str, Any],
                                              accuracy_scoring: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to calculate documentation accuracy confidence metrics.

    Args:
        documentation_claims: Claims extracted from documentation
        implementation_patterns: Patterns detected in implementation
        accuracy_scoring: Results from accuracy scoring analysis

    Returns:
        Confidence metrics assessment results
    """
    calculator = DocumentationAccuracyConfidenceMetrics()
    return calculator.calculate_confidence_metrics(documentation_claims, implementation_patterns, accuracy_scoring)
