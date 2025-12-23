"""Authority Ceiling Evaluation for Repository Intelligence Scanner."""

from typing import Dict, List


def evaluate_authority_ceiling(file_list: List[str], structure: Dict, semantic: Dict,
                              test_signals: Dict, governance: Dict, intent_posture: Dict,
                              misleading_signals: Dict, safe_change_surface: Dict,
                              risk_synthesis: Dict, decision_artifacts: Dict) -> Dict:
    """Evaluate and potentially adjust authority ceilings based on comprehensive analysis."""
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
    if not isinstance(decision_artifacts, dict):
        decision_artifacts = {}

    # Get current authority ceiling from decision artifacts
    current_ceiling = decision_artifacts.get("authority_ceiling", {})

    # Evaluate authority constraints
    authority_constraints = _evaluate_authority_constraints(risk_synthesis, intent_posture, governance)

    # Assess organizational factors
    organizational_factors = _assess_organizational_factors(structure, intent_posture)

    # Determine final authority ceiling
    final_ceiling = _determine_final_authority_ceiling(current_ceiling, authority_constraints, organizational_factors)

    # Generate authority rationale
    authority_rationale = _generate_authority_rationale(final_ceiling, authority_constraints, organizational_factors)

    # Assess authority confidence
    authority_confidence = _assess_authority_confidence(final_ceiling, decision_artifacts)

    return {
        "final_authority_ceiling": final_ceiling,
        "authority_constraints": authority_constraints,
        "organizational_factors": organizational_factors,
        "authority_rationale": authority_rationale,
        "authority_confidence": authority_confidence,
        "evaluation_timestamp": "2025-12-23T00:00:00Z",  # Placeholder for deterministic timestamp
        "evaluation_version": "1.0.0"
    }


def _evaluate_authority_constraints(risk_synthesis: Dict, intent_posture: Dict, governance: Dict) -> Dict:
    """Evaluate constraints that affect authority levels."""
    overall_risk = risk_synthesis.get("overall_risk_assessment", {})
    risk_level = overall_risk.get("overall_risk_level", "low")

    intent_classification = intent_posture.get("intent_classification", {})
    primary_intent = intent_classification.get("primary_intent", "unknown")

    governance_maturity = governance.get("governance_maturity_score", 0)

    constraints = []

    # Risk-based constraints
    if risk_level == "high":
        constraints.append({
            "constraint_type": "risk_based",
            "severity": "high",
            "description": "High overall risk requires senior authority",
            "authority_minimum": "senior_architect",
            "rationale": "High risk levels demand experienced decision makers"
        })
    elif risk_level == "medium":
        constraints.append({
            "constraint_type": "risk_based",
            "severity": "medium",
            "description": "Medium risk requires technical leadership",
            "authority_minimum": "technical_lead",
            "rationale": "Medium risk needs oversight from experienced technical personnel"
        })

    # Intent-based constraints
    if primary_intent in ["production_service", "infrastructure"]:
        constraints.append({
            "constraint_type": "intent_based",
            "severity": "high",
            "description": "Production/infrastructure code requires higher authority",
            "authority_minimum": "senior_technical_lead",
            "rationale": "Critical systems require senior approval to prevent outages"
        })
    elif primary_intent in ["library", "framework"]:
        constraints.append({
            "constraint_type": "intent_based",
            "severity": "medium",
            "description": "Library/framework changes affect downstream users",
            "authority_minimum": "technical_lead",
            "rationale": "API changes require coordination with dependent systems"
        })

    # Governance-based constraints
    if governance_maturity < 0.4:
        constraints.append({
            "constraint_type": "governance_based",
            "severity": "high",
            "description": "Low governance maturity requires authority elevation",
            "authority_minimum": "senior_technical_lead",
            "rationale": "Weak governance processes increase risk of poor decisions"
        })
    elif governance_maturity < 0.7:
        constraints.append({
            "constraint_type": "governance_based",
            "severity": "medium",
            "description": "Moderate governance requires oversight",
            "authority_minimum": "technical_lead",
            "rationale": "Governance gaps need experienced oversight"
        })

    return {
        "constraints": constraints,
        "constraint_count": len(constraints),
        "highest_severity": max([c.get("severity", "low") for c in constraints], default="low")
    }


def _assess_organizational_factors(structure: Dict, intent_posture: Dict) -> Dict:
    """Assess organizational factors affecting authority."""
    file_counts = structure.get("file_counts", {})
    total_files = sum(file_counts.values())

    intent_classification = intent_posture.get("intent_classification", {})
    maturity_level = intent_classification.get("maturity_level", "unknown")

    factors = []

    # Scale factors
    if total_files > 1000:
        factors.append({
            "factor_type": "scale",
            "impact": "high",
            "description": "Large codebase requires senior authority",
            "authority_implication": "senior_technical_lead",
            "rationale": "Large codebases have complex interactions requiring experienced oversight"
        })
    elif total_files > 100:
        factors.append({
            "factor_type": "scale",
            "impact": "medium",
            "description": "Medium codebase requires technical leadership",
            "authority_implication": "technical_lead",
            "rationale": "Medium codebases need experienced technical guidance"
        })

    # Maturity factors
    if maturity_level in ["experimental", "alpha"]:
        factors.append({
            "factor_type": "maturity",
            "impact": "high",
            "description": "Early-stage project requires senior authority",
            "authority_implication": "senior_architect",
            "rationale": "Experimental projects need architectural guidance for foundation decisions"
        })
    elif maturity_level == "beta":
        factors.append({
            "factor_type": "maturity",
            "impact": "medium",
            "description": "Beta-stage project needs oversight",
            "authority_implication": "technical_lead",
            "rationale": "Beta projects require experienced guidance for stabilization"
        })

    # Team factors (inferred from structure)
    test_ratio = file_counts.get("test", 0) / max(total_files, 1)
    if test_ratio < 0.1:
        factors.append({
            "factor_type": "team_maturity",
            "impact": "medium",
            "description": "Low testing indicates team maturity concerns",
            "authority_implication": "technical_lead",
            "rationale": "Teams with low testing maturity need experienced oversight"
        })

    return {
        "organizational_factors": factors,
        "factor_count": len(factors),
        "highest_impact": max([f.get("impact", "low") for f in factors], default="low")
    }


