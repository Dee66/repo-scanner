"""Governance signal analysis stage for Repository Intelligence Scanner."""

import os
from pathlib import Path
from typing import Dict, List, Set


def analyze_governance_signals(file_list: List[str], structure: Dict, semantic: Dict, test_signals: Dict) -> Dict:
    """Analyze governance and compliance signals in the repository."""
    governance = {
        "code_quality_governance": assess_code_quality_governance(file_list),
        "security_governance": assess_security_governance(file_list),
        "ci_cd_governance": assess_ci_cd_governance(file_list),
        "documentation_governance": assess_documentation_governance(file_list),
        "dependency_governance": assess_dependency_governance(file_list),
        "compliance_artifacts": identify_compliance_artifacts(file_list),
        "governance_maturity_score": calculate_governance_maturity(file_list, structure),
        "governance_gaps": identify_governance_gaps(file_list, structure)
    }
    
    return governance


def assess_code_quality_governance(file_list: List[str]) -> Dict:
    """Assess code quality governance tools and practices."""
    quality = {
        "linters": [],
        "formatters": [],
        "static_analyzers": [],
        "pre_commit_hooks": False,
        "code_quality_config_files": []
    }
    
    # Python linters and tools
    python_tools = {
        "pylint": "linters",
        "flake8": "linters", 
        "black": "formatters",
        "isort": "formatters",
        "mypy": "static_analyzers",
        "bandit": "static_analyzers",
        "safety": "static_analyzers"
    }
    
    for tool, category in python_tools.items():
        if any(tool.lower() in f.lower() for f in file_list):
            quality[category].append(tool)
    
    # Configuration files
    config_files = [
        ".pylintrc", "setup.cfg", "pyproject.toml", "tox.ini",
        ".flake8", ".pre-commit-config.yaml", ".prettierrc",
        "eslint.config.js", "tsconfig.json"
    ]
    
    for config in config_files:
        if any(config in f for f in file_list):
            quality["code_quality_config_files"].append(config)
    
    # Pre-commit hooks
    if any(".pre-commit-config" in f for f in file_list):
        quality["pre_commit_hooks"] = True
    
    return quality


def assess_security_governance(file_list: List[str]) -> Dict:
    """Assess security governance practices."""
    security = {
        "security_scanners": [],
        "vulnerability_management": [],
        "secret_scanning": False,
        "security_policies": [],
        "has_security_md": False
    }
    
    # Security tools
    security_tools = [
        "bandit", "safety", "trivy", "snyk", "owasp", "dependabot",
        "sonar", "checkov", "semgrep", "codeql"
    ]
    
    for tool in security_tools:
        if any(tool.lower() in f.lower() for f in file_list):
            security["security_scanners"].append(tool)
    
    # Security files
    security_files = [
        "SECURITY.md", ".secrets", "security.txt",
        ".github/security", "security-policy.md"
    ]
    
    for sec_file in security_files:
        if any(sec_file.lower() in f.lower() for f in file_list):
            security["security_policies"].append(sec_file)
            if "security.md" in sec_file.lower():
                security["has_security_md"] = True
    
    # Secret scanning
    if any("secret" in f.lower() or "credential" in f.lower() for f in file_list):
        security["secret_scanning"] = True
    
    return security


def assess_ci_cd_governance(file_list: List[str]) -> Dict:
    """Assess CI/CD governance and automation."""
    ci_cd = {
        "ci_platforms": [],
        "ci_config_files": [],
        "automation_scripts": [],
        "has_ci_cd": False,
        "build_automation": []
    }
    
    # CI platforms and files
    ci_patterns = {
        ".github/workflows": "GitHub Actions",
        ".gitlab-ci.yml": "GitLab CI",
        "Jenkinsfile": "Jenkins",
        "azure-pipelines.yml": "Azure DevOps",
        "bitbucket-pipelines.yml": "Bitbucket Pipelines",
        ".travis.yml": "Travis CI",
        "circle.yml": "CircleCI"
    }
    
    for pattern, platform in ci_patterns.items():
        if any(pattern in f for f in file_list):
            ci_cd["ci_platforms"].append(platform)
            ci_cd["ci_config_files"].append(pattern)
            ci_cd["has_ci_cd"] = True
    
    # Build automation
    build_files = ["Makefile", "build.gradle", "pom.xml", "package.json", "Dockerfile"]
    for build_file in build_files:
        if any(build_file in f for f in file_list):
            ci_cd["build_automation"].append(build_file)
    
    # Automation scripts
    script_patterns = ["scripts/", "tools/", ".sh", ".ps1", ".bat"]
    for pattern in script_patterns:
        if any(pattern in f for f in file_list):
            ci_cd["automation_scripts"].append(pattern)
    
    return ci_cd


