#!/usr/bin/env python3
"""
Full Regression Testing Script

Executes comprehensive regression testing on 100+ repositories
to validate system stability and effectiveness.
"""

import argparse
import concurrent.futures
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.metrics.effectiveness import EffectivenessMetricsCalculator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RegressionTester:
    """Comprehensive regression testing on multiple repositories."""

    def __init__(self, max_workers: int = 4, timeout: int = 600):
        """
        Initialize regression tester.

        Args:
            max_workers: Maximum concurrent workers
            timeout: Timeout per repository scan (seconds)
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.metrics_calculator = EffectivenessMetricsCalculator()

    def run_full_regression_test(self, repo_list: List[str],
                               output_dir: str = "regression_results") -> Dict[str, Any]:
        """
        Run full regression testing on repository list.

        Args:
            repo_list: List of repository URLs to test
            output_dir: Output directory for results

        Returns:
            Comprehensive regression test results
        """
        logger.info(f"Starting regression testing on {len(repo_list)} repositories")

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        start_time = datetime.now()

        # Run scans in parallel
        results = self._run_parallel_scans(repo_list, output_path)

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # Analyze results
        analysis = self._analyze_regression_results(results, total_time)

        # Generate comprehensive report
        report = {
            "test_metadata": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_time_seconds": total_time,
                "repositories_tested": len(repo_list),
                "max_workers": self.max_workers,
                "timeout_seconds": self.timeout
            },
            "results": results,
            "analysis": analysis,
            "recommendations": self._generate_recommendations(analysis)
        }

        # Save detailed report
        report_file = output_path / "regression_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # Save summary
        summary_file = output_path / "regression_summary.md"
        self._generate_summary_report(report, summary_file)

        logger.info(f"Regression testing completed. Report saved to {report_file}")

        return report

    def _run_parallel_scans(self, repo_list: List[str], output_path: Path) -> List[Dict[str, Any]]:
        """Run repository scans in parallel."""
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all scan tasks
            future_to_repo = {
                executor.submit(self._scan_single_repository, repo, output_path): repo
                for repo in repo_list
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_repo):
                repo = future_to_repo[future]
                try:
                    result = future.result(timeout=self.timeout)
                    results.append(result)
                    logger.info(f"Completed scan of {repo}: {'SUCCESS' if result['success'] else 'FAILED'}")
                except Exception as e:
                    logger.error(f"Scan of {repo} failed with exception: {e}")
                    results.append({
                        "repository": repo,
                        "success": False,
                        "error": str(e),
                        "scan_time": 0,
                        "timestamp": datetime.now().isoformat()
                    })

        return results

    def _scan_single_repository(self, repo_url: str, output_path: Path) -> Dict[str, Any]:
        """Scan a single repository and return results."""
        import subprocess

        repo_name = repo_url.split('/')[-1].replace('.git', '')
        repo_output_dir = output_path / repo_name
        repo_output_dir.mkdir(exist_ok=True)

        start_time = time.time()

        try:
            # Run the scanner
            cmd = [
                sys.executable, "-m", "src.cli",
                "scan",
                "--url", repo_url,
                "--output-dir", str(repo_output_dir),
                "--deterministic"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=Path(__file__).parent.parent
            )

            scan_time = time.time() - start_time
            success = result.returncode == 0

            scan_result = {
                "repository": repo_url,
                "repo_name": repo_name,
                "success": success,
                "scan_time": scan_time,
                "timestamp": datetime.now().isoformat(),
                "return_code": result.returncode
            }

            # Try to extract metrics from output
            if success:
                metrics = self._extract_scan_metrics(repo_output_dir)
                scan_result.update(metrics)

            if result.stderr:
                scan_result["stderr"] = result.stderr[:1000]  # Truncate long errors

            return scan_result

        except subprocess.TimeoutExpired:
            scan_time = time.time() - start_time
            return {
                "repository": repo_url,
                "repo_name": repo_name,
                "success": False,
                "scan_time": scan_time,
                "error": "timeout",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            scan_time = time.time() - start_time
            return {
                "repository": repo_url,
                "repo_name": repo_name,
                "success": False,
                "scan_time": scan_time,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    def _extract_scan_metrics(self, output_dir: Path) -> Dict[str, Any]:
        """Extract metrics from scan output."""
        metrics = {}

        # Try to read scan report
        report_file = output_dir / "scan_report.json"
        if report_file.exists():
            try:
                with open(report_file, 'r') as f:
                    data = json.load(f)

                # Extract key metrics
                structure = data.get("structure", {})
                metrics.update({
                    "total_files": structure.get("file_counts", {}).get("total", 0),
                    "code_files": structure.get("file_counts", {}).get("code", 0),
                    "languages_detected": list(structure.get("languages", {}).keys()),
                    "primary_language": structure.get("primary_language")
                })

                # Effectiveness metrics
                effectiveness = data.get("effectiveness_analysis", {})
                if effectiveness:
                    metrics.update({
                        "accuracy_score": effectiveness.get("accuracy_score", 0),
                        "false_positives": effectiveness.get("false_positives", 0),
                        "false_negatives": effectiveness.get("false_negatives", 0)
                    })

                # Determinism
                determinism = data.get("determinism_verification", {})
                metrics["deterministic"] = determinism.get("determinism_report", {}).get("determinism_status") == "verified"

            except Exception as e:
                metrics["extraction_error"] = str(e)

        return metrics

    def _analyze_regression_results(self, results: List[Dict[str, Any]], total_time: float) -> Dict[str, Any]:
        """Analyze regression test results."""
        total_repos = len(results)
        successful_scans = len([r for r in results if r["success"]])
        failed_scans = total_repos - successful_scans

        # Calculate success rate
        success_rate = successful_scans / total_repos if total_repos > 0 else 0

        # Performance metrics
        scan_times = [r["scan_time"] for r in results if r["success"]]
        avg_scan_time = sum(scan_times) / len(scan_times) if scan_times else 0
        max_scan_time = max(scan_times) if scan_times else 0
        min_scan_time = min(scan_times) if scan_times else 0

        # Effectiveness metrics
        accuracy_scores = [r.get("accuracy_score", 0) for r in results if r.get("accuracy_score", 0) > 0]
        avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0

        # Error analysis
        errors = {}
        for result in results:
            if not result["success"]:
                error_type = result.get("error", "unknown")
                errors[error_type] = errors.get(error_type, 0) + 1

        # Language distribution
        language_counts = {}
        for result in results:
            if result["success"]:
                languages = result.get("languages_detected", [])
                for lang in languages:
                    language_counts[lang] = language_counts.get(lang, 0) + 1

        return {
            "summary": {
                "total_repositories": total_repos,
                "successful_scans": successful_scans,
                "failed_scans": failed_scans,
                "success_rate": success_rate,
                "total_test_time": total_time
            },
            "performance": {
                "average_scan_time": avg_scan_time,
                "max_scan_time": max_scan_time,
                "min_scan_time": min_scan_time,
                "scans_per_minute": (successful_scans / total_time) * 60 if total_time > 0 else 0
            },
            "effectiveness": {
                "average_accuracy": avg_accuracy,
                "accuracy_distribution": self._calculate_distribution(accuracy_scores),
                "deterministic_scans": len([r for r in results if r.get("deterministic", False)])
            },
            "errors": {
                "error_types": errors,
                "most_common_error": max(errors.items(), key=lambda x: x[1]) if errors else None
            },
            "languages": {
                "language_distribution": language_counts,
                "unique_languages": len(language_counts)
            }
        }

    def _calculate_distribution(self, values: List[float]) -> Dict[str, int]:
        """Calculate distribution of values into buckets."""
        if not values:
            return {}

        distribution = {"0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}

        for value in values:
            if value < 0.2:
                distribution["0-0.2"] += 1
            elif value < 0.4:
                distribution["0.2-0.4"] += 1
            elif value < 0.6:
                distribution["0.4-0.6"] += 1
            elif value < 0.8:
                distribution["0.6-0.8"] += 1
            else:
                distribution["0.8-1.0"] += 1

        return distribution

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on regression test analysis."""
        recommendations = []

        summary = analysis["summary"]
        performance = analysis["performance"]
        effectiveness = analysis["effectiveness"]

        # Success rate recommendations
        if summary["success_rate"] < 0.95:
            recommendations.append("Improve scan success rate - investigate common failure modes")

        # Performance recommendations
        if performance["average_scan_time"] > 300:  # 5 minutes
            recommendations.append("Optimize scan performance - average scan time exceeds 5 minutes")

        if performance["max_scan_time"] > 600:  # 10 minutes
            recommendations.append("Address performance outliers - some scans take over 10 minutes")

        # Effectiveness recommendations
        if effectiveness["average_accuracy"] < 0.9:
            recommendations.append("Improve analysis accuracy - current average below 90%")

        if effectiveness["deterministic_scans"] < summary["successful_scans"] * 0.95:
            recommendations.append("Enhance determinism - less than 95% of scans are fully deterministic")

        return recommendations

    def _generate_summary_report(self, report: Dict[str, Any], output_file: Path):
        """Generate a human-readable summary report."""
        with open(output_file, 'w') as f:
            f.write("# Regression Testing Summary Report\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")

            # Summary section
            summary = report["analysis"]["summary"]
            f.write("## Summary\n\n")
            f.write(f"- **Total Repositories:** {summary['total_repositories']}\n")
            f.write(f"- **Successful Scans:** {summary['successful_scans']}\n")
            f.write(f"- **Failed Scans:** {summary['failed_scans']}\n")
            f.write(".1f")
            f.write(".1f")

            # Performance section
            perf = report["analysis"]["performance"]
            f.write("\n## Performance Metrics\n\n")
            f.write(".1f")
            f.write(".1f")
            f.write(".1f")
            f.write(".1f")

            # Effectiveness section
            eff = report["analysis"]["effectiveness"]
            f.write("\n## Effectiveness Metrics\n\n")
            f.write(".1f")
            f.write(f"- **Deterministic Scans:** {eff['deterministic_scans']}\n")

            # Recommendations
            recs = report["recommendations"]
            if recs:
                f.write("\n## Recommendations\n\n")
                for rec in recs:
                    f.write(f"- {rec}\n")

            f.write("\n---\n*Report generated by regression testing framework*")


