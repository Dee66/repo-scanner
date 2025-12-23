"""Safe Change Surface Modeling for Repository Intelligence Scanner."""

from typing import Dict, List


def analyze_safe_change_surface(file_list: List[str], structure: Dict, semantic: Dict,
                               test_signals: Dict, governance: Dict, intent_posture: Dict,
                               misleading_signals: Dict) -> Dict:
    """Analyze which parts of the codebase are safe to modify."""
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
    if not isinstance(misleading_signals, dict):
        misleading_signals = {}

    # Analyze different aspects of change safety
    test_coverage_safety = _analyze_test_coverage_safety(test_signals)
    complexity_safety = _analyze_complexity_safety(semantic)
    dependency_safety = _analyze_dependency_safety(semantic, governance)
    critical_path_safety = _analyze_critical_path_safety(file_list, structure, intent_posture)
    documentation_safety = _analyze_documentation_safety(structure, governance)

    # Combine safety assessments
    overall_safety = _calculate_overall_safety(test_coverage_safety, complexity_safety,
                                              dependency_safety, critical_path_safety,
                                              documentation_safety)

    # Generate specific recommendations
    safe_changes = _generate_safe_changes(overall_safety, file_list, structure)
    unsafe_changes = _generate_unsafe_changes(overall_safety, misleading_signals)

    return {
        "overall_change_safety": overall_safety,
        "safety_factors": {
            "test_coverage_safety": test_coverage_safety,
            "complexity_safety": complexity_safety,
            "dependency_safety": dependency_safety,
            "critical_path_safety": critical_path_safety,
            "documentation_safety": documentation_safety
        },
        "safe_changes": safe_changes,
        "unsafe_changes": unsafe_changes,
        "change_confidence": _calculate_change_confidence(overall_safety)
    }


def _analyze_test_coverage_safety(test_signals: Dict) -> Dict:
    """Analyze change safety based on test coverage."""
    testing_maturity = test_signals.get("testing_maturity_score", 0)
    test_gaps = test_signals.get("test_gaps", [])

    if testing_maturity >= 0.8:
        safety_level = "high"
        description = "Excellent test coverage provides strong safety net"
    elif testing_maturity >= 0.6:
        safety_level = "medium"
        description = "Good test coverage with some gaps"
    elif testing_maturity >= 0.3:
        safety_level = "low"
        description = "Limited test coverage increases change risk"
    else:
        safety_level = "very_low"
        description = "Minimal test coverage makes changes highly risky"

    return {
        "safety_level": safety_level,
        "description": description,
        "testing_maturity": testing_maturity,
        "test_gaps_count": len(test_gaps) if isinstance(test_gaps, list) else 0
    }


def _analyze_complexity_safety(semantic: Dict) -> Dict:
    """Analyze change safety based on code complexity."""
    functions = semantic.get("functions", [])
    if not isinstance(functions, list):
        functions = []

    # Analyze function complexity
    complex_functions = []
    simple_functions = []

    for func in functions:
        if isinstance(func, dict):
            complexity = func.get("complexity", 0)
            if complexity > 15:
                complex_functions.append(func)
            elif complexity <= 5:
                simple_functions.append(func)

    total_functions = len(functions)
    complex_ratio = len(complex_functions) / max(total_functions, 1)

    if complex_ratio < 0.1:
        safety_level = "high"
        description = "Low complexity codebase is generally safe to modify"
    elif complex_ratio < 0.3:
        safety_level = "medium"
        description = "Moderate complexity with some high-risk functions"
    else:
        safety_level = "low"
        description = "High complexity increases change risk significantly"

    return {
        "safety_level": safety_level,
        "description": description,
        "complex_functions_count": len(complex_functions),
        "simple_functions_count": len(simple_functions),
        "complexity_ratio": complex_ratio
    }


def _analyze_dependency_safety(semantic: Dict, governance: Dict) -> Dict:
    """Analyze change safety based on dependencies."""
    imports = semantic.get("imports", [])
    if not isinstance(imports, list):
        imports = []

    dependency_gov = governance.get("dependency_governance", {})
    has_lock_files = dependency_gov.get("has_lock_files", False)
    has_vulnerable_deps = dependency_gov.get("has_vulnerable_dependencies", False)

    # Count external vs internal dependencies
    external_deps = [imp for imp in imports if "." in imp and not imp.startswith("src.")]
    internal_deps = [imp for imp in imports if imp.startswith("src.") or "." not in imp]

    dependency_risk = len(external_deps) / max(len(imports), 1)

    if not has_lock_files:
        safety_level = "low"
        description = "No dependency lock files increase change risk"
    elif has_vulnerable_deps:
        safety_level = "low"
        description = "Vulnerable dependencies present"
    elif dependency_risk < 0.3:
        safety_level = "high"
        description = "Low external dependency usage is safer"
    else:
        safety_level = "medium"
        description = "Moderate external dependencies"

    return {
        "safety_level": safety_level,
        "description": description,
        "external_dependencies": len(external_deps),
        "internal_dependencies": len(internal_deps),
        "has_lock_files": has_lock_files,
        "has_vulnerable_deps": has_vulnerable_deps
    }