def assess_documentation_governance(file_list: List[str]) -> Dict:
    """Assess documentation governance and standards."""
    docs = {
        "readme_files": [],
        "contributing_guide": False,
        "code_of_conduct": False,
        "license_file": False,
        "changelog": False,
        "api_docs": False,
        "documentation_tools": []
    }
    
    # Standard documentation files
    doc_files = {
        "README": "readme_files",
        "CONTRIBUTING": "contributing_guide",
        "CODE_OF_CONDUCT": "code_of_conduct", 
        "LICENSE": "license_file",
        "CHANGELOG": "changelog"
    }
    
    for doc_pattern, key in doc_files.items():
        found = any(doc_pattern in f.upper() for f in file_list)
        if key == "readme_files":
            if found:
                docs[key].extend([f for f in file_list if doc_pattern in f.upper()])
        else:
            docs[key] = found
    
    # API documentation
    api_patterns = ["docs/", "api.md", "swagger", "openapi"]
    docs["api_docs"] = any(any(p in f.lower() for p in api_patterns) for f in file_list)
    
    # Documentation tools
    doc_tools = ["sphinx", "mkdocs", "docusaurus", "gitbook", "readthedocs"]
    for tool in doc_tools:
        if any(tool.lower() in f.lower() for f in file_list):
            docs["documentation_tools"].append(tool)
    
    return docs


def assess_dependency_governance(file_list: List[str]) -> Dict:
    """Assess dependency management and governance."""
    deps = {
        "dependency_files": [],
        "lock_files": [],
        "has_dependency_management": False,
        "has_lock_files": False,
        "dependency_scanning": False
    }
    
    # Dependency files by language
    dep_files = {
        "requirements.txt": "Python",
        "pyproject.toml": "Python",
        "Pipfile": "Python",
        "poetry.lock": "Python",
        "package.json": "Node.js",
        "yarn.lock": "Node.js",
        "package-lock.json": "Node.js",
        "Gemfile": "Ruby",
        "Gemfile.lock": "Ruby",
        "Cargo.toml": "Rust",
        "Cargo.lock": "Rust",
        "pom.xml": "Java",
        "build.gradle": "Java"
    }
    
    for dep_file, lang in dep_files.items():
        if any(dep_file in f for f in file_list):
            deps["dependency_files"].append({"file": dep_file, "language": lang})
            deps["has_dependency_management"] = True
    
    # Lock files
    lock_files = ["requirements-lock.txt", "poetry.lock", "yarn.lock", "package-lock.json", 
                  "Gemfile.lock", "Cargo.lock", "gradle.lockfile"]
    
    for lock_file in lock_files:
        if any(lock_file in f for f in file_list):
            deps["lock_files"].append(lock_file)
            deps["has_lock_files"] = True
    
    # Dependency scanning
    if any("dependabot" in f.lower() or "renovate" in f.lower() for f in file_list):
        deps["dependency_scanning"] = True
    
    return deps


def identify_compliance_artifacts(file_list: List[str]) -> List[Dict]:
    """Identify compliance and regulatory artifacts."""
    compliance = []
    
    # Common compliance artifacts
    compliance_files = {
        "LICENSE": {"type": "license", "compliance": "open_source"},
        "COPYING": {"type": "license", "compliance": "open_source"},
        "NOTICE": {"type": "legal_notice", "compliance": "legal"},
        "PATENTS": {"type": "patent_notice", "compliance": "intellectual_property"},
        "DCO": {"type": "developer_certificate", "compliance": "contribution"},
        "CLA": {"type": "contributor_license", "compliance": "contribution"}
    }
    
    for file_pattern, info in compliance_files.items():
        if any(file_pattern in f.upper() for f in file_list):
            compliance.append({
                "artifact": file_pattern,
                "type": info["type"],
                "compliance_area": info["compliance"],
                "found": True
            })
    
    return compliance


