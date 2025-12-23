"""Intent posture classification stage for Repository Intelligence Scanner."""

from typing import Dict, List, Set


def classify_intent_posture(file_list: List[str], structure: Dict, semantic: Dict, 
                           test_signals: Dict, governance: Dict) -> Dict:
    """Classify the intent and posture of the repository."""
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
    
    intent_classification = {
        "primary_intent": classify_primary_intent(file_list, structure, semantic),
        "security_posture": assess_security_posture(file_list, structure, semantic, governance),
        "maturity_classification": classify_maturity_level(structure, test_signals, governance),
        "risk_posture": assess_risk_posture(file_list, structure, semantic, test_signals, governance),
        "development_stage": determine_development_stage(file_list, structure, test_signals),
        "code_patterns": analyze_code_patterns(semantic),
        "intent_confidence": calculate_intent_confidence(structure, semantic, test_signals, governance)
    }
    
    return intent_classification


def classify_primary_intent(file_list: List[str], structure: Dict, semantic: Dict) -> Dict:
    """Classify the primary intent/purpose of the repository."""
    intent_signals = {
        "library": 0,
        "application": 0,
        "tool": 0,
        "framework": 0,
        "research": 0,
        "educational": 0,
        "infrastructure": 0
    }
    
    # Analyze file structure for intent signals
    file_counts = structure.get("file_counts", {})
    
    # Library signals
    if any("__init__.py" in f for f in file_list):
        intent_signals["library"] += 2
    if any("setup.py" in f or "pyproject.toml" in f for f in file_list):
        intent_signals["library"] += 1
    
    # Application signals
    if any("main.py" in f or "__main__.py" in f for f in file_list):
        intent_signals["application"] += 2
    if any("app.py" in f or "application.py" in f for f in file_list):
        intent_signals["application"] += 1
    
    # Tool/CLI signals
    if any("cli" in f.lower() or "command" in f.lower() for f in file_list):
        intent_signals["tool"] += 2
    if "argparse" in str(semantic) or "click" in str(semantic):
        intent_signals["tool"] += 1
    
    # Framework signals
    if file_counts.get("code", 0) > 50 and len([f for f in file_list if "template" in f.lower()]) > 0:
        intent_signals["framework"] += 1
    
    # Research signals
    if any("research" in f.lower() or "experiment" in f.lower() for f in file_list):
        intent_signals["research"] += 2
    if any("notebook" in f.lower() or ".ipynb" in f for f in file_list):
        intent_signals["research"] += 1
    
    # Educational signals
    if any("tutorial" in f.lower() or "example" in f.lower() or "lesson" in f.lower() for f in file_list):
        intent_signals["educational"] += 1
    
    # Infrastructure signals
    if any("docker" in f.lower() or "kubernetes" in f.lower() or "terraform" in f.lower() for f in file_list):
        intent_signals["infrastructure"] += 2
    if any("ci" in f.lower() or "cd" in f.lower() or "pipeline" in f.lower() for f in file_list):
        intent_signals["infrastructure"] += 1
    
    # Determine primary intent
    primary_intent = max(intent_signals.items(), key=lambda x: x[1])
    
    max_score = max(intent_signals.values()) if intent_signals else 0
    return {
        "primary_intent": primary_intent[0],
        "confidence_score": primary_intent[1] / max_score if max_score > 0 else 0,
        "intent_signals": intent_signals,
        "secondary_intents": sorted(intent_signals.items(), key=lambda x: (-x[1], x[0]))[1:3]
    }


