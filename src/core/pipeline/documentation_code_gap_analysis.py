"""Gap analysis between documentation and code implementation for documentation accuracy analysis."""

import logging
from typing import Dict, List, Any, Set, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class DocumentationCodeGapAnalyzer:
    """Analyzes gaps between documentation claims and code implementation."""

    def __init__(self):
        self.gap_categories = {
            'missing_implementation': 'Features documented but not implemented',
            'missing_documentation': 'Features implemented but not documented',
            'inconsistent_implementation': 'Implementation differs from documentation',
            'outdated_documentation': 'Documentation references outdated implementation',
            'incomplete_coverage': 'Partial implementation of documented features'
        }

    def analyze_documentation_code_gaps(self, documentation_claims: Dict[str, Any],
                                       implementation_patterns: Dict[str, Any],
                                       accuracy_scoring: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze gaps between documentation claims and code implementation.

        Args:
            documentation_claims: Extracted claims from documentation
            implementation_patterns: Detected implementation patterns
            accuracy_scoring: Results from accuracy scoring analysis

        Returns:
            Dict containing gap analysis results
        """
        try:
            # Identify specific gaps by category
            missing_implementation_gaps = self._identify_missing_implementation_gaps(
                documentation_claims, implementation_patterns
            )

            missing_documentation_gaps = self._identify_missing_documentation_gaps(
                documentation_claims, implementation_patterns
            )

            inconsistent_implementation_gaps = self._identify_inconsistent_implementation_gaps(
                documentation_claims, implementation_patterns, accuracy_scoring
            )

            outdated_documentation_gaps = self._identify_outdated_documentation_gaps(
                documentation_claims, implementation_patterns
            )

            incomplete_coverage_gaps = self._identify_incomplete_coverage_gaps(
                documentation_claims, implementation_patterns
            )

            # Calculate gap metrics
            gap_metrics = self._calculate_gap_metrics(
                missing_implementation_gaps, missing_documentation_gaps,
                inconsistent_implementation_gaps, outdated_documentation_gaps,
                incomplete_coverage_gaps
            )

            # Generate gap insights and recommendations
            gap_insights = self._generate_gap_insights(gap_metrics)

            # Prioritize gaps by severity and impact
            prioritized_gaps = self._prioritize_gaps(
                missing_implementation_gaps, missing_documentation_gaps,
                inconsistent_implementation_gaps, outdated_documentation_gaps,
                incomplete_coverage_gaps
            )

            return {
                'documentation_code_gap_analysis': {
                    'gap_categories': {
                        'missing_implementation': missing_implementation_gaps,
                        'missing_documentation': missing_documentation_gaps,
                        'inconsistent_implementation': inconsistent_implementation_gaps,
                        'outdated_documentation': outdated_documentation_gaps,
                        'incomplete_coverage': incomplete_coverage_gaps
                    },
                    'gap_metrics': gap_metrics,
                    'gap_insights': gap_insights,
                    'prioritized_gaps': prioritized_gaps,
                    'analysis_timestamp': self._get_timestamp()
                }
            }

        except Exception as e:
            logger.error(f"Error in gap analysis: {e}")
            return {
                'documentation_code_gap_analysis': {
                    'error': str(e),
                    'analysis_timestamp': self._get_timestamp()
                }
            }

    def _identify_missing_implementation_gaps(self, documentation_claims: Dict[str, Any],
                                             implementation_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify features documented but not implemented."""
        gaps = []

        claims = documentation_claims.get('claims', [])
        patterns = implementation_patterns.get('patterns', [])

        # Create pattern lookup for efficient checking
        pattern_types = set(pattern.get('type', '').lower() for pattern in patterns)
        pattern_categories = set()
        for pattern in patterns:
            pattern_categories.update(pattern.get('category', '').lower().split())

        for claim in claims:
            claim_text = claim.get('text', '').lower()
            claim_category = claim.get('category', '')

            # Check if claim references features not found in implementation
            claim_words = set(claim_text.split())
            found_patterns = pattern_types.intersection(claim_words)
            found_categories = pattern_categories.intersection(claim_words)

            if not found_patterns and not found_categories:
                # Look for specific feature indicators
                feature_indicators = ['api', 'function', 'method', 'class', 'module', 'service', 'endpoint']
                has_feature_indicator = any(indicator in claim_text for indicator in feature_indicators)

                if has_feature_indicator:
                    gaps.append({
                        'type': 'missing_implementation',
                        'claim_text': claim.get('text', ''),
                        'claim_category': claim_category,
                        'severity': 'high',
                        'confidence': 'medium',
                        'evidence': f"Claim mentions '{claim_text[:50]}...' but no corresponding implementation patterns found",
                        'recommendation': 'Implement the documented feature or update documentation'
                    })

        return gaps

    def _identify_missing_documentation_gaps(self, documentation_claims: Dict[str, Any],
                                           implementation_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify features implemented but not documented."""
        gaps = []

        claims = documentation_claims.get('claims', [])
        patterns = implementation_patterns.get('patterns', [])

        # Get documented features
        documented_features = set()
        for claim in claims:
            claim_text = claim.get('text', '').lower()
            documented_features.update(claim_text.split())

        for pattern in patterns:
            pattern_type = pattern.get('type', '').lower()
            pattern_category = pattern.get('category', '').lower()

            # Check if pattern represents a significant feature not documented
            significant_patterns = ['api', 'service', 'controller', 'handler', 'manager', 'processor']
            if any(sig in pattern_type for sig in significant_patterns):
                if pattern_type not in documented_features and pattern_category not in documented_features:
                    gaps.append({
                        'type': 'missing_documentation',
                        'pattern_type': pattern_type,
                        'pattern_category': pattern_category,
                        'file_path': pattern.get('file_path', ''),
                        'severity': 'medium',
                        'confidence': 'high',
                        'evidence': f"Implementation pattern '{pattern_type}' found in {pattern.get('file_path', '')} but not documented",
                        'recommendation': 'Add documentation for this implemented feature'
                    })

        return gaps

    def _identify_inconsistent_implementation_gaps(self, documentation_claims: Dict[str, Any],
                                                 implementation_patterns: Dict[str, Any],
                                                 accuracy_scoring: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify inconsistencies between documentation and implementation."""
        gaps = []

        accuracy_insights = accuracy_scoring.get('accuracy_insights', [])

        for insight in accuracy_insights:
            if insight.get('type') == 'inconsistency':
                gaps.append({
                    'type': 'inconsistent_implementation',
                    'description': insight.get('message', ''),
                    'severity': insight.get('severity', 'medium'),
                    'confidence': 'high',
                    'evidence': insight.get('evidence', ''),
                    'recommendation': 'Align implementation with documentation or update documentation to match implementation'
                })

        # Additional inconsistency detection
        claims = documentation_claims.get('claims', [])
        patterns = implementation_patterns.get('patterns', [])

        # Check for version mismatches
        for claim in claims:
            claim_text = claim.get('text', '').lower()
            if 'version' in claim_text or 'v.' in claim_text:
                # Look for version patterns in implementation
                version_patterns = [p for p in patterns if 'version' in p.get('type', '').lower()]
                if not version_patterns:
                    gaps.append({
                        'type': 'inconsistent_implementation',
                        'description': f"Documentation mentions version but no version patterns found in code",
                        'severity': 'medium',
                        'confidence': 'medium',
                        'evidence': f"Claim: '{claim_text[:50]}...'",
                        'recommendation': 'Ensure version information is consistent between documentation and code'
                    })

        return gaps

    def _identify_outdated_documentation_gaps(self, documentation_claims: Dict[str, Any],
                                            implementation_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify outdated documentation that references old implementation."""
        gaps = []

        claims = documentation_claims.get('claims', [])
        patterns = implementation_patterns.get('patterns', [])

        # Check for deprecated patterns mentioned in documentation
        deprecated_indicators = ['deprecated', 'obsolete', 'old', 'legacy', 'removed']

        for claim in claims:
            claim_text = claim.get('text', '').lower()
            if any(indicator in claim_text for indicator in deprecated_indicators):
                # Check if deprecated features are still in code
                current_patterns = [p for p in patterns if p.get('type', '').lower() in claim_text]
                if current_patterns:
                    gaps.append({
                        'type': 'outdated_documentation',
                        'description': 'Documentation mentions deprecated features still present in code',
                        'severity': 'medium',
                        'confidence': 'medium',
                        'evidence': f"Claim mentions deprecated feature but found in {len(current_patterns)} code locations",
                        'recommendation': 'Update documentation to reflect current implementation or remove deprecated code'
                    })

        # Check for technology version mismatches
        tech_versions = {
            'python': ['2.7', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11', '3.12'],
            'javascript': ['es5', 'es6', 'es2017', 'es2018', 'es2019', 'es2020']
        }

        for claim in claims:
            claim_text = claim.get('text', '').lower()
            for tech, versions in tech_versions.items():
                if tech in claim_text:
                    mentioned_versions = [v for v in versions if v in claim_text]
                    if mentioned_versions:
                        # This is a simplified check - in practice would need more sophisticated version detection
                        gaps.append({
                            'type': 'outdated_documentation',
                            'description': f'Documentation mentions {tech} version that may be outdated',
                            'severity': 'low',
                            'confidence': 'low',
                            'evidence': f"Claim mentions {tech} {mentioned_versions}",
                            'recommendation': 'Verify technology versions are current in both documentation and implementation'
                        })

        return gaps

    def _identify_incomplete_coverage_gaps(self, documentation_claims: Dict[str, Any],
                                         implementation_patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify partial implementation of documented features."""
        gaps = []

        claims = documentation_claims.get('claims', [])
        patterns = implementation_patterns.get('patterns', [])

        # Group patterns by category
        pattern_categories = {}
        for pattern in patterns:
            category = pattern.get('category', 'unknown')
            if category not in pattern_categories:
                pattern_categories[category] = []
            pattern_categories[category].append(pattern)

        # Check for incomplete feature sets
        for claim in claims:
            claim_text = claim.get('text', '').lower()
            claim_category = claim.get('category', '')

            # Look for features that suggest multiple components
            multi_component_indicators = ['and', 'or', 'also', 'including', 'such as', 'like']
            if any(indicator in claim_text for indicator in multi_component_indicators):
                # Check if all mentioned components are implemented
                category_patterns = pattern_categories.get(claim_category, [])
                if len(category_patterns) < 2:  # Expecting multiple components
                    gaps.append({
                        'type': 'incomplete_coverage',
                        'description': 'Documentation suggests multiple components but implementation appears incomplete',
                        'severity': 'medium',
                        'confidence': 'medium',
                        'evidence': f"Claim suggests multiple features: '{claim_text[:50]}...' but only {len(category_patterns)} patterns found",
                        'recommendation': 'Complete implementation of all documented features or update documentation'
                    })

        return gaps

    def _calculate_gap_metrics(self, missing_impl: List, missing_doc: List,
                             inconsistent: List, outdated: List, incomplete: List) -> Dict[str, Any]:
        """Calculate metrics for gap analysis."""
        total_gaps = len(missing_impl) + len(missing_doc) + len(inconsistent) + len(outdated) + len(incomplete)

        # Severity distribution
        severity_counts = {'high': 0, 'medium': 0, 'low': 0}
        confidence_counts = {'high': 0, 'medium': 0, 'low': 0}

        for gap_list in [missing_impl, missing_doc, inconsistent, outdated, incomplete]:
            for gap in gap_list:
                severity = gap.get('severity', 'medium')
                confidence = gap.get('confidence', 'medium')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

        return {
            'total_gaps': total_gaps,
            'gaps_by_category': {
                'missing_implementation': len(missing_impl),
                'missing_documentation': len(missing_doc),
                'inconsistent_implementation': len(inconsistent),
                'outdated_documentation': len(outdated),
                'incomplete_coverage': len(incomplete)
            },
            'severity_distribution': severity_counts,
            'confidence_distribution': confidence_counts,
            'gap_severity_score': self._calculate_severity_score(severity_counts, total_gaps)
        }

    def _calculate_severity_score(self, severity_counts: Dict[str, int], total_gaps: int) -> float:
        """Calculate overall severity score from 0-1."""
        if total_gaps == 0:
            return 0.0

        weights = {'high': 1.0, 'medium': 0.6, 'low': 0.3}
        weighted_sum = sum(severity_counts.get(level, 0) * weight for level, weight in weights.items())

        return round(weighted_sum / total_gaps, 3)

    def _generate_gap_insights(self, gap_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights about identified gaps."""
        insights = []

        total_gaps = gap_metrics.get('total_gaps', 0)
        severity_score = gap_metrics.get('gap_severity_score', 0)

        # Overall assessment
        if total_gaps == 0:
            insights.append({
                'type': 'positive',
                'category': 'overall_gaps',
                'message': 'No significant gaps found between documentation and implementation',
                'severity': 'info'
            })
        elif severity_score >= 0.7:
            insights.append({
                'type': 'critical',
                'category': 'overall_gaps',
                'message': f'Critical gaps identified ({total_gaps} total) - immediate attention required',
                'severity': 'critical'
            })
        elif severity_score >= 0.4:
            insights.append({
                'type': 'warning',
                'category': 'overall_gaps',
                'message': f'Moderate gaps identified ({total_gaps} total) - review and address',
                'severity': 'warning'
            })
        else:
            insights.append({
                'type': 'info',
                'category': 'overall_gaps',
                'message': f'Minor gaps identified ({total_gaps} total) - consider addressing',
                'severity': 'info'
            })

        # Category-specific insights
        gaps_by_category = gap_metrics.get('gaps_by_category', {})
        for category, count in gaps_by_category.items():
            if count > 0:
                insights.append({
                    'type': 'gap_detail',
                    'category': category,
                    'message': f'{count} {category.replace("_", " ")} gap(s) found',
                    'severity': 'info'
                })

        return insights

    def _prioritize_gaps(self, missing_impl: List, missing_doc: List, inconsistent: List,
                        outdated: List, incomplete: List) -> List[Dict[str, Any]]:
        """Prioritize gaps by severity and impact."""
        all_gaps = missing_impl + missing_doc + inconsistent + outdated + incomplete

        # Sort by severity (high -> medium -> low) then by confidence
        severity_order = {'high': 3, 'medium': 2, 'low': 1}
        confidence_order = {'high': 3, 'medium': 2, 'low': 1}

        prioritized = sorted(all_gaps, key=lambda g: (
            severity_order.get(g.get('severity', 'medium'), 2),
            confidence_order.get(g.get('confidence', 'medium'), 2)
        ), reverse=True)

        # Add priority ranking
        for i, gap in enumerate(prioritized):
            gap['priority_rank'] = i + 1

        return prioritized

    def _get_timestamp(self) -> str:
        """Get current timestamp for analysis."""
        return datetime.utcnow().isoformat()


def analyze_documentation_code_gaps(documentation_claims: Dict[str, Any],
                                  implementation_patterns: Dict[str, Any],
                                  accuracy_scoring: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to analyze gaps between documentation and code implementation.

    Args:
        documentation_claims: Claims extracted from documentation
        implementation_patterns: Patterns detected in implementation
        accuracy_scoring: Results from accuracy scoring analysis

    Returns:
        Gap analysis results
    """
    analyzer = DocumentationCodeGapAnalyzer()
    return analyzer.analyze_documentation_code_gaps(documentation_claims, implementation_patterns, accuracy_scoring)