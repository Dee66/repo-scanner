"""Security vulnerability analysis stage for Repository Intelligence Scanner."""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Set
from dataclasses import dataclass

@dataclass
class SecurityFinding:
    """Represents a security vulnerability finding."""
    vulnerability_type: str
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    file_path: str
    line_number: int
    description: str
    code_snippet: str
    cwe_id: str = ""  # Common Weakness Enumeration ID
    owasp_category: str = ""  # OWASP Top 10 category

class SecurityAnalyzer:
    """Analyzes code for security vulnerabilities using static analysis."""

    def __init__(self):
        # Common vulnerability patterns
        self.vulnerability_patterns = {
            'sql_injection': {
                'patterns': [
                    r'\.execute\s*\(\s*["\']?\s*SELECT.*%s.*["\']?\s*\)',
                    r'\.execute\s*\(\s*["\']?\s*INSERT.*%s.*["\']?\s*\)',
                    r'\.execute\s*\(\s*["\']?\s*UPDATE.*%s.*["\']?\s*\)',
                    r'\.execute\s*\(\s*["\']?\s*DELETE.*%s.*["\']?\s*\)',
                    r'cursor\.execute\s*\(\s*.*\+.*\)',
                    r'query\s*=.*%.*\s*db\.execute',
                ],
                'severity': 'high',
                'description': 'Potential SQL injection vulnerability',
                'cwe_id': 'CWE-89',
                'owasp_category': 'A03:2021-Injection'
            },
            'xss_vulnerability': {
                'patterns': [
                    r'innerHTML\s*=.*\+',
                    r'document\.write\s*\(.*\+.*\)',
                    r'eval\s*\(.*\+.*\)',
                    r'setTimeout\s*\(.*\+.*\)',
                    r'setInterval\s*\(.*\+.*\)',
                ],
                'severity': 'high',
                'description': 'Potential Cross-Site Scripting (XSS) vulnerability',
                'cwe_id': 'CWE-79',
                'owasp_category': 'A03:2021-Injection'
            },
            'weak_crypto': {
                'patterns': [
                    r'import\s+md5',
                    r'from\s+crypt\s+import',
                    r'hashlib\.md5\s*\(',
                    r'hashlib\.sha1\s*\(',
                    r'random\.',
                    r'os\.urandom',
                ],
                'severity': 'medium',
                'description': 'Potentially weak cryptographic implementation',
                'cwe_id': 'CWE-327',
                'owasp_category': 'A02:2021-Cryptographic Failures'
            },
            'hardcoded_secrets': {
                'patterns': [
                    r'password\s*=\s*["\'][^"\']+["\']',
                    r'secret\s*=\s*["\'][^"\']+["\']',
                    r'key\s*=\s*["\'][^"\']+["\']',
                    r'token\s*=\s*["\'][^"\']+["\']',
                    r'api_key\s*=\s*["\'][^"\']+["\']',
                ],
                'severity': 'high',
                'description': 'Potential hardcoded secrets or credentials',
                'cwe_id': 'CWE-798',
                'owasp_category': 'A05:2021-Security Misconfiguration'
            },
            'path_traversal': {
                'patterns': [
                    r'open\s*\(\s*.*\+.*\)',
                    r'file\s*=\s*open\s*\(.*\+.*\)',
                    r'with\s+open\s*\(.*\+.*\)',
                    r'\.\./',
                    r'\.\.\\',
                ],
                'severity': 'high',
                'description': 'Potential path traversal vulnerability',
                'cwe_id': 'CWE-22',
                'owasp_category': 'A01:2021-Broken Access Control'
            },
            'command_injection': {
                'patterns': [
                    r'os\.system\s*\(.*\+.*\)',
                    r'subprocess\.call\s*\(.*\+.*\)',
                    r'os\.popen\s*\(.*\+.*\)',
                    r'subprocess\.Popen\s*\(.*\+.*\)',
                ],
                'severity': 'critical',
                'description': 'Potential command injection vulnerability',
                'cwe_id': 'CWE-78',
                'owasp_category': 'A03:2021-Injection'
            },
            'insecure_deserialization': {
                'patterns': [
                    r'pickle\.loads?\s*\(',
                    r'yaml\.load\s*\(',
                    r'json\.loads?\s*\(',
                    r'eval\s*\(',
                ],
                'severity': 'high',
                'description': 'Potential insecure deserialization',
                'cwe_id': 'CWE-502',
                'owasp_category': 'A08:2021-Software and Data Integrity Failures'
            }
        }

    def analyze_security_vulnerabilities(self, file_list: List[str], semantic: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze files for security vulnerabilities.

        Args:
            file_list: List of file paths to analyze
            semantic: Semantic analysis results

        Returns:
            Dict containing security analysis results
        """
        findings = []
        analyzed_files = 0
        total_lines = 0

        for file_path in file_list:
            if self._should_analyze_file(file_path):
                file_findings = self._analyze_file(file_path)
                findings.extend(file_findings)
                analyzed_files += 1

                # Count lines for metrics
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        total_lines += len(f.readlines())
                except Exception:
                    pass

        # Calculate risk scores
        risk_score = self._calculate_risk_score(findings, analyzed_files, total_lines)

        return {
            'security_findings': [self._finding_to_dict(f) for f in findings],
            'summary': {
                'total_files_analyzed': analyzed_files,
                'total_findings': len(findings),
                'critical_findings': len([f for f in findings if f.severity == 'critical']),
                'high_findings': len([f for f in findings if f.severity == 'high']),
                'medium_findings': len([f for f in findings if f.severity == 'medium']),
                'low_findings': len([f for f in findings if f.severity == 'low']),
                'total_lines_analyzed': total_lines,
                'findings_per_1000_lines': round((len(findings) / max(total_lines, 1)) * 1000, 2)
            },
            'risk_assessment': risk_score,
            'owasp_coverage': self._assess_owasp_coverage(findings),
            'recommendations': self._generate_security_recommendations(findings)
        }

    def _should_analyze_file(self, file_path: str) -> bool:
        """Determine if a file should be analyzed for security issues."""
        # Skip binary files, images, etc.
        skip_extensions = {'.jpg', '.png', '.gif', '.pdf', '.zip', '.tar', '.gz', '.pyc', '.class'}

        if any(file_path.endswith(ext) for ext in skip_extensions):
            return False

        # Only analyze text files that are likely to contain code
        code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.php', '.rb', '.go', '.rs'}
        return any(file_path.endswith(ext) for ext in code_extensions)

    def _analyze_file(self, file_path: str) -> List[SecurityFinding]:
        """Analyze a single file for security vulnerabilities."""
        findings = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                for vuln_type, vuln_config in self.vulnerability_patterns.items():
                    for pattern in vuln_config['patterns']:
                        if re.search(pattern, line, re.IGNORECASE):
                            finding = SecurityFinding(
                                vulnerability_type=vuln_type,
                                severity=vuln_config['severity'],
                                file_path=file_path,
                                line_number=line_num,
                                description=vuln_config['description'],
                                code_snippet=line.strip(),
                                cwe_id=vuln_config.get('cwe_id', ''),
                                owasp_category=vuln_config.get('owasp_category', '')
                            )
                            findings.append(finding)
                            break  # Only report one finding per line per type

        except Exception as e:
            # Log error but continue analysis
            print(f"Error analyzing {file_path}: {e}")

        return findings

    def _calculate_risk_score(self, findings: List[SecurityFinding], files_analyzed: int, total_lines: int) -> Dict[str, Any]:
        """Calculate overall security risk score."""
        if not findings:
            return {
                'overall_risk': 'low',
                'risk_score': 0.1,
                'description': 'No security vulnerabilities detected'
            }

        # Weight findings by severity
        severity_weights = {
            'critical': 1.0,
            'high': 0.7,
            'medium': 0.4,
            'low': 0.1,
            'info': 0.05
        }

        total_weight = sum(severity_weights.get(f.severity, 0.1) for f in findings)
        avg_weight = total_weight / len(findings)

        # Normalize by code volume
        volume_factor = min(total_lines / 10000, 1.0)  # Cap at 10k lines
        risk_score = avg_weight * volume_factor

        # Determine risk level
        if risk_score >= 0.8:
            risk_level = 'critical'
        elif risk_score >= 0.6:
            risk_level = 'high'
        elif risk_score >= 0.4:
            risk_level = 'medium'
        elif risk_score >= 0.2:
            risk_level = 'low'
        else:
            risk_level = 'minimal'

        return {
            'overall_risk': risk_level,
            'risk_score': round(risk_score, 3),
            'description': f'Security risk assessment: {risk_level} ({risk_score:.1%})',
            'factors': {
                'findings_count': len(findings),
                'avg_severity_weight': round(avg_weight, 3),
                'volume_factor': round(volume_factor, 3)
            }
        }

    def _assess_owasp_coverage(self, findings: List[SecurityFinding]) -> Dict[str, Any]:
        """Assess coverage of OWASP Top 10 categories."""
        owasp_categories = {
            'A01:2021-Broken Access Control': 'Broken Access Control',
            'A02:2021-Cryptographic Failures': 'Cryptographic Failures',
            'A03:2021-Injection': 'Injection',
            'A04:2021-Insecure Design': 'Insecure Design',
            'A05:2021-Security Misconfiguration': 'Security Misconfiguration',
            'A06:2021-Vulnerable Components': 'Vulnerable Components',
            'A07:2021-Identification & Authentication': 'Identification & Authentication',
            'A08:2021-Software Integrity': 'Software Integrity',
            'A09:2021-Security Logging': 'Security Logging',
            'A10:2021-SSRF': 'Server-Side Request Forgery'
        }

        covered_categories = set()
        for finding in findings:
            if finding.owasp_category:
                covered_categories.add(finding.owasp_category)

        return {
            'covered_categories': list(covered_categories),
            'coverage_percentage': round(len(covered_categories) / len(owasp_categories) * 100, 1),
            'total_owasp_categories': len(owasp_categories),
            'covered_count': len(covered_categories)
        }

    def _generate_security_recommendations(self, findings: List[SecurityFinding]) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []

        if not findings:
            recommendations.append("No critical security issues detected. Continue regular security reviews.")
            return recommendations

        # Group findings by type
        findings_by_type = {}
        for finding in findings:
            vuln_type = finding.vulnerability_type
            if vuln_type not in findings_by_type:
                findings_by_type[vuln_type] = []
            findings_by_type[vuln_type].append(finding)

        # Generate recommendations based on finding types
        if 'sql_injection' in findings_by_type:
            recommendations.append("Implement parameterized queries or prepared statements for all database operations")

        if 'xss_vulnerability' in findings_by_type:
            recommendations.append("Implement proper output encoding and input validation for all user inputs")

        if 'command_injection' in findings_by_type:
            recommendations.append("Avoid shell command execution with user inputs; use safe APIs instead")

        if 'hardcoded_secrets' in findings_by_type:
            recommendations.append("Move all secrets to environment variables or secure credential stores")

        if 'weak_crypto' in findings_by_type:
            recommendations.append("Upgrade to modern cryptographic algorithms (AES-256, SHA-256+)")

        # General recommendations
        critical_count = len([f for f in findings if f.severity == 'critical'])
        if critical_count > 0:
            recommendations.append(f"Address {critical_count} critical security findings immediately")

        recommendations.append("Implement automated security testing in CI/CD pipeline")
        recommendations.append("Conduct regular security code reviews and penetration testing")

        return recommendations

    def _finding_to_dict(self, finding: SecurityFinding) -> Dict[str, Any]:
        """Convert SecurityFinding to dictionary."""
        return {
            'vulnerability_type': finding.vulnerability_type,
            'severity': finding.severity,
            'file_path': finding.file_path,
            'line_number': finding.line_number,
            'description': finding.description,
            'code_snippet': finding.code_snippet,
            'cwe_id': finding.cwe_id,
            'owasp_category': finding.owasp_category
        }

def analyze_security_vulnerabilities(file_list: List[str], semantic: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry point for security vulnerability analysis.

    Args:
        file_list: List of file paths to analyze
        semantic: Semantic analysis results from previous stages

    Returns:
        Dict containing security analysis results
    """
    analyzer = SecurityAnalyzer()
    return analyzer.analyze_security_vulnerabilities(file_list, semantic)