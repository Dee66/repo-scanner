"""Tests for output contract and quality assurance."""

import json

from src.core.quality.output_contract import generate_primary_report, generate_machine_output, generate_executive_verdict


def test_generate_primary_report_basic():
    """Test basic primary report generation."""
    analysis = {
        "repository_root": "/path/to/repo",
        "files": ["file1.txt", "file2.txt"]
    }
    repository_path = "/path/to/repo"
    
    report = generate_primary_report(analysis, repository_path)
    
    assert isinstance(report, str)
    assert "# Repository Analysis Report" in report
    assert "/path/to/repo" in report
    assert "2 files" in report
    
    # Check required sections
    required_sections = [
        "## Executive Summary",
        "## System Characterization",
        "## Evidence Highlights",
        "## Misleading Signals",
        "## Safe to Change Surface",
        "## What Not to Fix",
        "## Refusal or First Action",
        "## Confidence and Limits",
        "## Validity and Expiry"
    ]
    
    for section in required_sections:
        assert section in report


def test_generate_primary_report_fallback():
    """Test primary report generation with missing analysis data."""
    analysis = {}
    repository_path = "/fallback/repo"
    
    report = generate_primary_report(analysis, repository_path)
    
    assert "/fallback/repo" in report
    assert "0 files" in report


def test_generate_machine_output_basic():
    """Test basic machine output generation."""
    analysis = {
        "repository_root": "/path/to/repo",
        "files": ["file1.txt", "file2.txt", "file3.txt"]
    }
    repository_path = "/path/to/repo"
    
    output = generate_machine_output(analysis, repository_path)
    
    assert isinstance(output, dict)
    
    # Check required keys
    required_keys = ["run_id", "repository", "summary", "tasks", "gaps", "metadata"]
    for key in required_keys:
        assert key in output
    
    # Check repository info
    assert output["repository"]["name"] == "repo"
    assert output["repository"]["path"] == "/path/to/repo"
    
    # Check summary
    assert output["summary"]["files_scanned"] == 3
    assert output["summary"]["overall_score"] == 0.0
    assert output["summary"]["tests_discovered"] == 0
    assert output["summary"]["gaps_count"] == 0
    
    # Check metadata
    assert "scanner_version" in output["metadata"]
    assert "run_timestamp" in output["metadata"]
    assert "deterministic_hash" in output["metadata"]


def test_generate_machine_output_fallback():
    """Test machine output generation with missing analysis data."""
    analysis = {}
    repository_path = "/fallback/repo"
    
    output = generate_machine_output(analysis, repository_path)
    
    assert output["repository"]["name"] == "repo"
    assert output["repository"]["path"] == "/fallback/repo"
    assert output["summary"]["files_scanned"] == 0


def test_machine_output_json_serializable():
    """Test that machine output is JSON serializable."""
    analysis = {"files": ["test.txt"]}
    repository_path = "/test"
    
    output = generate_machine_output(analysis, repository_path)
    
    # Should not raise exception
    json_str = json.dumps(output, sort_keys=True)
    assert json_str
    
    # Should be able to parse back
    parsed = json.loads(json_str)
    assert parsed == output


def test_machine_output_schema_compliance():
    """Test that machine output complies with expected schema structure."""
    analysis = {"files": ["a.txt", "b.txt"]}
    repository_path = "/repo"
    
    output = generate_machine_output(analysis, repository_path)
    
    # Validate structure matches schema expectations
    assert isinstance(output["run_id"], str)
    assert isinstance(output["repository"], dict)
    assert isinstance(output["summary"], dict)
    assert isinstance(output["tasks"], dict)
    assert isinstance(output["gaps"], list)
    assert isinstance(output["metadata"], dict)
    
    # Validate summary fields
    summary = output["summary"]
    assert isinstance(summary["overall_score"], (int, float))
    assert isinstance(summary["files_scanned"], int)
    assert isinstance(summary["tests_discovered"], int)
    assert isinstance(summary["gaps_count"], int)


def test_generate_executive_verdict_pass():
    """Test executive verdict generation for PASS verdict."""
    analysis = {
        "risk_synthesis": {
            "overall_risk_assessment": {
                "overall_risk_level": "low",
                "description": "Repository appears safe"
            },
            "critical_issues": [],
            "recommendations": [
                {"action": "Add more tests", "priority": "medium"}
            ]
        },
        "decision_artifacts": {
            "confidence_assessment": {
                "confidence_score": 0.8,
                "confidence_level": "high"
            }
        }
    }
    repository_path = "/test/repo"
    
    verdict = generate_executive_verdict(analysis, repository_path)
    
    assert isinstance(verdict, str)
    assert "# Executive Verdict" in verdict
    assert "**Verdict:** PASS" in verdict
    assert "**Confidence:** HIGH (0.80)" in verdict
    assert "## Safe Action Summary" in verdict
    assert "Competent engineers can safely:" in verdict
    assert len(verdict.split()) < 300  # Under word limit


def test_generate_executive_verdict_fail():
    """Test executive verdict generation for FAIL verdict."""
    analysis = {
        "risk_synthesis": {
            "overall_risk_assessment": {
                "overall_risk_level": "critical",
                "description": "Critical security issues found"
            },
            "critical_issues": [
                {
                    "issue": "SQL injection vulnerability",
                    "severity": "high",
                    "impact": "Data breach risk"
                }
            ]
        },
        "decision_artifacts": {
            "confidence_assessment": {
                "confidence_score": 0.9,
                "confidence_level": "high"
            }
        }
    }
    repository_path = "/test/repo"
    
    verdict = generate_executive_verdict(analysis, repository_path)
    
    assert "**Verdict:** FAIL" in verdict
    assert "## Blocking Risks" in verdict
    assert "SQL injection vulnerability" in verdict
    assert "## Unsafe Action Summary" in verdict
    assert "Production deployments" in verdict


def test_generate_executive_verdict_insufficient_evidence():
    """Test executive verdict generation for INSUFFICIENT_EVIDENCE."""
    analysis = {
        "risk_synthesis": {
            "overall_risk_assessment": {
                "overall_risk_level": "unknown"
            }
        },
        "decision_artifacts": {
            "confidence_assessment": {
                "confidence_score": 0.3,
                "confidence_level": "low"
            }
        }
    }
    repository_path = "/test/repo"
    
    verdict = generate_executive_verdict(analysis, repository_path)
    
    assert "**Verdict:** INSUFFICIENT_EVIDENCE" in verdict
    assert "confidence too low" in verdict.lower()


def test_generate_executive_verdict_word_limit():
    """Test that executive verdict stays under 300 word limit."""
    # Create analysis with many issues to test truncation
    analysis = {
        "risk_synthesis": {
            "overall_risk_assessment": {
                "overall_risk_level": "high",
                "description": "Multiple critical issues identified across the codebase"
            },
            "critical_issues": [
                {"issue": f"Critical issue {i}", "severity": "high", "impact": f"Impact {i}"}
                for i in range(10)
            ],
            "recommendations": [
                {"action": f"Recommendation {i}", "priority": "high"}
                for i in range(10)
            ]
        },
        "decision_artifacts": {
            "confidence_assessment": {
                "confidence_score": 0.85,
                "confidence_level": "high"
            }
        }
    }
    repository_path = "/test/repo"
    
    verdict = generate_executive_verdict(analysis, repository_path)
    
    word_count = len(verdict.split())
    assert word_count <= 300, f"Verdict has {word_count} words, exceeds 300 word limit"