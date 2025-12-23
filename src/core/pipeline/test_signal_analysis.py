"""Test signal analysis stage for Repository Intelligence Scanner."""

import os
from pathlib import Path
from typing import Dict, List, Set


def analyze_test_signals(file_list: List[str], structure: Dict, semantic: Dict) -> Dict:
    """Analyze testing signals and coverage in the repository."""
    test_analysis = {
        "test_files": identify_test_files(file_list),
        "test_frameworks": detect_test_frameworks_detailed(file_list),
        "test_coverage_signals": assess_test_coverage(file_list, structure, semantic),
        "test_quality_signals": evaluate_test_quality(file_list, semantic),
        "testing_maturity_score": calculate_testing_maturity(structure, semantic),
        "test_gaps": identify_test_gaps(file_list, structure, semantic)
    }
    
    return test_analysis


def identify_test_files(file_list: List[str]) -> Dict:
    """Identify and categorize test files."""
    test_files = {
        "unit_tests": [],
        "integration_tests": [],
        "e2e_tests": [],
        "other_tests": [],
        "total_test_files": 0
    }
    
    for file_path in file_list:
        if is_test_file(file_path):
            test_files["total_test_files"] += 1
            
            if "unit" in file_path.lower() or "test_" in file_path.lower():
                test_files["unit_tests"].append(file_path)
            elif "integration" in file_path.lower() or "int" in file_path.lower():
                test_files["integration_tests"].append(file_path)
            elif "e2e" in file_path.lower() or "end_to_end" in file_path.lower():
                test_files["e2e_tests"].append(file_path)
            else:
                test_files["other_tests"].append(file_path)
    
    return test_files


def is_test_file(file_path: str) -> bool:
    """Determine if a file is a test file."""
    path_lower = file_path.lower()
    
    # Common test file patterns
    test_patterns = [
        "test" in path_lower,
        "spec" in path_lower,
        "_test." in path_lower,
        ".test." in path_lower,
        "tests/" in path_lower,
        "test_" in path_lower
    ]
    
    # Exclude certain directories
    exclude_patterns = [
        "node_modules" in path_lower,
        ".git" in path_lower,
        "__pycache__" in path_lower
    ]
    
    return any(test_patterns) and not any(exclude_patterns)


def detect_test_frameworks_detailed(file_list: List[str]) -> List[Dict]:
    """Detect test frameworks with more detail."""
    frameworks = []
    
    # Python frameworks
    if any("pytest" in f.lower() for f in file_list):
        frameworks.append({
            "framework": "pytest",
            "language": "Python",
            "confidence": "high"
        })
    
    if any("unittest" in f.lower() for f in file_list):
        frameworks.append({
            "framework": "unittest",
            "language": "Python",
            "confidence": "high"
        })
    
    # JavaScript frameworks
    if any("jest" in f.lower() for f in file_list):
        frameworks.append({
            "framework": "Jest",
            "language": "JavaScript",
            "confidence": "high"
        })
    
    if any("mocha" in f.lower() for f in file_list):
        frameworks.append({
            "framework": "Mocha",
            "language": "JavaScript",
            "confidence": "high"
        })
    
    # Look for test configuration files
    config_files = {
        "pytest.ini": "pytest",
        "tox.ini": "tox",
        "jest.config.js": "Jest",
        "karma.conf.js": "Karma"
    }
    
    for config_file, framework in config_files.items():
        if any(config_file in f for f in file_list):
            frameworks.append({
                "framework": framework,
                "language": "Configuration",
                "confidence": "high"
            })
    
    return frameworks


