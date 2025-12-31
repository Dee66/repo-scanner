"""Security testing depth analysis for Repository Intelligence Scanner."""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from ...exceptions import AnalysisError

@dataclass
class TestingFinding:
    """Represents a security testing finding."""
    finding_type: str
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    file_path: str
    description: str
    coverage_percentage: float = 0.0
    recommendation: str = ""
    test_types: List[str] = None

class SecurityTestingAnalyzer:
    """Analyzes depth and coverage of security testing."""

    def __init__(self):
        self.findings: List[TestingFinding] = []
        self.test_files: List[str] = []
        self.security_test_categories = {
            'authentication': ['auth', 'login', 'session', 'token', 'jwt', 'oauth'],
            'authorization': ['permission', 'role', 'access', 'rbac', 'abac'],
            'input_validation': ['sanitization', 'validation', 'filter', 'escape'],
            'cryptography': ['crypto', 'encrypt', 'decrypt', 'hash', 'key', 'certificate'],
            'data_protection': ['privacy', 'pii', 'sensitive', 'mask', 'anonymize'],
            'network_security': ['ssl', 'tls', 'https', 'certificate', 'hsts'],
            'injection': ['sql', 'xss', 'command', 'injection', 'sanitiz'],
            'error_handling': ['error', 'exception', 'logging', 'trace'],
            'configuration': ['config', 'secret', 'environment', 'hardening'],
            'fuzzing': ['fuzz', 'random', 'input', 'stress'],
            'performance': ['load', 'stress', 'dos', 'rate', 'limit'],
            'compliance': ['gdpr', 'hipaa', 'pci', 'soc2', 'iso27001']
        }

    def analyze_security_testing(self, file_list: List[str]) -> List[TestingFinding]:
        """Analyze security testing coverage and depth."""
        self.findings = []
        self.test_files = [f for f in file_list if self._is_test_file(f)]

        if not self.test_files:
            self.findings.append(TestingFinding(
                finding_type='no_security_tests',
                severity='high',
                file_path='',
                description='No security test files detected in repository',
                recommendation='Implement comprehensive security testing suite'
            ))
            return self.findings

        # Analyze test coverage by category
        coverage = self._analyze_test_coverage()

        # Check for specific security testing patterns
        self._analyze_authentication_testing()
        self._analyze_authorization_testing()
        self._analyze_input_validation_testing()
        self._analyze_cryptography_testing()
        self._analyze_network_security_testing()
        self._analyze_injection_testing()
        self._analyze_fuzz_testing()
        self._analyze_performance_security_testing()

        # Overall coverage assessment
        self._assess_overall_coverage(coverage)

        return self.findings

    def _analyze_test_coverage(self) -> Dict[str, float]:
        """Analyze coverage of different security testing categories."""
        coverage = {}

        for category, keywords in self.security_test_categories.items():
            category_tests = 0
            total_tests = len(self.test_files)

            for test_file in self.test_files:
                try:
                    with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()

                    # Check if file contains security testing for this category
                    if any(keyword in content for keyword in keywords):
                        category_tests += 1

                except Exception:
                    continue

            coverage[category] = (category_tests / total_tests * 100) if total_tests > 0 else 0

        return coverage

    def _analyze_authentication_testing(self):
        """Analyze authentication security testing."""
        auth_tests = []
        auth_patterns = [
            r'def test.*auth',
            r'def test.*login',
            r'def test.*session',
            r'def test.*token',
            r'def test.*password',
            r'def test.*credential'
        ]

        for test_file in self.test_files:
            try:
                with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if any(re.search(pattern, content, re.IGNORECASE) for pattern in auth_patterns):
                    auth_tests.append(test_file)

            except Exception:
                continue

        if len(auth_tests) < 3:  # Arbitrary threshold
            self.findings.append(TestingFinding(
                finding_type='insufficient_auth_testing',
                severity='medium',
                file_path='',
                description=f'Limited authentication testing detected ({len(auth_tests)} test files)',
                coverage_percentage=len(auth_tests) / max(len(self.test_files), 1) * 100,
                recommendation='Implement comprehensive authentication testing including brute force, session management, and token validation',
                test_types=['authentication', 'session_management']
            ))

    def _analyze_authorization_testing(self):
        """Analyze authorization and access control testing."""
        authz_tests = []
        authz_patterns = [
            r'def test.*permission',
            r'def test.*role',
            r'def test.*access',
            r'def test.*rbac',
            r'def test.*abac',
            r'def test.*authorization'
        ]

        for test_file in self.test_files:
            try:
                with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if any(re.search(pattern, content, re.IGNORECASE) for pattern in authz_patterns):
                    authz_tests.append(test_file)

            except Exception:
                continue

        if len(authz_tests) < 2:
            self.findings.append(TestingFinding(
                finding_type='insufficient_authz_testing',
                severity='medium',
                file_path='',
                description=f'Limited authorization testing detected ({len(authz_tests)} test files)',
                coverage_percentage=len(authz_tests) / max(len(self.test_files), 1) * 100,
                recommendation='Implement role-based and attribute-based access control testing',
                test_types=['authorization', 'access_control']
            ))

    def _analyze_input_validation_testing(self):
        """Analyze input validation and sanitization testing."""
        validation_tests = []
        validation_patterns = [
            r'def test.*sanitiz',
            r'def test.*validat',
            r'def test.*filter',
            r'def test.*escape',
            r'def test.*input',
            r'def test.*malicious'
        ]

        for test_file in self.test_files:
            try:
                with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if any(re.search(pattern, content, re.IGNORECASE) for pattern in validation_patterns):
                    validation_tests.append(test_file)

            except Exception:
                continue

        if len(validation_tests) < 3:
            self.findings.append(TestingFinding(
                finding_type='insufficient_validation_testing',
                severity='high',
                file_path='',
                description=f'Limited input validation testing detected ({len(validation_tests)} test files)',
                coverage_percentage=len(validation_tests) / max(len(self.test_files), 1) * 100,
                recommendation='Implement comprehensive input validation testing including boundary values, malicious inputs, and encoding attacks',
                test_types=['input_validation', 'sanitization']
            ))

    def _analyze_cryptography_testing(self):
        """Analyze cryptographic implementation testing."""
        crypto_tests = []
        crypto_patterns = [
            r'def test.*crypto',
            r'def test.*encrypt',
            r'def test.*decrypt',
            r'def test.*key',
            r'def test.*certificate',
            r'def test.*hash'
        ]

        for test_file in self.test_files:
            try:
                with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if any(re.search(pattern, content, re.IGNORECASE) for pattern in crypto_patterns):
                    crypto_tests.append(test_file)

            except Exception:
                continue

        if len(crypto_tests) < 2:
            self.findings.append(TestingFinding(
                finding_type='insufficient_crypto_testing',
                severity='medium',
                file_path='',
                description=f'Limited cryptography testing detected ({len(crypto_tests)} test files)',
                coverage_percentage=len(crypto_tests) / max(len(self.test_files), 1) * 100,
                recommendation='Implement cryptographic testing including key management, algorithm validation, and secure random generation',
                test_types=['cryptography', 'key_management']
            ))

    def _analyze_network_security_testing(self):
        """Analyze network security testing."""
        network_tests = []
        network_patterns = [
            r'def test.*ssl',
            r'def test.*tls',
            r'def test.*https',
            r'def test.*certificate',
            r'def test.*hsts',
            r'def test.*network'
        ]

        for test_file in self.test_files:
            try:
                with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if any(re.search(pattern, content, re.IGNORECASE) for pattern in network_patterns):
                    network_tests.append(test_file)

            except Exception:
                continue

        if len(network_tests) < 1:
            self.findings.append(TestingFinding(
                finding_type='insufficient_network_testing',
                severity='low',
                file_path='',
                description=f'Limited network security testing detected ({len(network_tests)} test files)',
                coverage_percentage=len(network_tests) / max(len(self.test_files), 1) * 100,
                recommendation='Implement SSL/TLS configuration testing and certificate validation testing',
                test_types=['network_security', 'tls_configuration']
            ))

    def _analyze_injection_testing(self):
        """Analyze injection attack testing."""
        injection_tests = []
        injection_patterns = [
            r'def test.*sql.*inject',
            r'def test.*xss',
            r'def test.*command.*inject',
            r'def test.*injection',
            r'def test.*sanitiz'
        ]

        for test_file in self.test_files:
            try:
                with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if any(re.search(pattern, content, re.IGNORECASE) for pattern in injection_patterns):
                    injection_tests.append(test_file)

            except Exception:
                continue

        if len(injection_tests) < 2:
            self.findings.append(TestingFinding(
                finding_type='insufficient_injection_testing',
                severity='high',
                file_path='',
                description=f'Limited injection testing detected ({len(injection_tests)} test files)',
                coverage_percentage=len(injection_tests) / max(len(self.test_files), 1) * 100,
                recommendation='Implement SQL injection, XSS, and command injection testing with various attack vectors',
                test_types=['sql_injection', 'xss', 'command_injection']
            ))

    def _analyze_fuzz_testing(self):
        """Analyze fuzz testing implementation."""
        fuzz_tests = []
        fuzz_patterns = [
            r'def test.*fuzz',
            r'fuzzer',
            r'property.*test',
            r'random.*input'
        ]

        for test_file in self.test_files:
            try:
                with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if any(re.search(pattern, content, re.IGNORECASE) for pattern in fuzz_patterns):
                    fuzz_tests.append(test_file)

            except Exception:
                continue

        if len(fuzz_tests) < 1:
            self.findings.append(TestingFinding(
                finding_type='missing_fuzz_testing',
                severity='medium',
                file_path='',
                description=f'No fuzz testing detected ({len(fuzz_tests)} test files)',
                coverage_percentage=len(fuzz_tests) / max(len(self.test_files), 1) * 100,
                recommendation='Implement fuzz testing for input validation and error handling',
                test_types=['fuzzing', 'property_testing']
            ))

    def _analyze_performance_security_testing(self):
        """Analyze performance-related security testing."""
        perf_tests = []
        perf_patterns = [
            r'def test.*dos',
            r'def test.*rate.*limit',
            r'def test.*load',
            r'def test.*stress',
            r'def test.*performance'
        ]

        for test_file in self.test_files:
            try:
                with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                if any(re.search(pattern, content, re.IGNORECASE) for pattern in perf_patterns):
                    perf_tests.append(test_file)

            except Exception:
                continue

        if len(perf_tests) < 1:
            self.findings.append(TestingFinding(
                finding_type='missing_performance_security_testing',
                severity='low',
                file_path='',
                description=f'No performance security testing detected ({len(perf_tests)} test files)',
                coverage_percentage=len(perf_tests) / max(len(self.test_files), 1) * 100,
                recommendation='Implement DoS protection testing, rate limiting validation, and performance under attack scenarios',
                test_types=['dos_protection', 'rate_limiting']
            ))

    def _assess_overall_coverage(self, coverage: Dict[str, float]):
        """Assess overall security testing coverage."""
        avg_coverage = sum(coverage.values()) / len(coverage) if coverage else 0

        if avg_coverage < 30:
            severity = 'high'
        elif avg_coverage < 50:
            severity = 'medium'
        else:
            severity = 'low'

        if avg_coverage < 70:  # Threshold for comprehensive coverage
            self.findings.append(TestingFinding(
                finding_type='insufficient_security_test_coverage',
                severity=severity,
                file_path='',
                description=f'Overall security testing coverage is {avg_coverage:.1f}%',
                coverage_percentage=avg_coverage,
                recommendation='Expand security testing to cover more categories and attack vectors',
                test_types=list(coverage.keys())
            ))

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        path = Path(file_path)
        name = path.name.lower()
        return ('test' in name or 'spec' in name) and path.suffix in ['.py', '.js', '.ts', '.java', '.go', '.rs']