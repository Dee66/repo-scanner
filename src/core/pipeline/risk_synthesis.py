"""Risk Synthesis for Repository Intelligence Scanner."""

from typing import Dict, List


def synthesize_risks(file_list: List[str], structure: Dict, semantic: Dict,
                    test_signals: Dict, governance: Dict, intent_posture: Dict,
                    misleading_signals: Dict, safe_change_surface: Dict, security_analysis: Dict = None,
                    code_comprehension: Dict = None, compliance_analysis: Dict = None, dependency_analysis: Dict = None, code_duplication_analysis: Dict = None, api_analysis: Dict = None, advanced_code_analysis: Dict = None) -> Dict:
    """Synthesize all analysis data into comprehensive risk assessment."""
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
    if not isinstance(safe_change_surface, dict):
        safe_change_surface = {}
    if security_analysis is None:
        security_analysis = {}
    if not isinstance(security_analysis, dict):
        security_analysis = {}
    if code_comprehension is None:
        code_comprehension = {}
    if not isinstance(code_comprehension, dict):
        code_comprehension = {}
    if compliance_analysis is None:
        compliance_analysis = {}
    if not isinstance(compliance_analysis, dict):
        compliance_analysis = {}
    if dependency_analysis is None:
        dependency_analysis = {}
    if not isinstance(dependency_analysis, dict):
        dependency_analysis = {}
    if code_duplication_analysis is None:
        code_duplication_analysis = {}
    if not isinstance(code_duplication_analysis, dict):
        code_duplication_analysis = {}
    if api_analysis is None:
        api_analysis = {}
    if not isinstance(api_analysis, dict):
        api_analysis = {}
    if advanced_code_analysis is None:
        advanced_code_analysis = {}
    if not isinstance(advanced_code_analysis, dict):
        advanced_code_analysis = {}

    # Calculate component risk scores
    structural_risk = _calculate_structural_risk(structure)
    semantic_risk = _calculate_semantic_risk(semantic)
    security_risk = _calculate_security_risk(security_analysis)
    comprehension_risk = _calculate_comprehension_risk(code_comprehension)
    compliance_risk = _calculate_compliance_risk(compliance_analysis)
    dependency_risk = _calculate_dependency_risk(dependency_analysis)
    duplication_risk = _calculate_duplication_risk(code_duplication_analysis)
    api_risk = _calculate_api_risk(api_analysis)
    advanced_code_risk = _calculate_advanced_code_risk(advanced_code_analysis)
    testing_risk = _calculate_testing_risk(test_signals)
    governance_risk = _calculate_governance_risk(governance)
    intent_risk = _calculate_intent_risk(intent_posture)
    misleading_risk = _calculate_misleading_risk(misleading_signals)
    change_risk = _calculate_change_risk(safe_change_surface)

    # Synthesize overall risk
    overall_risk = _synthesize_overall_risk(structural_risk, semantic_risk, security_risk, comprehension_risk, compliance_risk, dependency_risk, duplication_risk, api_risk, advanced_code_risk, testing_risk,
                                           governance_risk, intent_risk, misleading_risk, change_risk)

    # Generate risk-based recommendations
    recommendations = _generate_risk_recommendations(overall_risk, structural_risk, semantic_risk, security_risk,
                                                    comprehension_risk, compliance_risk, dependency_risk, duplication_risk, api_risk, advanced_code_risk, testing_risk, governance_risk, intent_risk,
                                                    misleading_risk, change_risk)

    # Identify critical issues
    critical_issues = _identify_critical_issues(structural_risk, semantic_risk, security_risk, comprehension_risk, compliance_risk, dependency_risk, duplication_risk, api_risk, advanced_code_risk, testing_risk,
                                              governance_risk, intent_risk, misleading_risk, change_risk)

    return {
        "overall_risk_assessment": overall_risk,
        "component_risks": {
            "structural_risk": structural_risk,
            "semantic_risk": semantic_risk,
            "security_risk": security_risk,
            "comprehension_risk": comprehension_risk,
            "compliance_risk": compliance_risk,
            "dependency_risk": dependency_risk,
            "duplication_risk": duplication_risk,
            "api_risk": api_risk,
            "advanced_code_risk": advanced_code_risk,
            "testing_risk": testing_risk,
            "governance_risk": governance_risk,
            "intent_risk": intent_risk,
            "misleading_risk": misleading_risk,
            "change_risk": change_risk
        },
        "recommendations": recommendations,
        "critical_issues": critical_issues,
        "risk_confidence": _calculate_risk_confidence(overall_risk)
    }


