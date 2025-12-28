#!/usr/bin/env python3
"""
Continuous Validation Pipeline

This script runs automated validation of the repository scanner against the collected
validation dataset to ensure 100% effectiveness across all supported languages and
repository types.
"""

import json
import os
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import sys


class ValidationPipeline:
    """Runs continuous validation against the repository dataset."""

    def __init__(self, base_dir: str = "validation_data/repositories"):
        self.base_dir = Path(base_dir)
        self.metadata_file = self.base_dir / "repositories_metadata.json"
        self.results_dir = self.base_dir / "validation_results"
        self.results_dir.mkdir(exist_ok=True)

    def load_metadata(self) -> Dict[str, Any]:
        """Load repository metadata."""
        if not self.metadata_file.exists():
            return {}

        with open(self.metadata_file, 'r') as f:
            return json.load(f)

    def run_analysis_on_repository(self, repo_name: str, repo_path: Path) -> Dict[str, Any]:
        """Run repository scanner analysis on a single repository."""
        print(f"Analyzing {repo_name}...")

        start_time = time.time()

        try:
            # Import the scanner module
            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
            from core.pipeline.analysis import execute_pipeline

            # Run analysis
            result = execute_pipeline(str(repo_path))

            analysis_time = time.time() - start_time

            return {
                'repository': repo_name,
                'success': True,
                'analysis_time_seconds': analysis_time,
                'result': result,
                'error': None,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            analysis_time = time.time() - start_time
            print(f"Analysis failed for {repo_name}: {e}")

            return {
                'repository': repo_name,
                'success': False,
                'analysis_time_seconds': analysis_time,
                'result': None,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def run_validation_pipeline(self, max_repositories: Optional[int] = None) -> Dict[str, Any]:
        """Run validation pipeline on all collected repositories."""
        metadata = self.load_metadata()

        if not metadata:
            return {'error': 'No repository metadata found'}

        # Filter to collected repositories only
        collected_repos = {
            name: data for name, data in metadata.items()
            if data.get('validation_status') == 'collected'
        }

        if max_repositories:
            # Take first N repositories for testing
            collected_repos = dict(list(collected_repos.items())[:max_repositories])

        print(f"Running validation on {len(collected_repos)} repositories...")

        results = []
        language_stats = {}
        type_stats = {}
        performance_stats = {
            'total_analysis_time': 0,
            'successful_analyses': 0,
            'failed_analyses': 0,
            'average_analysis_time': 0
        }

        for repo_name, repo_data in collected_repos.items():
            repo_path = self.base_dir / repo_name

            if not repo_path.exists():
                print(f"Repository {repo_name} not found at {repo_path}")
                continue

            # Run analysis
            result = self.run_analysis_on_repository(repo_name, repo_path)
            results.append(result)

            # Update statistics
            language = repo_data.get('language', 'unknown')
            repo_type = repo_data.get('repo_type', 'unknown')

            if language not in language_stats:
                language_stats[language] = {'total': 0, 'successful': 0, 'failed': 0}
            if repo_type not in type_stats:
                type_stats[repo_type] = {'total': 0, 'successful': 0, 'failed': 0}

            language_stats[language]['total'] += 1
            type_stats[repo_type]['total'] += 1

            performance_stats['total_analysis_time'] += result['analysis_time_seconds']

            if result['success']:
                performance_stats['successful_analyses'] += 1
                language_stats[language]['successful'] += 1
                type_stats[repo_type]['successful'] += 1
            else:
                performance_stats['failed_analyses'] += 1
                language_stats[language]['failed'] += 1
                type_stats[repo_type]['failed'] += 1

        # Calculate averages
        total_analyses = len(results)
        if total_analyses > 0:
            performance_stats['average_analysis_time'] = performance_stats['total_analysis_time'] / total_analyses

        # Calculate success rates
        for lang_stats in language_stats.values():
            total = lang_stats['total']
            if total > 0:
                lang_stats['success_rate'] = lang_stats['successful'] / total

        for type_stats_item in type_stats.values():
            total = type_stats_item['total']
            if total > 0:
                type_stats_item['success_rate'] = type_stats_item['successful'] / total

        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'total_repositories_analyzed': total_analyses,
            'language_statistics': language_stats,
            'repository_type_statistics': type_stats,
            'performance_statistics': performance_stats,
            'overall_success_rate': performance_stats['successful_analyses'] / total_analyses if total_analyses > 0 else 0,
            'results': results
        }

        # Save results
        results_file = self.results_dir / f"validation_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(validation_results, f, indent=2, default=str)

        return validation_results

    def generate_validation_report(self, validation_results: Dict[str, Any]) -> str:
        """Generate a human-readable validation report."""
        report = []
        report.append("# Repository Scanner Validation Report")
        report.append(f"**Generated:** {validation_results['timestamp']}")
        report.append("")

        report.append("## Executive Summary")
        total = validation_results['total_repositories_analyzed']
        successful = validation_results['performance_statistics']['successful_analyses']
        success_rate = validation_results['overall_success_rate'] * 100

        report.append(f"- **Total Repositories Analyzed:** {total}")
        report.append(f"- **Successful Analyses:** {successful}")
        report.append(f"- **Success Rate:** {success_rate:.1f}%")
        report.append(f"- **Average Analysis Time:** {validation_results['performance_statistics']['average_analysis_time']:.2f} seconds")
        report.append("")

        # Language breakdown
        report.append("## Language Coverage")
        report.append("| Language | Total | Successful | Failed | Success Rate |")
        report.append("|----------|-------|------------|--------|--------------|")

        for lang, stats in validation_results['language_statistics'].items():
            success_rate_lang = stats.get('success_rate', 0) * 100
            report.append(f"| {lang} | {stats['total']} | {stats['successful']} | {stats['failed']} | {success_rate_lang:.1f}% |")

        report.append("")

        # Repository type breakdown
        report.append("## Repository Type Coverage")
        report.append("| Type | Total | Successful | Failed | Success Rate |")
        report.append("|------|-------|------------|--------|--------------|")

        for repo_type, stats in validation_results['repository_type_statistics'].items():
            success_rate_type = stats.get('success_rate', 0) * 100
            report.append(f"| {repo_type} | {stats['total']} | {stats['successful']} | {stats['failed']} | {success_rate_type:.1f}% |")

        report.append("")

        # Performance analysis
        report.append("## Performance Analysis")
        perf = validation_results['performance_statistics']
        report.append(f"- **Total Analysis Time:** {perf['total_analysis_time']:.2f} seconds")
        report.append(f"- **Average per Repository:** {perf['average_analysis_time']:.2f} seconds")
        report.append(f"- **Fastest Analysis:** {min(r['analysis_time_seconds'] for r in validation_results['results']):.2f} seconds")
        report.append(f"- **Slowest Analysis:** {max(r['analysis_time_seconds'] for r in validation_results['results']):.2f} seconds")
        report.append("")

        # Failure analysis
        failed_results = [r for r in validation_results['results'] if not r['success']]
        if failed_results:
            report.append("## Analysis Failures")
            for failure in failed_results:
                report.append(f"- **{failure['repository']}:** {failure['error']}")
            report.append("")

        # Success criteria check
        report.append("## Success Criteria Assessment")
        success_criteria = [
            ("100% Analysis Success Rate", success_rate >= 100.0),
            ("All Languages Supported", all(stats.get('success_rate', 0) > 0 for stats in validation_results['language_statistics'].values())),
            ("Reasonable Performance (< 30s avg)", perf['average_analysis_time'] < 30.0),
        ]

        for criterion, met in success_criteria:
            status = "✅ PASS" if met else "❌ FAIL"
            report.append(f"- {status}: {criterion}")

        return "\n".join(report)


def main():
    """Main validation function."""
    import argparse

    parser = argparse.ArgumentParser(description="Run repository scanner validation pipeline")
    parser.add_argument("--max-repositories", type=int, help="Maximum number of repositories to analyze")
    parser.add_argument("--generate-report", action="store_true", help="Generate validation report")

    args = parser.parse_args()

    pipeline = ValidationPipeline()

    print("Starting validation pipeline...")
    results = pipeline.run_validation_pipeline(max_repositories=args.max_repositories)

    if args.generate_report:
        report = pipeline.generate_validation_report(results)
        report_file = pipeline.results_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"Report saved to: {report_file}")

    # Print summary
    print("\n=== Validation Summary ===")
    print(f"Total repositories analyzed: {results['total_repositories_analyzed']}")
    success_rate = results['overall_success_rate'] * 100
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Average analysis time: {results['performance_statistics']['average_analysis_time']:.2f} seconds")
    if success_rate >= 100.0:
        print("🎉 VALIDATION SUCCESSFUL: 100% effectiveness achieved!")
    else:
        print(f"⚠️  VALIDATION INCOMPLETE: {success_rate:.1f}% success rate")


if __name__ == "__main__":
    main()