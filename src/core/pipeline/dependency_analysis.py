#!/usr/bin/env python3
"""
Dependency Analysis Stage

Analyzes package dependencies for security vulnerabilities, license compliance,
and maintenance health. Supports multiple package managers and ecosystems.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta

import logging

logger = logging.getLogger(__name__)

class DependencyAnalyzer:
    """Analyzes dependencies for security, license, and maintenance issues."""

    def __init__(self):
        self.supported_files = {
            'python': ['requirements.txt', 'pyproject.toml', 'setup.py', 'Pipfile', 'Pipfile.lock'],
            'javascript': ['package.json', 'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml'],
            'java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
            'csharp': ['packages.config', '.csproj'],
            'php': ['composer.json', 'composer.lock'],
            'ruby': ['Gemfile', 'Gemfile.lock'],
            'go': ['go.mod', 'go.sum'],
            'rust': ['Cargo.toml', 'Cargo.lock']
        }

        # Known vulnerable packages (simplified - in practice would use CVE database)
        self.known_vulnerabilities = {
            'python': {
                'requests': ['<2.20.0'],  # Example vulnerability
                'django': ['<2.2.0'],
                'flask': ['<1.0.0']
            },
            'javascript': {
                'lodash': ['<4.17.11'],
                'moment': ['<2.20.0'],
                'axios': ['<0.18.1']
            }
        }

        # License compatibility matrix (simplified)
        self.license_compatibility = {
            'MIT': ['MIT', 'BSD', 'Apache-2.0', 'ISC'],
            'Apache-2.0': ['MIT', 'BSD', 'Apache-2.0', 'ISC'],
            'GPL-3.0': ['GPL-3.0', 'GPL-2.0'],
            'BSD': ['MIT', 'BSD', 'Apache-2.0', 'ISC']
        }

    def analyze_dependencies(self, file_list: List[str], semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive dependency analysis.

        Args:
            file_list: List of files to analyze
            semantic_data: Semantic analysis results

        Returns:
            Dict containing dependency analysis results
        """
        logger.info("Starting dependency analysis")

        dependency_results = {
            "ecosystems_detected": [],
            "dependencies_found": {},
            "vulnerabilities": [],
            "license_issues": [],
            "outdated_packages": [],
            "dependency_health_score": 100,
            "recommendations": [],
            "dependency_graph": {},
            "maintenance_risks": []
        }

        # Detect package files
        package_files = self._detect_package_files(file_list)

        # Analyze each ecosystem
        for ecosystem, files in package_files.items():
            dependency_results["ecosystems_detected"].append(ecosystem)

            for file_path in files:
                try:
                    deps = self._parse_package_file(file_path, ecosystem)
                    if deps:
                        dependency_results["dependencies_found"][ecosystem] = deps

                        # Check for vulnerabilities
                        vulns = self._check_vulnerabilities(deps, ecosystem)
                        dependency_results["vulnerabilities"].extend(vulns)

                        # Check license compatibility
                        license_issues = self._check_license_compatibility(deps, ecosystem)
                        dependency_results["license_issues"].extend(license_issues)

                        # Check for outdated packages (simplified heuristic)
                        outdated = self._check_outdated_packages(deps, ecosystem)
                        dependency_results["outdated_packages"].extend(outdated)

                except Exception as e:
                    logger.warning(f"Failed to analyze {file_path}: {e}")

        # Calculate dependency health score
        dependency_results["dependency_health_score"] = self._calculate_dependency_health_score(dependency_results)

        # Generate recommendations
        dependency_results["recommendations"] = self._generate_dependency_recommendations(dependency_results)

        # Build dependency graph (simplified)
        dependency_results["dependency_graph"] = self._build_dependency_graph(dependency_results)

        return dependency_results

    def _detect_package_files(self, file_list: List[str]) -> Dict[str, List[str]]:
        """Detect package management files in the repository."""
        package_files = {}

        for file_path in file_list:
            file_name = os.path.basename(file_path)

            for ecosystem, patterns in self.supported_files.items():
                if file_name in patterns:
                    if ecosystem not in package_files:
                        package_files[ecosystem] = []
                    package_files[ecosystem].append(file_path)

        return package_files

    def _parse_package_file(self, file_path: str, ecosystem: str) -> Optional[Dict[str, Any]]:
        """Parse a package file to extract dependencies."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if ecosystem == 'python':
                return self._parse_python_dependencies(content, file_path)
            elif ecosystem == 'javascript':
                return self._parse_javascript_dependencies(content, file_path)
            elif ecosystem == 'java':
                return self._parse_java_dependencies(content, file_path)
            else:
                # Generic parsing for other ecosystems
                return self._parse_generic_dependencies(content, file_path)

        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return None

    def _parse_python_dependencies(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse Python dependency files."""
        dependencies = {"runtime": [], "dev": [], "optional": []}

        if 'requirements.txt' in file_path:
            # Parse requirements.txt
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Extract package name (basic parsing)
                    match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                    if match:
                        dependencies["runtime"].append({
                            "name": match.group(1),
                            "version_spec": line,
                            "source": "requirements.txt"
                        })

        elif 'pyproject.toml' in file_path:
            # Basic TOML parsing for dependencies
            if '[tool.poetry.dependencies]' in content or '[project.dependencies]' in content:
                # This would need proper TOML parsing in production
                dependencies["runtime"].append({
                    "name": "parsed_from_pyproject",
                    "version_spec": "unknown",
                    "source": "pyproject.toml"
                })

        return dependencies

    def _parse_javascript_dependencies(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse JavaScript dependency files."""
        dependencies = {"runtime": [], "dev": [], "optional": []}

        if 'package.json' in file_path:
            try:
                package_data = json.loads(content)

                # Runtime dependencies
                if 'dependencies' in package_data:
                    for name, version in package_data['dependencies'].items():
                        dependencies["runtime"].append({
                            "name": name,
                            "version_spec": version,
                            "source": "package.json"
                        })

                # Dev dependencies
                if 'devDependencies' in package_data:
                    for name, version in package_data['devDependencies'].items():
                        dependencies["dev"].append({
                            "name": name,
                            "version_spec": version,
                            "source": "package.json"
                        })

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in {file_path}")

        return dependencies

    def _parse_java_dependencies(self, content: str, file_path: str) -> Dict[str, Any]:
        """Parse Java dependency files."""
        dependencies = {"runtime": [], "dev": [], "optional": []}

        if 'pom.xml' in file_path:
            # Basic XML parsing for Maven dependencies
            # Look for <dependency> blocks
            dependency_blocks = re.findall(r'<dependency>(.*?)</dependency>', content, re.DOTALL)
            for block in dependency_blocks:
                group_match = re.search(r'<groupId>([^<]+)</groupId>', block)
                artifact_match = re.search(r'<artifactId>([^<]+)</artifactId>', block)
                version_match = re.search(r'<version>([^<]+)</version>', block)

                if group_match and artifact_match:
                    name = f"{group_match.group(1)}:{artifact_match.group(1)}"
                    version = version_match.group(1) if version_match else "unknown"
                    dependencies["runtime"].append({
                        "name": name,
                        "version_spec": version,
                        "source": "pom.xml"
                    })

        return dependencies

    def _parse_generic_dependencies(self, content: str, file_path: str) -> Dict[str, Any]:
        """Generic dependency parsing for unsupported ecosystems."""
        return {"runtime": [], "dev": [], "optional": []}

    def _check_vulnerabilities(self, dependencies: Dict[str, List], ecosystem: str) -> List[Dict]:
        """Check dependencies for known vulnerabilities."""
        vulnerabilities = []

        vuln_db = self.known_vulnerabilities.get(ecosystem, {})

        for dep_type, deps in dependencies.items():
            for dep in deps:
                name = dep["name"].lower()
                if name in vuln_db:
                    # Check if version matches vulnerable range
                    # This is simplified - real implementation would use proper version comparison
                    vulnerabilities.append({
                        "package": dep["name"],
                        "ecosystem": ecosystem,
                        "severity": "high",
                        "description": f"Known vulnerability in {dep['name']}",
                        "affected_versions": vuln_db[name],
                        "current_version": dep.get("version_spec", "unknown"),
                        "source": dep.get("source", "unknown")
                    })

        return vulnerabilities

    def _check_license_compatibility(self, dependencies: Dict[str, List], ecosystem: str) -> List[Dict]:
        """Check for license compatibility issues."""
        license_issues = []

        # This is a simplified check - real implementation would need license data
        for dep_type, deps in dependencies.items():
            for dep in deps:
                # Simulate license checking
                if dep["name"].startswith("gpl") or "gpl" in dep["name"].lower():
                    license_issues.append({
                        "package": dep["name"],
                        "issue": "GPL license may restrict commercial use",
                        "severity": "medium",
                        "ecosystem": ecosystem
                    })

        return license_issues

    def _check_outdated_packages(self, dependencies: Dict[str, List], ecosystem: str) -> List[Dict]:
        """Check for potentially outdated packages."""
        outdated = []

        # Simplified heuristic - packages with version specs that look old
        for dep_type, deps in dependencies.items():
            for dep in deps:
                version_spec = dep.get("version_spec", "")
                if version_spec.startswith("1.") or version_spec.startswith("^1."):
                    outdated.append({
                        "package": dep["name"],
                        "current_spec": version_spec,
                        "issue": "Potentially outdated version specification",
                        "ecosystem": ecosystem
                    })

        return outdated

    def _calculate_dependency_health_score(self, results: Dict) -> float:
        """Calculate overall dependency health score."""
        base_score = 100

        # Deduct points for vulnerabilities
        vuln_count = len(results["vulnerabilities"])
        base_score -= min(vuln_count * 10, 40)

        # Deduct points for license issues
        license_count = len(results["license_issues"])
        base_score -= min(license_count * 5, 20)

        # Deduct points for outdated packages
        outdated_count = len(results["outdated_packages"])
        base_score -= min(outdated_count * 2, 20)

        # Deduct points for missing ecosystems or dependencies
        if not results["ecosystems_detected"]:
            base_score -= 30

        return max(0, base_score)

    def _generate_dependency_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on dependency analysis."""
        recommendations = []

        if results["vulnerabilities"]:
            recommendations.append(f"Address {len(results['vulnerabilities'])} dependency vulnerabilities immediately")

        if results["license_issues"]:
            recommendations.append(f"Review {len(results['license_issues'])} license compatibility issues")

        if results["outdated_packages"]:
            recommendations.append(f"Update {len(results['outdated_packages'])} potentially outdated dependencies")

        if not results["ecosystems_detected"]:
            recommendations.append("No dependency management files detected - consider adding package management")

        if results["dependency_health_score"] < 70:
            recommendations.append("Overall dependency health is poor - comprehensive dependency audit recommended")

        return recommendations

    def _build_dependency_graph(self, results: Dict) -> Dict[str, Any]:
        """Build a simplified dependency graph."""
        graph = {"nodes": [], "edges": []}

        for ecosystem, deps in results["dependencies_found"].items():
            for dep_type, dep_list in deps.items():
                for dep in dep_list:
                    graph["nodes"].append({
                        "id": f"{ecosystem}:{dep['name']}",
                        "label": dep["name"],
                        "ecosystem": ecosystem,
                        "type": dep_type
                    })

        return graph


def analyze_dependencies(file_list: List[str], semantic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze dependencies for security, license, and maintenance issues.

    Args:
        file_list: List of files to analyze
        semantic_data: Semantic analysis results

    Returns:
        Dict containing dependency analysis results
    """
    analyzer = DependencyAnalyzer()
    return analyzer.analyze_dependencies(file_list, semantic_data)