def _calculate_structural_risk(structure: Dict) -> Dict:
    """Calculate risk based on repository structure."""
    file_counts = structure.get("file_counts", {})
    total_files = sum(file_counts.values())
    code_files = file_counts.get("code", 0)
    test_files = file_counts.get("test", 0)
    config_files = file_counts.get("config", 0)

    # Risk factors
    risk_score = 0
    risk_factors = []

    # Large codebase without tests
    if code_files > 100 and test_files < code_files * 0.1:
        risk_score += 3
        risk_factors.append("insufficient_test_coverage")

    # Too many configuration files
    if config_files > total_files * 0.3:
        risk_score += 2
        risk_factors.append("excessive_configuration")

    # No clear structure
    if code_files > 50 and len(structure.get("build_systems", [])) == 0:
        risk_score += 2
        risk_factors.append("missing_build_system")

    # Determine risk level
    if risk_score >= 5:
        risk_level = "high"
    elif risk_score >= 3:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "description": f"Structural risk: {risk_level} ({risk_score} points)"
    }


def _calculate_semantic_risk(semantic: Dict) -> Dict:
    """Calculate risk based on code semantics."""
    functions = semantic.get("functions", [])
    imports = semantic.get("imports", [])
    code_quality_signals = semantic.get("code_quality_signals", [])

    risk_score = 0
    risk_factors = []

    # Complex functions
    complex_functions = [f for f in functions if isinstance(f, dict) and f.get("complexity", 0) > 20]
    if len(complex_functions) > len(functions) * 0.2:
        risk_score += 3
        risk_factors.append("high_function_complexity")

    # External dependencies
    external_deps = [imp for imp in imports if isinstance(imp, str) and "." in imp]
    if len(external_deps) > len(imports) * 0.5:
        risk_score += 2
        risk_factors.append("heavy_external_dependencies")

    # Code quality issues
    if len(code_quality_signals) > 10:
        risk_score += 2
        risk_factors.append("code_quality_concerns")

    # Determine risk level
    if risk_score >= 5:
        risk_level = "high"
    elif risk_score >= 3:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "description": f"Semantic risk: {risk_level} ({risk_score} points)"
    }


def _calculate_security_risk(security_analysis: Dict) -> Dict:
    """Calculate risk based on security vulnerabilities."""
    findings = security_analysis.get("security_findings", [])
    summary = security_analysis.get("summary", {})
    risk_assessment = security_analysis.get("risk_assessment", {})

    # Use the risk score from security analysis if available
    if risk_assessment and "risk_score" in risk_assessment:
        security_risk_score = risk_assessment["risk_score"] * 10  # Convert to 0-10 scale
        risk_level = risk_assessment.get("overall_risk", "low")
    else:
        # Fallback calculation based on findings
        security_risk_score = 0
        critical_count = summary.get("critical_findings", 0)
        high_count = summary.get("high_findings", 0)
        medium_count = summary.get("medium_findings", 0)

        security_risk_score = (critical_count * 5) + (high_count * 3) + (medium_count * 1)

        if security_risk_score >= 10:
            risk_level = "critical"
        elif security_risk_score >= 5:
            risk_level = "high"
        elif security_risk_score >= 2:
            risk_level = "medium"
        else:
            risk_level = "low"

    risk_factors = []
    if summary.get("critical_findings", 0) > 0:
        risk_factors.append("critical_security_vulnerabilities")
    if summary.get("high_findings", 0) > 0:
        risk_factors.append("high_security_vulnerabilities")
    if summary.get("findings_per_1000_lines", 0) > 5:
        risk_factors.append("high_vulnerability_density")

    return {
        "risk_level": risk_level,
        "risk_score": min(security_risk_score, 10),  # Cap at 10
        "risk_factors": risk_factors,
        "description": f"Security risk: {risk_level} ({security_risk_score:.1f} points)"
    }


