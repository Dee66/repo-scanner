"""Misleading Signal Detection for Repository Intelligence Scanner.

Enhanced algorithms for detecting deceptive or misleading signals in repositories
that could indicate poor quality, security risks, or maintenance issues.
"""

import re
import math
from typing import Dict, List, Any, Tuple, Set
from collections import Counter, defaultdict
from datetime import datetime, timedelta


def analyze_misleading_signals(file_list: List[str], structure: Dict, semantic: Dict,
                              test_signals: Dict, governance: Dict, intent_posture: Dict) -> Dict:
    """Analyze repository for misleading or deceptive signals with enhanced algorithms."""
    # Safety checks
    if not isinstance(file_list, list):
        file_list = []
    if not isinstance(structure, dict):
        structure = {}
    if not isinstance(semantic, dict):
        semantic = {}
    if not isinstance(test_signals, dict):
        test_signals = {}
    if not isinstance(governance, dict):
        governance = {}
    if not isinstance(intent_posture, dict):
        intent_posture = {}

    misleading_signals = {
        "code_quality_inconsistencies": [],
        "documentation_discrepancies": [],
        "governance_conflicts": [],
        "intent_mismatches": [],
        "maintenance_indicators": [],
        "security_deceptions": [],
        "dependency_risks": [],
        "architecture_deceptions": [],
        "temporal_anomalies": []
    }

    # Enhanced analysis with multiple detection algorithms
    _detect_code_quality_inconsistencies(file_list, structure, semantic, misleading_signals)
    _detect_documentation_discrepancies(file_list, structure, semantic, misleading_signals)
    _detect_governance_conflicts(governance, misleading_signals)
    _detect_intent_mismatches(file_list, structure, intent_posture, misleading_signals)
    _detect_maintenance_indicators(file_list, structure, test_signals, governance, misleading_signals)
    _detect_security_deceptions(governance, intent_posture, misleading_signals)
    _detect_dependency_risks(structure, semantic, misleading_signals)
    _detect_architecture_deceptions(file_list, structure, semantic, misleading_signals)
    _detect_temporal_anomalies(file_list, structure, misleading_signals)

    # Calculate comprehensive risk scoring
    risk_metrics = _calculate_risk_metrics(misleading_signals, structure, semantic, test_signals, governance)

    return {
        "misleading_signals": misleading_signals,
        "risk_metrics": risk_metrics,
        "overall_assessment": _generate_overall_assessment(risk_metrics),
        "recommendations": _generate_recommendations(misleading_signals, risk_metrics)
    }


def _detect_code_quality_inconsistencies(file_list: List[str], structure: Dict, semantic: Dict,
                                        misleading_signals: Dict) -> None:
    """Detect inconsistencies in code quality signals."""
    code_quality = semantic.get("code_quality_signals", [])
    if not isinstance(code_quality, list):
        code_quality = []

    # Check for mixed complexity levels
    complexities = [signal.get("complexity", 0) for signal in code_quality if isinstance(signal, dict)]
    if complexities:
        max_complexity = max(complexities)
        min_complexity = min(complexities)
        if max_complexity > 20 and min_complexity < 5:
            misleading_signals["code_quality_inconsistencies"].append({
                "type": "mixed_complexity_levels",
                "description": "Repository contains both very simple and very complex functions",
                "severity": "medium",
                "evidence": f"Complexity range: {min_complexity} to {max_complexity}"
            })

    # Check for inconsistent naming patterns
    functions = semantic.get("functions", [])
    if isinstance(functions, list):
        naming_patterns = []
        for func in functions:
            if isinstance(func, dict):
                name = func.get("name", "")
                if "_" in name and name.islower():
                    naming_patterns.append("snake_case")
                elif name[0].isupper() if name else False:
                    naming_patterns.append("camel_case")
                else:
                    naming_patterns.append("other")

        unique_patterns = set(naming_patterns)
        if len(unique_patterns) > 2:
            misleading_signals["code_quality_inconsistencies"].append({
                "type": "inconsistent_naming",
                "description": "Multiple inconsistent naming conventions used",
                "severity": "low",
                "evidence": f"Patterns detected: {', '.join(unique_patterns)}"
            })


