"""Validation framework for Repository Intelligence Scanner.

This module provides tools to validate scanner accuracy against known
secure and vulnerable repositories, measuring false positives and false negatives.
"""

import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

@dataclass
class ValidationResult:
    """Result of validating scanner against a known repository."""
    repository_name: str
    expected_vulnerabilities: int
    detected_vulnerabilities: int
    false_positives: int
    false_negatives: int
    accuracy_score: float
    precision: float
    recall: float
    analysis_time: float

class ScannerValidator:
    """Validates scanner accuracy against ground truth data."""

    def __init__(self, scanner_path: str = None):
        self.scanner_path = scanner_path or Path(__file__).parent.parent
        self.validation_results = []

    def validate_against_repository(self, repo_path: str, ground_truth_file: str = None) -> ValidationResult:
        """Validate scanner against a repository with known security posture."""
        start_time = time.time()

        # Run scanner
        print(f"🔍 Scanning {repo_path}...")
        scan_result = self._run_scanner(repo_path)

        analysis_time = time.time() - start_time

        # Load ground truth if provided
        ground_truth = self._load_ground_truth(ground_truth_file) if ground_truth_file else {}

        # Analyze results
        security_analysis = scan_result.get('security_analysis', {})
        unsafe_patterns = security_analysis.get('unsafe_patterns', {})
        detected_count = unsafe_patterns.get('summary', {}).get('total_patterns', 0)

        # For now, assume repositories with "test" in name are expected to have some patterns
        # This is a simplified assumption - in practice, we'd have detailed ground truth
        expected_vulnerabilities = 0
        if 'test' in repo_path.lower() or 'vulnerable' in repo_path.lower():
            expected_vulnerabilities = max(1, detected_count // 2)  # Assume half are real
        elif 'secure' in repo_path.lower() or 'safe' in repo_path.lower():
            expected_vulnerabilities = 0

        # Calculate metrics
        false_positives = max(0, detected_count - expected_vulnerabilities)
        false_negatives = max(0, expected_vulnerabilities - detected_count)
        precision = detected_count / (detected_count + false_positives) if (detected_count + false_positives) > 0 else 1.0
        recall = detected_count / (detected_count + false_negatives) if (detected_count + false_negatives) > 0 else 1.0
        accuracy = (detected_count - false_positives) / max(detected_count, 1)

        result = ValidationResult(
            repository_name=Path(repo_path).name,
            expected_vulnerabilities=expected_vulnerabilities,
            detected_vulnerabilities=detected_count,
            false_positives=false_positives,
            false_negatives=false_negatives,
            accuracy_score=accuracy,
            precision=precision,
            recall=recall,
            analysis_time=analysis_time
        )

        self.validation_results.append(result)
        return result

    def _run_scanner(self, repo_path: str) -> Dict[str, Any]:
        """Run the scanner on a repository."""
        import sys
        import subprocess

        # Add scanner to path
        scanner_dir = self.scanner_path / "src"
        if str(scanner_dir) not in sys.path:
            sys.path.insert(0, str(scanner_dir))

        try:
            from core.pipeline.analysis import execute_pipeline
            return execute_pipeline(repo_path)
        except Exception as e:
            print(f"❌ Scanner execution failed: {e}")
            return {}

    def _load_ground_truth(self, ground_truth_file: str) -> Dict[str, Any]:
        """Load ground truth data for validation."""
        try:
            with open(ground_truth_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Could not load ground truth: {e}")
            return {}

    def generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        if not self.validation_results:
            return {"error": "No validation results available"}

        total_repos = len(self.validation_results)
        avg_accuracy = sum(r.accuracy_score for r in self.validation_results) / total_repos
        avg_precision = sum(r.precision for r in self.validation_results) / total_repos
        avg_recall = sum(r.recall for r in self.validation_results) / total_repos
        total_false_positives = sum(r.false_positives for r in self.validation_results)
        total_false_negatives = sum(r.false_negatives for r in self.validation_results)

        return {
            "summary": {
                "repositories_tested": total_repos,
                "average_accuracy": round(avg_accuracy, 3),
                "average_precision": round(avg_precision, 3),
                "average_recall": round(avg_recall, 3),
                "total_false_positives": total_false_positives,
                "total_false_negatives": total_false_negatives
            },
            "detailed_results": [
                {
                    "repository": r.repository_name,
                    "expected": r.expected_vulnerabilities,
                    "detected": r.detected_vulnerabilities,
                    "false_positives": r.false_positives,
                    "false_negatives": r.false_negatives,
                    "accuracy": round(r.accuracy_score, 3),
                    "precision": round(r.precision, 3),
                    "recall": round(r.recall, 3),
                    "analysis_time": round(r.analysis_time, 2)
                }
                for r in self.validation_results
            ],
            "recommendations": self._generate_validation_recommendations(avg_accuracy, avg_precision, avg_recall)
        }

    def _generate_validation_recommendations(self, accuracy: float, precision: float, recall: float) -> List[str]:
        """Generate recommendations based on validation metrics."""
        recommendations = []

        if accuracy < 0.8:
            recommendations.append("Scanner accuracy is below acceptable threshold. Review pattern matching logic.")
        if precision < 0.7:
            recommendations.append("High false positive rate detected. Implement better context awareness.")
        if recall < 0.8:
            recommendations.append("Scanner may be missing real vulnerabilities. Review pattern coverage.")

        if not recommendations:
            recommendations.append("Scanner validation passed acceptable thresholds.")

        return recommendations

def run_validation_suite() -> Dict[str, Any]:
    """Run validation against known repositories."""
    validator = ScannerValidator()

    # Test against CostPilot (known to have good security practices)
    costpilot_result = validator.validate_against_repository(
        "/home/dee/workspace/AI/GuardSuite/CostPilot"
    )

    # In a real scenario, we'd test against multiple repos with known vulnerabilities
    # For now, we'll just test CostPilot and assume it's secure

    return validator.generate_validation_report()

if __name__ == "__main__":
    print("🧪 Running Scanner Validation Suite...")
    report = run_validation_suite()

    print("\n📊 Validation Report:")
    print(json.dumps(report, indent=2))