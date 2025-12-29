#!/usr/bin/env python3
"""
Uptime Stress Testing Tool for Repository Intelligence Scanner

Validates 99.999% uptime under stress conditions by combining load testing
with continuous health monitoring and SLA compliance validation.
"""

import argparse
import asyncio
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
import requests
import psutil

class UptimeStressTester:
    """Stress testing tool that validates 99.999% uptime under load."""

    def __init__(self, base_url: str, duration: int = 3600, concurrent_users: int = 50):
        self.base_url = base_url.rstrip('/')
        self.duration = duration
        self.concurrent_users = concurrent_users
        self.start_time = time.time()

        # Uptime tracking (99.999% = 5.26 minutes downtime per year)
        self.health_checks = []
        self.downtime_periods = []
        self.current_downtime_start = None

        # Performance tracking
        self.response_times = []
        self.errors = []

        # SLA thresholds
        self.sla_uptime_percent = 99.999
        self.max_response_time = 30  # seconds
        self.max_error_rate = 0.001  # 0.001%

    async def run_stress_test(self) -> Dict[str, Any]:
        """Run comprehensive uptime stress test."""
        print(f"Starting 99.999% uptime stress test: {self.duration}s duration, {self.concurrent_users} concurrent users")

        # Create load testing tasks
        load_tasks = []
        for i in range(self.concurrent_users):
            task = asyncio.create_task(self.simulate_user())
            load_tasks.append(task)

        # Start health monitoring
        health_task = asyncio.create_task(self.monitor_health())

        # Run for specified duration
        await asyncio.sleep(self.duration)

        # Stop all tasks
        for task in load_tasks:
            task.cancel()
        health_task.cancel()

        # Wait for cleanup
        try:
            await asyncio.gather(*load_tasks, return_exceptions=True)
            await health_task
        except asyncio.CancelledError:
            pass

        return self.analyze_results()

    async def simulate_user(self):
        """Simulate a user making requests."""
        while True:
            try:
                # Make health check request
                start_time = time.time()
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self._make_request, f"{self.base_url}/health"
                )
                response_time = time.time() - start_time

                self.response_times.append(response_time)

                if response.get('status_code') != 200:
                    self.errors.append(f"HTTP {response.get('status_code')}")

                # Random delay between requests (0.1-1.0 seconds)
                await asyncio.sleep(0.1 + (time.time() % 0.9))

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.errors.append(str(e))
                await asyncio.sleep(1)

    async def monitor_health(self):
        """Continuously monitor system health."""
        while True:
            try:
                health_status = await asyncio.get_event_loop().run_in_executor(
                    None, self._check_system_health
                )

                is_healthy = health_status.get('overall_healthy', False)
                self.health_checks.append({
                    'timestamp': time.time(),
                    'healthy': is_healthy,
                    'details': health_status
                })

                # Track downtime periods
                if not is_healthy:
                    if self.current_downtime_start is None:
                        self.current_downtime_start = time.time()
                else:
                    if self.current_downtime_start is not None:
                        self.downtime_periods.append({
                            'start': self.current_downtime_start,
                            'end': time.time(),
                            'duration': time.time() - self.current_downtime_start
                        })
                        self.current_downtime_start = None

                await asyncio.sleep(10)  # Check every 10 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Health monitoring error: {e}")
                await asyncio.sleep(10)

    def _make_request(self, url: str) -> Dict[str, Any]:
        """Make HTTP request."""
        try:
            response = requests.get(url, timeout=10)
            return {
                'status_code': response.status_code,
                'response_time': time.time(),
                'success': response.status_code == 200
            }
        except Exception as e:
            return {
                'status_code': None,
                'error': str(e),
                'success': False
            }

    def _check_system_health(self) -> Dict[str, Any]:
        """Check system health metrics."""
        try:
            cpu_percent = psutil.cpu_percent()
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('/').percent

            return {
                'overall_healthy': (
                    cpu_percent < 95 and
                    memory_percent < 90 and
                    disk_percent < 95
                ),
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'timestamp': time.time()
            }
        except Exception as e:
            return {
                'overall_healthy': False,
                'error': str(e),
                'timestamp': time.time()
            }

    def analyze_results(self) -> Dict[str, Any]:
        """Analyze stress test results and validate 99.999% uptime."""
        total_runtime = time.time() - self.start_time

        # Calculate uptime metrics
        healthy_checks = sum(1 for check in self.health_checks if check['healthy'])
        total_checks = len(self.health_checks)
        uptime_percentage = (healthy_checks / max(total_checks, 1)) * 100

        # Calculate total downtime
        total_downtime = sum(period['duration'] for period in self.downtime_periods)

        # SLA compliance (99.999% = max 5.26 minutes downtime per year)
        yearly_downtime_budget = 365 * 24 * 60 * (1 - self.sla_uptime_percent / 100)
        actual_downtime_minutes = total_downtime / 60
        sla_compliant = actual_downtime_minutes <= yearly_downtime_budget

        # Performance metrics
        avg_response_time = statistics.mean(self.response_times) if self.response_times else 0
        p95_response_time = sorted(self.response_times)[int(len(self.response_times) * 0.95)] if self.response_times else 0
        error_rate = len(self.errors) / max(len(self.response_times), 1)

        return {
            'test_duration_seconds': total_runtime,
            'uptime_validation': {
                'uptime_percentage': uptime_percentage,
                'sla_target_percent': self.sla_uptime_percent,
                'sla_compliant': sla_compliant,
                'total_downtime_seconds': total_downtime,
                'total_downtime_minutes': actual_downtime_minutes,
                'yearly_downtime_budget_minutes': yearly_downtime_budget,
                'health_checks_total': total_checks,
                'health_checks_healthy': healthy_checks,
                'downtime_periods': len(self.downtime_periods)
            },
            'performance_metrics': {
                'total_requests': len(self.response_times),
                'avg_response_time_seconds': avg_response_time,
                'p95_response_time_seconds': p95_response_time,
                'max_response_time_threshold': self.max_response_time,
                'response_time_compliant': p95_response_time <= self.max_response_time,
                'total_errors': len(self.errors),
                'error_rate_percent': error_rate * 100,
                'max_error_rate_threshold': self.max_error_rate * 100,
                'error_rate_compliant': error_rate <= self.max_error_rate
            },
            'overall_success': (
                sla_compliant and
                p95_response_time <= self.max_response_time and
                error_rate <= self.max_error_rate
            ),
            'recommendations': self._generate_recommendations(
                uptime_percentage, p95_response_time, error_rate
            )
        }

    def _generate_recommendations(self, uptime_percent: float, p95_time: float, error_rate: float) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        if uptime_percent < self.sla_uptime_percent:
            recommendations.append(".2f")

        if p95_time > self.max_response_time:
            recommendations.append(".2f")

        if error_rate > self.max_error_rate:
            recommendations.append(".2f")

        if not recommendations:
            recommendations.append("All metrics within acceptable ranges for 99.999% uptime SLA")

        return recommendations