def _analyze_critical_path_safety(file_list: List[str], structure: Dict, intent_posture: Dict) -> Dict:
    """Analyze change safety for critical paths."""
    primary_intent = intent_posture.get("primary_intent", {}).get("primary_intent", "")

    # Identify critical files based on intent
    critical_files = []

    if primary_intent == "application":
        critical_files.extend([f for f in file_list if "main.py" in f or "__main__.py" in f])
    elif primary_intent == "library":
        critical_files.extend([f for f in file_list if "__init__.py" in f or "setup.py" in f])
    elif primary_intent == "tool":
        critical_files.extend([f for f in file_list if "cli" in f.lower() or "command" in f.lower()])

    # Add configuration files
    config_files = structure.get("configuration", [])
    critical_files.extend(config_files)

    # Add CI/CD files
    ci_files = [f for f in file_list if ".github/workflows" in f or ".gitlab-ci" in f or "ci" in f.lower()]
    critical_files.extend(ci_files)

    critical_ratio = len(set(critical_files)) / max(len(file_list), 1)

    if critical_ratio < 0.1:
        safety_level = "high"
        description = "Few critical files, most changes are safe"
    elif critical_ratio < 0.3:
        safety_level = "medium"
        description = "Moderate number of critical files"
    else:
        safety_level = "low"
        description = "Many critical files increase change risk"

    return {
        "safety_level": safety_level,
        "description": description,
        "critical_files_count": len(set(critical_files)),
        "critical_files": sorted(list(set(critical_files)))[:10],  # Limit for readability
        "critical_ratio": critical_ratio
    }


def _analyze_documentation_safety(structure: Dict, governance: Dict) -> Dict:
    """Analyze change safety based on documentation coverage."""
    documentation = structure.get("documentation", [])
    if not isinstance(documentation, list):
        documentation = []

    file_counts = structure.get("file_counts", {})
    code_files = file_counts.get("code", 0)
    doc_files = file_counts.get("docs", 0)

    doc_coverage = doc_files / max(code_files, 1)

    doc_gov = governance.get("documentation_governance", {})
    has_readme = doc_gov.get("has_readme", False)
    has_api_docs = doc_gov.get("has_api_documentation", False)

    if doc_coverage > 0.5 and has_readme and has_api_docs:
        safety_level = "high"
        description = "Excellent documentation reduces change risk"
    elif doc_coverage > 0.2 and has_readme:
        safety_level = "medium"
        description = "Basic documentation coverage"
    elif has_readme:
        safety_level = "low"
        description = "Minimal documentation increases change risk"
    else:
        safety_level = "very_low"
        description = "No documentation makes changes very risky"

    return {
        "safety_level": safety_level,
        "description": description,
        "doc_files_count": doc_files,
        "doc_coverage_ratio": doc_coverage,
        "has_readme": has_readme,
        "has_api_docs": has_api_docs
    }


def _calculate_overall_safety(test_safety: Dict, complexity_safety: Dict, dependency_safety: Dict,
                             critical_safety: Dict, doc_safety: Dict) -> Dict:
    """Calculate overall change safety score."""
    safety_levels = {
        "very_low": 1,
        "low": 2,
        "medium": 3,
        "high": 4
    }

    factors = [test_safety, complexity_safety, dependency_safety, critical_safety, doc_safety]
    scores = [safety_levels.get(factor.get("safety_level", "low"), 2) for factor in factors]

    average_score = sum(scores) / len(scores)

    if average_score >= 3.5:
        overall_level = "high"
        description = "Generally safe to make changes"
    elif average_score >= 2.5:
        overall_level = "medium"
        description = "Changes require caution and testing"
    elif average_score >= 1.5:
        overall_level = "low"
        description = "Changes are risky, extensive testing required"
    else:
        overall_level = "very_low"
        description = "Changes are highly risky, avoid if possible"

    return {
        "overall_safety_level": overall_level,
        "description": description,
        "average_score": average_score,
        "safety_factors_count": len(factors)
    }


def _generate_safe_changes(overall_safety: Dict, file_list: List[str], structure: Dict) -> List[str]:
    """Generate list of safe changes based on analysis."""
    safe_changes = []

    safety_level = overall_safety.get("overall_safety_level", "low")

    if safety_level in ["high", "medium"]:
        # Suggest safe file types
        test_files = [f for f in file_list if "test" in f.lower() or f.endswith("_test.py")]
        if test_files:
            safe_changes.append("Add or modify test files")

        config_files = structure.get("configuration", [])
        if config_files and safety_level == "high":
            safe_changes.append("Modify configuration files")

        doc_files = [f for f in file_list if f.endswith(('.md', '.rst', '.txt'))]
        if doc_files:
            safe_changes.append("Update documentation")

        if safety_level == "high":
            safe_changes.append("Add new features with comprehensive tests")
            safe_changes.append("Refactor simple functions")

    if not safe_changes:
        safe_changes.append("No safe changes identified - proceed with extreme caution")

    return sorted(safe_changes)


def _generate_unsafe_changes(overall_safety: Dict, misleading_signals: Dict) -> List[str]:
    """Generate list of changes to avoid."""
    unsafe_changes = []

    safety_level = overall_safety.get("overall_safety_level", "low")
    total_misleading = misleading_signals.get("total_misleading_signals", 0)

    if safety_level == "very_low":
        unsafe_changes.append("Avoid all changes - repository is high risk")
    elif safety_level == "low":
        unsafe_changes.append("Avoid modifying core business logic")
        unsafe_changes.append("Avoid changes without extensive testing")

    if total_misleading > 0:
        unsafe_changes.append("Address misleading signals before making changes")

    if safety_level in ["low", "very_low"]:
        unsafe_changes.append("Avoid modifying critical path files")
        unsafe_changes.append("Avoid dependency updates without thorough testing")

    if not unsafe_changes:
        unsafe_changes.append("No specific unsafe changes identified")

    return sorted(unsafe_changes)


def _calculate_change_confidence(overall_safety: Dict) -> float:
    """Calculate confidence in the change safety assessment."""
    # Base confidence on the consistency of safety factors
    # Higher confidence when factors are consistent
    return 0.8  # Placeholder - could be more sophisticated