"""Decision Artifact Generation for Repository Intelligence Scanner."""

from typing import Dict, List


def generate_decision_artifacts(file_list: List[str], structure: Dict, semantic: Dict,
                               test_signals: Dict, governance: Dict, intent_posture: Dict,
                               misleading_signals: Dict, safe_change_surface: Dict,
                               risk_synthesis: Dict, bounty_context: Dict = None) -> Dict:
    """Generate decision-making artifacts based on comprehensive analysis."""
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
    if not isinstance(risk_synthesis, dict):
        risk_synthesis = {}
    if bounty_context is None:
        bounty_context = {}

    # Generate decision framework
    decision_framework = _generate_decision_framework(risk_synthesis)

    # Generate action plan
    action_plan = _generate_action_plan(risk_synthesis, safe_change_surface)

    # Determine authority ceiling
    authority_ceiling = _determine_authority_ceiling(risk_synthesis, intent_posture)

    # Generate confidence assessment
    confidence_assessment = _generate_confidence_assessment(risk_synthesis)

    # Generate next steps
    next_steps = _generate_next_steps(decision_framework, action_plan)

    # Generate bounty-specific artifacts if bounty context provided
    bounty_artifacts = {}
    if bounty_context:
        bounty_artifacts = _generate_bounty_artifacts(risk_synthesis, intent_posture,
                                                    governance, bounty_context)

    result = {
        "decision_framework": decision_framework,
        "action_plan": action_plan,
        "authority_ceiling": authority_ceiling,
        "confidence_assessment": confidence_assessment,
        "next_steps": next_steps,
        "decision_timestamp": "2025-01-01T00:00:00Z",  # Fixed timestamp for determinism
        "decision_version": "1.0.0"
    }

    # Add bounty artifacts if present
    if bounty_artifacts:
        result["bounty_artifacts"] = bounty_artifacts

    return result


def _generate_decision_framework(risk_synthesis: Dict) -> Dict:
    """Generate the decision framework based on risk assessment."""
    overall_risk = risk_synthesis.get("overall_risk_assessment", {})
    component_risks = risk_synthesis.get("component_risks", {})
    critical_issues = risk_synthesis.get("critical_issues", [])

    risk_level = overall_risk.get("overall_risk_level", "unknown")

    # Decision framework based on risk level
    if risk_level == "high":
        framework = {
            "decision_type": "conservative",
            "authority_required": "senior_technical_lead",
            "approval_gates": ["security_review", "architecture_review", "testing_review"],
            "timeframe": "extended_review_period",
            "rationale": "High risk requires careful consideration and multiple approvals"
        }
    elif risk_level == "medium":
        framework = {
            "decision_type": "balanced",
            "authority_required": "technical_lead",
            "approval_gates": ["code_review", "testing_review"],
            "timeframe": "standard_review_period",
            "rationale": "Medium risk requires standard oversight and review processes"
        }
    else:  # low
        framework = {
            "decision_type": "agile",
            "authority_required": "developer",
            "approval_gates": ["peer_review"],
            "timeframe": "rapid_deployment",
            "rationale": "Low risk allows for streamlined decision making"
        }

    # Adjust for critical issues
    if critical_issues:
        framework["decision_type"] = "conservative"
        framework["authority_required"] = "senior_technical_lead"
        framework["approval_gates"].append("risk_assessment_review")
        framework["rationale"] = "Critical issues detected - elevated decision framework required"

    return framework


def _generate_action_plan(risk_synthesis: Dict, safe_change_surface: Dict) -> Dict:
    """Generate prioritized action plan based on risks and safe changes."""
    recommendations = risk_synthesis.get("recommendations", [])
    safe_changes = safe_change_surface.get("safe_changes", [])
    unsafe_changes = safe_change_surface.get("unsafe_changes", [])

    # Categorize actions
    immediate_actions = []
    short_term_actions = []
    long_term_actions = []

    # Process recommendations by priority
    for rec in recommendations:
        if isinstance(rec, dict):
            priority = rec.get("priority", "medium")
            action = {
                "description": rec.get("action", ""),
                "category": rec.get("category", ""),
                "rationale": rec.get("rationale", ""),
                "estimated_effort": _estimate_effort(rec)
            }

            if priority == "critical":
                immediate_actions.append(action)
            elif priority == "high":
                short_term_actions.append(action)
            else:
                long_term_actions.append(action)

    # Add safe changes as low-priority actions
    for change in safe_changes[:3]:  # Limit to top 3
        if isinstance(change, str):
            long_term_actions.append({
                "description": change,
                "category": "safe_improvement",
                "rationale": "Safe change that can improve repository health",
                "estimated_effort": "low"
            })

    return {
        "immediate_actions": immediate_actions,
        "short_term_actions": short_term_actions,
        "long_term_actions": long_term_actions,
        "prohibited_actions": unsafe_changes,
        "action_count": len(immediate_actions) + len(short_term_actions) + len(long_term_actions)
    }


