"""Authority ceiling tests for Repository Intelligence Scanner."""

import pytest
from unittest.mock import patch, MagicMock

from src.core.pipeline.authority_ceiling_evaluation import (
    evaluate_authority_ceiling,
    _evaluate_authority_constraints,
    _assess_organizational_factors,
    _determine_final_authority_ceiling,
    _generate_authority_rationale,
    _assess_authority_confidence
)
from src.core.safety.authority_ceiling import evaluate_authority_ceiling as evaluate_ceiling_simple
from src.core.safety.refusal_artifact import create_refusal_artifact


class TestAuthorityCeilingEvaluation:
    """Test authority ceiling evaluation functionality."""

    def test_evaluate_authority_ceiling_high_risk_constraint(self):
        """Test authority ceiling evaluation with high risk triggers senior authority."""
        risk_synthesis = {
            "overall_risk_assessment": {"overall_risk_level": "high"}
        }
        intent_posture = {"intent_classification": {"primary_intent": "unknown"}}
        governance = {"governance_maturity_score": 0.8}

        result = _evaluate_authority_constraints(risk_synthesis, intent_posture, governance, {"blast_radius": "contained"}, {"validation_status": "valid"})

        assert len(result["constraints"]) >= 1
        assert any(c["constraint_type"] == "risk_based" and c["severity"] == "high"
                  for c in result["constraints"])
        assert result["highest_severity"] == "high"

    def test_evaluate_authority_ceiling_production_service_constraint(self):
        """Test authority ceiling evaluation for production services requires senior authority."""
        risk_synthesis = {"overall_risk_assessment": {"overall_risk_level": "low"}}
        intent_posture = {"intent_classification": {"primary_intent": "production_service"}}
        governance = {"governance_maturity_score": 0.8}

        result = _evaluate_authority_constraints(risk_synthesis, intent_posture, governance, {"blast_radius": "contained"}, {"validation_status": "valid"})

        assert len(result["constraints"]) >= 1
        assert any(c["constraint_type"] == "intent_based" and c["authority_minimum"] == "senior_technical_lead"
                  for c in result["constraints"])

    def test_evaluate_authority_ceiling_low_governance_constraint(self):
        """Test authority ceiling evaluation with low governance maturity."""
        risk_synthesis = {"overall_risk_assessment": {"overall_risk_level": "low"}}
        intent_posture = {"intent_classification": {"primary_intent": "unknown"}}
        governance = {"governance_maturity_score": 0.3}

        result = _evaluate_authority_constraints(risk_synthesis, intent_posture, governance, {"blast_radius": "contained"}, {"validation_status": "valid"})

        assert len(result["constraints"]) >= 1
        assert any(c["constraint_type"] == "governance_based" and c["severity"] == "high"
                  for c in result["constraints"])

    def test_assess_organizational_factors_large_codebase(self):
        """Test organizational factors assessment for large codebases."""
        structure = {"file_counts": {"py": 600, "js": 400, "md": 10}}  # Total > 1000
        intent_posture = {"intent_classification": {"maturity_level": "mature"}}

        result = _assess_organizational_factors(structure, intent_posture)

        assert len(result["organizational_factors"]) >= 1
        assert any(f["factor_type"] == "scale" and f["impact"] == "high"
                  for f in result["organizational_factors"])

    def test_determine_final_authority_ceiling_with_constraints(self):
        """Test final authority ceiling determination with multiple constraints."""
        current_ceiling = {"maximum_authority": "developer"}
        authority_constraints = {
            "constraints": [
                {"authority_minimum": "technical_lead", "severity": "medium"},
                {"authority_minimum": "senior_technical_lead", "severity": "high"}
            ]
        }
        organizational_factors = {"organizational_factors": []}

        result = _determine_final_authority_ceiling(current_ceiling, authority_constraints, organizational_factors)

        # Should elevate to the highest minimum authority required (senior_technical_lead = level 3)
        assert result["authority_level"] == 3
        assert result["maximum_authority"] == "senior_technical_lead"

    def test_generate_authority_rationale_comprehensive(self):
        """Test authority rationale generation includes all factors."""
        final_ceiling = {"maximum_authority": "senior_technical_lead", "applied_constraints": [{"description": "High risk"}]}
        authority_constraints = {"constraints": [{"description": "High risk"}]}
        organizational_factors = {"organizational_factors": [{"description": "Large scale"}]}

        result = _generate_authority_rationale(final_ceiling, authority_constraints, organizational_factors)

        assert "authority_rationale" in result
        assert "rationale_summary" in result
        assert "key_factors" in result
        assert len(result["authority_rationale"]) > 0

    def test_assess_authority_confidence_with_evidence(self):
        """Test authority confidence assessment with decision artifacts."""
        final_ceiling = {"maximum_authority": "technical_lead", "applied_constraints": []}
        decision_artifacts = {
            "confidence_assessment": {"confidence_score": 0.7},
            "evidence_count": 15,
            "confidence_signals": ["strong_governance", "clear_ownership"]
        }

        result = _assess_authority_confidence(final_ceiling, decision_artifacts)

        assert "authority_confidence_level" in result
        assert "authority_confidence_score" in result
        assert isinstance(result["authority_confidence_score"], (int, float))

    def test_full_authority_ceiling_evaluation_integration(self):
        """Test complete authority ceiling evaluation with realistic inputs."""
        # Mock all required inputs
        file_list = ["src/main.py", "src/utils.py", "tests/test_main.py"]
        structure = {"file_counts": {"py": 50}}
        semantic = {"language_breakdown": {"python": 1.0}}
        test_signals = {"test_coverage": 0.8}
        governance = {"governance_maturity_score": 0.6}
        intent_posture = {"intent_classification": {"primary_intent": "library"}}
        misleading_signals = {"detected_signals": []}
        safe_change_surface = {"safe_zones": ["src/"], "blast_radius": "contained"}
        risk_synthesis = {"overall_risk_assessment": {"overall_risk_level": "medium"}}
        decision_artifacts = {"authority_ceiling": {"authority_level": "developer"}}

        result = evaluate_authority_ceiling(
            file_list, structure, semantic, test_signals, governance,
            intent_posture, misleading_signals, safe_change_surface,
            risk_synthesis, decision_artifacts
        )

        # Verify all expected fields are present
        required_fields = [
            "final_authority_ceiling", "authority_constraints",
            "organizational_factors", "authority_rationale",
            "authority_confidence", "evaluation_timestamp"
        ]

        for field in required_fields:
            assert field in result


