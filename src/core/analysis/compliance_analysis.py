"""
Compliance Analysis Module

Analyzes repositories for compliance with various standards and regulations,
including GDPR, HIPAA, SOC 2, and security best practices.
"""

from typing import Dict, Any, List, Set
from pathlib import Path
import re

from .base import AnalysisComponent


class ComplianceAnalysis(AnalysisComponent):
    """
    Analyzes repository compliance with industry standards and regulations.

    Checks for:
    - Data handling compliance (GDPR, CCPA)
    - Security best practices
    - License compliance
    - Dependency security
    - Code quality standards
    """

    def __init__(self):
        self.compliance_checks = {
            "gdpr": self._check_gdpr_compliance,
            "hipaa": self._check_hipaa_compliance,
            "soc2": self._check_soc2_compliance,
            "security": self._check_security_best_practices,
            "license": self._check_license_compliance,
            "dependencies": self._check_dependency_security,
        }

    def analyze(self, repo_path: str, **kwargs) -> Dict[str, Any]:
        """
        Perform comprehensive compliance analysis.

        Args:
            repo_path: Path to the repository to analyze

        Returns:
            Dict containing compliance analysis results
        """
        repo = Path(repo_path)

        compliance_results = {}

        for check_name, check_func in self.compliance_checks.items():
            try:
                compliance_results[check_name] = check_func(repo)
            except Exception as e:
                compliance_results[check_name] = {
                    "status": "error",
                    "error": str(e),
                    "compliant": False
                }

        # Overall compliance score
        compliant_checks = sum(1 for r in compliance_results.values() if r.get("compliant", False))
        total_checks = len(compliance_results)

        overall_compliance = {
            "overall_score": compliant_checks / total_checks if total_checks > 0 else 0,
            "compliant_checks": compliant_checks,
            "total_checks": total_checks,
            "details": compliance_results
        }

        return {
            "compliance_analysis": overall_compliance
        }

    def _check_gdpr_compliance(self, repo: Path) -> Dict[str, Any]:
        """Check GDPR compliance indicators."""
        findings = []

        # Check for data processing files
        data_files = ["privacy_policy.md", "gdpr.md", "data_processing.md"]
        has_privacy_docs = any((repo / f).exists() for f in data_files)

        # Check for data handling in code
        code_files = list(repo.rglob("*.py")) + list(repo.rglob("*.js")) + list(repo.rglob("*.ts"))
        data_processing_indicators = [
            "personal_data", "user_data", "gdpr", "data_processing",
            "consent", "privacy_policy", "data_retention"
        ]

        has_data_processing = False
        for file_path in code_files[:50]:  # Limit to first 50 files for performance
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                if any(indicator in content.lower() for indicator in data_processing_indicators):
                    has_data_processing = True
                    break
            except:
                continue

        compliant = has_privacy_docs and has_data_processing

        return {
            "compliant": compliant,
            "has_privacy_documentation": has_privacy_docs,
            "has_data_processing_awareness": has_data_processing,
            "recommendations": [
                "Add privacy policy and data processing documentation" if not has_privacy_docs else None,
                "Implement GDPR-compliant data handling practices" if not has_data_processing else None,
            ]
        }

    def _check_hipaa_compliance(self, repo: Path) -> Dict[str, Any]:
        """Check HIPAA compliance indicators."""
        findings = []

        # HIPAA-specific files
        hipaa_files = ["hipaa_compliance.md", "phi_protection.md", "health_data.md"]
        has_hipaa_docs = any((repo / f).exists() for f in hipaa_files)

        # Check for PHI handling
        phi_indicators = [
            "protected_health_information", "phi", "medical_data",
            "patient_data", "health_records", "hipaa"
        ]

        code_files = list(repo.rglob("*.py"))[:50]
        has_phi_handling = False
        for file_path in code_files:
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                if any(indicator in content.lower() for indicator in phi_indicators):
                    has_phi_handling = True
                    break
            except:
                continue

        # HIPAA requires specific security measures
        security_indicators = ["encryption", "access_control", "audit_logging"]
        has_security_measures = any(
            self._check_file_contains(repo, pattern) for pattern in security_indicators
        )

        compliant = has_hipaa_docs and (not has_phi_handling or has_security_measures)

        return {
            "compliant": compliant,
            "has_hipaa_documentation": has_hipaa_docs,
            "handles_phi": has_phi_handling,
            "has_security_measures": has_security_measures,
            "recommendations": [
                "Add HIPAA compliance documentation",
                "Implement PHI protection measures if handling health data"
            ]
        }

    def _check_soc2_compliance(self, repo: Path) -> Dict[str, Any]:
        """Check SOC 2 compliance indicators."""
        # SOC 2 focuses on security, availability, processing integrity, confidentiality, privacy

        checks = {
            "security": self._check_security_controls(repo),
            "availability": self._check_availability_measures(repo),
            "integrity": self._check_data_integrity(repo),
            "confidentiality": self._check_confidentiality_measures(repo),
            "privacy": self._check_privacy_controls(repo)
        }

        compliant = all(result["compliant"] for result in checks.values())

        return {
            "compliant": compliant,
            "criteria": checks,
            "recommendations": [
                "Implement comprehensive security controls",
                "Add monitoring and availability measures",
                "Ensure data integrity mechanisms",
                "Implement confidentiality protections",
                "Add privacy controls and documentation"
            ]
        }

    def _check_security_best_practices(self, repo: Path) -> Dict[str, Any]:
        """Check adherence to security best practices."""
        security_checks = {
            "has_security_md": (repo / "SECURITY.md").exists(),
            "has_dependabot": (repo / ".github" / "dependabot.yml").exists(),
            "has_codeql": (repo / ".github" / "workflows" / "codeql.yml").exists(),
            "no_hardcoded_secrets": not self._check_file_contains(repo, r"(?i)(password|secret|key)\s*=\s*['\"][^'\"]+['\"]"),
            "uses_https": self._check_uses_https(repo),
        }

        compliant = sum(security_checks.values()) >= 3  # At least 3/5 checks pass

        return {
            "compliant": compliant,
            "checks": security_checks,
            "recommendations": [
                "Add SECURITY.md file",
                "Enable Dependabot for dependency updates",
                "Set up CodeQL security scanning",
                "Remove hardcoded secrets",
                "Use HTTPS for all external connections"
            ]
        }

    def _check_license_compliance(self, repo: Path) -> Dict[str, Any]:
        """Check license compliance."""
        license_files = ["LICENSE", "LICENSE.md", "COPYING"]
        has_license = any((repo / f).exists() for f in license_files)

        if has_license:
            # Read license content
            license_content = ""
            for license_file in license_files:
                license_path = repo / license_file
                if license_path.exists():
                    try:
                        license_content = license_path.read_text(encoding='utf-8', errors='ignore').lower()
                        break
                    except:
                        continue

            # Check for common license types
            license_types = {
                "mit": "mit" in license_content,
                "apache": "apache" in license_content,
                "gpl": "gpl" in license_content or "gnu" in license_content,
                "bsd": "bsd" in license_content,
            }

            recognized_license = any(license_types.values())
        else:
            recognized_license = False

        compliant = has_license and recognized_license

        return {
            "compliant": compliant,
            "has_license_file": has_license,
            "recognized_license": recognized_license,
            "recommendations": [
                "Add a LICENSE file" if not has_license else None,
                "Use a standard open-source license" if has_license and not recognized_license else None,
            ]
        }

    def _check_dependency_security(self, repo: Path) -> Dict[str, Any]:
        """Check dependency security."""
        # Check for dependency files
        dep_files = ["requirements.txt", "pyproject.toml", "package.json", "Cargo.toml"]
        has_dep_files = any((repo / f).exists() for f in dep_files)

        # Check for security scanning
        has_security_scan = (
            (repo / ".github" / "workflows").exists() and
            any("security" in wf.name.lower() or "audit" in wf.name.lower()
                for wf in (repo / ".github" / "workflows").glob("*.yml"))
        )

        # Check for known vulnerable patterns (simplified)
        vulnerable_patterns = [
            r"requests.*[<>=].*2\.0",  # Old requests version
            r"django.*[<>=].*2\.0",    # Old Django version
        ]

        has_vulnerabilities = False
        for pattern in vulnerable_patterns:
            if self._check_file_contains(repo, pattern):
                has_vulnerabilities = True
                break

        compliant = has_dep_files and not has_vulnerabilities

        return {
            "compliant": compliant,
            "has_dependency_files": has_dep_files,
            "has_security_scanning": has_security_scan,
            "has_known_vulnerabilities": has_vulnerabilities,
            "recommendations": [
                "Add dependency management files",
                "Implement automated security scanning",
                "Update vulnerable dependencies"
            ]
        }

    # Helper methods for individual checks
    def _check_security_controls(self, repo: Path) -> Dict[str, Any]:
        return {"compliant": (repo / ".github" / "workflows" / "security.yml").exists()}

    def _check_availability_measures(self, repo: Path) -> Dict[str, Any]:
        return {"compliant": (repo / "docker-compose.yml").exists() or (repo / "Dockerfile").exists()}

    def _check_data_integrity(self, repo: Path) -> Dict[str, Any]:
        return {"compliant": self._check_file_contains(repo, "test")}

    def _check_confidentiality_measures(self, repo: Path) -> Dict[str, Any]:
        return {"compliant": self._check_file_contains(repo, "encrypt")}

    def _check_privacy_controls(self, repo: Path) -> Dict[str, Any]:
        return {"compliant": (repo / "PRIVACY.md").exists() or (repo / "privacy_policy.md").exists()}

    def _check_file_contains(self, repo: Path, pattern: str, file_pattern: str = "*") -> bool:
        """Check if any file matching pattern contains the given text/pattern."""
        for file_path in repo.rglob(file_pattern):
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    if re.search(pattern, content, re.IGNORECASE):
                        return True
                except:
                    continue
        return False

    def _check_uses_https(self, repo: Path) -> bool:
        """Check if code uses HTTPS for external connections."""
        http_pattern = r"https?://"
        files_with_urls = self._check_file_contains(repo, http_pattern)

        if not files_with_urls:
            return True  # No URLs found, assume compliant

        # Check that HTTP URLs are not used (only HTTPS)
        http_only = self._check_file_contains(repo, r"http://")
        return not http_only