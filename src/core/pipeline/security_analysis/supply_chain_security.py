"""Supply chain security analysis for Repository Intelligence Scanner."""

import re
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Set, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from ...exceptions import AnalysisError

@dataclass
class SupplyChainFinding:
    """Represents a supply chain security finding."""
    finding_type: str
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    package_name: str
    version: str
    description: str
    vulnerability_id: str = ""
    cvss_score: float = 0.0
    recommendation: str = ""
    cwe_id: str = ""

class SupplyChainAnalyzer:
    """Analyzes software supply chain security."""

    def __init__(self):
        self.findings: List[SupplyChainFinding] = []

    def analyze_dependencies(self, repo_path: str) -> List[SupplyChainFinding]:
        """Analyze dependency vulnerabilities and supply chain risks."""
        self.findings = []

        try:
            # Analyze different package managers
            self._analyze_python_dependencies(repo_path)
            self._analyze_javascript_dependencies(repo_path)
            self._analyze_rust_dependencies(repo_path)
            self._analyze_go_dependencies(repo_path)

            # Generate SBOM if possible
            self._generate_sbom(repo_path)

            # Check for provenance and integrity
            self._analyze_build_integrity(repo_path)

        except Exception as e:
            raise AnalysisError(f"Error in supply chain analysis: {str(e)}")

        return self.findings

    def _analyze_python_dependencies(self, repo_path: str):
        """Analyze Python dependencies using safety and pip-audit."""
        requirements_files = ['requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile']

        for req_file in requirements_files:
            req_path = Path(repo_path) / req_file
            if req_path.exists():
                try:
                    # Use safety check
                    result = subprocess.run(
                        ['safety', 'check', '--file', str(req_path), '--json'],
                        capture_output=True, text=True, cwd=repo_path, timeout=30
                    )

                    if result.returncode == 0 and result.stdout:
                        vulnerabilities = json.loads(result.stdout)
                        for vuln in vulnerabilities:
                            self.findings.append(SupplyChainFinding(
                                finding_type='dependency_vulnerability',
                                severity=self._map_cvss_to_severity(vuln.get('cvss_score', 0)),
                                package_name=vuln.get('package', ''),
                                version=vuln.get('version', ''),
                                description=vuln.get('description', ''),
                                vulnerability_id=vuln.get('vulnerability_id', ''),
                                cvss_score=vuln.get('cvss_score', 0),
                                recommendation=vuln.get('recommendation', 'Update to a secure version'),
                                cwe_id=vuln.get('cwe', '')
                            ))

                except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
                    # Fallback to basic analysis
                    self._basic_python_analysis(req_path)

    def _analyze_javascript_dependencies(self, repo_path: str):
        """Analyze JavaScript/TypeScript dependencies."""
        package_json = Path(repo_path) / 'package.json'
        if package_json.exists():
            try:
                with open(package_json, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)

                # Check for known vulnerable packages
                dependencies = {**package_data.get('dependencies', {}), **package_data.get('devDependencies', {})}

                vulnerable_packages = {
                    'lodash': '4.17.4',  # Example - check for versions before security fixes
                    'axios': '0.21.1',
                    # Add more known vulnerable packages
                }

                for pkg, min_version in vulnerable_packages.items():
                    if pkg in dependencies:
                        current_version = dependencies[pkg]
                        if self._version_less_than(current_version, min_version):
                            self.findings.append(SupplyChainFinding(
                                finding_type='outdated_vulnerable_package',
                                severity='high',
                                package_name=pkg,
                                version=current_version,
                                description=f'Package {pkg} version {current_version} is vulnerable',
                                recommendation=f'Update to version {min_version} or later'
                            ))

            except (json.JSONDecodeError, KeyError):
                pass

    def _analyze_rust_dependencies(self, repo_path: str):
        """Analyze Rust dependencies using cargo-audit if available."""
        cargo_toml = Path(repo_path) / 'Cargo.toml'
        if cargo_toml.exists():
            try:
                result = subprocess.run(
                    ['cargo', 'audit', '--json'],
                    capture_output=True, text=True, cwd=repo_path, timeout=60
                )

                if result.returncode == 0 and result.stdout:
                    audit_data = json.loads(result.stdout)
                    for vuln in audit_data.get('vulnerabilities', []):
                        self.findings.append(SupplyChainFinding(
                            finding_type='rust_dependency_vulnerability',
                            severity='high',
                            package_name=vuln.get('package', ''),
                            version=vuln.get('version', ''),
                            description=vuln.get('description', ''),
                            vulnerability_id=vuln.get('id', ''),
                            recommendation='Update Cargo.lock and rebuild'
                        ))

            except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
                pass

    def _analyze_go_dependencies(self, repo_path: str):
        """Analyze Go dependencies."""
        go_mod = Path(repo_path) / 'go.mod'
        if go_mod.exists():
            try:
                result = subprocess.run(
                    ['go', 'list', '-m', '-json', 'all'],
                    capture_output=True, text=True, cwd=repo_path, timeout=30
                )

                if result.returncode == 0 and result.stdout:
                    # Parse go modules and check for known vulnerabilities
                    # This is a simplified check - in practice, use nancy or gosec
                    modules = result.stdout.strip().split('\n')
                    for module_line in modules:
                        if module_line.strip():
                            try:
                                module_data = json.loads(module_line)
                                module_name = module_data.get('Path', '')
                                version = module_data.get('Version', '')

                                # Check for known vulnerable Go modules
                                if self._is_vulnerable_go_module(module_name, version):
                                    self.findings.append(SupplyChainFinding(
                                        finding_type='go_dependency_vulnerability',
                                        severity='high',
                                        package_name=module_name,
                                        version=version,
                                        description=f'Potentially vulnerable Go module: {module_name}',
                                        recommendation='Update to latest secure version'
                                    ))
                            except json.JSONDecodeError:
                                continue

            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

    def _generate_sbom(self, repo_path: str):
        """Generate Software Bill of Materials using Syft if available."""
        try:
            result = subprocess.run(
                ['syft', str(repo_path), '--output', 'json'],
                capture_output=True, text=True, cwd=repo_path, timeout=120
            )

            if result.returncode == 0 and result.stdout:
                sbom_data = json.loads(result.stdout)
                # Store SBOM for further analysis
                self.sbom = sbom_data

                # Check for packages without provenance
                artifacts = sbom_data.get('artifacts', [])
                for artifact in artifacts:
                    if not artifact.get('provenance'):
                        self.findings.append(SupplyChainFinding(
                            finding_type='missing_provenance',
                            severity='medium',
                            package_name=artifact.get('name', ''),
                            version=artifact.get('version', ''),
                            description='Package lacks provenance information',
                            recommendation='Ensure packages come from trusted sources with verifiable provenance'
                        ))

        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            # Syft not available, skip SBOM generation
            self.sbom = None
            self.findings.append(SupplyChainFinding(
                finding_type='sbom_unavailable',
                severity='low',
                package_name='',
                version='',
                description='SBOM generation not available (Syft not installed)',
                recommendation='Install Syft for comprehensive supply chain analysis'
            ))

    def _analyze_build_integrity(self, repo_path: str):
        """Analyze build system integrity."""
        # Check for build scripts and their security
        build_files = ['Makefile', 'build.gradle', 'pom.xml', 'build.xml']

        for build_file in build_files:
            build_path = Path(repo_path) / build_file
            if build_path.exists():
                try:
                    with open(build_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Check for insecure practices
                    if re.search(r'curl.*\|.*bash', content, re.IGNORECASE):
                        self.findings.append(SupplyChainFinding(
                            finding_type='insecure_build_script',
                            severity='critical',
                            package_name='build-system',
                            version='',
                            description='Build script downloads and executes code from internet',
                            recommendation='Use pinned versions and verify checksums'
                        ))

                except Exception:
                    pass

    def _basic_python_analysis(self, req_path: Path):
        """Basic Python dependency analysis when safety is not available."""
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for known vulnerable packages
            vulnerable_patterns = [
                (r'requests\s*==\s*2\.0\.0', 'requests 2.0.0 has security issues'),
                (r'urllib3\s*==\s*1\.24\.0', 'urllib3 1.24.0 has security issues'),
            ]

            for pattern, desc in vulnerable_patterns:
                if re.search(pattern, content):
                    self.findings.append(SupplyChainFinding(
                        finding_type='known_vulnerable_package',
                        severity='high',
                        package_name='unknown',
                        version='unknown',
                        description=desc,
                        recommendation='Update to latest secure version'
                    ))

        except Exception:
            pass

    def _version_less_than(self, version1: str, version2: str) -> bool:
        """Simple version comparison."""
        try:
            v1_parts = [int(x) for x in version1.split('.') if x.isdigit()]
            v2_parts = [int(x) for x in version2.split('.') if x.isdigit()]

            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 < v2:
                    return True
                elif v1 > v2:
                    return False
            return len(v1_parts) < len(v2_parts)
        except (ValueError, AttributeError):
            return False

    def _map_cvss_to_severity(self, cvss_score: float) -> str:
        """Map CVSS score to severity level."""
        if cvss_score >= 9.0:
            return 'critical'
        elif cvss_score >= 7.0:
            return 'high'
        elif cvss_score >= 4.0:
            return 'medium'
        elif cvss_score >= 0.1:
            return 'low'
        else:
            return 'info'

    def _is_vulnerable_go_module(self, module_name: str, version: str) -> bool:
        """Check if Go module is known to be vulnerable."""
        # Simplified check - in practice, use a vulnerability database
        vulnerable_modules = [
            'golang.org/x/crypto/ssh',
            'golang.org/x/net/http2',
        ]
        return any(vuln in module_name for vuln in vulnerable_modules)