def _determine_authority_ceiling(risk_synthesis: Dict, intent_posture: Dict) -> Dict:
    """Determine the maximum authority level for decisions."""
    overall_risk = risk_synthesis.get("overall_risk_assessment", {})
    risk_level = overall_risk.get("overall_risk_level", "low")

    intent_classification = intent_posture.get("intent_classification", {})
    maturity_level = intent_classification.get("maturity_level", "unknown")

    # Base authority on risk and maturity
    if risk_level == "high" or maturity_level in ["experimental", "alpha"]:
        ceiling = {
            "maximum_authority": "senior_architect",
            "decision_scope": "limited_changes_only",
            "oversight_required": True,
            "rationale": "High risk or low maturity requires senior oversight"
        }
    elif risk_level == "medium" or maturity_level == "beta":
        ceiling = {
            "maximum_authority": "technical_lead",
            "decision_scope": "feature_changes_allowed",
            "oversight_required": True,
            "rationale": "Medium risk requires technical lead approval"
        }
    else:
        ceiling = {
            "maximum_authority": "developer",
            "decision_scope": "full_changes_allowed",
            "oversight_required": False,
            "rationale": "Low risk allows developer-level decisions"
        }

    return ceiling


def _generate_confidence_assessment(risk_synthesis: Dict) -> Dict:
    """Generate confidence assessment for the analysis."""
    risk_confidence = risk_synthesis.get("risk_confidence", 0.5)
    overall_risk = risk_synthesis.get("overall_risk_assessment", {})
    component_risks = risk_synthesis.get("component_risks", {})

    # Calculate confidence based on data completeness and consistency
    data_completeness = _assess_data_completeness(component_risks)
    analysis_consistency = _assess_analysis_consistency(component_risks)

    overall_confidence = (risk_confidence + data_completeness + analysis_consistency) / 3

    if overall_confidence >= 0.8:
        confidence_level = "high"
        description = "Strong confidence in analysis results"
    elif overall_confidence >= 0.6:
        confidence_level = "medium"
        description = "Moderate confidence with some uncertainties"
    else:
        confidence_level = "low"
        description = "Limited confidence - additional investigation recommended"

    return {
        "confidence_level": confidence_level,
        "confidence_score": overall_confidence,
        "description": description,
        "confidence_factors": {
            "risk_assessment_confidence": risk_confidence,
            "data_completeness": data_completeness,
            "analysis_consistency": analysis_consistency
        }
    }


def _generate_next_steps(decision_framework: Dict, action_plan: Dict) -> List[Dict]:
    """Generate prioritized next steps based on decision framework and action plan."""
    next_steps = []

    # Immediate next steps based on decision framework
    framework_type = decision_framework.get("decision_type", "balanced")

    if framework_type == "conservative":
        next_steps.append({
            "step": "Schedule senior review meeting",
            "priority": "immediate",
            "owner": "technical_lead",
            "timeframe": "within_24_hours",
            "rationale": "Conservative framework requires senior approval"
        })

    # Action-based next steps
    immediate_actions = action_plan.get("immediate_actions", [])
    if immediate_actions:
        next_steps.append({
            "step": f"Address {len(immediate_actions)} critical issue(s)",
            "priority": "immediate",
            "owner": "assigned_developer",
            "timeframe": "within_1_week",
            "rationale": "Critical issues require immediate attention"
        })

    short_term_actions = action_plan.get("short_term_actions", [])
    if short_term_actions:
        next_steps.append({
            "step": f"Plan {len(short_term_actions)} high-priority improvement(s)",
            "priority": "short_term",
            "owner": "technical_lead",
            "timeframe": "within_2_weeks",
            "rationale": "High-priority items need planning and scheduling"
        })

    # Documentation and communication steps
    next_steps.append({
        "step": "Document findings and share with team",
        "priority": "immediate",
        "owner": "analysis_owner",
        "timeframe": "within_48_hours",
        "rationale": "Team needs to be aware of analysis results"
    })

    return next_steps


