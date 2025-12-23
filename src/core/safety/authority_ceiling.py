"""Authority ceiling and safety mechanisms for Repository Intelligence Scanner."""

AUTHORITY_CEILING_DEFINITION = (
    "The maximum complexity, ambiguity, or risk beyond which the system refuses "
    "to render actionable guidance."
)

AUTHORITY_TRIGGERS = [
    "unbounded_blast_radius",
    "contradictory_governance_signals",
    "missing_ownership_artifacts",
    "excessive_polyglot_sprawl",
    "critical_paths_unverifiable"
]

BEHAVIOR_ON_TRIGGER = [
    "emit_refusal_artifact",
    "suppress_recommendations",
    "downgrade_all_confidence_levels"
]

def evaluate_authority_ceiling(repository_analysis: dict) -> dict:
    """Evaluate if analysis exceeds authority ceiling."""
    # Placeholder implementation
    return {"within_authority": True, "triggers": []}

def emit_refusal_artifact(reason: str) -> dict:
    """Emit a refusal artifact."""
    return {
        "refusal": True,
        "reason": reason,
        "missing_information": [],
        "blast_radius_unbounded": True,
        "responsible_human_role": "senior_reviewer"
    }
