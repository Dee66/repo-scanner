"""Tests for enhanced misleading signal detection algorithms."""

import pytest
from unittest.mock import MagicMock
from src.core.pipeline.misleading_signal_detection import (
    analyze_misleading_signals,
    _detect_code_quality_inconsistencies,
    _detect_documentation_discrepancies,
    _detect_governance_conflicts,
    _detect_intent_mismatches,
    _detect_maintenance_indicators,
    _detect_security_deceptions,
    _detect_dependency_risks,
    _detect_architecture_deceptions,
    _detect_temporal_anomalies,
    _calculate_risk_metrics,
    _calculate_assessment_confidence,
    _generate_overall_assessment,
    _generate_recommendations
)


class TestMisleadingSignalDetection:
    """Test enhanced misleading signal detection functionality."""

    def test_analyze_misleading_signals_basic(self):
        """Test basic misleading signal analysis."""
        file_list = ["src/main.py", "README.md"]
        structure = {"file_counts": {"code": 10, "docs": 1}}
        semantic = {"functions": [{"name": "test_func", "complexity": 5}]}
        test_signals = {"testing_maturity_score": 0.8}
        governance = {"ci_cd_governance": {"has_ci_cd": True}}
        intent_posture = {"primary_intent": {"primary_intent": "application"}}

        result = analyze_misleading_signals(file_list, structure, semantic, test_signals, governance, intent_posture)

        assert "misleading_signals" in result
        assert "risk_metrics" in result
        assert "overall_assessment" in result
        assert "recommendations" in result
        assert isinstance(result["misleading_signals"], dict)
        assert isinstance(result["risk_metrics"], dict)

    def test_detect_code_quality_inconsistencies(self):
        """Test code quality inconsistency detection."""
        file_list = ["src/main.py"]
        structure = {}
        semantic = {
            "code_quality_signals": [
                {"complexity": 25},
                {"complexity": 3}
            ],
            "functions": [
                {"name": "snake_case_func"},
                {"name": "CamelCaseFunc"},
                {"name": "otherFunc"}
            ]
        }
        misleading_signals = {"code_quality_inconsistencies": []}

        _detect_code_quality_inconsistencies(file_list, structure, semantic, misleading_signals)

        assert len(misleading_signals["code_quality_inconsistencies"]) >= 1
        # Should detect mixed complexity and naming inconsistencies

    def test_detect_documentation_discrepancies(self):
        """Test documentation discrepancy detection."""
        file_list = ["src/main.py", "src/utils.py", "README.md", "docs/guide.md"]
        structure = {
            "file_counts": {"code": 2, "docs": 2},
            "documentation": ["README.md", "docs/guide.md"]
        }
        semantic = {}
        misleading_signals = {"documentation_discrepancies": []}

        _detect_documentation_discrepancies(file_list, structure, semantic, misleading_signals)

        # Should not detect issues with proper documentation
        assert len(misleading_signals["documentation_discrepancies"]) == 0

    def test_detect_governance_conflicts(self):
        """Test governance conflict detection."""
        governance = {
            "ci_cd_governance": {"has_ci_cd": True},
            "security_governance": {"has_security_scanning": False},
            "license_governance": {"detected_licenses": ["MIT", "GPL"]}
        }
        misleading_signals = {"governance_conflicts": []}

        _detect_governance_conflicts(governance, misleading_signals)

        assert len(misleading_signals["governance_conflicts"]) >= 1
        # Should detect CI without security and multiple licenses

    def test_detect_intent_mismatches(self):
        """Test intent mismatch detection."""
        file_list = ["src/main.py", "setup.py"]
        structure = {"file_counts": {"code": 1, "test": 0}}
        intent_posture = {"primary_intent": {"primary_intent": "library"}}
        misleading_signals = {"intent_mismatches": []}

        _detect_intent_mismatches(file_list, structure, intent_posture, misleading_signals)

        # Should not detect mismatch since setup.py exists for library
        assert len(misleading_signals["intent_mismatches"]) == 0

    def test_detect_maintenance_indicators(self):
        """Test maintenance indicator detection."""
        file_list = ["TODO.md", "FIXME.txt"]
        structure = {}
        test_signals = {"testing_maturity_score": 0.2}
        governance = {"ci_cd_governance": {"has_ci_cd": False}}
        misleading_signals = {"maintenance_indicators": []}

        _detect_maintenance_indicators(file_list, structure, test_signals, governance, misleading_signals)

        assert len(misleading_signals["maintenance_indicators"]) >= 1
        # Should detect TODO without tests and missing CI/CD

    def test_detect_security_deceptions(self):
        """Test security deception detection."""
        governance = {
            "security_governance": {
                "security_tools": ["eslint", "bandit"],
                "has_security_policy": False
            }
        }
        intent_posture = {
            "security_posture": {"security_practices_score": 1}
        }
        misleading_signals = {"security_deceptions": []}

        _detect_security_deceptions(governance, intent_posture, misleading_signals)

        assert len(misleading_signals["security_deceptions"]) >= 1
        # Should detect low security score and tools without policy

    def test_detect_dependency_risks(self):
        """Test dependency risk detection."""
        structure = {
            "dependencies": {
                "direct": ["dep1", "dep2"] * 50,  # 100 deps
                "outdated": ["old_dep1", "old_dep2"] * 3,  # 6 outdated
                "conflicts": ["conflict1"]
            }
        }
        semantic = {}
        misleading_signals = {"dependency_risks": []}

        _detect_dependency_risks(structure, semantic, misleading_signals)

        assert len(misleading_signals["dependency_risks"]) >= 1
        # Should detect excessive dependencies, outdated deps, and conflicts

    def test_detect_architecture_deceptions(self):
        """Test architecture deception detection."""
        file_list = ["src/main.py"] * 250  # 250 files
        structure = {
            "file_counts": {"code": 250},
            "language_distribution": {"python": 100, "javascript": 50, "java": 30, "cpp": 20, "go": 10}
        }
        semantic = {}
        misleading_signals = {"architecture_deceptions": []}

        _detect_architecture_deceptions(file_list, structure, semantic, misleading_signals)

        assert len(misleading_signals["architecture_deceptions"]) >= 1
        # Should detect monolithic structure and language soup

    def test_detect_temporal_anomalies(self):
        """Test temporal anomaly detection."""
        file_list = []
        structure = {
            "temporal_analysis": {
                "commit_patterns": {"recent_burst": 60},
                "file_age_distribution": {"very_old": 5, "very_new": 15}
            }
        }
        misleading_signals = {"temporal_anomalies": []}

        _detect_temporal_anomalies(file_list, structure, misleading_signals)

        assert len(misleading_signals["temporal_anomalies"]) >= 1
        # Should detect commit burst and age inconsistency

    def test_calculate_risk_metrics(self):
        """Test risk metrics calculation."""
        misleading_signals = {
            "code_quality_inconsistencies": [
                {"severity": "high", "risk_score": 8.0},
                {"severity": "medium", "risk_score": 5.0}
            ],
            "security_deceptions": [
                {"severity": "high", "risk_score": 9.0}
            ]
        }
        structure = {"file_counts": {"code": 10}}
        semantic = {"functions": [{"name": "test"}]}
        test_signals = {"testing_maturity_score": 0.8}
        governance = {"ci_cd_governance": {"has_ci_cd": True}}

        result = _calculate_risk_metrics(misleading_signals, structure, semantic, test_signals, governance)

        assert "overall_risk_score" in result
        assert "risk_level" in result
        assert "signal_counts" in result
        assert "assessment_confidence" in result
        assert result["overall_risk_score"] > 0
        assert result["risk_level"] in ["minimal", "low", "medium", "high", "critical"]

    def test_calculate_assessment_confidence(self):
        """Test assessment confidence calculation."""
        structure = {"file_counts": {"code": 10}}
        semantic = {"functions": [{"name": "test"}]}
        test_signals = {"testing_maturity_score": 0.8}
        governance = {"ci_cd_governance": {"has_ci_cd": True}}

        confidence = _calculate_assessment_confidence(structure, semantic, test_signals, governance)

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_generate_overall_assessment(self):
        """Test overall assessment generation."""
        risk_metrics = {
            "risk_level": "high",
            "overall_risk_score": 7.5,
            "assessment_confidence": 0.85
        }

        assessment = _generate_overall_assessment(risk_metrics)

        assert "description" in assessment
        assert "recommendation" in assessment
        assert "action_required" in assessment
        assert assessment["risk_score"] == 7.5
        assert assessment["confidence"] == 0.85

    def test_generate_recommendations(self):
        """Test recommendation generation."""
        misleading_signals = {
            "governance_conflicts": [
                {"type": "ci_without_security", "risk_score": 8.0}
            ],
            "documentation_discrepancies": [
                {"type": "missing_documentation", "risk_score": 6.0}
            ]
        }
        risk_metrics = {"risk_level": "medium"}

        recommendations = _generate_recommendations(misleading_signals, risk_metrics)

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("security" in rec.lower() for rec in recommendations)
        assert any("documentation" in rec.lower() for rec in recommendations)

    def test_analyze_misleading_signals_empty_inputs(self):
        """Test analysis with empty inputs."""
        result = analyze_misleading_signals([], {}, {}, {}, {}, {})

        assert "misleading_signals" in result
        assert "risk_metrics" in result
        # Empty inputs should still detect missing governance and security
        assert result["risk_metrics"]["overall_risk_score"] > 0.0
        assert result["risk_metrics"]["risk_level"] in ["low", "medium", "high"]

    def test_analyze_misleading_signals_invalid_inputs(self):
        """Test analysis with invalid input types."""
        result = analyze_misleading_signals(None, None, None, None, None, None)

        assert "misleading_signals" in result
        assert "risk_metrics" in result
        # Should handle None inputs gracefully