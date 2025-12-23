#!/usr/bin/env python3
"""
Compliance Rule Sets Analysis Stage

Checks code against industry standards and security compliance requirements.
Supports multiple compliance frameworks and generates compliance reports.
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ComplianceRule:
    """Represents a single compliance rule."""

    def __init__(self, rule_id: str, name: str, description: str,
                 severity: str, framework: str, language: str = "any"):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.severity = severity  # 'critical', 'high', 'medium', 'low', 'info'
        self.framework = framework
        self.language = language
        self.check_function = None

    def set_check_function(self, func):
        """Set the function that performs the compliance check."""
        self.check_function = func
        return self

class ComplianceAnalyzer:
    """Analyzes code for compliance with industry standards."""

    def __init__(self):
        self.rules = []
        self._load_compliance_rules()

    def _load_compliance_rules(self):
        """Load predefined compliance rules."""
        # OWASP Top 10 for Web Applications
        self._load_owasp_rules()

        # Security Best Practices
        self._load_security_best_practices()

        # Code Quality Standards
        self._load_code_quality_rules()

        # Data Protection (GDPR, CCPA)
        self._load_data_protection_rules()

    def _load_owasp_rules(self):
        """Load OWASP Top 10 compliance rules."""
        owasp_rules = [
            ComplianceRule(
                "OWASP-A01", "SQL Injection Prevention",
                "Check for proper SQL query parameterization",
                "critical", "OWASP", "any"
            ).set_check_function(self._check_sql_injection),

            ComplianceRule(
                "OWASP-A02", "Broken Authentication",
                "Check for secure authentication patterns",
                "high", "OWASP", "any"
            ).set_check_function(self._check_broken_auth),

            ComplianceRule(
                "OWASP-A03", "Sensitive Data Exposure",
                "Check for proper encryption of sensitive data",
                "high", "OWASP", "any"
            ).set_check_function(self._check_sensitive_data),

            ComplianceRule(
                "OWASP-A04", "XML External Entities (XXE)",
                "Check for XML parsing vulnerabilities",
                "medium", "OWASP", "any"
            ).set_check_function(self._check_xxe),

            ComplianceRule(
                "OWASP-A05", "Broken Access Control",
                "Check for proper access control implementation",
                "high", "OWASP", "any"
            ).set_check_function(self._check_access_control),
        ]

        self.rules.extend(owasp_rules)

    def _load_security_best_practices(self):
        """Load general security best practices."""
        security_rules = [
            ComplianceRule(
                "SEC-001", "Hardcoded Secrets",
                "Check for hardcoded passwords, API keys, and secrets",
                "critical", "Security Best Practices", "any"
            ).set_check_function(self._check_hardcoded_secrets),

            ComplianceRule(
                "SEC-002", "Insecure Random Generation",
                "Check for use of insecure random number generators",
                "medium", "Security Best Practices", "any"
            ).set_check_function(self._check_insecure_random),

            ComplianceRule(
                "SEC-003", "Command Injection",
                "Check for potential command injection vulnerabilities",
                "high", "Security Best Practices", "any"
            ).set_check_function(self._check_command_injection),

            ComplianceRule(
                "SEC-004", "Path Traversal",
                "Check for path traversal vulnerabilities",
                "high", "Security Best Practices", "any"
            ).set_check_function(self._check_path_traversal),
        ]

        self.rules.extend(security_rules)

    def _load_code_quality_rules(self):
        """Load code quality and maintainability rules."""
        quality_rules = [
            ComplianceRule(
                "QUAL-001", "Code Complexity",
                "Check for overly complex functions and methods",
                "medium", "Code Quality", "any"
            ).set_check_function(self._check_code_complexity),

            ComplianceRule(
                "QUAL-002", "Dead Code",
                "Check for unused functions and variables",
                "low", "Code Quality", "any"
            ).set_check_function(self._check_dead_code),

            ComplianceRule(
                "QUAL-003", "Magic Numbers",
                "Check for unexplained numeric literals",
                "low", "Code Quality", "any"
            ).set_check_function(self._check_magic_numbers),

            ComplianceRule(
                "QUAL-004", "Long Functions",
                "Check for functions that are too long",
                "medium", "Code Quality", "any"
            ).set_check_function(self._check_long_functions),
        ]

        self.rules.extend(quality_rules)

    def _load_data_protection_rules(self):
        """Load data protection compliance rules."""
        data_rules = [
            ComplianceRule(
                "GDPR-001", "Personal Data Handling",
                "Check for proper handling of personal data",
                "high", "GDPR", "any"
            ).set_check_function(self._check_personal_data),

            ComplianceRule(
                "GDPR-002", "Data Retention",
                "Check for data retention policies",
                "medium", "GDPR", "any"
            ).set_check_function(self._check_data_retention),

            ComplianceRule(
                "CCPA-001", "Privacy Rights",
                "Check for CCPA compliance features",
                "medium", "CCPA", "any"
            ).set_check_function(self._check_privacy_rights),
        ]

        self.rules.extend(data_rules)

    def analyze_compliance(self, file_list: List[str], semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive compliance analysis.

        Args:
            file_list: List of files to analyze
            semantic_data: Semantic analysis results

        Returns:
            Dict containing compliance analysis results
        """
        logger.info("Starting compliance analysis")

        compliance_results = {
            "overall_compliance_score": 0,
            "framework_scores": {},
            "violations": [],
            "passed_rules": [],
            "compliance_by_severity": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0
            },
            "recommendations": []
        }

        total_rules = 0
        passed_rules = 0

        # Analyze each file against all applicable rules
        for file_path in file_list:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                file_language = self._detect_language(file_path)

                for rule in self.rules:
                    if rule.language == "any" or rule.language == file_language:
                        total_rules += 1
                        if rule.check_function:
                            result = rule.check_function(content, file_path, semantic_data)
                            if result:
                                compliance_results["violations"].append({
                                    "rule_id": rule.rule_id,
                                    "rule_name": rule.name,
                                    "severity": rule.severity,
                                    "framework": rule.framework,
                                    "file": file_path,
                                    "description": rule.description,
                                    "details": result
                                })
                                compliance_results["compliance_by_severity"][rule.severity] += 1
                            else:
                                passed_rules += 1
                                compliance_results["passed_rules"].append({
                                    "rule_id": rule.rule_id,
                                    "rule_name": rule.name,
                                    "framework": rule.framework
                                })

            except Exception as e:
                logger.warning(f"Failed to analyze {file_path} for compliance: {e}")

        # Calculate compliance scores
        if total_rules > 0:
            compliance_results["overall_compliance_score"] = (passed_rules / total_rules) * 100

        # Calculate framework-specific scores
        frameworks = {}
        for rule in self.rules:
            if rule.framework not in frameworks:
                frameworks[rule.framework] = {"total": 0, "passed": 0}
            frameworks[rule.framework]["total"] += 1

        for passed in compliance_results["passed_rules"]:
            framework = passed["framework"]
            if framework in frameworks:
                frameworks[framework]["passed"] += 1

        for framework, counts in frameworks.items():
            if counts["total"] > 0:
                score = (counts["passed"] / counts["total"]) * 100
                compliance_results["framework_scores"][framework] = score

        # Generate recommendations
        compliance_results["recommendations"] = self._generate_recommendations(compliance_results)

        return compliance_results

    def _detect_language(self, file_path: str) -> str:
        """Detect the programming language of a file."""
        if file_path.endswith('.py'):
            return 'python'
        elif file_path.endswith(('.js', '.jsx')):
            return 'javascript'
        elif file_path.endswith(('.ts', '.tsx')):
            return 'typescript'
        elif file_path.endswith('.java'):
            return 'java'
        else:
            return 'unknown'

    # Compliance Check Functions

    def _check_sql_injection(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for SQL injection vulnerabilities."""
        # Look for dangerous SQL patterns
        dangerous_patterns = [
            r'execute\s*\(\s*["\'].*?\+\s*.*?\s*["\']',  # String concatenation in SQL
            r'cursor\.execute\s*\(\s*["\'].*?\%.*?\s*["\']',  # Old-style string formatting
            r'["\'].*?\s*SELECT.*?\s*["\'].*?\+\s*',  # Dynamic SQL construction
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "Potential SQL injection vulnerability detected"

        return None

    def _check_broken_auth(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for broken authentication patterns."""
        # Look for weak authentication patterns
        weak_patterns = [
            r'password\s*=\s*["\'].*?["\']',  # Hardcoded passwords
            r'session\s*=\s*.*?\.get\s*\(\s*["\']session["\']',  # Basic session handling
            r'auth.*=\s*(True|False)',  # Simple boolean auth
        ]

        for pattern in weak_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "Weak authentication pattern detected"

        return None

    def _check_sensitive_data(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for sensitive data exposure."""
        sensitive_patterns = [
            r'password|passwd|pwd',  # Password references
            r'secret|token|key',  # Secrets and tokens
            r'ssn|social.*security',  # PII
            r'credit.*card|ccv',  # Financial data
        ]

        sensitive_count = 0
        for pattern in sensitive_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                sensitive_count += 1

        if sensitive_count > 2:
            return "Multiple sensitive data references detected"

        return None

    def _check_xxe(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for XXE vulnerabilities."""
        if 'xml' in content.lower() and ('parser' in content.lower() or 'sax' in content.lower()):
            if 'secure' not in content.lower() and 'safe' not in content.lower():
                return "Potential XXE vulnerability in XML parsing"

        return None

    def _check_access_control(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for access control issues."""
        # Look for missing access control patterns
        if ('admin' in content.lower() or 'user' in content.lower()) and 'role' not in content.lower():
            return "Potential access control issue - missing role checking"

        return None

    def _check_hardcoded_secrets(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for hardcoded secrets."""
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]

        for pattern in secret_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return "Hardcoded secret detected"

        return None

    def _check_insecure_random(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for insecure random number generation."""
        if 'random' in content.lower() and 'secure' not in content.lower():
            return "Potential use of insecure random number generation"

        return None

    def _check_command_injection(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for command injection vulnerabilities."""
        dangerous_patterns = [
            r'os\.system\s*\(\s*.*?\+\s*.*?\)',  # String concatenation in system calls
            r'subprocess\.call\s*\(\s*.*?\+\s*.*?\)',  # String concatenation in subprocess
            r'exec\s*\(\s*.*?\+\s*.*?\)',  # Dynamic exec calls
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, content):
                return "Potential command injection vulnerability"

        return None

    def _check_path_traversal(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for path traversal vulnerabilities."""
        if ('../' in content or '..\\' in content) and ('open' in content or 'file' in content):
            return "Potential path traversal vulnerability"

        return None

    def _check_code_complexity(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for overly complex code."""
        lines = content.split('\n')
        if len(lines) > 100:  # Simple complexity check
            return "File exceeds recommended length (100+ lines)"

        return None

    def _check_dead_code(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for dead/unused code patterns."""
        # This is a simple heuristic - in practice, this would need more sophisticated analysis
        if 'TODO' in content or 'FIXME' in content:
            return "TODO/FIXME comments indicate incomplete code"

        return None

    def _check_magic_numbers(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for magic numbers."""
        # Look for unexplained numbers (very basic check)
        magic_numbers = re.findall(r'\b\d{2,}\b', content)
        if len(magic_numbers) > 10:
            return "High number of unexplained numeric literals"

        return None

    def _check_long_functions(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for functions that are too long."""
        functions = re.findall(r'def\s+\w+\s*\([^)]*\):', content)
        if len(functions) > 0:
            avg_lines = len(content.split('\n')) / len(functions)
            if avg_lines > 50:
                return "Functions appear to be too long on average"

        return None

    def _check_personal_data(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for personal data handling."""
        pii_patterns = [
            r'email|phone|address',
            r'name|age|birth',
            r'ssn|social.*security',
        ]

        pii_count = 0
        for pattern in pii_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                pii_count += 1

        if pii_count > 1:
            return "Potential personal data handling detected"

        return None

    def _check_data_retention(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for data retention policies."""
        # This is a very basic check - real implementation would need more context
        if 'delete' in content.lower() or 'expire' in content.lower():
            return None  # Has some data lifecycle management
        else:
            return "No apparent data retention policies"

    def _check_privacy_rights(self, content: str, file_path: str, semantic_data: Dict) -> Optional[str]:
        """Check for privacy rights implementation."""
        privacy_terms = ['consent', 'opt-out', 'gdpr', 'ccpa', 'privacy']
        has_privacy = any(term in content.lower() for term in privacy_terms)

        if not has_privacy:
            return "No apparent privacy rights implementation"

        return None

    def _generate_recommendations(self, compliance_results: Dict) -> List[str]:
        """Generate recommendations based on compliance results."""
        recommendations = []

        score = compliance_results["overall_compliance_score"]

        if score < 70:
            recommendations.append("Overall compliance is low - implement security training and code reviews")
        elif score < 85:
            recommendations.append("Compliance is moderate - focus on critical and high-severity issues")

        # Framework-specific recommendations
        framework_scores = compliance_results["framework_scores"]

        if "OWASP" in framework_scores and framework_scores["OWASP"] < 80:
            recommendations.append("Improve OWASP Top 10 compliance - focus on injection prevention and authentication")

        if "Security Best Practices" in framework_scores and framework_scores["Security Best Practices"] < 80:
            recommendations.append("Address security best practices - eliminate hardcoded secrets and insecure patterns")

        # Severity-based recommendations
        violations = compliance_results["violations"]
        critical_count = sum(1 for v in violations if v["severity"] == "critical")
        high_count = sum(1 for v in violations if v["severity"] == "high")

        if critical_count > 0:
            recommendations.append(f"Address {critical_count} critical compliance violations immediately")
        if high_count > 0:
            recommendations.append(f"Address {high_count} high-severity compliance issues promptly")

        return recommendations


def analyze_compliance(file_list: List[str], semantic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze compliance with industry standards and security frameworks.

    Args:
        file_list: List of files to analyze
        semantic_data: Semantic analysis results

    Returns:
        Dict containing compliance analysis results
    """
    analyzer = ComplianceAnalyzer()
    return analyzer.analyze_compliance(file_list, semantic_data)