def _calculate_comprehension_risk(code_comprehension: Dict) -> Dict:
    """Calculate risk based on code comprehension analysis."""
    try:
        comprehension_data = code_comprehension.get("comprehension_analysis", {})
        quality_assessment = comprehension_data.get("quality_assessment", {})
        risk_indicators = comprehension_data.get("risk_indicators", [])

        risk_score = 0
        risk_factors = []

        # Quality assessment factors
        maturity = quality_assessment.get("code_maturity", "")
        if maturity == "Complex codebase - may need refactoring":
            risk_score += 3
            risk_factors.append("high_code_complexity")

        if not quality_assessment.get("architecture_consistency", True):
            risk_score += 2
            risk_factors.append("inconsistent_architecture")

        issue_density = quality_assessment.get("issue_density", 0)
        if isinstance(issue_density, (int, float)):
            if issue_density > 2:
                risk_score += 3
                risk_factors.append("high_issue_density")
            elif issue_density > 1:
                risk_score += 1
                risk_factors.append("moderate_issue_density")

        # Risk indicators
        if len(risk_indicators) > 5:
            risk_score += 2
            risk_factors.append("multiple_code_risks")

        # AI analysis availability
        analysis_metadata = code_comprehension.get("analysis_metadata", {})
        if analysis_metadata.get("files_analyzed", 0) == 0:
            risk_score += 2
            risk_factors.append("no_ai_analysis_available")

        # Determine risk level
        if risk_score >= 6:
            risk_level = "high"
        elif risk_score >= 3:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "description": f"Comprehension risk: {risk_level} ({risk_score} points)"
        }
    except Exception as e:
        # Fallback in case of any issues
        return {
            "risk_level": "low",
            "risk_score": 0,
            "risk_factors": ["ai_analysis_error"],
            "description": f"Comprehension risk: low (analysis error: {str(e)})"
        }


def _calculate_testing_risk(test_signals: Dict) -> Dict:
    """Calculate risk based on testing practices."""
    testing_maturity = test_signals.get("testing_maturity_score", 0)
    test_gaps = test_signals.get("test_gaps", [])

    risk_score = 0
    risk_factors = []

    if testing_maturity < 0.3:
        risk_score += 4
        risk_factors.append("very_low_test_maturity")
    elif testing_maturity < 0.6:
        risk_score += 2
        risk_factors.append("low_test_maturity")

    if len(test_gaps) > 3:
        risk_score += 2
        risk_factors.append("multiple_test_gaps")

    # Determine risk level
    if risk_score >= 4:
        risk_level = "high"
    elif risk_score >= 2:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "description": f"Testing risk: {risk_level} ({risk_score} points)"
    }


def _calculate_governance_risk(governance: Dict) -> Dict:
    """Calculate risk based on governance practices."""
    governance_maturity = governance.get("governance_maturity_score", 0)
    security_gov = governance.get("security_governance", {})
    license_gov = governance.get("license_governance", {})

    risk_score = 0
    risk_factors = []

    if governance_maturity < 0.3:
        risk_score += 4
        risk_factors.append("very_low_governance_maturity")
    elif governance_maturity < 0.6:
        risk_score += 2
        risk_factors.append("low_governance_maturity")

    if not security_gov.get("has_security_scanning"):
        risk_score += 2
        risk_factors.append("missing_security_scanning")

    if len(license_gov.get("detected_licenses", [])) > 1:
        risk_score += 1
        risk_factors.append("multiple_licenses")

    # Determine risk level
    if risk_score >= 4:
        risk_level = "high"
    elif risk_score >= 2:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "description": f"Governance risk: {risk_level} ({risk_score} points)"
    }


def _calculate_intent_risk(intent_posture: Dict) -> Dict:
    """Calculate risk based on intent posture."""
    security_posture = intent_posture.get("security_posture", {})
    maturity_classification = intent_posture.get("maturity_classification", {})

    risk_score = 0
    risk_factors = []

    security_score = security_posture.get("security_practices_score", 0)
    if security_score < 3:
        risk_score += 3
        risk_factors.append("low_security_posture")

    maturity_score = maturity_classification.get("maturity_score", 0)
    if maturity_score < 0.3:
        risk_score += 2
        risk_factors.append("low_maturity_level")

    # Determine risk level
    if risk_score >= 4:
        risk_level = "high"
    elif risk_score >= 2:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "description": f"Intent risk: {risk_level} ({risk_score} points)"
    }


def _calculate_misleading_risk(misleading_signals: Dict) -> Dict:
    """Calculate risk based on misleading signals."""
    total_signals = misleading_signals.get("total_misleading_signals", 0)
    overall_risk = misleading_signals.get("overall_misleading_risk", "low")

    risk_score = 0
    risk_factors = []

    if overall_risk == "high":
        risk_score += 4
        risk_factors.append("high_misleading_signals")
    elif overall_risk == "medium":
        risk_score += 2
        risk_factors.append("medium_misleading_signals")

    if total_signals > 5:
        risk_score += 1
        risk_factors.append("multiple_misleading_signals")

    # Determine risk level
    if risk_score >= 4:
        risk_level = "high"
    elif risk_score >= 2:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "description": f"Misleading risk: {risk_level} ({risk_score} points)"
    }