def _detect_documentation_discrepancies(file_list: List[str], structure: Dict, semantic: Dict,
                                       misleading_signals: Dict) -> None:
    """Detect discrepancies between documentation and code."""
    documentation = structure.get("documentation", [])
    if not isinstance(documentation, list):
        documentation = []

    file_counts = structure.get("file_counts", {})
    code_files = file_counts.get("code", 0)
    doc_files = file_counts.get("docs", 0)

    # Check for documentation/code ratio mismatch
    if code_files > 50 and doc_files == 0:
        misleading_signals["documentation_discrepancies"].append({
            "type": "missing_documentation",
            "description": "Large codebase with no documentation files",
            "severity": "medium",
            "evidence": f"{code_files} code files, {doc_files} documentation files"
        })

    # Check for README inconsistencies
    readme_files = [f for f in file_list if "readme" in f.lower()]
    if len(readme_files) > 1:
        misleading_signals["documentation_discrepancies"].append({
            "type": "multiple_readmes",
            "description": "Multiple README files may indicate confusion or duplication",
            "severity": "low",
            "evidence": f"Found {len(readme_files)} README files: {readme_files}"
        })


def _detect_governance_conflicts(governance: Dict, misleading_signals: Dict) -> None:
    """Detect conflicts in governance signals."""
    ci_cd = governance.get("ci_cd_governance", {})
    security = governance.get("security_governance", {})

    # Check for CI without security scanning
    if ci_cd.get("has_ci_cd") and not security.get("has_security_scanning"):
        misleading_signals["governance_conflicts"].append({
            "type": "ci_without_security",
            "description": "CI/CD pipeline exists but no security scanning detected",
            "severity": "high",
            "evidence": "CI/CD present, security scanning absent"
        })

    # Check for conflicting license signals
    licenses = governance.get("license_governance", {}).get("detected_licenses", [])
    if isinstance(licenses, list) and len(licenses) > 1:
        misleading_signals["governance_conflicts"].append({
            "type": "multiple_licenses",
            "description": "Multiple licenses detected, may indicate confusion",
            "severity": "medium",
            "evidence": f"Licenses: {', '.join(licenses)}"
        })


def _detect_intent_mismatches(file_list: List[str], structure: Dict, intent_posture: Dict,
                             misleading_signals: Dict) -> None:
    """Detect mismatches between stated intent and actual structure."""
    primary_intent = intent_posture.get("primary_intent", {}).get("primary_intent", "")

    file_counts = structure.get("file_counts", {})
    code_files = file_counts.get("code", 0)
    test_files = file_counts.get("test", 0)

    # Check for library intent but no setup files
    if primary_intent == "library" and not any("setup.py" in f or "pyproject.toml" in f for f in file_list):
        misleading_signals["intent_mismatches"].append({
            "type": "library_without_setup",
            "description": "Classified as library but no setup files found",
            "severity": "medium",
            "evidence": "Primary intent: library, missing setup.py/pyproject.toml"
        })

    # Check for application intent but no entry points
    if primary_intent == "application" and not any("main.py" in f or "__main__.py" in f for f in file_list):
        misleading_signals["intent_mismatches"].append({
            "type": "application_without_entry",
            "description": "Classified as application but no main entry point found",
            "severity": "low",
            "evidence": "Primary intent: application, missing main.py/__main__.py"
        })


def _detect_maintenance_indicators(file_list: List[str], structure: Dict, test_signals: Dict,
                                  governance: Dict, misleading_signals: Dict) -> None:
    """Detect indicators of poor maintenance."""
    # Check for TODO/FIXME comments vs test coverage
    test_maturity = test_signals.get("testing_maturity_score", 0)
    todo_files = [f for f in file_list if "todo" in f.lower() or "fixme" in f.lower()]

    if todo_files and test_maturity < 0.3:
        misleading_signals["maintenance_indicators"].append({
            "type": "todo_without_tests",
            "description": "TODO/FIXME files present but low test coverage",
            "severity": "medium",
            "evidence": f"Test maturity: {test_maturity:.2f}, TODO files: {len(todo_files)}"
        })

    # Check for outdated governance
    ci_cd = governance.get("ci_cd_governance", {})
    if not ci_cd.get("has_ci_cd"):
        misleading_signals["maintenance_indicators"].append({
            "type": "missing_ci_cd",
            "description": "No CI/CD pipeline detected, may indicate poor maintenance",
            "severity": "low",
            "evidence": "CI/CD governance: absent"
        })


