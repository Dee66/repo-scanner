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
    
    # Extract safe to change surface
    safe_change_surface = repository_analysis.get("safe_change_surface", [])
    
    # Extract no touch zones (critical issues)
    no_touch_zones = []
    critical_issues = risk_synthesis.get("critical_issues", [])
    for issue in critical_issues:
        if isinstance(issue, dict):
            no_touch_zones.append({
                "file_path": issue.get("file_path", ""),
                "component": issue.get("component", issue.get("issue", "")),
                "severity": issue.get("severity", "high"),
                "rationale": issue.get("impact", issue.get("description", ""))
            })
    
    # Extract misleading signals
    misleading_signals = repository_analysis.get("misleading_signals", [])
    
    # What not to fix (recommendations with low priority)
    what_not_to_fix = []
    recommendations = risk_synthesis.get("recommendations", [])
    for rec in recommendations:
        if isinstance(rec, dict) and rec.get("priority", "").lower() in ["low", "optional"]:
            what_not_to_fix.append({
                "issue_type": rec.get("type", "unknown"),
                "description": rec.get("description", rec.get("action", "")),
                "file_path": rec.get("file_path", ""),
                "rationale": rec.get("rationale", "Low priority issue"),
                "priority_level": "do_not_fix"
            })
    
    # Refusal artifact (if verdict indicates inability to provide guidance)
    refusal_artifact = None
    if executive_verdict == "INSUFFICIENT_EVIDENCE" and confidence_score < 0.3:
        refusal_artifact = {
            "refusal_reason": "Insufficient evidence to provide reliable guidance",
            "refusal_category": "insufficient_evidence",
            "refusal_timestamp": repository_analysis.get("metadata", {}).get("run_timestamp", ""),
            "next_steps": [
                "Gather more evidence about repository structure",
                "Review testing and governance practices",
                "Consult with domain experts"
            ]
        }
    
    # Confidence and limits
    confidence_breakdown = confidence_assessment.get("confidence_breakdown", {
        "structural_analysis": 0.0,
        "governance_signals": 0.0,
        "testing_coverage": 0.0,
        "integration_patterns": 0.0
    })
    
    confidence_and_limits = {
        "overall_confidence": confidence_score,
        "confidence_breakdown": confidence_breakdown,
        "analysis_limits": confidence_assessment.get("limitations", [
            "Analysis limited to observable repository structure",
            "Cannot assess runtime behavior",
            "Cannot verify external dependencies"
        ]),
        "assumptions_made": confidence_assessment.get("assumptions", [
            "Repository follows standard practices",
            "Code is representative of actual usage",
            "External services are functioning normally"
        ])
    }
    
    # Validity window
    from datetime import datetime, timedelta
    run_timestamp = repository_analysis.get("metadata", {}).get("run_timestamp", datetime.now().isoformat())
    try:
        valid_from = datetime.fromisoformat(run_timestamp.replace('Z', '+00:00'))
        valid_until = valid_from + timedelta(days=30)  # 30 days validity
    except:
        valid_from = datetime.now()
        valid_until = valid_from + timedelta(days=30)
    
    validity_window = {
        "valid_from": valid_from.isoformat(),
        "valid_until": valid_until.isoformat(),
        "invalidation_triggers": [
            "Major repository restructuring",
            "Significant changes to critical components",
            "Introduction of new external dependencies",
            "Changes to governance or testing practices"
        ],
        "recommended_refresh_interval": "30 days"
    }
    
    # Extract artifacts (individual findings)
    artifacts = repository_analysis.get("decision_artifacts", {}).get("artifacts", [])
    
    result = {
        "executive_verdict": executive_verdict,
        "safe_to_change_surface": safe_change_surface,
        "no_touch_zones": no_touch_zones,
        "misleading_signals": misleading_signals,
        "what_not_to_fix": what_not_to_fix,
        "confidence_and_limits": confidence_and_limits,
        "validity_window": validity_window,
        "artifacts": artifacts
    }
    
    # Add refusal artifact only if applicable
    if refusal_artifact:
        result["refusal_artifact_if_applicable"] = refusal_artifact
    
    return result