def _calculate_change_risk(safe_change_surface: Dict) -> Dict:
    """Calculate risk based on change safety."""
    overall_safety = safe_change_surface.get("overall_change_safety", {})
    safety_level = overall_safety.get("overall_safety_level", "low")

    risk_score = 0
    risk_factors = []

    if safety_level == "very_low":
        risk_score += 4
        risk_factors.append("very_low_change_safety")
    elif safety_level == "low":
        risk_score += 2
        risk_factors.append("low_change_safety")

    # Determine risk level
    if risk_score >= 4:
        risk_level = "high"
    elif risk_score >= 2:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "risk_factors": risk_factors,
        "description": f"Change risk: {risk_level} ({risk_score} points)"
    }


def _synthesize_overall_risk(structural_risk: Dict, semantic_risk: Dict, security_risk: Dict, comprehension_risk: Dict, compliance_risk: Dict, dependency_risk: Dict, duplication_risk: Dict, api_risk: Dict, advanced_code_risk: Dict, testing_risk: Dict,
                           governance_risk: Dict, intent_risk: Dict, misleading_risk: Dict,
                           change_risk: Dict) -> Dict:
    """Synthesize overall risk from component risks."""
    risk_levels = {
        "low": 1,
        "medium": 2,
        "high": 3
    }

    component_risks = [structural_risk, semantic_risk, security_risk, comprehension_risk, compliance_risk, dependency_risk, duplication_risk, api_risk, advanced_code_risk, testing_risk, governance_risk,
                      intent_risk, misleading_risk, change_risk]

    # Weight the risks (security and testing are most critical)
    weights = {
        "structural_risk": 1,
        "semantic_risk": 1,
        "security_risk": 3,  # Security is highest priority
        "comprehension_risk": 2,  # AI comprehension provides valuable insights
        "compliance_risk": 2,  # Compliance violations have significant impact
        "dependency_risk": 2,  # Dependency health affects security and maintenance
        "duplication_risk": 1,  # Code duplication affects maintainability
        "api_risk": 2,  # API design and security issues have significant impact
        "advanced_code_risk": 2,  # Advanced code analysis reveals complex issues
        "testing_risk": 2,
        "governance_risk": 2,
        "intent_risk": 1,
        "misleading_risk": 1,
        "change_risk": 1
    }

    weighted_sum = 0
    total_weight = 0

    for i, risk in enumerate(component_risks):
        risk_name = list(weights.keys())[i]
        weight = weights[risk_name]
        level_score = risk_levels.get(risk.get("risk_level", "low"), 1)
        weighted_sum += level_score * weight
        total_weight += weight

    average_risk = weighted_sum / total_weight

    if average_risk >= 2.5:
        overall_level = "high"
        description = "High risk - significant concerns across multiple areas"
    elif average_risk >= 1.8:
        overall_level = "medium"
        description = "Medium risk - some concerns requiring attention"
    else:
        overall_level = "low"
        description = "Low risk - generally acceptable for most use cases"

    return {
        "overall_risk_level": overall_level,
        "description": description,
        "average_risk_score": average_risk,
        "risk_components_count": len(component_risks)
    }


