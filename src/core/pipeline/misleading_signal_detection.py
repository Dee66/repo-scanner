"""Misleading Signal Detection for Repository Intelligence Scanner."""

from typing import Dict, List


def analyze_misleading_signals(file_list: List[str], structure: Dict, semantic: Dict,
                              test_signals: Dict, governance: Dict, intent_posture: Dict) -> Dict:
    """Analyze repository for misleading or deceptive signals."""
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
        "security_deceptions": []
    }

    # Analyze code quality inconsistencies
    _detect_code_quality_inconsistencies(file_list, structure, semantic, misleading_signals)

    # Analyze documentation discrepancies
    _detect_documentation_discrepancies(file_list, structure, semantic, misleading_signals)

    # Analyze governance conflicts
    _detect_governance_conflicts(governance, misleading_signals)

    # Analyze intent mismatches
    _detect_intent_mismatches(file_list, structure, intent_posture, misleading_signals)

    # Analyze maintenance indicators
    _detect_maintenance_indicators(file_list, structure, test_signals, governance, misleading_signals)

    # Analyze security deceptions
    _detect_security_deceptions(governance, intent_posture, misleading_signals)

    # Calculate overall misleading score
    total_signals = sum(len(signals) for signals in misleading_signals.values())
    overall_risk = "low"
    if total_signals >= 5:
        overall_risk = "high"
    elif total_signals >= 3:
        overall_risk = "medium"

    return {
        "misleading_signals": misleading_signals,
        "total_misleading_signals": total_signals,
        "overall_misleading_risk": overall_risk,
        "requires_caution": total_signals > 0
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
            "evidence": f"Security score: {security_score}/10"
        })

    # Check for security tools without proper configuration
    security_gov = governance.get("security_governance", {})
    tools = security_gov.get("security_tools", [])
    if isinstance(tools, list) and tools and not security_gov.get("has_security_policy"):
        misleading_signals["security_deceptions"].append({
            "type": "tools_without_policy",
            "description": "Security tools present but no security policy",
            "severity": "medium",
            "evidence": f"Tools: {tools}, Policy: missing"
        })