def _detect_security_deceptions(governance: Dict, intent_posture: Dict, misleading_signals: Dict) -> None:
    """Detect potentially deceptive security signals."""
    security_posture = intent_posture.get("security_posture", {})
    security_score = security_posture.get("security_practices_score", 0)

    # Check for claimed security but poor practices
    if security_score < 2:
        misleading_signals["security_deceptions"].append({
            "type": "low_security_score",
            "description": "Security practices score is very low",
            "severity": "high",
            "evidence": f"Security score: {security_score}/10",
            "risk_score": 9.0
        })

    # Check for security tools without proper configuration
    security_gov = governance.get("security_governance", {})
    tools = security_gov.get("security_tools", [])
    if isinstance(tools, list) and tools and not security_gov.get("has_security_policy"):
        misleading_signals["security_deceptions"].append({
            "type": "tools_without_policy",
            "description": "Security tools present but no security policy",
            "severity": "medium",
            "evidence": f"Tools: {tools}, Policy: missing",
            "risk_score": 7.0
        })


def _detect_dependency_risks(structure: Dict, semantic: Dict, misleading_signals: Dict) -> None:
    """Detect risky dependency patterns and potential supply chain issues."""
    dependencies = structure.get("dependencies", {})
    if not isinstance(dependencies, dict):
        dependencies = {}

    # Check for extremely high number of dependencies
    total_deps = len(dependencies.get("direct", [])) + len(dependencies.get("transitive", []))
    if total_deps > 100:
        misleading_signals["dependency_risks"].append({
            "type": "excessive_dependencies",
            "description": "Repository has an unusually high number of dependencies",
            "severity": "high",
            "evidence": f"Total dependencies: {total_deps}",
            "risk_score": 8.5
        })

    # Check for outdated dependency patterns
    outdated_deps = dependencies.get("outdated", [])
    if isinstance(outdated_deps, list) and len(outdated_deps) > 5:
        misleading_signals["dependency_risks"].append({
            "type": "many_outdated_dependencies",
            "description": "Many dependencies are significantly outdated",
            "severity": "medium",
            "evidence": f"Outdated dependencies: {len(outdated_deps)}",
            "risk_score": 6.0
        })

    # Check for dependency version conflicts
    conflicts = dependencies.get("conflicts", [])
    if isinstance(conflicts, list) and conflicts:
        misleading_signals["dependency_risks"].append({
            "type": "dependency_conflicts",
            "description": "Dependency version conflicts detected",
            "severity": "high",
            "evidence": f"Conflicts: {len(conflicts)}",
            "risk_score": 9.0
        })


def _detect_architecture_deceptions(file_list: List[str], structure: Dict, semantic: Dict,
                                   misleading_signals: Dict) -> None:
    """Detect architectural deceptions and anti-patterns."""
    file_counts = structure.get("file_counts", {})
    code_files = file_counts.get("code", 0)

    # Check for monolithic structure in large codebases
    if code_files > 200:
        # Look for lack of modular structure
        directories = set()
        for file_path in file_list:
            if "/" in file_path:
                directories.add(file_path.split("/")[0])

        if len(directories) < 3:
            misleading_signals["architecture_deceptions"].append({
                "type": "monolithic_structure",
                "description": "Large codebase with minimal directory structure suggests monolithic architecture",
                "severity": "medium",
                "evidence": f"{code_files} files in {len(directories)} top-level directories",
                "risk_score": 5.5
            })

    # Check for mixed language antipatterns
    language_counts = structure.get("language_distribution", {})
    if isinstance(language_counts, dict) and len(language_counts) > 3:
        misleading_signals["architecture_deceptions"].append({
            "type": "language_soup",
            "description": "Too many programming languages in a single repository",
            "severity": "low",
            "evidence": f"Languages detected: {', '.join(language_counts.keys())}",
            "risk_score": 4.0
        })

    # Check for god object/file antipatterns
    large_files = [f for f in file_list if _estimate_file_size(f) > 5000]  # >5000 lines
    if large_files:
        misleading_signals["architecture_deceptions"].append({
            "type": "large_files",
            "description": "Repository contains unusually large source files",
            "severity": "medium",
            "evidence": f"Large files: {len(large_files)}",
            "risk_score": 6.0
        })


