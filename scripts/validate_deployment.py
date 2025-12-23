#!/usr/bin/env python3
"""
Enterprise Deployment Validation Script

Validates production deployment of Repository Intelligence Scanner
across multiple dimensions: functionality, performance, security, and monitoring.
"""

import argparse
import requests
import time
import json
import subprocess
import sys
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class ValidationResult:
    """Result of a validation check."""
    check_name: str
    status: str  # 'PASS', 'FAIL', 'WARN'
    message: str
    details: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None

class DeploymentValidator:
    """Validates enterprise deployment of Repository Intelligence Scanner."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})

    def run_validation(self) -> List[ValidationResult]:
        """Run all validation checks."""
        checks = [
            self._check_api_health,
            self._check_monitoring_endpoints,
            self._check_basic_functionality,
            self._check_performance_metrics,
            self._check_security_headers,
            self._check_rate_limiting,
            self._load_testing,
        ]

        results = []
        for check in checks:
            try:
                start_time = time.time()
                result = check()
                result.duration = time.time() - start_time
                results.append(result)
                print(f"{'✅' if result.status == 'PASS' else '❌' if result.status == 'FAIL' else '⚠️'} {result.check_name}: {result.message}")
            except Exception as e:
                results.append(ValidationResult(
                    check_name=check.__name__.replace('_check_', '').replace('_', ' ').title(),
                    status='FAIL',
                    message=f'Check failed with error: {e}',
                    duration=time.time() - start_time
                ))

        return results

    def _check_api_health(self) -> ValidationResult:
        """Check basic API health."""
        try:
            response = self.session.get(f'{self.base_url}/health', timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') in ['healthy', 'ok']:
                    return ValidationResult('API Health', 'PASS', 'API is healthy', {'status': data.get('status')})
                else:
                    return ValidationResult('API Health', 'WARN', f'API reports status: {data.get("status")}')
            else:
                return ValidationResult('API Health', 'FAIL', f'HTTP {response.status_code}')
        except Exception as e:
            return ValidationResult('API Health', 'FAIL', f'Connection failed: {e}')

    def _check_monitoring_endpoints(self) -> ValidationResult:
        """Check monitoring endpoints."""
        endpoints = ['/health/detailed', '/metrics', '/performance', '/alerts']
        failed_endpoints = []

        for endpoint in endpoints:
            try:
                response = self.session.get(f'{self.base_url}{endpoint}', timeout=10)
                if response.status_code != 200:
                    failed_endpoints.append(f'{endpoint}: HTTP {response.status_code}')
            except Exception as e:
                failed_endpoints.append(f'{endpoint}: {e}')

        if not failed_endpoints:
            return ValidationResult('Monitoring Endpoints', 'PASS', 'All monitoring endpoints accessible')
        else:
            return ValidationResult('Monitoring Endpoints', 'FAIL', f'Failed endpoints: {", ".join(failed_endpoints)}')

    def _check_basic_functionality(self) -> ValidationResult:
        """Check basic API functionality."""
        try:
            # Test scan endpoint with minimal payload
            payload = {
                'repository_path': '/tmp/test-repo',
                'output_format': 'json'
            }
            response = self.session.post(f'{self.base_url}/scan', json=payload, timeout=30)

            if response.status_code in [200, 201, 202]:
                data = response.json()
                if 'job_id' in data:
                    return ValidationResult('Basic Functionality', 'PASS', 'Scan job created successfully', {'job_id': data['job_id']})
                else:
                    return ValidationResult('Basic Functionality', 'WARN', 'Scan endpoint responded but missing job_id')
            elif response.status_code == 404:
                # Expected if repository doesn't exist
                return ValidationResult('Basic Functionality', 'PASS', 'Scan endpoint accessible (404 expected for test repo)')
            else:
                return ValidationResult('Basic Functionality', 'FAIL', f'Unexpected response: HTTP {response.status_code}')
        except Exception as e:
            return ValidationResult('Basic Functionality', 'FAIL', f'Functionality test failed: {e}')

    def _check_performance_metrics(self) -> ValidationResult:
        """Check performance metrics collection."""
        try:
            response = self.session.get(f'{self.base_url}/performance', timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and len(data) > 0:
                    return ValidationResult('Performance Metrics', 'PASS', f'Performance metrics collected: {len(data)} operations')
                else:
                    return ValidationResult('Performance Metrics', 'WARN', 'Performance metrics endpoint returned empty data')
            else:
                return ValidationResult('Performance Metrics', 'FAIL', f'HTTP {response.status_code}')
        except Exception as e:
            return ValidationResult('Performance Metrics', 'FAIL', f'Performance check failed: {e}')

    def _check_security_headers(self) -> ValidationResult:
        """Check security headers."""
        try:
            response = self.session.get(f'{self.base_url}/health', timeout=10)
            headers = response.headers

            security_headers = [
                'X-Content-Type-Options',
                'X-Frame-Options',
                'X-XSS-Protection',
                'Strict-Transport-Security'
            ]

            missing_headers = [h for h in security_headers if h not in headers]

            if not missing_headers:
                return ValidationResult('Security Headers', 'PASS', 'All security headers present')
            else:
                return ValidationResult('Security Headers', 'WARN', f'Missing headers: {", ".join(missing_headers)}')
        except Exception as e:
            return ValidationResult('Security Headers', 'FAIL', f'Security check failed: {e}')

    def _check_rate_limiting(self) -> ValidationResult:
        """Check rate limiting (basic test)."""
        try:
            # Make multiple rapid requests
            responses = []
            for i in range(10):
                response = self.session.get(f'{self.base_url}/health', timeout=5)
                responses.append(response.status_code)
                time.sleep(0.1)

            rate_limited = any(code == 429 for code in responses)

            if rate_limited:
                return ValidationResult('Rate Limiting', 'PASS', 'Rate limiting is active')
            else:
                return ValidationResult('Rate Limiting', 'WARN', 'Rate limiting not detected (may not be configured)')
        except Exception as e:
            return ValidationResult('Rate Limiting', 'FAIL', f'Rate limiting check failed: {e}')

    def _load_testing(self) -> ValidationResult:
        """Basic load testing."""
        try:
            def make_request():
                return self.session.get(f'{self.base_url}/health', timeout=10)

            # Make 20 concurrent requests
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(make_request) for _ in range(20)]
                results = []

                for future in as_completed(futures):
                    try:
                        response = future.result()
                        results.append(response.status_code)
                    except Exception as e:
                        results.append(f'error: {e}')

            success_count = sum(1 for r in results if r == 200)
            error_count = len(results) - success_count

            if success_count >= 18:  # 90% success rate
                return ValidationResult('Load Testing', 'PASS', f'Load test passed: {success_count}/{len(results)} successful')
            else:
                return ValidationResult('Load Testing', 'FAIL', f'Load test failed: {success_count}/{len(results)} successful, {error_count} errors')
        except Exception as e:
            return ValidationResult('Load Testing', 'FAIL', f'Load testing failed: {e}')

def main():
    parser = argparse.ArgumentParser(description='Validate Repository Intelligence Scanner deployment')
    parser.add_argument('--url', required=True, help='Base URL of the deployment')
    parser.add_argument('--api-key', help='API key for authentication')
    parser.add_argument('--output', choices=['console', 'json'], default='console', help='Output format')

    args = parser.parse_args()

    print(f"🚀 Validating deployment at: {args.url}")
    print("=" * 60)

    validator = DeploymentValidator(args.url, args.api_key)
    results = validator.run_validation()

    print("\\n" + "=" * 60)

    # Summary
    passed = sum(1 for r in results if r.status == 'PASS')
    failed = sum(1 for r in results if r.status == 'FAIL')
    warned = sum(1 for r in results if r.status == 'WARN')

    print(f"📊 Validation Summary: {passed} passed, {warned} warnings, {failed} failed")

    if args.output == 'json':
        output = {
            'summary': {
                'total': len(results),
                'passed': passed,
                'failed': failed,
                'warned': warned,
                'success_rate': (passed / len(results)) * 100 if results else 0
            },
            'results': [
                {
                    'check': r.check_name,
                    'status': r.status,
                    'message': r.message,
                    'duration': r.duration,
                    'details': r.details
                } for r in results
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        if failed == 0:
            print("🎉 DEPLOYMENT VALIDATION SUCCESSFUL!")
            if warned > 0:
                print(f"⚠️  {warned} warnings to review")
        else:
            print(f"❌ DEPLOYMENT VALIDATION FAILED: {failed} critical issues")
            sys.exit(1)

if __name__ == '__main__':
    main()