def _determine_final_authority_ceiling(current_ceiling: Dict, authority_constraints: Dict, organizational_factors: Dict) -> Dict:
    """Determine the final authority ceiling considering all factors."""
    # Authority hierarchy (lower number = higher authority)
    authority_hierarchy = {
        "developer": 5,
        "technical_lead": 4,
        "senior_technical_lead": 3,
        "senior_architect": 2,
        "chief_architect": 1
    }

    # Start with current ceiling
    current_authority = current_ceiling.get("maximum_authority", "developer")
    current_level = authority_hierarchy.get(current_authority, 5)

    # Apply constraints
    final_level = current_level
    applied_constraints = []

    for constraint in authority_constraints.get("constraints", []):
        constraint_authority = constraint.get("authority_minimum", "developer")
        constraint_level = authority_hierarchy.get(constraint_authority, 5)

        if constraint_level < final_level:
            final_level = constraint_level
            applied_constraints.append(constraint)

    # Apply organizational factors
    for factor in organizational_factors.get("organizational_factors", []):
        factor_authority = factor.get("authority_implication", "developer")
        factor_level = authority_hierarchy.get(factor_authority, 5)

        if factor_level < final_level:
            final_level = factor_level
            applied_constraints.append(factor)

    # Convert back to authority name
    authority_names = {v: k for k, v in authority_hierarchy.items()}
    final_authority = authority_names.get(final_level, "developer")

    # Determine decision scope based on final authority
    if final_authority in ["chief_architect", "senior_architect"]:
        decision_scope = "architectural_decisions_only"
        oversight_required = True
    elif final_authority == "senior_technical_lead":
        decision_scope = "major_changes_only"
        oversight_required = True
    elif final_authority == "technical_lead":
        decision_scope = "feature_changes_allowed"
        oversight_required = True
    else:
        decision_scope = "routine_changes_only"
        oversight_required = False

    return {
        "maximum_authority": final_authority,
        "decision_scope": decision_scope,
        "oversight_required": oversight_required,
        "authority_level": final_level,
        "applied_constraints": applied_constraints,
        "constraint_count": len(applied_constraints)
    }


def _generate_authority_rationale(final_ceiling: Dict, authority_constraints: Dict, organizational_factors: Dict) -> Dict:
    """Generate detailed rationale for authority ceiling determination."""
    applied_constraints = final_ceiling.get("applied_constraints", [])
    final_authority = final_ceiling.get("maximum_authority", "developer")

    rationale_parts = []

    if applied_constraints:
        rationale_parts.append(f"Authority elevated to {final_authority.replace('_', ' ')} due to {len(applied_constraints)} constraining factor(s)")

        # Group constraints by type
        constraint_types = {}
        for constraint in applied_constraints:
            ctype = constraint.get("constraint_type", "unknown")
            if ctype not in constraint_types:
                constraint_types[ctype] = []
            constraint_types[ctype].append(constraint)

        for ctype, constraints in constraint_types.items():
            descriptions = [c.get("description", "") for c in constraints]
            rationale_parts.append(f"{ctype.replace('_', ' ').title()}: {', '.join(descriptions)}")
    else:
        rationale_parts.append(f"Standard authority level ({final_authority.replace('_', ' ')}) maintained - no elevation required")

    # Add scope implications
    decision_scope = final_ceiling.get("decision_scope", "unknown")
    oversight = "required" if final_ceiling.get("oversight_required", False) else "not required"

    rationale_parts.append(f"Decision scope limited to {decision_scope.replace('_', ' ')} with oversight {oversight}")

    return {
        "authority_rationale": rationale_parts,
        "rationale_summary": " ".join(rationale_parts),
        "key_factors": [c.get("description", "") for c in applied_constraints[:3]]  # Top 3 factors
    }


def _assess_authority_confidence(final_ceiling: Dict, decision_artifacts: Dict) -> Dict:
    """Assess confidence in the authority ceiling determination."""
    applied_constraints = final_ceiling.get("applied_constraints", [])
    confidence_assessment = decision_artifacts.get("confidence_assessment", {})

    base_confidence = confidence_assessment.get("confidence_score", 0.5)

    # Adjust confidence based on constraint application
    if applied_constraints:
        # Constraints provide clearer guidance, increasing confidence
        constraint_confidence = min(0.9, base_confidence + 0.1 * len(applied_constraints))
    else:
        # No constraints means more subjective decision, slightly lower confidence
        constraint_confidence = max(0.6, base_confidence - 0.1)

    # Determine confidence level
    if constraint_confidence >= 0.8:
        confidence_level = "high"
        description = "Strong confidence in authority ceiling determination"
    elif constraint_confidence >= 0.6:
        confidence_level = "medium"
        description = "Moderate confidence with some subjectivity"
    else:
        confidence_level = "low"
        description = "Limited confidence - additional review recommended"

    return {
        "authority_confidence_level": confidence_level,
        "authority_confidence_score": constraint_confidence,
        "description": description,
        "confidence_factors": {
            "base_analysis_confidence": base_confidence,
            "constraint_application": len(applied_constraints) > 0,
            "constraint_count": len(applied_constraints)
        }
    }