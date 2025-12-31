"""Compliance framework analysis for Repository Intelligence Scanner."""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass

from ...exceptions import AnalysisError

@dataclass
class ComplianceFinding:
    """Represents a compliance framework finding."""
    framework: str  # 'GDPR', 'SOC2', 'ISO27001', etc.
    requirement: str
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    file_path: str
    line_number: int
    description: str
    code_snippet: str
    recommendation: str = ""
    compliance_category: str = ""

class ComplianceAnalyzer:
    """Analyzes code for compliance with various frameworks."""

    def __init__(self):
        self.findings: List[ComplianceFinding] = []
        self.frameworks = {
            'GDPR': self._get_gdpr_rules(),
            'SOC2': self._get_soc2_rules(),
            'ISO27001': self._get_iso27001_rules()
        }

    def analyze_compliance(self, file_list: List[str]) -> Dict[str, List[ComplianceFinding]]:
        """Analyze files for compliance with various frameworks."""
        results = {}

        for framework, rules in self.frameworks.items():
            self.findings = []
            for file_path in file_list:
                if self._is_code_file(file_path):
                    self._analyze_file_for_framework(file_path, framework, rules)
            results[framework] = self.findings.copy()

        return results

    def _analyze_file_for_framework(self, file_path: str, framework: str, rules: Dict[str, Any]):
        """Analyze a single file for a specific compliance framework."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            for rule in rules:
                self._check_rule(content, lines, file_path, framework, rule)

        except Exception as e:
            raise AnalysisError(f"Error analyzing {file_path} for {framework}: {str(e)}")

    def _check_rule(self, content: str, lines: List[str], file_path: str, framework: str, rule: Dict[str, Any]):
        """Check a specific compliance rule."""
        patterns = rule.get('patterns', [])
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE):
                line_num = self._get_line_number(lines, match.start())
                if not self._should_skip_finding(file_path, lines, line_num):
                    self.findings.append(ComplianceFinding(
                        framework=framework,
                        requirement=rule['requirement'],
                        severity=rule['severity'],
                        file_path=file_path,
                        line_number=line_num,
                        description=rule['description'],
                        code_snippet=self._get_code_snippet(lines, line_num),
                        recommendation=rule.get('recommendation', ''),
                        compliance_category=rule.get('category', '')
                    ))

    def _get_gdpr_rules(self) -> List[Dict[str, Any]]:
        """Get GDPR compliance rules."""
        return [
            {
                'requirement': 'Article 25 - Data Protection by Design',
                'severity': 'medium',
                'description': 'Potential personal data processing without privacy considerations',
                'category': 'Data Protection',
                'patterns': [
                    r'email\s*=.*input',  # Email collection
                    r'phone\s*=.*input',  # Phone collection
                    r'address\s*=.*input',  # Address collection
                    r'ssn\s*=.*input',  # SSN collection
                ],
                'recommendation': 'Implement data minimization and privacy by design principles'
            },
            {
                'requirement': 'Article 32 - Security of Processing',
                'severity': 'high',
                'description': 'Potential inadequate security measures for personal data',
                'category': 'Security',
                'patterns': [
                    r'store\s*\(\s*.*email.*\)',  # Storing emails without encryption
                    r'save\s*\(\s*.*phone.*\)',  # Storing phone numbers
                ],
                'recommendation': 'Implement appropriate technical and organizational measures'
            }
        ]

    def _get_soc2_rules(self) -> List[Dict[str, Any]]:
        """Get SOC2 compliance rules."""
        return [
            {
                'requirement': 'CC6.1 - Logical and Physical Access Controls',
                'severity': 'high',
                'description': 'Potential inadequate access controls',
                'category': 'Access Control',
                'patterns': [
                    r'admin\s*=\s*True',  # Hardcoded admin access
                    r'access\s*=\s*True',  # Automatic access grant
                ],
                'recommendation': 'Implement proper access control mechanisms'
            },
            {
                'requirement': 'CC7.1 - Monitoring System Activities',
                'severity': 'medium',
                'description': 'Limited logging and monitoring capabilities',
                'category': 'Monitoring',
                'patterns': [
                    r'print\s*\(\s*.*\)',  # Using print instead of proper logging
                ],
                'recommendation': 'Implement comprehensive logging and monitoring'
            }
        ]

    def _get_iso27001_rules(self) -> List[Dict[str, Any]]:
        """Get ISO27001 compliance rules."""
        return [
            {
                'requirement': 'A.9 - Access Control',
                'severity': 'high',
                'description': 'Potential access control weaknesses',
                'category': 'Access Control',
                'patterns': [
                    r'if\s+user\s*==\s*["\']admin["\']',  # Simple role check
                    r'password\s*==\s*["\'][^"\']+["\']',  # Hardcoded password
                ],
                'recommendation': 'Implement role-based access control (RBAC)'
            },
            {
                'requirement': 'A.12 - Operations Security',
                'severity': 'medium',
                'description': 'Potential operational security issues',
                'category': 'Operations',
                'patterns': [
                    r'os\.system\s*\(',  # Direct system calls
                    r'subprocess\.call\s*\(',  # Subprocess calls
                ],
                'recommendation': 'Implement secure operational procedures'
            }
        ]

    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file."""
        code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb'}
        return Path(file_path).suffix.lower() in code_extensions

    def _should_skip_finding(self, file_path: str, lines: List[str], line_num: int) -> bool:
        """Determine if a finding should be skipped."""
        # Skip test files
        if self._is_test_file(file_path):
            return True

        # Skip comments
        if line_num > 0 and line_num <= len(lines):
            line = lines[line_num - 1].strip()
            if line.startswith('#') or line.startswith('//') or '/*' in line:
                return True

        return False

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        path = Path(file_path)
        return 'test' in path.name.lower() or path.parent.name.lower() == 'tests'

    def _get_line_number(self, lines: List[str], char_pos: int) -> int:
        """Get line number from character position."""
        line_num = 1
        current_pos = 0
        for line in lines:
            current_pos += len(line) + 1  # +1 for newline
            if current_pos > char_pos:
                return line_num
            line_num += 1
        return line_num

    def _get_code_snippet(self, lines: List[str], line_num: int, context: int = 2) -> str:
        """Get code snippet around a line."""
        start = max(1, line_num - context)
        end = min(len(lines), line_num + context)
        snippet_lines = []
        for i in range(start, end + 1):
            marker = ">>> " if i == line_num else "    "
            snippet_lines.append(f"{marker}{i:4d}: {lines[i-1] if i <= len(lines) else ''}")
        return '\n'.join(snippet_lines)