def _estimate_effort(recommendation: Dict) -> str:
    """Estimate effort level for a recommendation."""
    category = recommendation.get("category", "")
    action = recommendation.get("action", "").lower()

    # Effort estimation based on category and action
    if "security" in category or "governance" in category:
        if "establish" in action or "implement" in action:
            return "high"
        else:
            return "medium"
    elif "testing" in category:
        if "comprehensive" in action:
            return "high"
        else:
            return "medium"
    elif "code_quality" in category or "structure" in category:
        return "medium"
    else:
        return "low"


def _assess_data_completeness(component_risks: Dict) -> float:
    """Assess completeness of analysis data."""
    required_components = ["structural_risk", "semantic_risk", "testing_risk",
                          "governance_risk", "intent_risk", "misleading_risk", "change_risk", "advanced_code_risk"]

    present_components = sum(1 for comp in required_components if comp in component_risks)
    return present_components / len(required_components)


def _assess_analysis_consistency(component_risks: Dict) -> float:
    """Assess consistency of analysis results."""
    risk_levels = []
    for risk_data in component_risks.values():
        if isinstance(risk_data, dict):
            level = risk_data.get("risk_level", "")
            if level in ["low", "medium", "high"]:
                risk_levels.append({"low": 1, "medium": 2, "high": 3}[level])

    if not risk_levels:
        return 0.5

    # Consistency is higher when risk levels are clustered
    mean_risk = sum(risk_levels) / len(risk_levels)
    variance = sum((r - mean_risk) ** 2 for r in risk_levels) / len(risk_levels)
    consistency = max(0, 1 - variance / 2)  # Normalize variance to 0-1 scale

    return consistency


def _generate_bounty_artifacts(risk_synthesis: Dict, intent_posture: Dict,
                              governance: Dict, bounty_context: Dict) -> Dict:
    """Generate bounty-specific decision artifacts for Algora bounty hunting."""
    # Extract bounty context
    issue_complexity = bounty_context.get("issue_complexity", "medium")
    maintainer_responsiveness = bounty_context.get("maintainer_responsiveness", 0.5)
    codebase_velocity = bounty_context.get("codebase_velocity", 0.5)
    issue_quality_score = bounty_context.get("issue_quality_score", 0.5)

    # Calculate profitability score (0-1 scale)
    profitability_score = _calculate_profitability_score(
        risk_synthesis, issue_complexity, maintainer_responsiveness,
        codebase_velocity, issue_quality_score
    )

    # Assess maintainer compatibility
    maintainer_compatibility = _assess_maintainer_compatibility(
        intent_posture, governance, bounty_context
    )

    # Calculate merge confidence (0-1 scale)
    merge_confidence = _calculate_merge_confidence(
        profitability_score, maintainer_compatibility, risk_synthesis
    )

    # Generate bounty-specific recommendations
    bounty_recommendations = _generate_bounty_recommendations(
        profitability_score, merge_confidence, maintainer_compatibility
    )

    return {
        "profitability_score": profitability_score,
        "maintainer_compatibility": maintainer_compatibility,
        "merge_confidence": merge_confidence,
        "bounty_recommendations": bounty_recommendations,
        "bounty_timestamp": "2025-01-01T00:00:00Z",
        "bounty_version": "1.0.0"
    }


def _calculate_profitability_score(risk_synthesis: Dict, issue_complexity: str,
                                 maintainer_responsiveness: float, codebase_velocity: float,
                                 issue_quality_score: float) -> float:
    """Calculate bounty profitability score using Bayesian probability framework."""
    # Base risk assessment
    overall_risk = risk_synthesis.get("overall_risk_assessment", {})
    risk_level = overall_risk.get("overall_risk_level", "medium")

    # Risk level to numeric conversion
    risk_scores = {"low": 0.9, "medium": 0.6, "high": 0.2}
    base_risk_score = risk_scores.get(risk_level, 0.5)

    # Issue complexity adjustment
    complexity_multipliers = {"low": 1.2, "medium": 1.0, "high": 0.7}
    complexity_score = complexity_multipliers.get(issue_complexity, 1.0)

    # Weighted combination for profitability
    # Weights: risk (40%), complexity (20%), responsiveness (15%), velocity (15%), quality (10%)
    profitability = (
        base_risk_score * 0.4 +
        complexity_score * 0.2 +
        maintainer_responsiveness * 0.15 +
        codebase_velocity * 0.15 +
        issue_quality_score * 0.1
    )

    return min(1.0, max(0.0, profitability))


