"""Comprehensive security audit and hardening for all components."""

import hashlib
import hmac
import secrets
import re
import os
import json
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
import logging
from datetime import datetime, timedelta
import ipaddress
import urllib.parse
from dataclasses import dataclass, asdict

# Optional security audit imports
try:
    from .logging_aggregation import setup_structured_logging
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False

@dataclass
class SecurityFinding:
    """Represents a security finding from the audit."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    category: str  # input_validation, auth, config, data_protection, etc.
    component: str
    title: str
    description: str
    recommendation: str
    cwe_id: Optional[str] = None  # Common Weakness Enumeration ID
    owasp_id: Optional[str] = None  # OWASP Top 10 ID
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    evidence: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class SecurityAuditor:
    """Comprehensive security auditor for the repository scanner."""

    def __init__(self):
        if LOGGING_AVAILABLE:
            self.logger = setup_structured_logging("security_audit")
        else:
            self.logger = logging.getLogger(__name__)

        self.findings: List[SecurityFinding] = []
        self.audit_start_time = datetime.utcnow()

        # Security patterns and rules
        self._load_security_rules()

    def _load_security_rules(self):
        """Load security rules and patterns."""
        self.dangerous_patterns = {
            'sql_injection': re.compile(r'(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER).*?\+.*?', re.IGNORECASE),
            'command_injection': re.compile(r'(os\.system|subprocess\.|os\.popen|eval\(|exec\().*?\+.*?', re.IGNORECASE),
            'path_traversal': re.compile(r'\.\./|\.\.\\'),
            'hardcoded_secrets': re.compile(r'(password|secret|key|token)\s*=\s*["\'][^"\']*["\']', re.IGNORECASE),
            'weak_crypto': re.compile(r'(md5|sha1)\(', re.IGNORECASE),
            'insecure_random': re.compile(r'random\.(random|randint|choice|sample)', re.IGNORECASE),
        }

        self.required_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security'
        ]

        self.sensitive_files = [
            '.env', '.git', 'id_rsa', 'secrets.json', 'config.yml',
            'passwords.txt', 'keys.pem', 'private.key'
        ]

    def audit_all_components(self) -> List[SecurityFinding]:
        """Run comprehensive security audit on all components."""
        self.logger.info("Starting comprehensive security audit")

        # Core components audit
        self._audit_core_components()

        # Optional components audit
        self._audit_optional_components()

        # Configuration audit
        self._audit_configuration()

        # API security audit
        self._audit_api_security()

        # Data protection audit
        self._audit_data_protection()

        # Dependency security
        self._audit_dependencies()

        # File system security
        self._audit_file_system()

        audit_duration = datetime.utcnow() - self.audit_start_time
        self.logger.info(f"Security audit completed in {audit_duration.total_seconds():.2f} seconds")
        self.logger.info(f"Found {len(self.findings)} security findings")

        return self.findings

    def _audit_core_components(self):
        """Audit core components for security issues."""
        core_files = [
            'src/core/pipeline/analysis.py',
            'src/core/exceptions.py',
            'src/core/timeouts_and_limits.py',
            'src/core/quality/output_contract.py',
            'src/core/system_config.py'
        ]

        for file_path in core_files:
            if os.path.exists(file_path):
                self._audit_python_file(file_path, 'core')

    def _audit_optional_components(self):
        """Audit optional components for security issues."""
        optional_files = [
            'src/optional/api_server.py',
            'src/optional/dashboard.py',
            'src/optional/metrics_collector.py',
            'src/optional/alerting.py',
            'src/optional/tracing.py',
            'src/optional/monitoring.py',
            'src/optional/logging_aggregation.py',
            'src/optional/circuit_breaker.py',
            'src/optional/error_handling.py',
            'src/optional/recovery_strategies.py'
        ]

        for file_path in optional_files:
            if os.path.exists(file_path):
                self._audit_python_file(file_path, 'optional')

    def _audit_python_file(self, file_path: str, component: str):
        """Audit a Python file for security issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # Check for dangerous patterns
            for pattern_name, pattern in self.dangerous_patterns.items():
                for match in pattern.finditer(content):
                    line_num = content[:match.start()].count('\n') + 1
                    self._add_finding(
                        severity=self._get_pattern_severity(pattern_name),
                        category='code_security',
                        component=component,
                        title=f'Potentially dangerous pattern: {pattern_name}',
                        description=f'Found {pattern_name} pattern in {file_path}:{line_num}',
                        recommendation=self._get_pattern_recommendation(pattern_name),
                        file_path=file_path,
                        line_number=line_num,
                        evidence=lines[line_num-1].strip() if line_num <= len(lines) else ''
                    )

            # Check for input validation
            self._check_input_validation(file_path, content, component)

            # Check for authentication/authorization
            self._check_auth_security(file_path, content, component)

        except Exception as e:
            self.logger.error(f"Error auditing {file_path}: {e}")

    def _check_input_validation(self, file_path: str, content: str, component: str):
        """Check for proper input validation."""
        # Look for user input handling without validation
        input_patterns = [
            r'request\.(args|get|form|json)',
            r'input\(',
            r'raw_input\(',
            r'sys\.argv',
            r'os\.environ'
        ]

        for pattern in input_patterns:
            if re.search(pattern, content):
                # Check if validation is present nearby
                validation_indicators = [
                    'validate', 'sanitize', 'escape', 'check_', 'is_valid',
                    're\.match', 're\.search', 're\.fullmatch'
                ]

                has_validation = any(re.search(indicator, content, re.IGNORECASE) for indicator in validation_indicators)

                if not has_validation:
                    self._add_finding(
                        severity='MEDIUM',
                        category='input_validation',
                        component=component,
                        title='Potential input validation gap',
                        description=f'Found user input handling in {file_path} without apparent validation',
                        recommendation='Implement proper input validation and sanitization for all user inputs',
                        file_path=file_path,
                        owasp_id='A01:2021-Broken Access Control'
                    )

    def _check_auth_security(self, file_path: str, content: str, component: str):
        """Check for authentication and authorization security."""
        # Check for missing authentication
        if 'route' in content.lower() or '@app.' in content:
            # API endpoint found
            if not re.search(r'auth|token|jwt|session|login', content, re.IGNORECASE):
                self._add_finding(
                    severity='HIGH',
                    category='authentication',
                    component=component,
                    title='API endpoint without authentication',
                    description=f'API endpoint in {file_path} appears to lack authentication',
                    recommendation='Implement proper authentication for all API endpoints',
                    file_path=file_path,
                    owasp_id='A01:2021-Broken Access Control'
                )

    def _audit_configuration(self):
        """Audit configuration for security issues."""
        # Check for hardcoded secrets
        config_files = ['pyproject.toml', 'setup.py', 'requirements.txt', 'Pipfile', 'Pipfile.lock']

        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for suspicious patterns
                    if re.search(r'password|secret|key|token', content, re.IGNORECASE):
                        self._add_finding(
                            severity='HIGH',
                            category='configuration',
                            component='config',
                            title='Potential sensitive data in config',
                            description=f'Found potential sensitive data patterns in {config_file}',
                            recommendation='Remove hardcoded secrets and use environment variables or secure config',
                            file_path=config_file,
                            cwe_id='CWE-798'
                        )
                except Exception as e:
                    self.logger.error(f"Error auditing config {config_file}: {e}")

    def _audit_api_security(self):
        """Audit API security."""
        # Check API server for security headers
        api_file = 'src/optional/api_server.py'
        if os.path.exists(api_file):
            try:
                with open(api_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for security headers
                missing_headers = []
                for header in self.required_headers:
                    if header not in content:
                        missing_headers.append(header)

                if missing_headers:
                    self._add_finding(
                        severity='MEDIUM',
                        category='api_security',
                        component='api_server',
                        title='Missing security headers',
                        description=f'API server missing security headers: {", ".join(missing_headers)}',
                        recommendation='Add security headers to prevent common web vulnerabilities',
                        file_path=api_file,
                        owasp_id='A05:2021-Security Misconfiguration'
                    )

                # Check for HTTPS enforcement
                if 'https' not in content.lower():
                    self._add_finding(
                        severity='MEDIUM',
                        category='api_security',
                        component='api_server',
                        title='HTTPS not enforced',
                        description='API server does not appear to enforce HTTPS',
                        recommendation='Configure HTTPS and redirect HTTP to HTTPS',
                        file_path=api_file,
                        owasp_id='A05:2021-Security Misconfiguration'
                    )

            except Exception as e:
                self.logger.error(f"Error auditing API security: {e}")

    def _audit_data_protection(self):
        """Audit data protection measures."""
        # Check for proper data handling
        data_files = ['src/core/pipeline/analysis.py', 'src/optional/api_server.py']

        for file_path in data_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for sensitive data logging
                    if re.search(r'log.*password|print.*secret|log.*token', content, re.IGNORECASE):
                        self._add_finding(
                            severity='HIGH',
                            category='data_protection',
                            component='data_handling',
                            title='Potential sensitive data exposure',
                            description=f'Found potential logging of sensitive data in {file_path}',
                            recommendation='Never log sensitive data like passwords, tokens, or secrets',
                            file_path=file_path,
                            cwe_id='CWE-532'
                        )

                except Exception as e:
                    self.logger.error(f"Error auditing data protection in {file_path}: {e}")

    def _audit_dependencies(self):
        """Audit dependencies for security issues."""
        # Check requirements.txt for known vulnerable packages
        req_file = 'requirements.txt'
        if os.path.exists(req_file):
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    requirements = f.read()

                # Check for potentially vulnerable versions
                vulnerable_patterns = [
                    r'flask.*==.*0\.',  # Old Flask versions
                    r'django.*==.*1\.',  # Old Django versions
                    r'requests.*<.*2\.',  # Old requests versions
                ]

                for pattern in vulnerable_patterns:
                    if re.search(pattern, requirements):
                        self._add_finding(
                            severity='HIGH',
                            category='dependencies',
                            component='dependencies',
                            title='Potentially vulnerable dependency version',
                            description=f'Found potentially vulnerable dependency version in {req_file}',
                            recommendation='Update dependencies to latest secure versions',
                            file_path=req_file,
                            owasp_id='A06:2021-Vulnerable and Outdated Components'
                        )

            except Exception as e:
                self.logger.error(f"Error auditing dependencies: {e}")

    def _audit_file_system(self):
        """Audit file system security."""
        # Check for sensitive files that shouldn't be committed
        sensitive_found = []
        for root, dirs, files in os.walk('.'):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')

            for file in files:
                if file in self.sensitive_files:
                    sensitive_found.append(os.path.join(root, file))

        if sensitive_found:
            self._add_finding(
                severity='CRITICAL',
                category='file_security',
                component='filesystem',
                title='Sensitive files found in repository',
                description=f'Found sensitive files that should not be committed: {", ".join(sensitive_found)}',
                recommendation='Remove sensitive files from repository and add to .gitignore',
                cwe_id='CWE-200'
            )

    def _add_finding(self, **kwargs):
        """Add a security finding."""
        finding = SecurityFinding(**kwargs)
        self.findings.append(finding)
        self.logger.warning(f"Security finding: {finding.title} ({finding.severity})")

    def _get_pattern_severity(self, pattern_name: str) -> str:
        """Get severity level for a security pattern."""
        severity_map = {
            'sql_injection': 'CRITICAL',
            'command_injection': 'CRITICAL',
            'path_traversal': 'HIGH',
            'hardcoded_secrets': 'HIGH',
            'weak_crypto': 'MEDIUM',
            'insecure_random': 'MEDIUM'
        }
        return severity_map.get(pattern_name, 'MEDIUM')

    def _get_pattern_recommendation(self, pattern_name: str) -> str:
        """Get recommendation for a security pattern."""
        recommendations = {
            'sql_injection': 'Use parameterized queries or ORM instead of string concatenation',
            'command_injection': 'Use subprocess with argument lists instead of shell=True',
            'path_traversal': 'Validate and sanitize file paths, use os.path.normpath()',
            'hardcoded_secrets': 'Use environment variables or secure config management',
            'weak_crypto': 'Use SHA-256 or stronger, avoid MD5/SHA-1',
            'insecure_random': 'Use secrets module for security-sensitive random values'
        }
        return recommendations.get(pattern_name, 'Review and fix security issue')

    def generate_report(self) -> str:
        """Generate a comprehensive security audit report."""
        report = []
        report.append("# Security Audit Report")
        report.append(f"**Audit Date:** {self.audit_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append(f"**Total Findings:** {len(self.findings)}")
        report.append("")

        # Summary by severity
        severity_counts = {}
        for finding in self.findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1

        report.append("## Summary by Severity")
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
            count = severity_counts.get(severity, 0)
            if count > 0:
                report.append(f"- **{severity}:** {count} findings")
        report.append("")

        # Findings by category
        category_counts = {}
        for finding in self.findings:
            category_counts[finding.category] = category_counts.get(finding.category, 0) + 1

        report.append("## Findings by Category")
        for category, count in sorted(category_counts.items()):
            report.append(f"- **{category}:** {count} findings")
        report.append("")

        # Detailed findings
        report.append("## Detailed Findings")
        report.append("")

        # Sort by severity
        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}
        sorted_findings = sorted(self.findings, key=lambda x: severity_order.get(x.severity, 5))

        for finding in sorted_findings:
            report.append(f"### {finding.severity}: {finding.title}")
            report.append(f"**Component:** {finding.component}")
            report.append(f"**Category:** {finding.category}")
            if finding.file_path:
                location = finding.file_path
                if finding.line_number:
                    location += f":{finding.line_number}"
                report.append(f"**Location:** {location}")
            report.append(f"**Description:** {finding.description}")
            report.append(f"**Recommendation:** {finding.recommendation}")
            if finding.cwe_id:
                report.append(f"**CWE:** {finding.cwe_id}")
            if finding.owasp_id:
                report.append(f"**OWASP:** {finding.owasp_id}")
            if finding.evidence:
                report.append(f"**Evidence:** `{finding.evidence}`")
            report.append("")

        return "\n".join(report)

def run_security_audit() -> List[SecurityFinding]:
    """Run the complete security audit."""
    auditor = SecurityAuditor()
    return auditor.audit_all_components()

def generate_security_report(findings: List[SecurityFinding]) -> str:
    """Generate a security report from findings."""
    auditor = SecurityAuditor()
    auditor.findings = findings
    return auditor.generate_report()