def assess_security_posture(file_list: List[str], structure: Dict, semantic: Dict, governance: Dict) -> Dict:
    """Assess the security posture of the repository."""
    security_posture = {
        "overall_posture": "unknown",
        "security_practices_score": 0,
        "vulnerability_indicators": [],
        "security_controls": [],
        "security_recommendations": [],
        "risk_level": "medium"
    }
    
    if not isinstance(governance, dict):
        governance = {}
    
    max_score = 10
    score = 0
    
    # Security governance factors
    security_gov = governance.get("security_governance", {})
    if isinstance(security_gov, dict):
        security_scanners = security_gov.get("security_scanners", [])
        if isinstance(security_scanners, list):
            if security_scanners:
                score += 2
                security_posture["security_controls"].extend(security_scanners)
        
        if security_gov.get("has_security_md"):
            score += 1
            security_posture["security_controls"].append("security_policy")
        
        if security_gov.get("secret_scanning"):
            score += 1
            security_posture["security_controls"].append("secret_scanning")
    
    # Dependency governance
    dep_gov = governance.get("dependency_governance", {})
    if isinstance(dep_gov, dict):
        if dep_gov.get("has_lock_files"):
            score += 1
            security_posture["security_controls"].append("dependency_locking")
        
        if dep_gov.get("dependency_scanning"):
            score += 1
            security_posture["security_controls"].append("dependency_scanning")
    
    # Code quality factors
    code_quality = governance.get("code_quality_governance", {})
    if isinstance(code_quality, dict):
        static_analyzers = code_quality.get("static_analyzers", [])
        if isinstance(static_analyzers, list):
            if static_analyzers:
                score += 1
                security_posture["security_controls"].extend(static_analyzers)
    
    # Test coverage
    test_signals = {}  # We don't have test_signals here, but we can get it from structure or something
    # For now, skip
    
    # CI/CD security
    ci_cd = governance.get("ci_cd_governance", {})
    if isinstance(ci_cd, dict):
        if ci_cd.get("has_ci_cd"):
            score += 1
            security_posture["security_controls"].append("automated_testing")
    
    # Determine overall posture
    security_posture["security_practices_score"] = score / max_score
    
    if score >= 7:
        security_posture["overall_posture"] = "strong"
        security_posture["risk_level"] = "low"
    elif score >= 4:
        security_posture["overall_posture"] = "moderate"
        security_posture["risk_level"] = "medium"
    else:
        security_posture["overall_posture"] = "weak"
        security_posture["risk_level"] = "high"
    
    # Sort lists for determinism
    security_posture["security_recommendations"] = sorted(security_posture["security_recommendations"])
    security_posture["security_controls"] = sorted(security_posture["security_controls"])
    
    return security_posture


def classify_maturity_level(structure: Dict, test_signals: Dict, governance: Dict) -> Dict:
    """Classify the maturity level of the codebase."""
    maturity_factors = {
        "testing_maturity": test_signals.get("testing_maturity_score", 0),
        "governance_maturity": governance.get("governance_maturity_score", 0),
        "code_structure": 0,
        "documentation_completeness": 0
    }
    
    maturity_recommendations = []
    
    # Code structure maturity
    file_counts = structure.get("file_counts", {})
    if file_counts.get("code", 0) > 0:
        test_ratio = file_counts.get("test", 0) / file_counts["code"]
        if test_ratio > 0.5:
            maturity_factors["code_structure"] = 1.0
        elif test_ratio > 0.2:
            maturity_factors["code_structure"] = 0.7
        elif test_ratio > 0.1:
            maturity_factors["code_structure"] = 0.4
    
    # Documentation completeness
    docs_gov = governance.get("documentation_governance", {})
    doc_score = 0
    if docs_gov.get("readme_files"):
        doc_score += 0.3
    if docs_gov.get("contributing_guide"):
        doc_score += 0.2
    if docs_gov.get("license_file"):
        doc_score += 0.2
    if docs_gov.get("code_of_conduct"):
        doc_score += 0.15
    if docs_gov.get("changelog"):
        doc_score += 0.15
    maturity_factors["documentation_completeness"] = doc_score
    
    # Overall maturity calculation
    weights = {
        "testing_maturity": 0.3,
        "governance_maturity": 0.3,
        "code_structure": 0.2,
        "documentation_completeness": 0.2
    }
    
    overall_maturity = sum(maturity_factors[k] * weights[k] for k in weights)
    
    # Classify maturity level
    if overall_maturity >= 0.8:
        level = "production_ready"
        description = "Mature, production-ready codebase"
    elif overall_maturity >= 0.6:
        level = "beta"
        description = "Beta-quality, mostly stable"
    elif overall_maturity >= 0.4:
        level = "alpha"
        description = "Alpha-quality, functional but incomplete"
    elif overall_maturity >= 0.2:
        level = "prototype"
        description = "Prototype or proof-of-concept"
    else:
        level = "experimental"
        description = "Experimental or early development"
    
    # Sort lists for determinism
    maturity_factors["maturity_recommendations"] = sorted(maturity_recommendations)
    
    return {
        "maturity_level": level,
        "maturity_score": overall_maturity,
        "description": description,
        "maturity_factors": maturity_factors
    }


