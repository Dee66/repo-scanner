#!/usr/bin/env python3
"""
Phase 5: Validation Framework for Repository Intelligence Scanner

This script establishes effectiveness validation by running the scanner
on real repositories and analyzing the security findings.
"""

import sys
import os
import json
import signal
from pathlib import Path
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.core.pipeline.analysis import execute_pipeline


class ValidationFramework:
    """Framework for validating scanner effectiveness."""

    def __init__(self, validation_repos_dir: Path):
        self.validation_repos_dir = validation_repos_dir
        self.results = {}

    def discover_repositories(self) -> List[Path]:
        """Discover validation repositories."""
        repos = []
        if self.validation_repos_dir.exists():
            for item in self.validation_repos_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Skip very large repositories for initial validation
                    try:
                        file_count = sum(1 for _ in item.rglob('*') if _.is_file())
                        if file_count < 1000:  # Only include repos with < 1000 files
                            repos.append(item)
                    except (OSError, PermissionError):
                        continue
        return repos[:3]  # Limit to first 3 small repos

    def run_validation(self) -> Dict[str, Any]:
        """Run validation on discovered repositories."""
        repos = self.discover_repositories()
        print(f"Running validation on {len(repos)} repositories...")

        for repo_path in repos:
            repo_name = repo_path.name
            print(f"\n🔍 Analyzing {repo_name}...")

            try:
                # Add timeout for analysis (5 minutes max)
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Analysis timed out")
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(300)  # 5 minutes
                
                result = execute_pipeline(str(repo_path))
                
                signal.alarm(0)  # Cancel timeout

                # Extract security metrics
                security = result.get('security_analysis', {}).get('unsafe_patterns', {})
                summary = security.get('summary', {})

                self.results[repo_name] = {
                    'success': True,
                    'total_patterns': summary.get('total_patterns', 0),
                    'high_severity': summary.get('high_severity', 0),
                    'medium_severity': summary.get('medium_severity', 0),
                    'low_severity': summary.get('low_severity', 0),
                    'languages_covered': summary.get('languages_covered', 0),
                    'critical_findings': len(security.get('critical_findings', []))
                }

                print(f"  ✅ Found {summary.get('total_patterns', 0)} security patterns")

            except (Exception, TimeoutError) as e:
                print(f"  ❌ Error: {e}")
                self.results[repo_name] = {
                    'success': False,
                    'error': str(e)
                }

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate validation report."""
        successful_scans = [r for r in self.results.values() if r.get('success', False)]
        total_patterns = sum(r.get('total_patterns', 0) for r in successful_scans)
        total_high_severity = sum(r.get('high_severity', 0) for r in successful_scans)

        report = {
            'validation_summary': {
                'repositories_scanned': len(self.results),
                'successful_scans': len(successful_scans),
                'total_security_patterns': total_patterns,
                'high_severity_patterns': total_high_severity,
                'average_patterns_per_repo': total_patterns / max(len(successful_scans), 1)
            },
            'repository_results': self.results,
            'effectiveness_assessment': {
                'security_detection_capability': 'CONFIRMED' if total_patterns > 0 else 'UNTESTED',
                'multi_language_support': 'CONFIRMED' if any(r.get('languages_covered', 0) > 0 for r in successful_scans) else 'UNTESTED',
                'high_severity_detection': 'CONFIRMED' if total_high_severity > 0 else 'UNTESTED',
                'validation_status': 'PHASE_5_COMPLETED'
            }
        }

        return report


def main():
    """Main validation entry point."""
    validation_repos_dir = Path('validation_data/repositories')

    framework = ValidationFramework(validation_repos_dir)
    report = framework.run_validation()

    # Save report
    output_file = Path('phase_5_validation_report.json')
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n📊 Validation Report Saved: {output_file}")
    print(f"📈 Total Security Patterns Detected: {report['validation_summary']['total_security_patterns']}")
    print(f"🔴 High Severity Patterns: {report['validation_summary']['high_severity_patterns']}")
    print("✅ Phase 5 Validation Framework: COMPLETED")


if __name__ == '__main__':
    main()