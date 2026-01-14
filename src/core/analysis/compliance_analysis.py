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

        # Generate certification reports
        certification_reports = self._generate_certification_reports(repo, compliance_results)

        return {
            "compliance_analysis": overall_compliance,
            "certification_reports": certification_reports
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

    def _generate_certification_reports(self, repo: Path, compliance_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate certification reports for various standards.

        Args:
            repo: Repository path
            compliance_results: Results from compliance checks

        Returns:
            Dict containing certification reports
        """
        reports = {}

        # ISO 27001 Information Security Management Systems
        reports["iso27001"] = self._generate_iso27001_report(repo, compliance_results)

        # NIST Cybersecurity Framework
        reports["nist_csf"] = self._generate_nist_csf_report(repo, compliance_results)

        # SOC 2 Trust Services Criteria
        reports["soc2"] = self._generate_soc2_report(repo, compliance_results)

        return reports

    def _generate_iso27001_report(self, repo: Path, compliance_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ISO 27001 certification report."""
        iso27001_controls = {
            "A.5": "Information security policies",  # Maps to security best practices
            "A.6": "Organization of information security",  # Maps to security controls
            "A.7": "Human resource security",  # Not directly checked
            "A.8": "Asset management",  # Maps to license compliance
            "A.9": "Access control",  # Maps to security measures
            "A.10": "Cryptography",  # Maps to confidentiality
            "A.11": "Physical and environmental security",  # Not applicable
            "A.12": "Operations security",  # Maps to availability
            "A.13": "Communications security",  # Maps to HTTPS usage
            "A.14": "System acquisition, development and maintenance",  # Maps to dependency security
            "A.15": "Supplier relationships",  # Not directly checked
            "A.16": "Information security incident management",  # Maps to security incident response
            "A.17": "Information security aspects of business continuity",  # Maps to availability
            "A.18": "Compliance",  # Maps to overall compliance
        }

        control_compliance = {}
        for control, description in iso27001_controls.items():
            if "security" in description.lower():
                control_compliance[control] = compliance_results.get("security", {}).get("compliant", False)
            elif "license" in description.lower():
                control_compliance[control] = compliance_results.get("license", {}).get("compliant", False)
            elif "cryptography" in description.lower() or "confidentiality" in description.lower():
                control_compliance[control] = compliance_results.get("soc2", {}).get("criteria", {}).get("confidentiality", {}).get("compliant", False)
            elif "availability" in description.lower():
                control_compliance[control] = compliance_results.get("soc2", {}).get("criteria", {}).get("availability", {}).get("compliant", False)
            elif "https" in description.lower():
                control_compliance[control] = compliance_results.get("security", {}).get("checks", {}).get("uses_https", False)
            elif "dependency" in description.lower():
                control_compliance[control] = compliance_results.get("dependencies", {}).get("compliant", False)
            else:
                control_compliance[control] = False

        compliant_controls = sum(control_compliance.values())
        total_controls = len(control_compliance)

        return {
            "standard": "ISO 27001:2022",
            "compliance_score": compliant_controls / total_controls if total_controls > 0 else 0,
            "compliant_controls": compliant_controls,
            "total_controls": total_controls,
            "control_details": control_compliance,
            "certification_recommendations": [
                "Implement comprehensive information security policies",
                "Establish security organization and responsibilities",
                "Conduct regular security audits and assessments",
                "Develop incident response and business continuity plans"
            ]
        }

    def _generate_nist_csf_report(self, repo: Path, compliance_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate NIST Cybersecurity Framework report."""
        nist_functions = {
            "Identify": ["Asset Management", "Risk Assessment", "Supply Chain Risk Management"],
            "Protect": ["Access Control", "Data Security", "Information Protection Processes", "Protective Technology"],
            "Detect": ["Anomalies and Events", "Security Continuous Monitoring", "Detection Processes"],
            "Respond": ["Response Planning", "Communications", "Analysis", "Mitigation", "Improvements"],
            "Recover": ["Recovery Planning", "Improvements", "Communications"]
        }

        function_compliance = {}
        for function, categories in nist_functions.items():
            category_compliance = []
            for category in categories:
                if "access" in category.lower():
                    category_compliance.append(compliance_results.get("security", {}).get("compliant", False))
                elif "data" in category.lower() or "information" in category.lower():
                    category_compliance.append(compliance_results.get("gdpr", {}).get("compliant", False) or compliance_results.get("hipaa", {}).get("compliant", False))
                elif "monitoring" in category.lower():
                    category_compliance.append(compliance_results.get("security", {}).get("checks", {}).get("has_codeql", False))
                elif "response" in category.lower() or "recovery" in category.lower():
                    category_compliance.append(compliance_results.get("soc2", {}).get("compliant", False))
                else:
                    category_compliance.append(False)
            function_compliance[function] = any(category_compliance)

        compliant_functions = sum(function_compliance.values())
        total_functions = len(function_compliance)

        return {
            "standard": "NIST Cybersecurity Framework v1.1",
            "compliance_score": compliant_functions / total_functions if total_functions > 0 else 0,
            "compliant_functions": compliant_functions,
            "total_functions": total_functions,
            "function_details": function_compliance,
            "certification_recommendations": [
                "Implement comprehensive risk assessment processes",
                "Deploy continuous monitoring and detection capabilities",
                "Develop incident response and recovery plans",
                "Establish regular security assessments and audits"
            ]
        }

    def _generate_soc2_report(self, repo: Path, compliance_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SOC 2 certification report."""
        soc2_criteria = {
            "Security": ["Access Controls", "System Operations", "Change Management", "Risk Mitigation"],
            "Availability": ["System Availability", "Monitoring", "Incident Response"],
            "Processing Integrity": ["Data Processing", "Quality Assurance", "Output Controls"],
            "Confidentiality": ["Data Protection", "Encryption", "Access Controls"],
            "Privacy": ["Data Collection", "Data Usage", "Data Retention", "Data Disposal"]
        }

        criteria_compliance = {}
        for criterion, controls in soc2_criteria.items():
            control_compliance = []
            for control in controls:
                if "access" in control.lower():
                    control_compliance.append(compliance_results.get("security", {}).get("compliant", False))
                elif "availability" in control.lower() or "monitoring" in control.lower():
                    control_compliance.append(compliance_results.get("soc2", {}).get("criteria", {}).get("availability", {}).get("compliant", False))
                elif "integrity" in control.lower() or "processing" in control.lower():
                    control_compliance.append(compliance_results.get("soc2", {}).get("criteria", {}).get("integrity", {}).get("compliant", False))
                elif "confidentiality" in control.lower() or "encryption" in control.lower():
                    control_compliance.append(compliance_results.get("soc2", {}).get("criteria", {}).get("confidentiality", {}).get("compliant", False))
                elif "privacy" in control.lower():
                    control_compliance.append(compliance_results.get("soc2", {}).get("criteria", {}).get("privacy", {}).get("compliant", False))
                else:
                    control_compliance.append(False)
            criteria_compliance[criterion] = any(control_compliance)

        compliant_criteria = sum(criteria_compliance.values())
        total_criteria = len(criteria_compliance)

        return {
            "standard": "SOC 2 Trust Services Criteria",
            "compliance_score": compliant_criteria / total_criteria if total_criteria > 0 else 0,
            "compliant_criteria": compliant_criteria,
            "total_criteria": total_criteria,
            "criteria_details": criteria_compliance,
            "certification_recommendations": [
                "Implement comprehensive access controls and monitoring",
                "Establish data protection and encryption measures",
                "Develop incident response and business continuity procedures",
                "Conduct regular independent audits and assessments"
            ]
        }