def _assess_maintainer_compatibility(intent_posture: Dict, governance: Dict,
                                   bounty_context: Dict) -> Dict:
    """Assess compatibility with maintainer preferences and patterns."""
    compatibility_score = 0.5  # Default neutral score
    compatibility_factors = {}

    # Analyze intent posture for maintainer preferences
    maturity_level = intent_posture.get("maturity_classification", {}).get("maturity_level", "unknown")
    development_stage = intent_posture.get("development_stage", "unknown")

    # Maturity compatibility
    if maturity_level in ["stable", "mature"]:
        compatibility_score += 0.2
        compatibility_factors["maturity_alignment"] = "High compatibility with stable codebase"
    elif maturity_level in ["beta", "experimental"]:
        compatibility_score -= 0.1
        compatibility_factors["maturity_alignment"] = "Lower compatibility with experimental codebase"

    # Governance compatibility
    governance_maturity = governance.get("governance_maturity_score", 0.5)
    compatibility_score += (governance_maturity - 0.5) * 0.3
    compatibility_factors["governance_alignment"] = f"Governance maturity: {governance_maturity:.2f}"

    # Code quality standards alignment
    code_quality_governance = governance.get("code_quality_governance", {})
    if code_quality_governance.get("linters") or code_quality_governance.get("formatters"):
        compatibility_score += 0.1
        compatibility_factors["code_quality"] = "Strong code quality standards detected"

    return {
        "compatibility_score": min(1.0, max(0.0, compatibility_score)),
        "compatibility_factors": compatibility_factors,
        "recommended_approach": "conservative" if compatibility_score < 0.6 else "standard"
    }


def _calculate_merge_confidence(profitability_score: float, maintainer_compatibility: Dict,
                               risk_synthesis: Dict) -> float:
    """Calculate confidence in successful bounty merge."""
    compatibility_score = maintainer_compatibility.get("compatibility_score", 0.5)

    # Base confidence from profitability and compatibility
    base_confidence = (profitability_score + compatibility_score) / 2

    # Adjust based on risk synthesis confidence
    risk_confidence = risk_synthesis.get("risk_confidence", 0.5)
    confidence_adjustment = (risk_confidence - 0.5) * 0.2

    final_confidence = base_confidence + confidence_adjustment

    return min(1.0, max(0.0, final_confidence))


def _generate_bounty_recommendations(profitability_score: float, merge_confidence: float,
                                   maintainer_compatibility: Dict) -> List[Dict]:
    """Generate bounty-specific recommendations based on analysis."""
    recommendations = []

    # Profitability-based recommendations
    if profitability_score >= 0.8:
        recommendations.append({
            "priority": "high",
            "action": "pursue_bounty",
            "rationale": f"High profitability score ({profitability_score:.2f}) indicates strong merge potential",
            "confidence": merge_confidence
        })
    elif profitability_score >= 0.6:
        recommendations.append({
            "priority": "medium",
            "action": "evaluate_further",
            "rationale": f"Moderate profitability ({profitability_score:.2f}) - requires additional analysis",
            "confidence": merge_confidence
        })
    else:
        recommendations.append({
            "priority": "low",
            "action": "avoid_bounty",
            "rationale": f"Low profitability score ({profitability_score:.2f}) suggests poor merge prospects",
            "confidence": merge_confidence
        })

    # Compatibility-based recommendations
    compatibility_score = maintainer_compatibility.get("compatibility_score", 0.5)
    if compatibility_score >= 0.7:
        recommendations.append({
            "priority": "medium",
            "action": "align_with_maintainer_preferences",
            "rationale": f"High maintainer compatibility ({compatibility_score:.2f}) - follow established patterns",
            "confidence": 0.8
        })

    return recommendations