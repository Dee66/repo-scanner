"""Confidence Scoring and Validation for Repository Intelligence Scanner."""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math

from ...exceptions import AnalysisError

class ConfidenceLevel(Enum):
    """Confidence levels for findings."""
    VERY_HIGH = "very_high"  # 0.9-1.0
    HIGH = "high"           # 0.7-0.89
    MEDIUM = "medium"       # 0.5-0.69
    LOW = "low"            # 0.3-0.49
    VERY_LOW = "very_low"   # 0.0-0.29

@dataclass
class ConfidenceMetrics:
    """Metrics for calculating confidence scores."""
    pattern_matches: int = 0
    context_relevance: float = 0.0
    code_quality: float = 0.0
    architectural_consistency: float = 0.0
    cross_file_validation: float = 0.0

@dataclass
class ValidatedFinding:
    """A finding with confidence validation."""
    vulnerability_type: str
    confidence_level: ConfidenceLevel
    confidence_score: float
    validation_factors: Dict[str, float]
    evidence_strength: str
    false_positive_probability: float
    file_path: str
    line_number: int
    description: str
    code_snippet: str

class ConfidenceScorer:
    """Calculates confidence scores for security findings."""

    def __init__(self):
        self.validation_rules = self._load_validation_rules()

    def _load_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load validation rules for different finding types."""
        return {
            'sql_injection': {
                'context_indicators': [
                    r'\bimport\s+sqlite3\b', r'\bimport\s+psycopg2\b', r'\bimport\s+mysqldb\b',
                    r'\bfrom\s+sqlalchemy\b', r'\.execute\s*\(', r'\.cursor\s*\('
                ],
                'safe_patterns': [
                    r'prepared.*statement', r'parameterized.*query', r'\.execute\s*\(\s*[\'\"]', r'%s.*%s'
                ],
                'risk_multipliers': {
                    'user_input_nearby': 1.5,
                    'no_sanitization': 1.3,
                    'dynamic_query': 2.0
                }
            },
            'xss_vulnerability': {
                'context_indicators': [
                    r'\bdocument\.write\b', r'\innerHTML\s*=', r'\.html\s*\(',
                    r'<script>', r'javascript:', r'onclick\s*=', r'onload\s*='
                ],
                'safe_patterns': [
                    r'\.textContent\s*=', r'\.text\s*=', r'encodeURIComponent', r'escape\s*\('
                ],
                'risk_multipliers': {
                    'user_input_direct': 2.0,
                    'no_encoding': 1.8,
                    'raw_html_output': 1.5
                }
            },
            'command_injection': {
                'context_indicators': [
                    r'os\.system\s*\(', r'subprocess\.', r'exec\s*\(', r'eval\s*\(',
                    r'popen\s*\(', r'\.call\s*\(', r'\.run\s*\('
                ],
                'safe_patterns': [
                    r'shell\s*=\s*False', r'shlex\.quote', r'subprocess\.PIPE'
                ],
                'risk_multipliers': {
                    'shell_true': 2.0,
                    'user_input_concat': 1.8,
                    'no_validation': 1.5
                }
            },
            'hardcoded_secrets': {
                'context_indicators': [
                    r'password\s*=', r'secret\s*=', r'key\s*=', r'token\s*=',
                    r'api_key\s*=', r'auth\s*=', r'credential\s*='
                ],
                'safe_patterns': [
                    r'os\.environ', r'getenv\s*\(', r'config\.', r'settings\.',
                    r'from\s+secrets\b', r'import\s+secrets'
                ],
                'risk_multipliers': {
                    'literal_string': 2.0,
                    'common_words': 1.5,
                    'no_env_usage': 1.3
                }
            },
            'path_traversal': {
                'context_indicators': [
                    r'open\s*\(', r'Path\s*\(', r'file\s*=', r'read\s*\(',
                    r'write\s*\(', r'\.join\s*\(', r'pathlib\.'
                ],
                'safe_patterns': [
                    r'os\.path\.basename', r'secure_filename', r'pathlib\.Path.*resolve',
                    r'input.*validate', r'sanitize.*path'
                ],
                'risk_multipliers': {
                    'user_input_path': 2.0,
                    'no_validation': 1.8,
                    'parent_directory': 1.5
                }
            },
            # Architectural security patterns - positive indicators
            'zero_network_enforcement': {
                'context_indicators': [
                    r'network.*check', r'offline.*mode', r'credential.*validation',
                    r'proxy.*detection', r'telemetry.*disable'
                ],
                'safe_patterns': [],  # No "safe" patterns for positive indicators
                'risk_multipliers': {}  # Positive indicators don't have risk multipliers
            },
            'prevention_first_validation': {
                'context_indicators': [
                    r'pre.*validation', r'fail.*safe', r'prevent.*before',
                    r'safety.*check', r'conservative.*approach'
                ],
                'safe_patterns': [],
                'risk_multipliers': {}
            },
            'cryptographic_boundary': {
                'context_indicators': [
                    r'build.*crypto', r'runtime.*isolation', r'key.*lifecycle',
                    r'cryptographic.*boundary', r'memory.*crypto'
                ],
                'safe_patterns': [],
                'risk_multipliers': {}
            },
            'multi_layer_input_validation': {
                'context_indicators': [
                    r'input.*validation', r'sanitization.*layer', r'depth.*limit',
                    r'injection.*prevent', r'malformed.*handle'
                ],
                'safe_patterns': [],
                'risk_multipliers': {}
            },
            'deterministic_security_model': {
                'context_indicators': [
                    r'deterministic.*output', r'audit.*trail', r'hash.*stable',
                    r'consistent.*result', r'trustworthy.*analysis'
                ],
                'safe_patterns': [],
                'risk_multipliers': {}
            }
        }

    def validate_findings(self, findings: List[Dict[str, Any]], file_list: List[str],
                         semantic_data: Dict[str, Any]) -> List[ValidatedFinding]:
        """Validate and score confidence for security findings."""
        validated_findings = []

        # Build file content cache for cross-validation
        file_contents = self._build_file_cache(file_list)

        for finding in findings:
            validated = self._validate_single_finding(finding, file_contents, semantic_data)
            if validated:
                validated_findings.append(validated)

        return validated_findings

    def _validate_single_finding(self, finding: Dict[str, Any], file_contents: Dict[str, str],
                                semantic_data: Dict[str, Any]) -> Optional[ValidatedFinding]:
        """Validate a single finding with confidence scoring."""
        vuln_type = finding.get('vulnerability_type', '')
        file_path = finding.get('file_path', '')
        line_number = finding.get('line_number', 0)

        if vuln_type not in self.validation_rules:
            # For architectural patterns, use simpler validation
            return self._validate_architectural_finding(finding)

        rule = self.validation_rules[vuln_type]
        content = file_contents.get(file_path, '')

        # Calculate base confidence
        base_confidence = self._calculate_base_confidence(finding, content, rule)

        # Apply risk multipliers
        risk_multiplier = self._calculate_risk_multiplier(finding, content, rule)

        # Context relevance
        context_score = self._calculate_context_relevance(finding, content, rule)

        # Cross-file validation
        cross_file_score = self._calculate_cross_file_validation(finding, file_contents, semantic_data)

        # Final confidence score
        final_confidence = min(1.0, base_confidence * risk_multiplier * context_score * cross_file_score)

        # Determine confidence level
        confidence_level = self._get_confidence_level(final_confidence)

        # Calculate false positive probability
        false_positive_prob = self._calculate_false_positive_probability(final_confidence, vuln_type)

        # Evidence strength
        evidence_strength = self._assess_evidence_strength(final_confidence, context_score, cross_file_score)

        return ValidatedFinding(
            vulnerability_type=vuln_type,
            confidence_level=confidence_level,
            confidence_score=final_confidence,
            validation_factors={
                'base_confidence': base_confidence,
                'risk_multiplier': risk_multiplier,
                'context_relevance': context_score,
                'cross_file_validation': cross_file_score
            },
            evidence_strength=evidence_strength,
            false_positive_probability=false_positive_prob,
            file_path=file_path,
            line_number=line_number,
            description=finding.get('description', ''),
            code_snippet=finding.get('code_snippet', '')
        )

    def _validate_architectural_finding(self, finding: Dict[str, Any]) -> Optional[ValidatedFinding]:
        """Validate architectural security findings."""
        vuln_type = finding.get('vulnerability_type', '')

        # Architectural patterns are generally positive indicators
        # Use simpler validation based on pattern specificity
        base_confidence = 0.7  # Architectural patterns are more reliable

        # Adjust based on pattern type
        if 'mechanisms' in vuln_type or 'security' in vuln_type:
            base_confidence = 0.8
        elif 'boundaries' in vuln_type or 'lifecycle' in vuln_type:
            base_confidence = 0.75

        confidence_level = self._get_confidence_level(base_confidence)

        return ValidatedFinding(
            vulnerability_type=vuln_type,
            confidence_level=confidence_level,
            confidence_score=base_confidence,
            validation_factors={
                'base_confidence': base_confidence,
                'architectural_relevance': 0.9,
                'pattern_specificity': 0.8
            },
            evidence_strength='strong',
            false_positive_probability=0.1,  # Low false positive for architectural patterns
            file_path=finding.get('file_path', ''),
            line_number=finding.get('line_number', 0),
            description=finding.get('description', ''),
            code_snippet=finding.get('code_snippet', '')
        )

    def _calculate_base_confidence(self, finding: Dict[str, Any], content: str,
                                 rule: Dict[str, Any]) -> float:
        """Calculate base confidence based on pattern matching."""
        vuln_type = finding.get('vulnerability_type', '')
        code_snippet = finding.get('code_snippet', '')

        # Count context indicators
        context_matches = 0
        for indicator in rule['context_indicators']:
            if re.search(indicator, content, re.IGNORECASE | re.MULTILINE):
                context_matches += 1

        # Count safe patterns (reduce confidence)
        safe_matches = 0
        for safe_pattern in rule['safe_patterns']:
            if re.search(safe_pattern, code_snippet, re.IGNORECASE):
                safe_matches += 1

        # Base confidence from context
        context_confidence = min(1.0, context_matches / len(rule['context_indicators']) * 0.8)

        # Reduce confidence for safe patterns
        safety_reduction = safe_matches * 0.3
        safety_reduction = min(0.8, safety_reduction)  # Cap reduction

        return max(0.1, context_confidence - safety_reduction)

    def _calculate_risk_multiplier(self, finding: Dict[str, Any], content: str,
                                 rule: Dict[str, Any]) -> float:
        """Calculate risk multiplier based on dangerous patterns."""
        multiplier = 1.0
        code_snippet = finding.get('code_snippet', '')

        for risk_factor, risk_value in rule['risk_multipliers'].items():
            if self._check_risk_factor(risk_factor, code_snippet, content):
                multiplier *= risk_value

        return min(3.0, multiplier)  # Cap multiplier

    def _check_risk_factor(self, factor: str, snippet: str, content: str) -> bool:
        """Check if a specific risk factor is present."""
        if factor == 'user_input_nearby':
            return bool(re.search(r'input|request|args?|params?', content, re.IGNORECASE))
        elif factor == 'no_sanitization':
            return not re.search(r'sanitize|escape|validate|clean', content, re.IGNORECASE)
        elif factor == 'dynamic_query':
            return '%' in snippet or '+' in snippet
        elif factor == 'user_input_direct':
            return re.search(r'innerHTML\s*=.*\+|document\.write\s*\(.*\+', snippet)
        elif factor == 'no_encoding':
            return not re.search(r'encode|escape', snippet, re.IGNORECASE)
        elif factor == 'raw_html_output':
            return 'innerHTML' in snippet
        elif factor == 'shell_true':
            return re.search(r'shell\s*=\s*True', content, re.IGNORECASE)
        elif factor == 'user_input_concat':
            return '+' in snippet and re.search(r'input|request|args?', content, re.IGNORECASE)
        elif factor == 'no_validation':
            return not re.search(r'validate|sanitize|check', content, re.IGNORECASE)
        elif factor == 'literal_string':
            return re.search(r'["\'][^"\']+["\']', snippet)
        elif factor == 'common_words':
            return re.search(r'password|secret|key|token', snippet, re.IGNORECASE)
        elif factor == 'no_env_usage':
            return not re.search(r'os\.environ|getenv|config', content, re.IGNORECASE)
        elif factor == 'user_input_path':
            return re.search(r'input|request.*path|filename', content, re.IGNORECASE)
        elif factor == 'parent_directory':
            return '..' in snippet

        return False

    def _calculate_context_relevance(self, finding: Dict[str, Any], content: str,
                                   rule: Dict[str, Any]) -> float:
        """Calculate context relevance score."""
        # Check if finding is in appropriate context
        lines = content.split('\n')
        line_num = finding.get('line_number', 0)

        if line_num > 0 and line_num <= len(lines):
            line = lines[line_num - 1]

            # Check if in comment or test
            if self._is_comment_or_test(line, finding.get('file_path', '')):
                return 0.3  # Low relevance for comments/tests

            # Check proximity to related code
            nearby_lines = self._get_nearby_lines(lines, line_num, 5)
            nearby_content = '\n'.join(nearby_lines)

            context_matches = 0
            for indicator in rule['context_indicators']:
                if re.search(indicator, nearby_content, re.IGNORECASE):
                    context_matches += 1

            return min(1.0, 0.5 + (context_matches / len(rule['context_indicators'])) * 0.5)

        return 0.5  # Default medium relevance

    def _calculate_cross_file_validation(self, finding: Dict[str, Any],
                                       file_contents: Dict[str, str],
                                       semantic_data: Dict[str, Any]) -> float:
        """Calculate cross-file validation score."""
        file_path = finding.get('file_path', '')
        vuln_type = finding.get('vulnerability_type', '')

        # Check for related security patterns in other files
        related_files = 0
        total_files = len(file_contents)

        for other_file, content in file_contents.items():
            if other_file != file_path:
                # Look for complementary security patterns
                if vuln_type == 'sql_injection':
                    if re.search(r'prepared.*statement|parameterized', content, re.IGNORECASE):
                        related_files += 1
                elif vuln_type == 'xss_vulnerability':
                    if re.search(r'encodeURIComponent|escape', content, re.IGNORECASE):
                        related_files += 1
                elif vuln_type == 'hardcoded_secrets':
                    if re.search(r'os\.environ|getenv', content, re.IGNORECASE):
                        related_files += 1

        # Normalize score
        if total_files > 1:
            return 0.5 + (related_files / (total_files - 1)) * 0.5
        return 0.5

    def _get_confidence_level(self, score: float) -> ConfidenceLevel:
        """Get confidence level from score."""
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.5:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.3:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _calculate_false_positive_probability(self, confidence: float, vuln_type: str) -> float:
        """Calculate false positive probability."""
        # Base false positive rates by vulnerability type
        base_rates = {
            'sql_injection': 0.15,
            'xss_vulnerability': 0.12,
            'command_injection': 0.18,
            'hardcoded_secrets': 0.08,
            'path_traversal': 0.20,
            'weak_crypto': 0.25,
            'insecure_deserialization': 0.30
        }

        base_rate = base_rates.get(vuln_type, 0.20)

        # Adjust based on confidence
        if confidence >= 0.8:
            return base_rate * 0.3  # Much lower false positive rate
        elif confidence >= 0.6:
            return base_rate * 0.6  # Lower false positive rate
        elif confidence >= 0.4:
            return base_rate  # Base rate
        else:
            return min(0.8, base_rate * 1.5)  # Higher false positive rate

    def _assess_evidence_strength(self, confidence: float, context: float, cross_file: float) -> str:
        """Assess evidence strength."""
        avg_score = (confidence + context + cross_file) / 3

        if avg_score >= 0.8:
            return 'very_strong'
        elif avg_score >= 0.6:
            return 'strong'
        elif avg_score >= 0.4:
            return 'moderate'
        elif avg_score >= 0.2:
            return 'weak'
        else:
            return 'very_weak'

    def _build_file_cache(self, file_list: List[str]) -> Dict[str, str]:
        """Build cache of file contents for validation."""
        cache = {}
        for file_path in file_list:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    cache[file_path] = f.read()
            except Exception:
                cache[file_path] = ''
        return cache

    def _is_comment_or_test(self, line: str, file_path: str) -> bool:
        """Check if line is in comment or test file."""
        if line.strip().startswith(('#', '//', '/*', '*')):
            return True

        file_lower = file_path.lower()
        return any(test_ind in file_lower for test_ind in ['test', 'spec', 'fixture', 'mock'])

    def _get_nearby_lines(self, lines: List[str], line_num: int, context: int) -> List[str]:
        """Get lines near the target line."""
        start = max(0, line_num - context - 1)
        end = min(len(lines), line_num + context)
        return lines[start:end]

    def generate_confidence_report(self, validated_findings: List[ValidatedFinding]) -> Dict[str, Any]:
        """Generate confidence report."""
        if not validated_findings:
            return {'overall_confidence': 1.0, 'findings_breakdown': {}}

        # Calculate overall confidence
        avg_confidence = sum(f.confidence_score for f in validated_findings) / len(validated_findings)

        # Breakdown by confidence level
        level_counts = {}
        for level in ConfidenceLevel:
            level_counts[level.value] = len([f for f in validated_findings if f.confidence_level == level])

        # False positive analysis
        avg_false_positive = sum(f.false_positive_probability for f in validated_findings) / len(validated_findings)

        # Evidence strength distribution
        evidence_counts = {}
        for finding in validated_findings:
            strength = finding.evidence_strength
            evidence_counts[strength] = evidence_counts.get(strength, 0) + 1

        return {
            'overall_confidence': round(avg_confidence, 3),
            'total_validated_findings': len(validated_findings),
            'confidence_distribution': level_counts,
            'average_false_positive_probability': round(avg_false_positive, 3),
            'evidence_strength_distribution': evidence_counts,
            'reliability_assessment': self._assess_reliability(avg_confidence, avg_false_positive)
        }

    def _assess_reliability(self, avg_confidence: float, avg_false_positive: float) -> str:
        """Assess overall reliability."""
        if avg_confidence >= 0.8 and avg_false_positive <= 0.1:
            return 'excellent'
        elif avg_confidence >= 0.7 and avg_false_positive <= 0.15:
            return 'good'
        elif avg_confidence >= 0.6 and avg_false_positive <= 0.2:
            return 'acceptable'
        elif avg_confidence >= 0.5 and avg_false_positive <= 0.25:
            return 'marginal'
        else:
            return 'poor'