def _detect_temporal_anomalies(file_list: List[str], structure: Dict, misleading_signals: Dict) -> None:
    """Detect temporal anomalies that might indicate deceptive practices."""
    temporal_data = structure.get("temporal_analysis", {})

    # Check for suspicious commit patterns
    commit_patterns = temporal_data.get("commit_patterns", {})
    if isinstance(commit_patterns, dict):
        # Check for burst commits (many commits in short time)
        recent_commits = commit_patterns.get("recent_burst", 0)
        if recent_commits > 50:
            misleading_signals["temporal_anomalies"].append({
                "type": "commit_burst",
                "description": "Unusual burst of recent commits may indicate rushed work or cleanup",
                "severity": "low",
                "evidence": f"Recent commits: {recent_commits}",
                "risk_score": 3.5
            })

    # Check for file age inconsistencies
    file_ages = temporal_data.get("file_age_distribution", {})
    if isinstance(file_ages, dict):
        very_old_files = file_ages.get("very_old", 0)
        very_new_files = file_ages.get("very_new", 0)

        if very_old_files > 0 and very_new_files > very_old_files * 2:
            misleading_signals["temporal_anomalies"].append({
                "type": "age_inconsistency",
                "description": "Many new files alongside old files may indicate inconsistent maintenance",
                "severity": "medium",
                "evidence": f"Old files: {very_old_files}, New files: {very_new_files}",
                "risk_score": 5.0
            })


def _calculate_risk_metrics(misleading_signals: Dict, structure: Dict, semantic: Dict,
                           test_signals: Dict, governance: Dict) -> Dict:
    """Calculate comprehensive risk metrics from detected signals."""
    # Count signals by severity
    severity_counts = {"low": 0, "medium": 0, "high": 0}
    total_risk_score = 0.0
    signal_count = 0

    for category, signals in misleading_signals.items():
        for signal in signals:
            severity = signal.get("severity", "low")
            risk_score = signal.get("risk_score", 1.0)

            severity_counts[severity] += 1
            total_risk_score += risk_score
            signal_count += 1

    # Calculate weighted risk score
    if signal_count > 0:
        average_risk = total_risk_score / signal_count
        # Weight high severity signals more heavily
        weighted_score = (severity_counts["high"] * 3.0 + severity_counts["medium"] * 2.0 + severity_counts["low"] * 1.0) / max(signal_count, 1)
        final_score = min(10.0, (average_risk + weighted_score) / 2)
    else:
        final_score = 0.0

    # Determine risk level
    if final_score >= 7.0:
        risk_level = "critical"
    elif final_score >= 5.0:
        risk_level = "high"
    elif final_score >= 3.0:
        risk_level = "medium"
    elif final_score >= 1.0:
        risk_level = "low"
    else:
        risk_level = "minimal"

    # Calculate confidence in assessment
    confidence = _calculate_assessment_confidence(structure, semantic, test_signals, governance)

    return {
        "overall_risk_score": round(final_score, 2),
        "risk_level": risk_level,
        "signal_counts": {
            "total": signal_count,
            "by_severity": severity_counts
        },
        "assessment_confidence": confidence,
        "risk_factors": _identify_top_risk_factors(misleading_signals)
    }