def assess_test_coverage(file_list: List[str], structure: Dict, semantic: Dict) -> Dict:
    """Assess test coverage signals."""
    coverage = {
        "test_to_code_ratio": 0.0,
        "has_coverage_tools": False,
        "coverage_tools": [],
        "test_file_percentage": 0.0,
        "untested_modules": []
    }
    
    file_counts = structure.get("file_counts", {})
    total_code = file_counts.get("code", 0)
    total_test = file_counts.get("test", 0)
    
    if total_code > 0:
        coverage["test_to_code_ratio"] = total_test / total_code
        coverage["test_file_percentage"] = (total_test / (total_code + total_test)) * 100 if (total_code + total_test) > 0 else 0
    
    # Check for coverage tools
    coverage_tools = ["coverage.py", "pytest-cov", "nyc", "istanbul"]
    for tool in coverage_tools:
        if any(tool.lower() in f.lower() for f in file_list):
            coverage["has_coverage_tools"] = True
            coverage["coverage_tools"].append(tool)
    
    # Identify potentially untested modules
    python_analysis = semantic.get("python_analysis", {})
    modules = python_analysis.get("modules", [])
    test_files = [f for f in file_list if is_test_file(f)]
    
    for module in modules:
        module_name = Path(module).stem
        expected_test = f"test_{module_name}.py"
        if not any(expected_test in tf for tf in test_files):
            coverage["untested_modules"].append(module)
    
    return coverage


def evaluate_test_quality(file_list: List[str], semantic: Dict) -> List[Dict]:
    """Evaluate test quality signals."""
    quality_signals = []
    
    python_analysis = semantic.get("python_analysis", {})
    functions = python_analysis.get("functions", [])
    classes = python_analysis.get("classes", [])
    
    # Check for test functions
    test_functions = [f for f in functions if "test" in f["name"].lower()]
    
    if len(test_functions) > 0:
        quality_signals.append({
            "signal": "test_functions_found",
            "count": len(test_functions),
            "quality": "positive"
        })
    
    # Check for test classes
    test_classes = [c for c in classes if "test" in c["name"].lower()]
    
    if len(test_classes) > 0:
        quality_signals.append({
            "signal": "test_classes_found",
            "count": len(test_classes),
            "quality": "positive"
        })
    
    # Check for fixtures/setup methods
    setup_methods = [f for f in functions if "setup" in f["name"].lower() or "teardown" in f["name"].lower()]
    
    if len(setup_methods) > 0:
        quality_signals.append({
            "signal": "test_setup_methods",
            "count": len(setup_methods),
            "quality": "positive"
        })
    
    return quality_signals


def calculate_testing_maturity(structure: Dict, semantic: Dict) -> float:
    """Calculate a testing maturity score (0-1)."""
    score = 0.0
    max_score = 5.0
    
    # Factor 1: Test file ratio
    file_counts = structure.get("file_counts", {})
    test_ratio = file_counts.get("test", 0) / max(file_counts.get("code", 1), 1)
    if test_ratio > 0.5:
        score += 1.0
    elif test_ratio > 0.2:
        score += 0.5
    
    # Factor 2: Test frameworks detected
    test_frameworks = structure.get("test_frameworks", [])
    if len(test_frameworks) > 0:
        score += 1.0
    
    # Factor 3: Test quality signals
    python_analysis = semantic.get("python_analysis", {})
    test_functions = len([f for f in python_analysis.get("functions", []) if "test" in f["name"].lower()])
    if test_functions > 10:
        score += 1.0
    elif test_functions > 0:
        score += 0.5
    
    # Factor 4: Test organization
    if any("tests/" in f for f in structure.get("file_counts", {})):
        score += 1.0
    
    # Factor 5: CI/CD integration (placeholder)
    # This would check for CI files that run tests
    
    return min(score / max_score, 1.0)


def identify_test_gaps(file_list: List[str], structure: Dict, semantic: Dict) -> List[Dict]:
    """Identify gaps in testing coverage."""
    gaps = []
    
    # Check for missing test directories
    has_test_dir = any("test" in f.lower() and os.path.isdir(f) for f in file_list)
    if not has_test_dir:
        gaps.append({
            "gap_type": "missing_test_directory",
            "description": "No dedicated test directory found",
            "severity": "medium"
        })
    
    # Check for low test coverage
    coverage = assess_test_coverage(file_list, structure, semantic)
    if coverage["test_to_code_ratio"] < 0.1:
        gaps.append({
            "gap_type": "low_test_coverage",
            "description": f"Test to code ratio is only {coverage['test_to_code_ratio']:.2f}",
            "severity": "high"
        })
    
    # Check for untested modules
    if len(coverage["untested_modules"]) > 5:
        gaps.append({
            "gap_type": "untested_modules",
            "description": f"{len(coverage['untested_modules'])} modules appear untested",
            "severity": "high"
        })
    
    return gaps