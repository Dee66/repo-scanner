"""Claims vs Implementation Accuracy Scoring for Repository Intelligence Scanner.

This module compares documentation claims with detected implementation patterns
to score the accuracy of documentation against actual codebase capabilities.
"""

import re
from typing import Dict, List, Any, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class ClaimsAccuracyScorer:
    """Scores the accuracy of documentation claims against implementation."""

    def __init__(self):
        self.claim_categories = {
            'features': ['feature_claim'],
            'requirements': ['requirement_claim'],
            'installation': ['installation_command'],
            'usage': ['usage_example'],
            'api': ['api_endpoint']
        }

        self.pattern_mappings = {
            'security': ['authentication', 'encryption', 'authorization', 'input_validation'],
            'architecture': ['microservices', 'database_patterns', 'web_frameworks', 'testing_patterns'],
            'features': ['api_endpoints', 'file_processing', 'data_processing', 'machine_learning'],
            'languages': ['python', 'javascript', 'java']
        }

    def score_claims_accuracy(self, documentation_claims: Dict, implementation_patterns: Dict) -> Dict[str, Any]:
        """Score the accuracy of documentation claims against implementation patterns."""
        accuracy_scores = {}
        claim_verifications = {}

        # Score each claim category
        for category, claim_types in self.claim_categories.items():
            category_claims = self._extract_category_claims(documentation_claims, claim_types)
            category_score = self._score_category_accuracy(category_claims, implementation_patterns, category)
            accuracy_scores[category] = category_score
            claim_verifications[category] = category_score['verifications']

        # Calculate overall accuracy metrics
        overall_accuracy = self._calculate_overall_accuracy(accuracy_scores)

        # Generate accuracy insights
        accuracy_insights = self._generate_accuracy_insights(accuracy_scores, implementation_patterns)

        # Identify documentation gaps
        documentation_gaps = self._identify_documentation_gaps(documentation_claims, implementation_patterns)

        return {
            "accuracy_scores": accuracy_scores,
            "overall_accuracy": overall_accuracy,
            "claim_verifications": claim_verifications,
            "accuracy_insights": accuracy_insights,
            "documentation_gaps": documentation_gaps,
            "confidence_assessment": self._assess_confidence(accuracy_scores)
        }

    def _extract_category_claims(self, documentation_claims: Dict, claim_types: List[str]) -> List[Dict]:
        """Extract claims of specific types from documentation analysis."""
        all_claims = []

        for readme_file, claims in documentation_claims.items():
            for claim_type in claim_types:
                if claim_type in claims:
                    for claim in claims[claim_type]:
                        claim_copy = claim.copy()
                        claim_copy['readme_file'] = readme_file
                        all_claims.append(claim_copy)

        return all_claims

    def _score_category_accuracy(self, claims: List[Dict], implementation_patterns: Dict, category: str) -> Dict[str, Any]:
        """Score accuracy for a specific category of claims."""
        verifications = []
        total_confidence = 0
        verified_count = 0

        for claim in claims:
            verification = self._verify_claim_against_patterns(claim, implementation_patterns, category)
            verifications.append(verification)

            if verification['verified']:
                verified_count += 1
                total_confidence += verification['confidence']
            else:
                total_confidence += verification['confidence'] * 0.5  # Penalize unverified claims less

        total_claims = len(claims)
        average_confidence = total_confidence / max(1, total_claims)
        verification_rate = verified_count / max(1, total_claims)

        return {
            "total_claims": total_claims,
            "verified_claims": verified_count,
            "verification_rate": verification_rate,
            "average_confidence": average_confidence,
            "accuracy_score": verification_rate * average_confidence,
            "verifications": verifications
        }

    def _verify_claim_against_patterns(self, claim: Dict, implementation_patterns: Dict, category: str) -> Dict[str, Any]:
        """Verify a single claim against detected implementation patterns."""
        claim_text = claim.get('text', '').lower()
        claim_type = claim.get('type', '')

        verification = {
            'claim': claim,
            'verified': False,
            'confidence': 0.0,
            'evidence': [],
            'issues': [],
            'matched_patterns': []
        }

        # Check against implementation patterns based on category
        if category == 'features':
            verification = self._verify_feature_claim(claim_text, implementation_patterns, verification)
        elif category == 'requirements':
            verification = self._verify_requirement_claim(claim_text, implementation_patterns, verification)
        elif category == 'installation':
            verification = self._verify_installation_claim(claim_text, implementation_patterns, verification)
        elif category == 'usage':
            verification = self._verify_usage_claim(claim_text, implementation_patterns, verification)
        elif category == 'api':
            verification = self._verify_api_claim(claim, implementation_patterns, verification)

        return verification

    def _verify_feature_claim(self, claim_text: str, implementation_patterns: Dict, verification: Dict) -> Dict[str, Any]:
        """Verify a feature claim against implementation patterns."""
        # Check feature detection
        feature_detection = implementation_patterns.get('feature_detection', {})
        implemented_features = feature_detection.get('implemented_features', [])

        # Check architecture detection
        architecture_detection = implementation_patterns.get('architecture_detection', {})
        detected_patterns = architecture_detection.get('detected_patterns', [])

        # Look for keyword matches
        matched_features = []
        for feature in implemented_features:
            if self._text_matches_feature(claim_text, feature):
                matched_features.append(feature)
                verification['matched_patterns'].append(f"feature:{feature}")

        matched_architectures = []
        for pattern in detected_patterns:
            if self._text_matches_architecture(claim_text, pattern):
                matched_architectures.append(pattern)
                verification['matched_patterns'].append(f"architecture:{pattern}")

        # Check pattern matches
        pattern_matches = implementation_patterns.get('pattern_matches', {})
        security_matches = pattern_matches.get('security_patterns', {})
        architecture_matches = pattern_matches.get('architecture_patterns', {})

        matched_security = self._find_matching_patterns(claim_text, security_matches)
        matched_arch = self._find_matching_patterns(claim_text, architecture_matches)

        verification['matched_patterns'].extend([f"security:{p}" for p in matched_security])
        verification['matched_patterns'].extend([f"arch:{p}" for p in matched_arch])

        # Determine verification
        total_matches = len(matched_features) + len(matched_architectures) + len(matched_security) + len(matched_arch)

        if total_matches > 0:
            verification['verified'] = True
            verification['confidence'] = min(1.0, 0.5 + (total_matches * 0.1))
            verification['evidence'].append(f"Found {total_matches} matching implementation patterns")
        else:
            verification['verified'] = False
            verification['confidence'] = 0.3
            verification['issues'].append("No matching implementation patterns found")

        return verification

    def _verify_requirement_claim(self, claim_text: str, implementation_patterns: Dict, verification: Dict) -> Dict[str, Any]:
        """Verify a requirement claim."""
        # Check for language/framework requirements
        pattern_matches = implementation_patterns.get('pattern_matches', {})
        language_patterns = pattern_matches.get('language_patterns', {})

        matched_languages = self._find_matching_patterns(claim_text, language_patterns)

        if matched_languages:
            verification['verified'] = True
            verification['confidence'] = 0.8
            verification['evidence'].append(f"Detected {matched_languages} in codebase")
            verification['matched_patterns'].extend([f"language:{lang}" for lang in matched_languages])
        else:
            # Check for common requirement keywords
            if any(req in claim_text for req in ['python', 'node', 'java', 'database', 'api']):
                verification['verified'] = False
                verification['confidence'] = 0.4
                verification['issues'].append("Requirement mentioned but not clearly detected in implementation")
            else:
                verification['verified'] = True  # Assume basic requirements are met
                verification['confidence'] = 0.6

        return verification

    def _verify_installation_claim(self, claim_text: str, implementation_patterns: Dict, verification: Dict) -> Dict[str, Any]:
        """Verify an installation claim."""
        # Check for package manager patterns
        if 'pip install' in claim_text:
            # Look for Python patterns
            pattern_matches = implementation_patterns.get('pattern_matches', {})
            python_patterns = pattern_matches.get('language_patterns', {}).get('python', {})

            if python_patterns.get('files_with_pattern', 0) > 0:
                verification['verified'] = True
                verification['confidence'] = 0.9
                verification['evidence'].append("Python code detected, pip installation likely valid")
            else:
                verification['verified'] = False
                verification['confidence'] = 0.2
                verification['issues'].append("pip install claimed but limited Python code detected")

        elif 'npm install' in claim_text:
            # Look for JavaScript patterns
            js_patterns = implementation_patterns.get('pattern_matches', {}).get('language_patterns', {}).get('javascript', {})

            if js_patterns.get('files_with_pattern', 0) > 0:
                verification['verified'] = True
                verification['confidence'] = 0.9
                verification['evidence'].append("JavaScript code detected, npm installation likely valid")
            else:
                verification['verified'] = False
                verification['confidence'] = 0.2
                verification['issues'].append("npm install claimed but limited JavaScript code detected")

        else:
            # Generic installation claim
            verification['verified'] = True
            verification['confidence'] = 0.7
            verification['evidence'].append("Installation method appears reasonable")

        return verification

    def _verify_usage_claim(self, claim_text: str, implementation_patterns: Dict, verification: Dict) -> Dict[str, Any]:
        """Verify a usage claim (harder to verify automatically)."""
        # Usage examples are generally assumed to be valid unless obviously wrong
        verification['verified'] = True
        verification['confidence'] = 0.7
        verification['evidence'].append("Usage examples present in documentation")
        return verification

    def _verify_api_claim(self, claim: Dict, implementation_patterns: Dict, verification: Dict) -> Dict[str, Any]:
        """Verify an API claim."""
        endpoint = claim.get('endpoint', '')
        method = claim.get('method', '')

        # Check feature detection for API endpoints
        feature_detection = implementation_patterns.get('feature_detection', {})
        implemented_features = feature_detection.get('implemented_features', [])

        if 'api_endpoints' in implemented_features:
            verification['verified'] = True
            verification['confidence'] = 0.8
            verification['evidence'].append("API endpoints detected in implementation")
            verification['matched_patterns'].append("feature:api_endpoints")
        else:
            verification['verified'] = False
            verification['confidence'] = 0.3
            verification['issues'].append("API endpoints claimed but not detected in implementation")

        return verification

    def _text_matches_feature(self, claim_text: str, feature: str) -> bool:
        """Check if claim text matches a detected feature."""
        feature_keywords = {
            'api_endpoints': ['api', 'endpoint', 'rest', 'route'],
            'file_processing': ['file', 'upload', 'download', 'read', 'write'],
            'data_processing': ['data', 'process', 'transform', 'analyze'],
            'machine_learning': ['ml', 'ai', 'learn', 'predict', 'model', 'neural']
        }

        keywords = feature_keywords.get(feature, [feature.replace('_', ' ')])
        return any(keyword in claim_text for keyword in keywords)

    def _text_matches_architecture(self, claim_text: str, pattern: str) -> bool:
        """Check if claim text matches an architectural pattern."""
        pattern_keywords = {
            'microservices': ['microservice', 'service', 'api', 'distributed'],
            'web_application': ['web', 'http', 'browser', 'frontend'],
            'database_application': ['database', 'db', 'sql', 'store', 'persist'],
            'tested_codebase': ['test', 'testing', 'tdd', 'quality']
        }

        keywords = pattern_keywords.get(pattern, [pattern.replace('_', ' ')])
        return any(keyword in claim_text for keyword in keywords)

    def _find_matching_patterns(self, claim_text: str, pattern_matches: Dict) -> List[str]:
        """Find patterns that match the claim text."""
        matches = []

        for pattern_name, pattern_data in pattern_matches.items():
            sample_matches = pattern_data.get('sample_matches', [])
            for sample in sample_matches:
                if sample.lower() in claim_text:
                    matches.append(pattern_name)
                    break

        return matches

    def _calculate_overall_accuracy(self, accuracy_scores: Dict) -> Dict[str, Any]:
        """Calculate overall documentation accuracy."""
        total_claims = sum(scores['total_claims'] for scores in accuracy_scores.values())
        total_verified = sum(scores['verified_claims'] for scores in accuracy_scores.values())

        if total_claims == 0:
            return {
                "overall_score": 0.0,
                "verification_rate": 0.0,
                "total_claims": 0,
                "total_verified": 0
            }

        verification_rate = total_verified / total_claims

        # Weight accuracy scores by claim count
        weighted_score = 0
        total_weight = 0

        for category_scores in accuracy_scores.values():
            weight = category_scores['total_claims']
            score = category_scores['accuracy_score']
            weighted_score += score * weight
            total_weight += weight

        overall_score = weighted_score / max(1, total_weight)

        return {
            "overall_score": overall_score,
            "verification_rate": verification_rate,
            "total_claims": total_claims,
            "total_verified": total_verified,
            "accuracy_grade": self._score_to_grade(overall_score)
        }

    def _score_to_grade(self, score: float) -> str:
        """Convert accuracy score to a grade."""
        if score >= 0.9:
            return "A"
        elif score >= 0.8:
            return "B"
        elif score >= 0.7:
            return "C"
        elif score >= 0.6:
            return "D"
        else:
            return "F"

    def _generate_accuracy_insights(self, accuracy_scores: Dict, implementation_patterns: Dict) -> List[Dict[str, Any]]:
        """Generate insights about documentation accuracy."""
        insights = []

        # Check for categories with low accuracy
        for category, scores in accuracy_scores.items():
            if scores['verification_rate'] < 0.5 and scores['total_claims'] > 0:
                insights.append({
                    "type": "issue",
                    "category": category,
                    "title": f"Low {category} claim verification",
                    "description": f"Only {scores['verified_claims']}/{scores['total_claims']} {category} claims verified",
                    "severity": "high" if scores['verification_rate'] < 0.3 else "medium"
                })

        # Check for undocumented features
        feature_detection = implementation_patterns.get('feature_detection', {})
        implemented_features = feature_detection.get('implemented_features', [])

        architecture_detection = implementation_patterns.get('architecture_detection', {})
        detected_patterns = architecture_detection.get('detected_patterns', [])

        if implemented_features or detected_patterns:
            insights.append({
                "type": "opportunity",
                "category": "documentation_completeness",
                "title": "Potential undocumented features",
                "description": f"Detected {len(implemented_features)} features and {len(detected_patterns)} architectural patterns that may not be fully documented",
                "severity": "medium"
            })

        # Check for high accuracy categories
        for category, scores in accuracy_scores.items():
            if scores['verification_rate'] > 0.8 and scores['total_claims'] > 2:
                insights.append({
                    "type": "positive",
                    "category": category,
                    "title": f"High {category} documentation accuracy",
                    "description": f"{scores['verified_claims']}/{scores['total_claims']} {category} claims verified with high confidence",
                    "severity": "low"
                })

        return insights

    def _identify_documentation_gaps(self, documentation_claims: Dict, implementation_patterns: Dict) -> List[Dict[str, Any]]:
        """Identify gaps between documentation and implementation."""
        gaps = []

        # Check for implemented features not mentioned in docs
        feature_detection = implementation_patterns.get('feature_detection', {})
        implemented_features = set(feature_detection.get('implemented_features', []))

        # Extract documented features
        documented_features = set()
        for readme_file, claims in documentation_claims.items():
            for claim in claims.get('features', []):
                claim_text = claim.get('text', '').lower()
                # Map claim text to feature categories
                if any(kw in claim_text for kw in ['api', 'endpoint']):
                    documented_features.add('api_endpoints')
                elif any(kw in claim_text for kw in ['file', 'upload', 'download']):
                    documented_features.add('file_processing')
                elif any(kw in claim_text for kw in ['data', 'process', 'transform']):
                    documented_features.add('data_processing')
                elif any(kw in claim_text for kw in ['ml', 'ai', 'learn', 'predict']):
                    documented_features.add('machine_learning')

        undocumented_features = implemented_features - documented_features
        if undocumented_features:
            gaps.append({
                "type": "undocumented_feature",
                "description": f"Features implemented but not documented: {list(undocumented_features)}",
                "severity": "medium"
            })

        # Check for architectural patterns not mentioned
        architecture_detection = implementation_patterns.get('architecture_detection', {})
        detected_patterns = set(architecture_detection.get('detected_patterns', []))

        # This is harder to check automatically, but we can flag potential gaps
        if detected_patterns and len(documentation_claims) > 0:
            gaps.append({
                "type": "architecture_documentation",
                "description": f"Consider documenting detected architectural patterns: {list(detected_patterns)}",
                "severity": "low"
            })

        return gaps

    def _assess_confidence(self, accuracy_scores: Dict) -> Dict[str, Any]:
        """Assess overall confidence in the accuracy assessment."""
        total_claims = sum(scores['total_claims'] for scores in accuracy_scores.values())

        if total_claims == 0:
            return {"confidence_level": "low", "reason": "No claims to verify"}

        # Confidence based on number of claims and verification consistency
        verification_rates = [scores['verification_rate'] for scores in accuracy_scores.values() if scores['total_claims'] > 0]

        if not verification_rates:
            return {"confidence_level": "low", "reason": "Insufficient data"}

        avg_verification = sum(verification_rates) / len(verification_rates)
        consistency = 1 - (max(verification_rates) - min(verification_rates))  # Lower variance = higher consistency

        if total_claims >= 10 and avg_verification > 0.7 and consistency > 0.7:
            confidence_level = "high"
            reason = "Large sample size with consistent high verification rates"
        elif total_claims >= 5 and avg_verification > 0.5:
            confidence_level = "medium"
            reason = "Moderate sample size with reasonable verification rates"
        else:
            confidence_level = "low"
            reason = "Limited sample size or low verification rates"

        return {
            "confidence_level": confidence_level,
            "reason": reason,
            "total_claims_analyzed": total_claims,
            "average_verification_rate": avg_verification,
            "verification_consistency": consistency
        }


def score_claims_vs_implementation_accuracy(documentation_claims: Dict, implementation_patterns: Dict) -> Dict[str, Any]:
    """Main entry point for claims vs implementation accuracy scoring."""
    scorer = ClaimsAccuracyScorer()
    return scorer.score_claims_accuracy(documentation_claims, implementation_patterns)