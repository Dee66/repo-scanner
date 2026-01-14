"""Calibration tests for detector accuracy using golden repositories."""

import pytest
import json
from pathlib import Path
from typing import Dict, List, Any

from src.core.pipeline.security_analysis import analyze_security_vulnerabilities


class GoldenRepo:
    """Represents a golden repository with known security issues."""

    def __init__(self, path: Path, name: str, expected_findings: Dict[str, Any]):
        self.path = path
        self.name = name
        self.expected_findings = expected_findings


class CalibrationHarness:
    """Runs calibration tests on golden repositories."""

    def __init__(self):
        self.golden_repos = self._load_golden_repos()

    def _load_golden_repos(self) -> List[GoldenRepo]:
        """Load golden repositories from the golden-repos directory."""
        golden_repos_dir = Path(__file__).parent.parent / "golden-repos"
        repos = []

        if not golden_repos_dir.exists():
            return repos

        # Python web app - known issues: SQL injection, command injection, path traversal, info disclosure
        python_repo = GoldenRepo(
            golden_repos_dir / "python-web-app",
            "python-web-app",
            {
                "sql_injection": ["app.py:8"],
                "command_injection": ["app.py:15"],
                "path_traversal": ["app.py:22"],
                "information_disclosure": ["app.py:28"]
            }
        )
        repos.append(python_repo)

        # Node.js API - known issues: SQL injection, command injection, path traversal, info disclosure, no auth
        nodejs_repo = GoldenRepo(
            golden_repos_dir / "nodejs-api",
            "nodejs-api",
            {
                "sql_injection": ["server.js:9"],
                "command_injection": ["server.js:15"],
                "path_traversal": ["server.js:22"],
                "information_disclosure": ["server.js:27"],
                "missing_authentication": ["server.js:37"]
            }
        )
        repos.append(nodejs_repo)

        # Java enterprise - known issues: SQL injection, path traversal
        java_repo = GoldenRepo(
            golden_repos_dir / "java-enterprise",
            "java-enterprise",
            {
                "sql_injection": ["UserServlet.java:18"],
                "path_traversal": ["UserServlet.java:32"]
            }
        )
        repos.append(java_repo)

        # Rust CLI - known issues: command injection, path traversal, hardcoded secrets
        rust_repo = GoldenRepo(
            golden_repos_dir / "rust-cli",
            "rust-cli",
            {
                "command_injection": ["main.rs:13"],
                "path_traversal": ["main.rs:20"],
                "hardcoded_secrets": ["main.rs:26"]
            }
        )
        repos.append(rust_repo)

        return repos

    def run_calibration_test(self, repo: GoldenRepo) -> Dict[str, Any]:
        """Run security analysis on a golden repository and compute metrics."""
        try:
            # Get all files in the repository
            file_list = []
            for file_path in repo.path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    file_list.append(str(file_path))

            # Run security analysis
            semantic_analysis = {}  # Not needed for basic pattern detection
            analysis_result = analyze_security_vulnerabilities(file_list, semantic_analysis)

            # Compute metrics
            metrics = self._compute_metrics(analysis_result, repo.expected_findings)

            return {
                "repo": repo.name,
                "error": None,
                "metrics": metrics,
                "analysis_result": analysis_result
            }

        except Exception as e:
            return {
                "repo": repo.name,
                "error": f"Analysis failed: {str(e)}",
                "metrics": None
            }

    def _compute_metrics(self, analysis_result: Dict[str, Any], expected_findings: Dict[str, Any]) -> Dict[str, Any]:
        """Compute precision, recall, and F1 metrics."""
        # Extract detected findings from analysis result
        detected_findings = set()
        if "patterns_by_language" in analysis_result:
            for lang_patterns in analysis_result["patterns_by_language"].values():
                for pattern in lang_patterns:
                    for finding in pattern.get("patterns", []):
                        finding_type = finding.get("type", "")
                        line = finding.get("line", 0)
                        file_path = pattern.get("file_path", "")
                        # Create a comparable key
                        detected_findings.add(f"{finding_type}:{Path(file_path).name}:{line}")

        # Convert expected findings to comparable format
        expected_set = set()
        for finding_type, locations in expected_findings.items():
            for location in locations:
                # Parse "file:line" format
                if ":" in location:
                    file_part, line_part = location.split(":", 1)
                    expected_set.add(f"{finding_type}:{file_part}:{line_part}")

        # Calculate metrics
        true_positives = len(detected_findings & expected_set)
        false_positives = len(detected_findings - expected_set)
        false_negatives = len(expected_set - detected_findings)

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "expected_findings": len(expected_set),
            "detected_findings": len(detected_findings)
        }


@pytest.fixture
def calibration_harness():
    """Fixture providing calibration harness."""
    return CalibrationHarness()


@pytest.mark.parametrize("repo_name", ["python-web-app", "nodejs-api", "java-enterprise", "rust-cli"])
def test_detector_calibration(calibration_harness, repo_name):
    """Test detector accuracy on golden repositories."""
    # Find the repo
    repo = None
    for r in calibration_harness.golden_repos:
        if r.name == repo_name:
            repo = r
            break

    assert repo is not None, f"Golden repo {repo_name} not found"

    # Run calibration
    result = calibration_harness.run_calibration_test(repo)

    # Check for errors
    if result["error"]:
        pytest.fail(f"Calibration failed for {repo_name}: {result['error']}")

    # Check metrics
    metrics = result["metrics"]
    assert metrics is not None

    # Basic sanity checks
    assert metrics["precision"] >= 0.0
    assert metrics["recall"] >= 0.0
    assert metrics["f1_score"] >= 0.0

    # Log metrics for analysis
    print(f"\n{repo_name} calibration results:")
    print(f"  Expected findings: {metrics['expected_findings']}")
    print(f"  Detected findings: {metrics['detected_findings']}")
    print(".3f")
    print(".3f")
    print(".3f")


def test_overall_calibration_metrics(calibration_harness):
    """Test overall calibration metrics across all golden repos."""
    total_tp = total_fp = total_fn = 0

    for repo in calibration_harness.golden_repos:
        result = calibration_harness.run_calibration_test(repo)
        if result["error"] or not result["metrics"]:
            continue

        metrics = result["metrics"]
        total_tp += metrics["true_positives"]
        total_fp += metrics["false_positives"]
        total_fn += metrics["false_negatives"]

    # Compute overall metrics
    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0

    print("\nOverall calibration metrics:")
    print(f"  Total true positives: {total_tp}")
    print(f"  Total false positives: {total_fp}")
    print(f"  Total false negatives: {total_fn}")
    print(f"  Overall precision: {overall_precision:.3f}")
    print(f"  Overall recall: {overall_recall:.3f}")
    print(f"  Overall F1 score: {overall_f1:.3f}")

    # Assert minimum acceptable performance (adjust thresholds as needed)
    assert overall_precision >= 0.5, f"Overall precision too low: {overall_precision}"
    assert overall_recall >= 0.5, f"Overall recall too low: {overall_recall}"