def _calculate_assessment_confidence(structure: Dict, semantic: Dict, test_signals: Dict,
                                   governance: Dict) -> float:
    """Calculate confidence level in the misleading signal assessment."""
    confidence = 1.0  # Base confidence

    # Reduce confidence if data is incomplete
    if not structure.get("file_counts"):
        confidence *= 0.8
    if not semantic.get("functions"):
        confidence *= 0.9
    if not test_signals:
        confidence *= 0.85
    if not governance:
        confidence *= 0.9

    # Increase confidence with more comprehensive data
    if structure.get("temporal_analysis"):
        confidence *= 1.1
    if semantic.get("code_quality_signals"):
        confidence *= 1.05
    if test_signals.get("testing_maturity_score", 0) > 0.5:
        confidence *= 1.1

    return min(1.0, confidence)


def _identify_top_risk_factors(misleading_signals: Dict) -> List[str]:
    """Identify the top risk factors from detected signals."""
    risk_factors = []

    for category, signals in misleading_signals.items():
        for signal in signals:
            risk_score = signal.get("risk_score", 0)
            if risk_score >= 6.0:  # High risk signals
                risk_factors.append(signal.get("type", "unknown"))

    return risk_factors[:5]  # Top 5 risk factors


def _generate_overall_assessment(risk_metrics: Dict) -> Dict:
    """Generate overall assessment based on risk metrics."""
    risk_level = risk_metrics["risk_level"]
    risk_score = risk_metrics["overall_risk_score"]

    assessments = {
        "minimal": {
            "description": "Repository appears trustworthy with minimal misleading signals",
            "recommendation": "Proceed with standard due diligence",
            "action_required": False
        },
        "low": {
            "description": "Some minor inconsistencies detected but overall trustworthy",
            "recommendation": "Review identified issues before proceeding",
            "action_required": False
        },
        "medium": {
            "description": "Moderate misleading signals suggest caution",
            "recommendation": "Thorough review recommended, consider additional verification",
            "action_required": True
        },
        "high": {
            "description": "Significant misleading signals indicate potential risks",
            "recommendation": "Strong caution advised, extensive verification required",
            "action_required": True
        },
        "critical": {
            "description": "Critical misleading signals suggest high risk",
            "recommendation": "Avoid or conduct comprehensive security audit",
            "action_required": True
        }
    }

    assessment = assessments.get(risk_level, assessments["medium"])
    assessment["risk_score"] = risk_score
    assessment["confidence"] = risk_metrics["assessment_confidence"]

    return assessment


def _generate_recommendations(misleading_signals: Dict, risk_metrics: Dict) -> List[str]:
    """Generate specific recommendations based on detected signals."""
    recommendations = []

    # General recommendations based on risk level
    risk_level = risk_metrics["risk_level"]
    if risk_level in ["high", "critical"]:
        recommendations.append("Conduct comprehensive security audit before use")
        recommendations.append("Review all third-party dependencies for vulnerabilities")
    elif risk_level == "medium":
        recommendations.append("Perform additional code review and testing")
        recommendations.append("Verify dependency security and update status")

    # Specific recommendations based on signal types
    signal_types = set()
    for category, signals in misleading_signals.items():
        for signal in signals:
            signal_types.add(signal.get("type", ""))

    if "ci_without_security" in signal_types:
        recommendations.append("Implement automated security scanning in CI/CD pipeline")
    if "missing_documentation" in signal_types:
        recommendations.append("Add comprehensive documentation and README files")
    if "multiple_licenses" in signal_types:
        recommendations.append("Clarify and consolidate license usage")
    if "excessive_dependencies" in signal_types:
        recommendations.append("Audit and minimize dependency footprint")
    if "monolithic_structure" in signal_types:
        recommendations.append("Consider modular architecture refactoring")

    return recommendations


def _estimate_file_size(file_path: str) -> int:
    """Estimate file size in lines (simplified heuristic)."""
    # This is a rough heuristic - in practice you'd read the actual file
    # For now, we'll use file path patterns to estimate
    if "test" in file_path.lower():
        return 100  # Test files tend to be smaller
    elif "config" in file_path.lower():
        return 50   # Config files are usually small
    elif file_path.endswith(('.py', '.js', '.java', '.cpp', '.c')):
        return 200  # Average source file size
    else:
        return 100  # Default estimate