def assess_risk_posture(file_list: List[str], structure: Dict, semantic: Dict, test_signals: Dict, governance: Dict) -> Dict:
    """Assess the overall risk posture of the repository."""
    risk_factors = {
        "security_risks": 0,
        "quality_risks": 0,
        "maintenance_risks": 0,
        "operational_risks": 0
    }
    
    # Security risks
    security_posture = assess_security_posture([], structure, semantic, governance)
    if security_posture["risk_level"] == "high":
        risk_factors["security_risks"] = 3
    elif security_posture["risk_level"] == "medium":
        risk_factors["security_risks"] = 2
    else:
        risk_factors["security_risks"] = 1
    
    # Quality risks
    test_maturity = test_signals.get("testing_maturity_score", 0)
    if test_maturity < 0.3:
        risk_factors["quality_risks"] = 3
    elif test_maturity < 0.6:
        risk_factors["quality_risks"] = 2
    else:
        risk_factors["quality_risks"] = 1
    
    # Maintenance risks
    gov_maturity = governance.get("governance_maturity_score", 0)
    if gov_maturity < 0.4:
        risk_factors["maintenance_risks"] = 3
    elif gov_maturity < 0.7:
        risk_factors["maintenance_risks"] = 2
    else:
        risk_factors["maintenance_risks"] = 1
    
    # Operational risks
    ci_cd = governance.get("ci_cd_governance", {})
    if not ci_cd.get("has_ci_cd"):
        risk_factors["operational_risks"] = 2
    
    total_risk_score = sum(risk_factors.values())
    
    if total_risk_score >= 10:
        overall_risk = "high"
    elif total_risk_score >= 6:
        overall_risk = "medium"
    else:
        overall_risk = "low"
    
    return {
        "overall_risk_level": overall_risk,
        "risk_score": total_risk_score,
        "risk_factors": risk_factors,
        "risk_mitigation_suggestions": generate_risk_mitigations(risk_factors)
    }


def determine_development_stage(file_list: List[str], structure: Dict, test_signals: Dict) -> Dict:
    """Determine the development stage of the project."""
    stage_indicators = {
        "concept": 0,
        "development": 0,
        "testing": 0,
        "stabilization": 0,
        "production": 0
    }
    
    # Concept stage indicators
    if len(file_list) < 10:
        stage_indicators["concept"] += 2
    if any("readme" in f.lower() for f in file_list if "readme" in f.lower()):
        stage_indicators["concept"] += 1
    
    # Development stage indicators
    test_maturity = test_signals.get("testing_maturity_score", 0)
    if 0.2 < test_maturity < 0.6:
        stage_indicators["development"] += 2
    if len([f for f in file_list if "todo" in f.lower() or "fixme" in f.lower()]) > 0:
        stage_indicators["development"] += 1
    
    # Testing stage indicators
    if test_maturity >= 0.6:
        stage_indicators["testing"] += 2
    test_gaps = test_signals.get("test_gaps", [])
    if len(test_gaps) == 0:
        stage_indicators["testing"] += 1
    
    # Stabilization stage indicators
    if test_maturity >= 0.7:
        stage_indicators["stabilization"] += 2
    gov_gaps = structure.get("governance_gaps", [])
    if len(gov_gaps) <= 1:
        stage_indicators["stabilization"] += 1
    
    # Production stage indicators
    if test_maturity >= 0.8:
        stage_indicators["production"] += 2
    if len(gov_gaps) == 0:
        stage_indicators["production"] += 1
    
    # Determine primary stage
    primary_stage = max(stage_indicators.items(), key=lambda x: x[1])
    
    stage_descriptions = {
        "concept": "Early concept or planning phase",
        "development": "Active development with basic functionality",
        "testing": "Core functionality complete, focus on testing",
        "stabilization": "Bug fixing and stabilization",
        "production": "Production-ready with comprehensive practices"
    }
    
    return {
        "development_stage": primary_stage[0],
        "stage_confidence": primary_stage[1] / max(stage_indicators.values()) if stage_indicators else 0,
        "stage_description": stage_descriptions.get(primary_stage[0], "Unknown"),
        "stage_indicators": stage_indicators
    }