def _generate_risk_recommendations(overall_risk: Dict, structural_risk: Dict, semantic_risk: Dict,
                                 security_risk: Dict, comprehension_risk: Dict, compliance_risk: Dict, dependency_risk: Dict, duplication_risk: Dict, api_risk: Dict, advanced_code_risk: Dict, testing_risk: Dict, governance_risk: Dict, intent_risk: Dict,
                                 misleading_risk: Dict, change_risk: Dict) -> List[Dict]:
    """Generate prioritized risk-based recommendations."""
    recommendations = []

    # Critical security recommendations (highest priority)
    if security_risk["risk_level"] in ["critical", "high"]:
        recommendations.append({
            "priority": "critical",
            "category": "security",
            "action": "Address critical security vulnerabilities immediately",
            "rationale": f"Security risk level: {security_risk['risk_level']} - immediate action required"
        })

    # Critical compliance recommendations
    if compliance_risk["risk_level"] == "critical":
        recommendations.append({
            "priority": "critical",
            "category": "compliance",
            "action": "Address critical compliance violations immediately",
            "rationale": "Critical compliance violations pose legal and regulatory risk"
        })

    # Critical dependency recommendations
    if dependency_risk["risk_level"] == "critical":
        recommendations.append({
            "priority": "critical",
            "category": "dependencies",
            "action": "Address critical dependency vulnerabilities immediately",
            "rationale": "Critical dependency issues pose immediate security risk"
        })

    # Critical duplication recommendations
    if duplication_risk["risk_level"] == "critical":
        recommendations.append({
            "priority": "critical",
            "category": "code_quality",
            "action": "Address critical code duplication immediately",
            "rationale": "Critical code duplication indicates severe maintainability issues"
        })

    # High priority recommendations
    if testing_risk["risk_level"] == "high":
        recommendations.append({
            "priority": "critical",
            "category": "testing",
            "action": "Implement comprehensive test suite",
            "rationale": "High testing risk indicates insufficient quality assurance"
        })

    if governance_risk["risk_level"] == "high":
        recommendations.append({
            "priority": "critical",
            "category": "governance",
            "action": "Establish governance framework",
            "rationale": "High governance risk indicates missing critical processes"
        })

    if compliance_risk["risk_level"] == "high":
        recommendations.append({
            "priority": "high",
            "category": "compliance",
            "action": "Address high-severity compliance issues",
            "rationale": "High compliance risk indicates significant standards violations"
        })

    if dependency_risk["risk_level"] == "high":
        recommendations.append({
            "priority": "high",
            "category": "dependencies",
            "action": "Address dependency health issues",
            "rationale": "High dependency risk indicates security and maintenance concerns"
        })

    if duplication_risk["risk_level"] == "high":
        recommendations.append({
            "priority": "high",
            "category": "code_quality",
            "action": "Address high code duplication",
            "rationale": "High duplication risk indicates significant maintainability issues"
        })

    if misleading_risk["risk_level"] == "high":
        recommendations.append({
            "priority": "high",
            "category": "misleading_signals",
            "action": "Address misleading signals before proceeding",
            "rationale": "High misleading signals indicate potential deception or confusion"
        })

    # Medium priority recommendations
    if intent_risk["risk_level"] == "high":
        recommendations.append({
            "priority": "high",
            "category": "intent",
            "action": "Clarify repository intent and posture",
            "rationale": "Unclear intent increases operational risk"
        })

    if semantic_risk["risk_level"] == "high":
        recommendations.append({
            "priority": "medium",
            "category": "code_quality",
            "action": "Refactor complex code and improve quality",
            "rationale": "High semantic risk indicates maintainability issues"
        })

    if change_risk["risk_level"] == "high":
        recommendations.append({
            "priority": "medium",
            "category": "change_safety",
            "action": "Improve change safety through better practices",
            "rationale": "High change risk indicates unsafe modification patterns"
        })

    # Low priority recommendations
    if structural_risk["risk_level"] == "high":
        recommendations.append({
            "priority": "low",
            "category": "structure",
            "action": "Reorganize repository structure",
            "rationale": "Structural issues affect long-term maintainability"
        })

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recommendations.sort(key=lambda x: priority_order.get(x["priority"], 4))

    return recommendations


def _identify_critical_issues(structural_risk: Dict, semantic_risk: Dict, security_risk: Dict, comprehension_risk: Dict, compliance_risk: Dict, dependency_risk: Dict, duplication_risk: Dict, api_risk: Dict, advanced_code_risk: Dict, testing_risk: Dict,
                            governance_risk: Dict, intent_risk: Dict, misleading_risk: Dict,
                            change_risk: Dict) -> List[Dict]:
    """Identify critical issues that require immediate attention."""
    critical_issues = []

    # Security critical issues (highest priority)
    if security_risk["risk_level"] == "critical":
        critical_issues.append({
            "severity": "critical",
            "issue": "Critical security vulnerabilities detected",
            "impact": "Immediate security risk - repository compromised",
            "immediate_action_required": True
        })

    # Compliance critical issues
    if compliance_risk["risk_level"] == "critical":
        critical_issues.append({
            "severity": "critical",
            "issue": "Critical compliance violations detected",
            "impact": "Legal and regulatory risk - immediate remediation required",
            "immediate_action_required": True
        })

    # Dependency critical issues
    if dependency_risk["risk_level"] == "critical":
        critical_issues.append({
            "severity": "critical",
            "issue": "Critical dependency vulnerabilities detected",
            "impact": "Immediate security risk from vulnerable dependencies",
            "immediate_action_required": True
        })

    # Duplication critical issues
    if duplication_risk["risk_level"] == "critical":
        critical_issues.append({
            "severity": "critical",
            "issue": "Critical code duplication detected",
            "impact": "Severe maintainability issues - immediate refactoring required",
            "immediate_action_required": True
        })

    # Check for show-stoppers
    if testing_risk["risk_level"] == "high" and governance_risk["risk_level"] == "high":
        critical_issues.append({
            "severity": "critical",
            "issue": "Fundamental quality and governance gaps",
            "impact": "Repository unsuitable for production use",
            "immediate_action_required": True
        })

    if misleading_risk["risk_level"] == "high":
        critical_issues.append({
            "severity": "high",
            "issue": "Significant misleading signals detected",
            "impact": "Potential security or operational risks",
            "immediate_action_required": True
        })

    if intent_risk["risk_level"] == "high" and change_risk["risk_level"] == "high":
        critical_issues.append({
            "severity": "high",
            "issue": "Unclear intent combined with unsafe change patterns",
            "impact": "High risk of unintended consequences",
            "immediate_action_required": True
        })

    return critical_issues