def load_repository_list(file_path: str) -> List[str]:
    """Load repository list from file."""
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]


def main():
    """Main entry point for regression testing."""
    parser = argparse.ArgumentParser(description="Full Regression Testing")
    parser.add_argument("--repo-list", required=True, help="File containing repository URLs")
    parser.add_argument("--output-dir", default="regression_results", help="Output directory")
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum concurrent workers")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout per scan (seconds)")
    parser.add_argument("--limit", type=int, help="Limit number of repositories to test")

    args = parser.parse_args()

    # Load repository list
    try:
        repos = load_repository_list(args.repo_list)
        if args.limit:
            repos = repos[:args.limit]
        logger.info(f"Loaded {len(repos)} repositories for testing")
    except Exception as e:
        logger.error(f"Failed to load repository list: {e}")
        sys.exit(1)

    if len(repos) < 100:
        logger.warning(f"Only {len(repos)} repositories loaded. Regression testing typically requires 100+ repositories.")

    # Run regression testing
    tester = RegressionTester(max_workers=args.max_workers, timeout=args.timeout)
    results = tester.run_full_regression_test(repos, args.output_dir)

    # Print summary
    analysis = results["analysis"]
    summary = analysis["summary"]

    print("\n🎯 Regression Testing Complete!")
    print(f"📊 Repositories tested: {summary['total_repositories']}")
    print(".1f")
    print(".1f")

    if results["recommendations"]:
        print("\n📋 Recommendations:")
        for rec in results["recommendations"]:
            print(f"  - {rec}")

    # Exit with error if success rate is too low
    if summary["success_rate"] < 0.8:
        logger.error("Success rate below 80% - regression testing failed")
        sys.exit(1)


if __name__ == "__main__":
    main()