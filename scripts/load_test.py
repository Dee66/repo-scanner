#!/usr/bin/env python3
"""
Simple Load Testing Tool for Repository Intelligence Scanner

Generates configurable HTTP load against the API for basic performance testing.
"""

import argparse
import requests
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

class LoadTester:
    """Simple load testing tool."""

    def __init__(self, url: str, num_threads: int = 10, duration: int = 60):
        self.url = url
        self.num_threads = num_threads
        self.duration = duration
        self.results = []
        self.stop_flag = threading.Event()

    def make_request(self) -> Dict[str, Any]:
        """Make a single request and measure response time."""
        start_time = time.time()
        try:
            response = requests.get(self.url, timeout=10)
            response_time = time.time() - start_time
            return {
                'success': response.status_code == 200,
                'response_time': response_time,
                'status_code': response.status_code
            }
        except Exception as e:
            response_time = time.time() - start_time
            return {
                'success': False,
                'response_time': response_time,
                'error': str(e)
            }

    def worker(self) -> List[Dict[str, Any]]:
        """Worker thread that makes requests."""
        results = []
        while not self.stop_flag.is_set():
            result = self.make_request()
            results.append(result)
            time.sleep(0.1)  # Rate limiting
        return results

    def run_test(self) -> Dict[str, Any]:
        """Run the load test."""
        print(f"Starting load test: {self.num_threads} threads, {self.duration} seconds")

        # Start worker threads
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = [executor.submit(self.worker) for _ in range(self.num_threads)]

            # Let it run for the specified duration
            time.sleep(self.duration)
            self.stop_flag.set()

            # Collect results
            for future in as_completed(futures):
                self.results.extend(future.result())

        # Analyze results
        return self.analyze_results()

    def analyze_results(self) -> Dict[str, Any]:
        """Analyze test results."""
        if not self.results:
            return {'error': 'No results collected'}

        response_times = [r['response_time'] for r in self.results]
        success_count = sum(1 for r in r if r['success'])
        total_requests = len(self.results)

        return {
            'total_requests': total_requests,
            'successful_requests': success_count,
            'failed_requests': total_requests - success_count,
            'success_rate': success_count / total_requests if total_requests > 0 else 0,
            'requests_per_second': total_requests / self.duration,
            'avg_response_time': statistics.mean(response_times),
            'median_response_time': statistics.median(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'p95_response_time': sorted(response_times)[int(len(response_times) * 0.95)] if response_times else 0
        }

def main():
    parser = argparse.ArgumentParser(description='Simple Load Tester')
    parser.add_argument('--url', required=True, help='URL to test')
    parser.add_argument('--threads', type=int, default=10, help='Number of concurrent threads')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    tester = LoadTester(args.url, args.threads, args.duration)
    results = tester.run_test()

    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        print("Load Test Results:")
        print(f"Total Requests: {results['total_requests']}")
        print(f"Successful: {results['successful_requests']}")
        print(f"Failed: {results['failed_requests']}")
        print(".1f")
        print(".2f")
        print(".3f")
        print(".3f")
        print(".3f")
        print(".3f")
        print(".3f")

if __name__ == "__main__":
    main()