def calculate_governance_maturity(file_list: List[str], structure: Dict) -> float:
    """Calculate governance maturity score (0-1)."""
    score = 0.0
    max_score = 8.0
    
    # Factor 1: CI/CD presence
    if any(".github/workflows" in f or ".gitlab-ci" in f or "Jenkinsfile" in f for f in file_list):
        score += 1.0
    
    # Factor 2: Code quality tools
    quality_tools = ["pylint", "flake8", "black", "mypy", "pre-commit"]
    if any(any(tool in f.lower() for f in file_list) for tool in quality_tools):
        score += 1.0
    
    # Factor 3: Security practices
    security_indicators = ["SECURITY.md", "dependabot", "bandit", "safety"]
    if any(any(indicator.lower() in f.lower() for f in file_list) for indicator in security_indicators):
        score += 1.0
    
    # Factor 4: Documentation completeness
    doc_files = ["README", "CONTRIBUTING", "LICENSE", "CHANGELOG"]
    doc_score = sum(1 for doc in doc_files if any(doc in f.upper() for f in file_list)) / len(doc_files)
    score += doc_score
    
    # Factor 5: Dependency management
    dep_files = ["requirements.txt", "pyproject.toml", "package.json", "Cargo.toml"]
    if any(any(dep in f for f in file_list) for dep in dep_files):
        score += 1.0
    
    # Factor 6: Testing maturity (from test signals)
    test_maturity = structure.get("test_frameworks", [])
    if len(test_maturity) > 0:
        score += 0.5
    
    # Factor 7: Version control practices
    if any(".gitignore" in f for f in file_list):
        score += 0.5
    
    # Factor 8: Compliance artifacts
    compliance_files = ["LICENSE", "CODE_OF_CONDUCT"]
    if any(any(comp in f.upper() for f in file_list) for comp in compliance_files):
        score += 0.5
    
    return min(score / max_score, 1.0)


def identify_governance_gaps(file_list: List[str], structure: Dict) -> List[Dict]:
    """Identify governance gaps and improvement opportunities."""
    gaps = []
    
    # Check for missing CI/CD
    has_ci = any(".github/workflows" in f or ".gitlab-ci" in f or "Jenkinsfile" in f for f in file_list)
    if not has_ci:
        gaps.append({
            "gap_type": "missing_ci_cd",
            "description": "No CI/CD pipeline detected",
            "severity": "high",
            "recommendation": "Implement automated testing and deployment pipelines"
        })
    
    # Check for missing code quality tools
    quality_tools = ["pylint", "flake8", "black", "pre-commit"]
    has_quality = any(any(tool in f.lower() for f in file_list) for tool in quality_tools)
    if not has_quality:
        gaps.append({
            "gap_type": "missing_code_quality",
            "description": "No automated code quality tools detected",
            "severity": "medium",
            "recommendation": "Add linters, formatters, and pre-commit hooks"
        })
    
    # Check for missing security practices
    security_indicators = ["SECURITY.md", "dependabot", "bandit"]
    has_security = any(any(indicator.lower() in f.lower() for f in file_list) for indicator in security_indicators)
    if not has_security:
        gaps.append({
            "gap_type": "missing_security_practices",
            "description": "Limited security governance detected",
            "severity": "high",
            "recommendation": "Add security scanning, dependency updates, and security policy"
        })
    
    # Check for incomplete documentation
    required_docs = ["README", "LICENSE"]
    missing_docs = [doc for doc in required_docs if not any(doc in f.upper() for f in file_list)]
    if missing_docs:
        gaps.append({
            "gap_type": "incomplete_documentation",
            "description": f"Missing documentation: {', '.join(missing_docs)}",
            "severity": "medium",
            "recommendation": "Add comprehensive documentation and legal files"
        })
    
    return gaps