def _calculate_compliance_risk(compliance_analysis: Dict) -> Dict:
    """Calculate risk based on compliance analysis."""
    try:
        violations = compliance_analysis.get("violations", [])
        overall_score = compliance_analysis.get("overall_compliance_score", 100)

        risk_score = 0
        risk_factors = []

        # Calculate risk based on compliance score
        if overall_score < 70:
            risk_score += 4
            risk_factors.append("low_overall_compliance")
        elif overall_score < 85:
            risk_score += 2
            risk_factors.append("moderate_compliance_issues")

        # Calculate risk based on violation severity
        critical_violations = sum(1 for v in violations if v.get("severity") == "critical")
        high_violations = sum(1 for v in violations if v.get("severity") == "high")

        risk_score += critical_violations * 3  # 3 points per critical violation
        risk_score += high_violations * 2      # 2 points per high violation

        if critical_violations > 0:
            risk_factors.append("critical_compliance_violations")
        if high_violations > 0:
            risk_factors.append("high_severity_compliance_violations")

        # Check for specific high-risk frameworks
        framework_scores = compliance_analysis.get("framework_scores", {})
        owasp_score = framework_scores.get("OWASP", 100)
        if owasp_score < 80:
            risk_score += 2
            risk_factors.append("owasp_compliance_issues")

        security_score = framework_scores.get("Security Best Practices", 100)
        if security_score < 80:
            risk_score += 2
            risk_factors.append("security_best_practice_violations")

        # Determine risk level
        if risk_score >= 8:
            risk_level = "high"
        elif risk_score >= 4:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "risk_score": min(risk_score, 10),  # Cap at 10
            "risk_factors": risk_factors,
            "description": f"Compliance risk: {risk_level} ({risk_score} points)"
        }

    except Exception as e:
        # Fallback for any errors
        return {
            "risk_level": "unknown",
            "risk_score": 0,
            "risk_factors": ["compliance_analysis_error"],
            "description": f"Compliance risk assessment failed: {str(e)}"
        }


def _calculate_dependency_risk(dependency_analysis: Dict) -> Dict:
    """Calculate risk based on dependency analysis."""
    try:
        vulnerabilities = dependency_analysis.get("vulnerabilities", [])
        license_issues = dependency_analysis.get("license_issues", [])
        outdated_packages = dependency_analysis.get("outdated_packages", [])
        health_score = dependency_analysis.get("dependency_health_score", 100)
        ecosystems = dependency_analysis.get("ecosystems_detected", [])

        risk_score = 0
        risk_factors = []

        # Calculate risk based on health score
        if health_score < 50:
            risk_score += 8
            risk_factors.append("very_poor_dependency_health")
        elif health_score < 70:
            risk_score += 5
            risk_factors.append("poor_dependency_health")
        elif health_score < 85:
            risk_score += 2
            risk_factors.append("moderate_dependency_health")

        # Vulnerabilities increase risk significantly
        vuln_count = len(vulnerabilities)
        if vuln_count > 0:
            risk_score += min(vuln_count * 3, 15)  # Max 15 points from vulnerabilities
            risk_factors.append(f"{vuln_count}_vulnerable_dependencies")

        # License issues
        license_count = len(license_issues)
        if license_count > 0:
            risk_score += min(license_count * 2, 10)
            risk_factors.append(f"{license_count}_license_issues")

        # Outdated packages
        outdated_count = len(outdated_packages)
        if outdated_count > 0:
            risk_score += min(outdated_count, 5)
            risk_factors.append(f"{outdated_count}_outdated_packages")

        # No dependency management
        if not ecosystems:
            risk_score += 10
            risk_factors.append("no_dependency_management")

        # Determine risk level
        if risk_score >= 15:
            risk_level = "critical"
            description = f"Critical dependency risk ({risk_score} points)"
        elif risk_score >= 8:
            risk_level = "high"
            description = f"High dependency risk ({risk_score} points)"
        elif risk_score >= 4:
            risk_level = "medium"
            description = f"Medium dependency risk ({risk_score} points)"
        else:
            risk_level = "low"
            description = f"Low dependency risk ({risk_score} points)"

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "description": description
        }

    except Exception as e:
        # Fallback for any errors
        return {
            "risk_level": "unknown",
            "risk_score": 0,
            "risk_factors": ["dependency_analysis_error"],
            "description": f"Dependency risk assessment failed: {str(e)}"
        }


