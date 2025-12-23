#!/usr/bin/env python3
"""
Enterprise Performance Benchmarking Suite

Comprehensive performance testing and benchmarking for Repository Intelligence Scanner
including load testing, stress testing, and performance regression detection.
"""

import argparse
import asyncio
import aiohttp
import time
import json
import statistics
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import matplotlib.pyplot as plt
import numpy as np

@dataclass
class BenchmarkResult:
    """Result of a benchmark test."""
    test_name: str
    duration: float
    requests_per_second: float
    avg_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    success_rate: float
    error_count: int
    total_requests: int
    timestamp: str

@dataclass
class LoadTestConfig:
    """Configuration for load testing."""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = None
    payload: Dict[str, Any] = None
    concurrent_users: int = 10
    total_requests: int = 1000
    ramp_up_time: int = 30
    test_duration: int = 300
    timeout: int = 30

class PerformanceBenchmarker:
    """Enterprise performance benchmarking suite."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session_headers = {}
        if api_key:
            self.session_headers['Authorization'] = f'Bearer {api_key}'

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    async def make_request(self, session: aiohttp.ClientSession,
                          endpoint: str, method: str = "GET",
                          payload: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a single HTTP request."""
        start_time = time.time()
        try:
            url = f"{self.base_url}{endpoint}"
            async with session.request(method, url, json=payload,
                                     timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_time = time.time() - start_time
                return {
                    'status': response.status,
                    'response_time': response_time,
                    'success': response.status < 400,
                    'data': await response.text()
                }
        except Exception as e:
            return {
                'status': 0,
                'response_time': time.time() - start_time,
                'success': False,
                'error': str(e)
            }

    async def run_load_test(self, config: LoadTestConfig) -> BenchmarkResult:
        """Run a comprehensive load test."""
        self.logger.info(f"Starting load test: {config.concurrent_users} users, "
                        f"{config.total_requests} requests")

        response_times = []
        success_count = 0
        error_count = 0

        async with aiohttp.ClientSession(headers=self.session_headers) as session:
            # Ramp up users gradually
            semaphore = asyncio.Semaphore(config.concurrent_users)

            async def worker():
                async with semaphore:
                    result = await self.make_request(session, "/", config.method, config.payload)
                    return result

            # Run the test
            start_time = time.time()
            tasks = []

            for i in range(config.total_requests):
                # Ramp up delay
                if config.ramp_up_time > 0:
                    delay = (i / config.total_requests) * config.ramp_up_time
                    await asyncio.sleep(delay / config.total_requests)

                task = asyncio.create_task(worker())
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_duration = time.time() - start_time

            # Process results
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                    continue

                response_times.append(result['response_time'])
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1

        # Calculate statistics
        if response_times:
            avg_response_time = statistics.mean(response_times)
            median_response_time = statistics.median(response_times)
            p95_response_time = np.percentile(response_times, 95)
            p99_response_time = np.percentile(response_times, 99)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = median_response_time = p95_response_time = p99_response_time = 0
            min_response_time = max_response_time = 0

        requests_per_second = len(response_times) / total_duration if total_duration > 0 else 0
        success_rate = success_count / config.total_requests if config.total_requests > 0 else 0

        return BenchmarkResult(
            test_name=f"load_test_{config.concurrent_users}users",
            duration=total_duration,
            requests_per_second=requests_per_second,
            avg_response_time=avg_response_time,
            median_response_time=median_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            success_rate=success_rate,
            error_count=error_count,
            total_requests=config.total_requests,
            timestamp=time.strftime('%Y-%m-%d %H:%M:%S')
        )

    async def run_health_check_benchmark(self) -> BenchmarkResult:
        """Benchmark health check endpoint."""
        config = LoadTestConfig(
            url=f"{self.base_url}/health",
            concurrent_users=50,
            total_requests=1000,
            test_duration=60
        )
        return await self.run_load_test(config)

    async def run_api_scan_benchmark(self, repo_url: str) -> BenchmarkResult:
        """Benchmark repository scanning API."""
        payload = {
            "repository_url": repo_url,
            "analysis_depth": "standard",
            "include_security": True
        }

        config = LoadTestConfig(
            url=f"{self.base_url}/scan",
            method="POST",
            payload=payload,
            concurrent_users=5,
            total_requests=50,
            test_duration=300
        )
        return await self.run_load_test(config)

    def generate_report(self, results: List[BenchmarkResult],
                       output_file: str = "benchmark_report.json"):
        """Generate comprehensive benchmark report."""
        report = {
            'summary': {
                'total_tests': len(results),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'system_info': {
                    'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
                    'platform': __import__('platform').platform()
                }
            },
            'results': [asdict(result) for result in results],
            'analysis': self._analyze_results(results)
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Benchmark report saved to {output_file}")
        return report

    def _analyze_results(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Analyze benchmark results for insights."""
        if not results:
            return {}

        # Performance analysis
        avg_rps = statistics.mean([r.requests_per_second for r in results])
        avg_response_time = statistics.mean([r.avg_response_time for r in results])
        avg_success_rate = statistics.mean([r.success_rate for r in results])

        # Identify bottlenecks
        slow_tests = [r for r in results if r.avg_response_time > 1.0]
        failing_tests = [r for r in results if r.success_rate < 0.95]

        return {
            'overall_performance': {
                'average_rps': avg_rps,
                'average_response_time': avg_response_time,
                'average_success_rate': avg_success_rate
            },
            'bottlenecks': {
                'slow_tests': [r.test_name for r in slow_tests],
                'failing_tests': [r.test_name for r in failing_tests]
            },
            'recommendations': self._generate_recommendations(results)
        }

    def _generate_recommendations(self, results: List[BenchmarkResult]) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []

        avg_rps = statistics.mean([r.requests_per_second for r in results])
        avg_success = statistics.mean([r.success_rate for r in results])

        if avg_rps < 10:
            recommendations.append("Consider increasing server resources or optimizing application performance")
        if avg_success < 0.95:
            recommendations.append("High error rate detected - investigate server stability and error handling")
        if any(r.avg_response_time > 5 for r in results):
            recommendations.append("Response times are high - consider caching, database optimization, or async processing")

        return recommendations

    def create_performance_chart(self, results: List[BenchmarkResult],
                               output_file: str = "performance_chart.png"):
        """Create performance visualization chart."""
        try:
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))

            # Response time distribution
            response_times = []
            for result in results:
                response_times.extend([result.avg_response_time] * result.total_requests)
            ax1.hist(response_times, bins=50, alpha=0.7)
            ax1.set_title('Response Time Distribution')
            ax1.set_xlabel('Response Time (s)')
            ax1.set_ylabel('Frequency')

            # Requests per second
            test_names = [r.test_name for r in results]
            rps_values = [r.requests_per_second for r in results]
            ax2.bar(test_names, rps_values)
            ax2.set_title('Requests per Second')
            ax2.set_ylabel('RPS')
            ax2.tick_params(axis='x', rotation=45)

            # Success rate
            success_rates = [r.success_rate * 100 for r in results]
            ax3.bar(test_names, success_rates)
            ax3.set_title('Success Rate')
            ax3.set_ylabel('Success Rate (%)')
            ax3.set_ylim(0, 100)
            ax3.tick_params(axis='x', rotation=45)

            # P95 response time
            p95_times = [r.p95_response_time for r in results]
            ax4.bar(test_names, p95_times)
            ax4.set_title('P95 Response Time')
            ax4.set_ylabel('P95 Time (s)')
            ax4.tick_params(axis='x', rotation=45)

            plt.tight_layout()
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            plt.close()

            self.logger.info(f"Performance chart saved to {output_file}")

        except ImportError:
            self.logger.warning("matplotlib not available, skipping chart generation")

async def main():
    """Main benchmarking function."""
    parser = argparse.ArgumentParser(description='Repository Scanner Performance Benchmarking')
    parser.add_argument('--url', required=True, help='Base URL of the API')
    parser.add_argument('--api-key', help='API key for authentication')
    parser.add_argument('--test-type', choices=['health', 'scan', 'full'],
                       default='full', help='Type of benchmark to run')
    parser.add_argument('--repo-url', default='https://github.com/microsoft/vscode',
                       help='Repository URL for scan testing')
    parser.add_argument('--output', default='benchmark_report.json',
                       help='Output file for results')
    parser.add_argument('--chart', default='performance_chart.png',
                       help='Output file for performance chart')

    args = parser.parse_args()

    benchmarker = PerformanceBenchmarker(args.url, args.api_key)
    results = []

    try:
        if args.test_type in ['health', 'full']:
            print("Running health check benchmark...")
            health_result = await benchmarker.run_health_check_benchmark()
            results.append(health_result)
            print(".2f")

        if args.test_type in ['scan', 'full']:
            print("Running scan API benchmark...")
            scan_result = await benchmarker.run_api_scan_benchmark(args.repo_url)
            results.append(scan_result)
            print(".2f")

        # Generate report
        report = benchmarker.generate_report(results, args.output)
        benchmarker.create_performance_chart(results, args.chart)

        print(f"\nBenchmarking complete!")
        print(f"Results saved to: {args.output}")
        print(f"Chart saved to: {args.chart}")

        # Print summary
        print("\nSummary:")
        for result in results:
            print(f"- {result.test_name}: {result.requests_per_second:.1f} RPS, "
                  f"{result.avg_response_time:.3f}s avg, "
                  f"{result.success_rate*100:.1f}% success")

    except Exception as e:
        print(f"Benchmarking failed: {e}")
        return 1

    return 0

if __name__ == "__main__":
    asyncio.run(main())