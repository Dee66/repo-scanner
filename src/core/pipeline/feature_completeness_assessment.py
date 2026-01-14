"""Feature completeness assessment for documentation accuracy analysis."""

import logging
from typing import Dict, List, Any, Set, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FeatureCompletenessAssessor:
    """Assesses completeness of documented features against implemented capabilities."""

    def __init__(self):
        self.feature_categories = {
            'security': ['authentication', 'authorization', 'encryption', 'validation', 'sanitization'],
            'architecture': ['microservices', 'serverless', 'monolithic', 'distributed', 'containerized'],
            'functionality': ['api', 'database', 'file_system', 'networking', 'caching'],
            'languages': ['python', 'javascript', 'java', 'go', 'rust', 'typescript'],
            'frameworks': ['django', 'flask', 'fastapi', 'react', 'vue', 'angular', 'spring']
        }

    def assess_feature_completeness(self, documentation_claims: Dict[str, Any],
                                  implementation_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess completeness of documented features against implementation.

        Args:
            documentation_claims: Extracted claims from documentation
            implementation_patterns: Detected implementation patterns

        Returns:
            Dict containing completeness assessment results
        """
        try:
            # Extract documented features by category
            documented_features = self._extract_documented_features(documentation_claims)

            # Extract implemented features by category
            implemented_features = self._extract_implemented_features(implementation_patterns)

            # Calculate completeness metrics
            completeness_metrics = self._calculate_completeness_metrics(
                documented_features, implemented_features
            )

            # Identify gaps and missing features
            gaps_analysis = self._analyze_feature_gaps(
                documented_features, implemented_features
            )

            # Generate completeness insights
            insights = self._generate_completeness_insights(
                completeness_metrics, gaps_analysis
            )

            return {
                'feature_completeness_assessment': {
                    'documented_features': documented_features,
                    'implemented_features': implemented_features,
                    'completeness_metrics': completeness_metrics,
                    'gaps_analysis': gaps_analysis,
                    'insights': insights,
                    'assessment_timestamp': self._get_timestamp()
                }
            }

        except Exception as e:
            logger.error(f"Error in feature completeness assessment: {e}")
            return {
                'feature_completeness_assessment': {
                    'error': str(e),
                    'assessment_timestamp': self._get_timestamp()
                }
            }

    def _extract_documented_features(self, documentation_claims: Dict[str, Any]) -> Dict[str, Set[str]]:
        """Extract features claimed in documentation by category."""
        documented_features = {category: set() for category in self.feature_categories.keys()}

        claims = documentation_claims.get('claims', [])
        for claim in claims:
            claim_text = claim.get('text', '').lower()
            category = claim.get('category', '')

            # Map claim to feature categories
            for feature_cat, keywords in self.feature_categories.items():
                for keyword in keywords:
                    if keyword in claim_text:
                        documented_features[feature_cat].add(keyword)

        return documented_features

    def _extract_implemented_features(self, implementation_patterns: Dict[str, Any]) -> Dict[str, Set[str]]:
        """Extract features detected in implementation by category."""
        implemented_features = {category: set() for category in self.feature_categories.keys()}

        patterns = implementation_patterns.get('patterns', [])
        for pattern in patterns:
            pattern_type = pattern.get('type', '').lower()
            category = pattern.get('category', '')

            # Map pattern to feature categories
            for feature_cat, keywords in self.feature_categories.items():
                for keyword in keywords:
                    if keyword in pattern_type or keyword in category:
                        implemented_features[feature_cat].add(keyword)

        return implemented_features

    def _calculate_completeness_metrics(self, documented: Dict[str, Set[str]],
                                      implemented: Dict[str, Set[str]]) -> Dict[str, Any]:
        """Calculate completeness metrics for each category."""
        metrics = {}

        for category in self.feature_categories.keys():
            doc_features = documented.get(category, set())
            impl_features = implemented.get(category, set())

            # Calculate coverage metrics
            if doc_features:
                implemented_coverage = len(doc_features.intersection(impl_features)) / len(doc_features)
                over_documented = len(doc_features - impl_features) / len(doc_features)
                under_documented = len(impl_features - doc_features) / max(len(impl_features), 1)
            else:
                implemented_coverage = 0.0
                over_documented = 0.0
                under_documented = 1.0 if impl_features else 0.0

            metrics[category] = {
                'documented_count': len(doc_features),
                'implemented_count': len(impl_features),
                'implemented_coverage': round(implemented_coverage, 3),
                'over_documented_ratio': round(over_documented, 3),
                'under_documented_ratio': round(under_documented, 3),
                'completeness_score': round(implemented_coverage * (1 - over_documented), 3)
            }

        # Overall metrics
        total_doc = sum(len(doc) for doc in documented.values())
        total_impl = sum(len(impl) for impl in implemented.values())

        if total_doc > 0:
            overall_coverage = sum(m['implemented_coverage'] * m['documented_count'] for m in metrics.values()) / total_doc
            overall_completeness = sum(m['completeness_score'] * m['documented_count'] for m in metrics.values()) / total_doc
        else:
            overall_coverage = 0.0
            overall_completeness = 0.0

        metrics['overall'] = {
            'total_documented': total_doc,
            'total_implemented': total_impl,
            'overall_coverage': round(overall_coverage, 3),
            'overall_completeness': round(overall_completeness, 3)
        }

        return metrics

    def _analyze_feature_gaps(self, documented: Dict[str, Set[str]],
                            implemented: Dict[str, Set[str]]) -> Dict[str, Any]:
        """Analyze gaps between documented and implemented features."""
        gaps = {}

        for category in self.feature_categories.keys():
            doc_features = documented.get(category, set())
            impl_features = implemented.get(category, set())

            gaps[category] = {
                'missing_from_implementation': list(doc_features - impl_features),
                'missing_from_documentation': list(impl_features - doc_features),
                'fully_implemented': list(doc_features.intersection(impl_features))
            }

        return gaps

    def _generate_completeness_insights(self, metrics: Dict[str, Any],
                                      gaps: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights about feature completeness."""
        insights = []

        overall = metrics.get('overall', {})

        # Overall completeness insight
        if overall.get('overall_completeness', 0) >= 0.8:
            insights.append({
                'type': 'positive',
                'category': 'overall',
                'message': f"High feature completeness ({overall.get('overall_completeness', 0):.1%}) - documentation well-aligned with implementation",
                'severity': 'info'
            })
        elif overall.get('overall_completeness', 0) >= 0.5:
            insights.append({
                'type': 'warning',
                'category': 'overall',
                'message': f"Moderate feature completeness ({overall.get('overall_completeness', 0):.1%}) - some gaps between documentation and implementation",
                'severity': 'warning'
            })
        else:
            insights.append({
                'type': 'critical',
                'category': 'overall',
                'message': f"Low feature completeness ({overall.get('overall_completeness', 0):.1%}) - significant misalignment between documentation and implementation",
                'severity': 'critical'
            })

        # Category-specific insights
        for category, cat_metrics in metrics.items():
            if category == 'overall':
                continue

            completeness = cat_metrics.get('completeness_score', 0)
            missing_impl = gaps.get(category, {}).get('missing_from_implementation', [])
            missing_doc = gaps.get(category, {}).get('missing_from_documentation', [])

            if missing_impl:
                insights.append({
                    'type': 'gap',
                    'category': category,
                    'message': f"Features documented but not implemented in {category}: {', '.join(missing_impl[:3])}{'...' if len(missing_impl) > 3 else ''}",
                    'severity': 'warning'
                })

            if missing_doc:
                insights.append({
                    'type': 'gap',
                    'category': category,
                    'message': f"Features implemented but not documented in {category}: {', '.join(missing_doc[:3])}{'...' if len(missing_doc) > 3 else ''}",
                    'severity': 'info'
                })

        return insights

    def _get_timestamp(self) -> str:
        """Get current timestamp for assessment."""
        from datetime import datetime
        return datetime.utcnow().isoformat()


def assess_feature_completeness(documentation_claims: Dict[str, Any],
                              implementation_patterns: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to assess feature completeness.

    Args:
        documentation_claims: Claims extracted from documentation
        implementation_patterns: Patterns detected in implementation

    Returns:
        Feature completeness assessment results
    """
    assessor = FeatureCompletenessAssessor()
    return assessor.assess_feature_completeness(documentation_claims, implementation_patterns)