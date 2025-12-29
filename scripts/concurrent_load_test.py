#!/usr/bin/env python3
"""
Concurrent Load Testing for Repository Intelligence Scanner

Tests the system's ability to handle concurrent repository analysis scenarios.
This validates performance under load and ensures thread safety.
"""

import json
import os
import time
import threading
import statistics
import queue
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys


class ConcurrentLoadTester:
    """Tests concurrent repository analysis scenarios."""

    def __init__(self, base_dir: str = "validation_data/repositories",
                 num_concurrent: int = 5, duration: int = 300):
        self.base_dir = Path(base_dir)
        self.metadata_file = self.base_dir / "repositories_metadata.json"
        self.num_concurrent = num_concurrent
        self.duration = duration
        self.results = []
        self.stop_flag = threading.Event()
        self.lock = threading.Lock()

    def load_metadata(self) -> Dict[str, Any]:
        """Load repository metadata."""
        if not self.metadata_file.exists():
            return {}

        with open(self.metadata_file, 'r') as f:
            return json.load(f)

    def analyze_repository(self, repo_name: str, repo_path: Path) -> Dict[str, Any]:
        """Analyze a single repository."""
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
                'analysis_time': analysis_time,
                'result': result,
                'error': None,
                'timestamp': datetime.now().isoformat(),
                'thread_id': threading.current_thread().ident
            }

        except Exception as e:
            analysis_time = time.time() - start_time
            print(f"Analysis failed for {repo_name}: {e}")

            return {
                'repository': repo_name,
                'success': False,
                'analysis_time': analysis_time,
                'result': None,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'thread_id': threading.current_thread().ident
            }

    def worker(self, repo_queue: queue.Queue) -> List[Dict[str, Any]]:
        """Worker thread that processes repositories from queue."""
        results = []

        while not self.stop_flag.is_set():
            try:
                repo_name, repo_path = repo_queue.get(timeout=1.0)
                result = self.analyze_repository(repo_name, repo_path)

                with self.lock:
                    results.append(result)

                # Small delay to prevent overwhelming the system
                time.sleep(0.1)

            except queue.Empty:
                # Queue is empty
                break
            except Exception as e:
                print(f"Worker error: {e}")
                break

        return results

    def run_concurrent_load_test(self) -> Dict[str, Any]:
        """Run concurrent load testing."""
        metadata = self.load_metadata()

        if not metadata:
            return {'error': 'No repository metadata found'}

        # Filter to collected repositories only
        collected_repos = [
            (name, self.base_dir / name)
            for name, data in metadata.items()
            if data.get('validation_status') == 'collected'
        ]

        if len(collected_repos) < self.num_concurrent:
            print(f"Warning: Only {len(collected_repos)} repositories available, reducing concurrency to {len(collected_repos)}")
            self.num_concurrent = len(collected_repos)

        print(f"Starting concurrent load test: {self.num_concurrent} concurrent analyses, {self.duration} seconds duration")
        print(f"Testing with {len(collected_repos)} repositories")

        start_time = time.time()
        all_results = []

        # Create repository queue (thread-safe)
        repo_queue = queue.Queue()
        for repo in collected_repos:
            repo_queue.put(repo)

        # Start worker threads
        with ThreadPoolExecutor(max_workers=self.num_concurrent) as executor:
            futures = [executor.submit(self.worker, repo_queue) for _ in range(self.num_concurrent)]

            # Let it run for the specified duration or until all repos are processed
            end_time = time.time() + self.duration
            while time.time() < end_time and repo_queue:
                time.sleep(1)

            # Signal workers to stop
            self.stop_flag.set()

            # Collect results from all workers
            for future in as_completed(futures):
                try:
                    worker_results = future.result(timeout=10)
                    all_results.extend(worker_results)
                except Exception as e:
                    print(f"Error collecting worker results: {e}")

        total_time = time.time() - start_time

        # Analyze results
        return self.analyze_results(all_results, total_time)

    def analyze_results(self, results: List[Dict[str, Any]], total_time: float) -> Dict[str, Any]:
        """Analyze load test results."""
        if not results:
            return {'error': 'No results collected'}

        # Basic statistics
        successful_analyses = [r for r in results if r['success']]
        failed_analyses = [r for r in results if not r['success']]

        analysis_times = [r['analysis_time'] for r in results]

        # Thread utilization
        thread_ids = set(r.get('thread_id') for r in results if r.get('thread_id'))
        active_threads = len(thread_ids)

        # Performance metrics
        total_analyses = len(results)
        success_rate = len(successful_analyses) / total_analyses if total_analyses > 0 else 0
        analyses_per_second = total_analyses / total_time if total_time > 0 else 0

        return {
            'test_duration_seconds': total_time,
            'concurrent_threads': self.num_concurrent,
            'active_threads': active_threads,
            'total_analyses': total_analyses,
            'successful_analyses': len(successful_analyses),
            'failed_analyses': len(failed_analyses),
            'success_rate': success_rate,
            'analyses_per_second': analyses_per_second,
            'avg_analysis_time': statistics.mean(analysis_times) if analysis_times else 0,
            'median_analysis_time': statistics.median(analysis_times) if analysis_times else 0,
            'min_analysis_time': min(analysis_times) if analysis_times else 0,
            'max_analysis_time': max(analysis_times) if analysis_times else 0,
            'p95_analysis_time': sorted(analysis_times)[int(len(analysis_times) * 0.95)] if len(analysis_times) > 1 else 0,
            'results': results,
            'failure_analysis': self.analyze_failures(failed_analyses)
        }

    def analyze_failures(self, failed_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze failure patterns."""
        if not failed_results:
            return {'no_failures': True}

        error_counts = {}
        for result in failed_results:
            error = result.get('error', 'Unknown error')
            # Group similar errors
            error_key = error.split(':')[0] if ':' in error else error
            error_counts[error_key] = error_counts.get(error_key, 0) + 1

        return {
            'total_failures': len(failed_results),
            'error_distribution': error_counts,
            'most_common_error': max(error_counts.items(), key=lambda x: x[1]) if error_counts else None
        }


def main():
    """Main load testing function."""
    import argparse

    parser = argparse.ArgumentParser(description="Concurrent Load Testing for Repository Scanner")
    parser.add_argument("--concurrent", type=int, default=5, help="Number of concurrent analyses")
    parser.add_argument("--duration", type=int, default=300, help="Test duration in seconds")
    parser.add_argument("--generate-report", action="store_true", help="Generate detailed report")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    tester = ConcurrentLoadTester(
        num_concurrent=args.concurrent,
        duration=args.duration
    )

    print("Starting concurrent load testing...")
    results = tester.run_concurrent_load_test()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        # Print summary
        print("\n=== Concurrent Load Test Results ===")
        print(f"Test Duration: {results['test_duration_seconds']:.1f} seconds")
        print(f"Concurrent Threads: {results['concurrent_threads']}")
        print(f"Active Threads: {results['active_threads']}")
        print(f"Total Analyses: {results['total_analyses']}")
        print(f"Successful: {results['successful_analyses']}")
        print(f"Failed: {results['failed_analyses']}")
        print(f"Success Rate: {results['success_rate']:.1%}")
        print(f"Analyses/Second: {results['analyses_per_second']:.2f}")
        print(f"Avg Analysis Time: {results['avg_analysis_time']:.2f}s")
        print(f"Median Analysis Time: {results['median_analysis_time']:.2f}s")
        print(f"P95 Analysis Time: {results['p95_analysis_time']:.2f}s")

        if results.get('failure_analysis', {}).get('total_failures', 0) > 0:
            print(f"\nFailures: {results['failure_analysis']['total_failures']}")
            for error, count in results['failure_analysis']['error_distribution'].items():
                print(f"  {error}: {count}")

    if args.generate_report:
        report_file = Path("validation_data/repositories") / "concurrent_load_test_report.json"
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nDetailed report saved to: {report_file}")


if __name__ == "__main__":
    main()