def analyze_code_patterns(semantic: Dict) -> Dict:
    """Analyze code patterns for security and quality indicators."""
    patterns = {
        "security_patterns": [],
        "quality_patterns": [],
        "architecture_patterns": []
    }
    
    python_analysis = semantic.get("python_analysis", {})
    if not isinstance(python_analysis, dict):
        python_analysis = {}
    
    imports = python_analysis.get("imports", [])
    if not isinstance(imports, list):
        imports = []
    
    # Security patterns
    security_imports = ["cryptography", "hashlib", "secrets", "ssl", "jwt"]
    for imp in security_imports:
        if any(imp in i for i in imports):
            patterns["security_patterns"].append(f"uses_{imp}")
    
    # Quality patterns
    quality_indicators = ["typing", "dataclasses", "pydantic", "loguru", "structlog"]
    for indicator in quality_indicators:
        if any(indicator in i for i in imports):
            patterns["quality_patterns"].append(f"uses_{indicator}")
    
    # Architecture patterns
    arch_patterns = ["fastapi", "flask", "django", "click", "typer"]
    for pattern in arch_patterns:
        if any(pattern in i for i in imports):
            patterns["architecture_patterns"].append(f"web_framework_{pattern}")
    
    return patterns


def calculate_intent_confidence(structure: Dict, semantic: Dict, test_signals: Dict, governance: Dict) -> float:
    """Calculate confidence in intent classification."""
    confidence_factors = []
    
    # Structure clarity
    file_counts = structure.get("file_counts", {})
    total_files = file_counts.get("total", 0)
    if total_files > 20:
        confidence_factors.append(0.8)
    elif total_files > 10:
        confidence_factors.append(0.6)
    else:
        confidence_factors.append(0.4)
    
    # Semantic clarity
    python_analysis = semantic.get("python_analysis", {})
    if python_analysis.get("total_functions", 0) > 10:
        confidence_factors.append(0.9)
    elif python_analysis.get("total_functions", 0) > 5:
        confidence_factors.append(0.7)
    else:
        confidence_factors.append(0.5)
    
    # Governance clarity
    gov_maturity = governance.get("governance_maturity_score", 0)
    confidence_factors.append(0.5 + (gov_maturity * 0.5))
    
    # Test clarity
    test_maturity = test_signals.get("testing_maturity_score", 0)
    confidence_factors.append(0.5 + (test_maturity * 0.5))
    
    return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0


def generate_risk_mitigations(risk_factors: Dict) -> List[str]:
    """Generate risk mitigation suggestions based on risk factors."""
    mitigations = []
    
    if risk_factors.get("security_risks", 0) >= 2:
        mitigations.extend([
            "Implement automated security scanning",
            "Add security policy and disclosure guidelines",
            "Use dependency scanning tools"
        ])
    
    if risk_factors.get("quality_risks", 0) >= 2:
        mitigations.extend([
            "Increase test coverage to at least 70%",
            "Add code quality tools (linters, formatters)",
            "Implement code review processes"
        ])
    
    if risk_factors.get("maintenance_risks", 0) >= 2:
        mitigations.extend([
            "Add comprehensive documentation",
            "Implement CI/CD pipelines",
            "Establish contribution guidelines"
        ])
    
    if risk_factors.get("operational_risks", 0) >= 2:
        mitigations.extend([
            "Set up automated testing and deployment",
            "Add monitoring and logging",
            "Implement proper error handling"
        ])
    
    return sorted(list(set(mitigations)))  # Remove duplicates and sort for determinism