def _calculate_duplication_risk(code_duplication_analysis: Dict) -> Dict:
    """Calculate risk based on code duplication analysis."""
    try:
        duplication_score = code_duplication_analysis.get("duplication_score", 100)
        metrics = code_duplication_analysis.get("duplication_metrics", {})
        severity_breakdown = code_duplication_analysis.get("severity_breakdown", {})

        risk_score = 0
        risk_factors = []

        # Calculate risk based on duplication score (lower score = higher risk)
        if duplication_score < 50:
            risk_score += 8
            risk_factors.append("severe_duplication")
        elif duplication_score < 70:
            risk_score += 5
            risk_factors.append("high_duplication")
        elif duplication_score < 85:
            risk_score += 2
            risk_factors.append("moderate_duplication")

        # Factor in duplicate line ratio
        duplicate_ratio = metrics.get("duplicate_line_ratio", 0)
        if duplicate_ratio > 0.3:
            risk_score += 3
            risk_factors.append("high_duplicate_ratio")
        elif duplicate_ratio > 0.15:
            risk_score += 1
            risk_factors.append("moderate_duplicate_ratio")

        # Factor in severity breakdown
        critical_files = severity_breakdown.get("critical", 0)
        high_files = severity_breakdown.get("high", 0)

        if critical_files > 0:
            risk_score += min(critical_files * 2, 10)
            risk_factors.append(f"{critical_files}_files_critical_duplication")

        if high_files > 0:
            risk_score += min(high_files, 5)
            risk_factors.append(f"{high_files}_files_high_duplication")

        # Factor in clone groups
        largest_clone = metrics.get("largest_clone_group", 0)
        if largest_clone > 10:
            risk_score += 2
            risk_factors.append("large_clone_groups")

        # Determine risk level
        if risk_score >= 12:
            risk_level = "critical"
            description = f"Critical duplication risk ({risk_score} points)"
        elif risk_score >= 6:
            risk_level = "high"
            description = f"High duplication risk ({risk_score} points)"
        elif risk_score >= 3:
            risk_level = "medium"
            description = f"Medium duplication risk ({risk_score} points)"
        else:
            risk_level = "low"
            description = f"Low duplication risk ({risk_score} points)"

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "description": description
        }

    except Exception as e:
        # Fallback for any errors
        return {
            "risk_level": "unknown",
            "risk_score": 0,
            "risk_factors": ["duplication_analysis_error"],
            "description": f"Duplication risk assessment failed: {str(e)}"
        }


def _calculate_api_risk(api_analysis: Dict) -> Dict:
    """Calculate risk based on API analysis."""
    try:
        api_score = api_analysis.get("api_score", 100)
        metrics = api_analysis.get("api_metrics", {})
        security_findings = api_analysis.get("security_findings", [])
        compliance_issues = api_analysis.get("compliance_issues", [])

        risk_score = 0
        risk_factors = []

        # Calculate risk based on API score (lower score = higher risk)
        if api_score < 50:
            risk_score += 8
            risk_factors.append("severe_api_issues")
        elif api_score < 70:
            risk_score += 5
            risk_factors.append("high_api_issues")
        elif api_score < 85:
            risk_score += 2
            risk_factors.append("moderate_api_issues")

        # Factor in security findings
        critical_security = len([f for f in security_findings if f.get("severity") == "critical"])
        high_security = len([f for f in security_findings if f.get("severity") == "high"])

        if critical_security > 0:
            risk_score += min(critical_security * 3, 12)
            risk_factors.append(f"{critical_security}_critical_api_security_issues")

        if high_security > 0:
            risk_score += min(high_security * 2, 8)
            risk_factors.append(f"{high_security}_high_api_security_issues")

        # Factor in compliance issues
        compliance_violations = len(compliance_issues)
        if compliance_violations > 0:
            risk_score += min(compliance_violations, 5)
            risk_factors.append(f"{compliance_violations}_api_compliance_violations")

        # Factor in API design issues
        design_issues = metrics.get("design_issues", 0)
        if design_issues > 5:
            risk_score += 3
            risk_factors.append("poor_api_design")
        elif design_issues > 2:
            risk_score += 1
            risk_factors.append("moderate_api_design_issues")

        # Factor in endpoint coverage
        endpoint_coverage = metrics.get("endpoint_coverage", 1.0)
        if endpoint_coverage < 0.5:
            risk_score += 2
            risk_factors.append("low_api_endpoint_coverage")

        # Determine risk level
        if risk_score >= 12:
            risk_level = "critical"
            description = f"Critical API risk ({risk_score} points)"
        elif risk_score >= 6:
            risk_level = "high"
            description = f"High API risk ({risk_score} points)"
        elif risk_score >= 3:
            risk_level = "medium"
            description = f"Medium API risk ({risk_score} points)"
        else:
            risk_level = "low"
            description = f"Low API risk ({risk_score} points)"

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "description": description
        }

    except Exception as e:
        # Fallback for any errors
        return {
            "risk_level": "unknown",
            "risk_score": 0,
            "risk_factors": ["api_analysis_error"],
            "description": f"API risk assessment failed: {str(e)}"
        }


