"""Refusal artifact for Repository Intelligence Scanner."""

REFUSAL_ARTIFACT_DEFINITION = (
    "A first-class output stating that responsible guidance cannot be rendered."
)

REQUIRED_REFUSAL_FIELDS = [
    "reason_for_refusal",
    "missing_or_unknowable_information",
    "blast_radius_unbounded_statement",
    "responsible_human_role_required"
]

REFUSAL_GUARANTEES = [
    "refusal_is_success",
    "refusal_is_auditable"
]

def create_refusal_artifact(reason: str, missing_info: list) -> dict:
    """Create a refusal artifact."""
    return {
        "refusal": True,
        "reason_for_refusal": reason,
        "missing_or_unknowable_information": missing_info,
        "blast_radius_unbounded_statement": True,
        "responsible_human_role_required": "senior_reviewer"
    }