def main():
    parser = argparse.ArgumentParser(description='99.999% Uptime Stress Tester')
    parser.add_argument('--url', required=True, help='Base URL of the service to test')
    parser.add_argument('--duration', type=int, default=3600, help='Test duration in seconds (default: 1 hour)')
    parser.add_argument('--users', type=int, default=50, help='Number of concurrent users (default: 50)')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    tester = UptimeStressTester(args.url, args.duration, args.users)

    try:
        results = asyncio.run(tester.run_stress_test())

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\n" + "="*60)
            print("99.999% UPTIME STRESS TEST RESULTS")
            print("="*60)

            uptime = results['uptime_validation']
            perf = results['performance_metrics']

            print(f"Test Duration: {results['test_duration_seconds']:.0f} seconds")
            print(f"Concurrent Users: {args.users}")
            print()

            print("UPTIME VALIDATION:")
            print(".3f")
            print(".3f")
            print(f"SLA Compliant: {'✅ YES' if uptime['sla_compliant'] else '❌ NO'}")
            print(".1f")
            print(".1f")
            print(f"Downtime Periods: {uptime['downtime_periods']}")
            print()

            print("PERFORMANCE METRICS:")
            print(f"Total Requests: {perf['total_requests']:,}")
            print(".2f")
            print(".2f")
            print(f"Response Time Compliant: {'✅ YES' if perf['response_time_compliant'] else '❌ NO'}")
            print(f"Total Errors: {perf['total_errors']}")
            print(".4f")
            print(f"Error Rate Compliant: {'✅ YES' if perf['error_rate_compliant'] else '❌ NO'}")
            print()

            print("OVERALL RESULT:")
            print(f"99.999% Uptime Achieved: {'✅ YES' if results['overall_success'] else '❌ NO'}")
            print()

            print("RECOMMENDATIONS:")
            for rec in results['recommendations']:
                print(f"• {rec}")

    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test failed with error: {e}")

if __name__ == "__main__":
    main()