def _calculate_advanced_code_risk(advanced_code_analysis: Dict) -> Dict:
    """Calculate risk based on advanced code analysis results."""
    try:
        if not advanced_code_analysis:
            return {
                "risk_level": "low",
                "risk_score": 0,
                "risk_factors": [],
                "description": "No advanced code analysis data available"
            }

        risk_score = 0
        risk_factors = []

        # Analyze complexity metrics
        complexity_analysis = advanced_code_analysis.get("complexity_analysis", {})
        for file_path, file_complexity in complexity_analysis.items():
            if isinstance(file_complexity, dict):
                cyclomatic = file_complexity.get("cyclomatic_complexity", 0)
                cognitive = file_complexity.get("cognitive_complexity", 0)

                # High complexity functions
                if cyclomatic > 15:
                    risk_score += 2
                    risk_factors.append(f"high_cyclomatic_complexity_{file_path}")
                elif cyclomatic > 10:
                    risk_score += 1
                    risk_factors.append(f"moderate_cyclomatic_complexity_{file_path}")

                if cognitive > 20:
                    risk_score += 2
                    risk_factors.append(f"high_cognitive_complexity_{file_path}")
                elif cognitive > 15:
                    risk_score += 1
                    risk_factors.append(f"moderate_cognitive_complexity_{file_path}")

        # Analyze control flow issues
        control_flow_analysis = advanced_code_analysis.get("control_flow_analysis", {})
        for file_path, file_control in control_flow_analysis.items():
            if isinstance(file_control, dict):
                avg_complexity = file_control.get("average_function_complexity", 0)
                if avg_complexity > 10:
                    risk_score += 2
                    risk_factors.append(f"complex_control_flow_{file_path}")
                elif avg_complexity > 5:
                    risk_score += 1
                    risk_factors.append(f"moderate_control_flow_{file_path}")

        # Analyze data flow issues
        data_flow_analysis = advanced_code_analysis.get("data_flow_analysis", {})
        for file_path, file_data in data_flow_analysis.items():
            if isinstance(file_data, dict):
                variables = file_data.get("variables", {})
                for var_name, var_info in variables.items():
                    if var_info.get("total_definitions", 0) > 5:
                        risk_score += 1
                        risk_factors.append(f"frequent_variable_redefinition_{file_path}")

        # Analyze advanced insights
        insights = advanced_code_analysis.get("advanced_insights", [])
        for insight in insights:
            if insight.get("severity") == "high":
                risk_score += 3
                risk_factors.append(f"advanced_insight_{insight.get('type', 'unknown')}")
            elif insight.get("severity") == "medium":
                risk_score += 2
                risk_factors.append(f"advanced_insight_{insight.get('type', 'unknown')}")

        # Determine risk level
        if risk_score >= 8:
            risk_level = "high"
        elif risk_score >= 4:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "description": f"Advanced code risk: {risk_level} ({risk_score} points from complexity and flow analysis)"
        }

    except Exception as e:
        return {
            "risk_level": "unknown",
            "risk_score": 0,
            "risk_factors": ["advanced_code_analysis_error"],
            "description": f"Advanced code risk assessment failed: {str(e)}"
        }


def _calculate_risk_confidence(overall_risk: Dict) -> float:
    """Calculate confidence in the risk assessment."""
    # Base confidence on data completeness and consistency
    return 0.85  # Placeholder - could be more sophisticated