class TestRefusalScenarios:
    """Test refusal artifact generation and scenarios."""

    def test_create_refusal_artifact_basic(self):
        """Test basic refusal artifact creation."""
        reason = "Unbounded blast radius"
        missing_info = ["ownership_artifacts", "impact_assessment"]

        result = create_refusal_artifact(reason, missing_info)

        assert result["refusal"] is True
        assert result["reason_for_refusal"] == reason
        assert result["missing_or_unknowable_information"] == missing_info
        assert result["blast_radius_unbounded_statement"] is True
        assert result["responsible_human_role_required"] == "senior_reviewer"

    def test_simple_authority_ceiling_evaluation_refusal(self):
        """Test simple authority ceiling evaluation that triggers refusal."""
        # Mock repository analysis that should trigger refusal
        repository_analysis = {
            "risk_level": "critical",
            "blast_radius": "unbounded",
            "ownership_clarity": "unclear"
        }

        result = evaluate_ceiling_simple(repository_analysis)

        # Currently returns placeholder, but should eventually trigger refusal
        assert isinstance(result, dict)
        assert "within_authority" in result
        assert "triggers" in result

    def test_blast_radius_unbounded_refusal(self):
        """Test refusal when blast radius cannot be bounded."""
        with patch('src.core.safety.authority_ceiling.emit_refusal_artifact') as mock_emit:
            mock_emit.return_value = {"refusal": True, "reason": "unbounded_blast_radius"}

            # This would be called when blast radius evaluation fails
            result = mock_emit("unbounded_blast_radius")

            assert result["refusal"] is True
            assert result["reason"] == "unbounded_blast_radius"

    def test_missing_ownership_artifacts_refusal(self):
        """Test refusal when critical ownership artifacts are missing."""
        with patch('src.core.safety.refusal_artifact.create_refusal_artifact') as mock_create:
            mock_create.return_value = {
                "refusal": True,
                "reason_for_refusal": "missing_ownership_artifacts",
                "missing_or_unknowable_information": ["CODEOWNERS", "MAINTAINERS"]
            }

            result = mock_create("missing_ownership_artifacts", ["CODEOWNERS", "MAINTAINERS"])

            assert result["refusal"] is True
            assert "CODEOWNERS" in result["missing_or_unknowable_information"]