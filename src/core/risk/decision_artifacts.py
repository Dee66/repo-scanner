"""Decision artifacts for Repository Intelligence Scanner."""

DECISION_ARTIFACTS = [
    "executive_verdict",
    "safe_to_change_surface",
    "no_touch_zones",
    "misleading_signals",
    "what_not_to_fix",
    "refusal_artifact_if_applicable",
    "confidence_and_limits",
    "validity_window"
]

def generate_decision_artifacts(repository_analysis: dict) -> dict:
    """Generate all decision artifacts."""
    risk_synthesis = repository_analysis.get("risk_synthesis", {})
    confidence_assessment = repository_analysis.get("decision_artifacts", {}).get("confidence_assessment", {})
    
    # Compute executive verdict
    overall_risk = risk_synthesis.get("overall_risk_assessment", {})
    risk_level = overall_risk.get("overall_risk_level", "unknown").lower()
    confidence_score = confidence_assessment.get("confidence_score", 0.0)
    
    if confidence_score < 0.5:
        executive_verdict = "INSUFFICIENT_EVIDENCE"
    elif risk_level in ["low", "minimal"]:
        executive_verdict = "PASS"
    elif risk_level in ["high", "critical"]:
        executive_verdict = "FAIL"
    elif risk_level == "medium":
        executive_verdict = "CAUTION"
    else:
        executive_verdict = "INSUFFICIENT_EVIDENCE"
        executive_verdict = "CAUTION"
    
    # Extract safe to change surface
    safe_change_surface = repository_analysis.get("safe_change_surface", [])
    
    # Extract no touch zones (critical issues)
    no_touch_zones = []
    critical_issues = risk_synthesis.get("critical_issues", [])
    for issue in critical_issues:
        if isinstance(issue, dict):
            no_touch_zones.append({
                "area": issue.get("issue", ""),
                "severity": issue.get("severity", ""),
                "rationale": issue.get("impact", "")
            })
    
    # Extract misleading signals
    misleading_signals = repository_analysis.get("misleading_signals", [])
    
    # What not to fix (recommendations with low priority)
    what_not_to_fix = []
    recommendations = risk_synthesis.get("recommendations", [])
    for rec in recommendations:
        if isinstance(rec, dict) and rec.get("priority", "").lower() in ["low", "optional"]:
            what_not_to_fix.append(rec.get("action", ""))
    
    # Refusal artifact (if verdict is UNSAFE)
    refusal_artifact = None
    if executive_verdict == "UNSAFE":
        refusal_artifact = {
            "reason": "Critical risks identified",
            "blocking_issues": [issue.get("issue", "") for issue in critical_issues if isinstance(issue, dict)][:3]
        }
    
    # Confidence and limits
    confidence_level = confidence_assessment.get("confidence_level", "LOW")
    confidence_and_limits = {
        "level": confidence_level.upper(),
        "score": confidence_score,
        "limitations": confidence_assessment.get("limitations", [])
    }
    
    # Validity window (placeholder - could be based on analysis timestamp)
    validity_window = {
        "valid_until": None,  # Could implement time-based expiry
        "conditions": ["Repository state unchanged", "No new critical issues introduced"]
    }
    
    return {
        "executive_verdict": executive_verdict,
        "safe_to_change_surface": safe_change_surface,
        "no_touch_zones": no_touch_zones,
        "misleading_signals": misleading_signals,
        "what_not_to_fix": what_not_to_fix,
        "refusal_artifact": refusal_artifact,
        "confidence_and_limits": confidence_and_limits,
        "validity_window": validity_window
    }
