#!/usr/bin/env python3
"""
Enterprise Deployment Validation Framework

Comprehensive validation of Repository Intelligence Scanner production deployment
including infrastructure, security, performance, and operational readiness checks.
"""

import argparse
import subprocess
import json
import yaml
import requests
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import sys

@dataclass
class ValidationCheck:
    """Individual validation check result."""
    name: str
    category: str
    status: str  # 'PASS', 'FAIL', 'WARN', 'SKIP'
    message: str
    details: Optional[Dict[str, Any]] = None
    remediation: Optional[str] = None
    duration: Optional[float] = None

class DeploymentValidator:
    """Comprehensive deployment validation framework."""

    def __init__(self, namespace: str = "repo-scanner", kubeconfig: Optional[str] = None):
        self.namespace = namespace
        self.kubeconfig = kubeconfig
        self.results: List[ValidationCheck] = []
        self.logger = logging.getLogger(__name__)

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def run_kubectl(self, args: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """Run kubectl command and return results."""
        cmd = ["kubectl"]
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        cmd.extend(args)

        try:
            result = subprocess.run(cmd, capture_output=capture_output, text=True, timeout=30)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    def add_result(self, check: ValidationCheck):
        """Add validation result."""
        self.results.append(check)
        status_emoji = {
            'PASS': '✅',
            'FAIL': '❌',
            'WARN': '⚠️',
            'SKIP': '⏭️'
        }
        self.logger.info(f"{status_emoji[check.status]} {check.category}: {check.name} - {check.message}")

    def validate_namespace(self) -> ValidationCheck:
        """Validate namespace exists and is properly configured."""
        start_time = time.time()

        code, stdout, stderr = self.run_kubectl(["get", "namespace", self.namespace, "-o", "json"])

        if code != 0:
            return ValidationCheck(
                name="namespace_exists",
                category="Infrastructure",
                status="FAIL",
                message=f"Namespace {self.namespace} does not exist",
                remediation=f"Create namespace: kubectl create namespace {self.namespace}",
                duration=time.time() - start_time
            )

        try:
            ns_data = json.loads(stdout)
            labels = ns_data.get('metadata', {}).get('labels', {})

            # Check for security labels
            security_labels = [
                'pod-security.kubernetes.io/enforce',
                'pod-security.kubernetes.io/enforce-version'
            ]

            missing_labels = [label for label in security_labels if label not in labels]

            if missing_labels:
                return ValidationCheck(
                    name="namespace_security_labels",
                    category="Security",
                    status="WARN",
                    message=f"Missing security labels: {missing_labels}",
                    remediation="Apply security labels to namespace",
                    duration=time.time() - start_time
                )

            return ValidationCheck(
                name="namespace_configured",
                category="Infrastructure",
                status="PASS",
                message=f"Namespace {self.namespace} exists and is properly configured",
                duration=time.time() - start_time
            )

        except json.JSONDecodeError:
            return ValidationCheck(
                name="namespace_parsing",
                category="Infrastructure",
                status="FAIL",
                message="Failed to parse namespace data",
                duration=time.time() - start_time
            )

    def validate_kubernetes_resources(self) -> List[ValidationCheck]:
        """Validate all Kubernetes resources."""
        checks = []
        resources = [
            ("configmap", "repo-scanner-config"),
            ("secret", "repo-scanner-secrets"),
            ("serviceaccount", "repo-scanner-sa"),
            ("role", "repo-scanner-role"),
            ("rolebinding", "repo-scanner-rolebinding"),
            ("deployment", "repo-scanner-api"),
            ("service", "repo-scanner"),
            ("networkpolicy", "repo-scanner-network-policy"),
            ("servicemonitor", "repo-scanner"),
            ("prometheusrule", "repo-scanner-alerts"),
            ("pvc", "repo-scanner-storage"),
            ("hpa", "repo-scanner")
        ]

        for resource_type, resource_name in resources:
            start_time = time.time()
            code, stdout, stderr = self.run_kubectl([
                "get", resource_type, resource_name,
                "-n", self.namespace, "-o", "json"
            ])

            if code != 0:
                checks.append(ValidationCheck(
                    name=f"{resource_type}_{resource_name}",
                    category="Infrastructure",
                    status="FAIL",
                    message=f"{resource_type}/{resource_name} not found",
                    remediation=f"Apply the {resource_type} manifest",
                    duration=time.time() - start_time
                ))
            else:
                checks.append(ValidationCheck(
                    name=f"{resource_type}_{resource_name}",
                    category="Infrastructure",
                    status="PASS",
                    message=f"{resource_type}/{resource_name} exists",
                    duration=time.time() - start_time
                ))

        return checks

    def validate_pod_security(self) -> List[ValidationCheck]:
        """Validate pod security configurations."""
        checks = []

        # Check deployment security context
        code, stdout, stderr = self.run_kubectl([
            "get", "deployment", "repo-scanner-api",
            "-n", self.namespace, "-o", "jsonpath='{.spec.template.spec.securityContext}'"
        ])

        if code != 0:
            checks.append(ValidationCheck(
                name="deployment_security_context",
                category="Security",
                status="FAIL",
                message="Cannot retrieve deployment security context",
                remediation="Check deployment manifest and apply security contexts"
            ))
        else:
            # Parse security context
            try:
                security_context = json.loads(stdout.strip("'"))
                if not security_context.get('runAsNonRoot'):
                    checks.append(ValidationCheck(
                        name="run_as_non_root",
                        category="Security",
                        status="FAIL",
                        message="Pods not configured to run as non-root",
                        remediation="Set runAsNonRoot: true in deployment securityContext"
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="run_as_non_root",
                        category="Security",
                        status="PASS",
                        message="Pods configured to run as non-root"
                    ))
            except:
                checks.append(ValidationCheck(
                    name="security_context_parsing",
                    category="Security",
                    status="WARN",
                    message="Could not parse security context"
                ))

        # Check container security contexts
        code, stdout, stderr = self.run_kubectl([
            "get", "deployment", "repo-scanner-api",
            "-n", self.namespace, "-o", "jsonpath='{.spec.template.spec.containers[0].securityContext}'"
        ])

        if code == 0:
            try:
                container_security = json.loads(stdout.strip("'"))
                if container_security.get('readOnlyRootFilesystem'):
                    checks.append(ValidationCheck(
                        name="read_only_root_filesystem",
                        category="Security",
                        status="PASS",
                        message="Read-only root filesystem enabled"
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="read_only_root_filesystem",
                        category="Security",
                        status="WARN",
                        message="Read-only root filesystem not enabled",
                        remediation="Set readOnlyRootFilesystem: true in container securityContext"
                    ))

                dropped_caps = container_security.get('capabilities', {}).get('drop', [])
                if 'ALL' in dropped_caps:
                    checks.append(ValidationCheck(
                        name="capabilities_dropped",
                        category="Security",
                        status="PASS",
                        message="All capabilities dropped"
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="capabilities_dropped",
                        category="Security",
                        status="WARN",
                        message="Not all capabilities dropped",
                        remediation="Add 'ALL' to capabilities.drop in container securityContext"
                    ))
            except:
                checks.append(ValidationCheck(
                    name="container_security_parsing",
                    category="Security",
                    status="WARN",
                    message="Could not parse container security context"
                ))

        return checks

    def validate_network_policies(self) -> List[ValidationCheck]:
        """Validate network policies."""
        checks = []

        # Check network policy exists
        code, stdout, stderr = self.run_kubectl([
            "get", "networkpolicy", "repo-scanner-network-policy",
            "-n", self.namespace
        ])

        if code != 0:
            checks.append(ValidationCheck(
                name="network_policy_exists",
                category="Security",
                status="FAIL",
                message="Network policy not found",
                remediation="Apply network policy manifests"
            ))
            return checks

        checks.append(ValidationCheck(
            name="network_policy_exists",
            category="Security",
            status="PASS",
            message="Network policy exists"
        ))

        # Check for deny-all policy
        code, stdout, stderr = self.run_kubectl([
            "get", "networkpolicy", "repo-scanner-deny-all",
            "-n", self.namespace
        ])

        if code == 0:
            checks.append(ValidationCheck(
                name="deny_all_policy",
                category="Security",
                status="PASS",
                message="Deny-all network policy exists"
            ))
        else:
            checks.append(ValidationCheck(
                name="deny_all_policy",
                category="Security",
                status="WARN",
                message="Deny-all network policy not found",
                remediation="Apply deny-all network policy for additional security"
            ))

        return checks

    def validate_monitoring(self) -> List[ValidationCheck]:
        """Validate monitoring setup."""
        checks = []

        # Check ServiceMonitor
        code, stdout, stderr = self.run_kubectl([
            "get", "servicemonitor", "repo-scanner", "-n", self.namespace
        ])

        if code == 0:
            checks.append(ValidationCheck(
                name="servicemonitor_exists",
                category="Monitoring",
                status="PASS",
                message="ServiceMonitor configured"
            ))
        else:
            checks.append(ValidationCheck(
                name="servicemonitor_exists",
                category="Monitoring",
                status="WARN",
                message="ServiceMonitor not found",
                remediation="Apply ServiceMonitor manifest for Prometheus metrics collection"
            ))

        # Check PrometheusRule
        code, stdout, stderr = self.run_kubectl([
            "get", "prometheusrule", "repo-scanner-alerts", "-n", self.namespace
        ])

        if code == 0:
            checks.append(ValidationCheck(
                name="prometheus_rules",
                category="Monitoring",
                status="PASS",
                message="Prometheus alerting rules configured"
            ))
        else:
            checks.append(ValidationCheck(
                name="prometheus_rules",
                category="Monitoring",
                status="WARN",
                message="Prometheus rules not found",
                remediation="Apply PrometheusRule manifest for alerting"
            ))

        return checks

    def validate_resource_limits(self) -> List[ValidationCheck]:
        """Validate resource limits and quotas."""
        checks = []

        # Check ResourceQuota
        code, stdout, stderr = self.run_kubectl([
            "get", "resourcequota", "repo-scanner-quota", "-n", self.namespace
        ])

        if code == 0:
            checks.append(ValidationCheck(
                name="resource_quota",
                category="Infrastructure",
                status="PASS",
                message="Resource quota configured"
            ))
        else:
            checks.append(ValidationCheck(
                name="resource_quota",
                category="Infrastructure",
                status="WARN",
                message="Resource quota not configured",
                remediation="Apply ResourceQuota manifest to limit namespace resources"
            ))

        # Check LimitRange
        code, stdout, stderr = self.run_kubectl([
            "get", "limitrange", "repo-scanner-limits", "-n", self.namespace
        ])

        if code == 0:
            checks.append(ValidationCheck(
                name="limit_range",
                category="Infrastructure",
                status="PASS",
                message="Limit range configured"
            ))
        else:
            checks.append(ValidationCheck(
                name="limit_range",
                category="Infrastructure",
                status="WARN",
                message="Limit range not configured",
                remediation="Apply LimitRange manifest for default resource limits"
            ))

        return checks

    def validate_deployment_health(self) -> List[ValidationCheck]:
        """Validate deployment health and status."""
        checks = []

        # Check deployment status
        code, stdout, stderr = self.run_kubectl([
            "get", "deployment", "repo-scanner-api",
            "-n", self.namespace, "-o", "json"
        ])

        if code != 0:
            checks.append(ValidationCheck(
                name="deployment_exists",
                category="Infrastructure",
                status="FAIL",
                message="Deployment not found",
                remediation="Apply deployment manifest"
            ))
            return checks

        try:
            deployment = json.loads(stdout)
            spec_replicas = deployment['spec']['replicas']
            status_replicas = deployment['status'].get('readyReplicas', 0)

            if status_replicas == spec_replicas:
                checks.append(ValidationCheck(
                    name="deployment_ready",
                    category="Infrastructure",
                    status="PASS",
                    message=f"Deployment ready: {status_replicas}/{spec_replicas} replicas"
                ))
            else:
                checks.append(ValidationCheck(
                    name="deployment_ready",
                    category="Infrastructure",
                    status="FAIL",
                    message=f"Deployment not ready: {status_replicas}/{spec_replicas} replicas",
                    remediation="Check pod status and deployment events"
                ))

            # Check pod status
            code, stdout, stderr = self.run_kubectl([
                "get", "pods", "-l", "app=repo-scanner",
                "-n", self.namespace, "-o", "json"
            ])

            if code == 0:
                pods = json.loads(stdout)
                total_pods = len(pods['items'])
                running_pods = sum(1 for pod in pods['items']
                                 if pod['status']['phase'] == 'Running')

                if running_pods == total_pods:
                    checks.append(ValidationCheck(
                        name="pods_running",
                        category="Infrastructure",
                        status="PASS",
                        message=f"All pods running: {running_pods}/{total_pods}"
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="pods_running",
                        category="Infrastructure",
                        status="FAIL",
                        message=f"Not all pods running: {running_pods}/{total_pods}",
                        remediation="Check pod logs and events for issues"
                    ))

        except json.JSONDecodeError:
            checks.append(ValidationCheck(
                name="deployment_parsing",
                category="Infrastructure",
                status="FAIL",
                message="Failed to parse deployment data"
            ))

        return checks

    def validate_helm_chart(self) -> List[ValidationCheck]:
        """Validate Helm chart configuration."""
        checks = []

        helm_path = Path("helm/repo-scanner")
        if not helm_path.exists():
            checks.append(ValidationCheck(
                name="helm_chart_exists",
                category="Infrastructure",
                status="FAIL",
                message="Helm chart not found",
                remediation="Create Helm chart in helm/repo-scanner/"
            ))
            return checks

        # Check Chart.yaml
        chart_file = helm_path / "Chart.yaml"
        if chart_file.exists():
            try:
                with open(chart_file) as f:
                    chart_data = yaml.safe_load(f)

                required_fields = ['name', 'version', 'appVersion']
                missing_fields = [field for field in required_fields
                                if field not in chart_data]

                if missing_fields:
                    checks.append(ValidationCheck(
                        name="helm_chart_metadata",
                        category="Infrastructure",
                        status="FAIL",
                        message=f"Missing Chart.yaml fields: {missing_fields}",
                        remediation="Add required fields to Chart.yaml"
                    ))
                else:
                    checks.append(ValidationCheck(
                        name="helm_chart_metadata",
                        category="Infrastructure",
                        status="PASS",
                        message="Helm chart metadata complete"
                    ))
            except Exception as e:
                checks.append(ValidationCheck(
                    name="helm_chart_parsing",
                    category="Infrastructure",
                    status="FAIL",
                    message=f"Failed to parse Chart.yaml: {e}",
                    remediation="Fix Chart.yaml syntax"
                ))
        else:
            checks.append(ValidationCheck(
                name="helm_chart_yaml",
                category="Infrastructure",
                status="FAIL",
                message="Chart.yaml not found",
                remediation="Create Chart.yaml in helm/repo-scanner/"
            ))

        # Check values.yaml
        values_file = helm_path / "values.yaml"
        if values_file.exists():
            checks.append(ValidationCheck(
                name="helm_values_file",
                category="Infrastructure",
                status="PASS",
                message="Helm values.yaml exists"
            ))
        else:
            checks.append(ValidationCheck(
                name="helm_values_file",
                category="Infrastructure",
                status="FAIL",
                message="values.yaml not found",
                remediation="Create values.yaml in helm/repo-scanner/"
            ))

        # Check templates
        templates_dir = helm_path / "templates"
        if templates_dir.exists():
            template_files = list(templates_dir.glob("*.yaml"))
            if template_files:
                checks.append(ValidationCheck(
                    name="helm_templates",
                    category="Infrastructure",
                    status="PASS",
                    message=f"Helm templates found: {len(template_files)} files"
                ))
            else:
                checks.append(ValidationCheck(
                    name="helm_templates",
                    category="Infrastructure",
                    status="WARN",
                    message="No template files found",
                    remediation="Add Kubernetes manifests to templates/"
                ))
        else:
            checks.append(ValidationCheck(
                name="helm_templates_dir",
                category="Infrastructure",
                status="FAIL",
                message="templates/ directory not found",
                remediation="Create templates/ directory with Kubernetes manifests"
            ))

        return checks

    def validate_api_endpoints(self, api_url: Optional[str] = None) -> List[ValidationCheck]:
        """Validate API endpoints if URL provided."""
        checks = []

        if not api_url:
            checks.append(ValidationCheck(
                name="api_validation",
                category="API",
                status="SKIP",
                message="API URL not provided, skipping API validation"
            ))
            return checks

        # Test health endpoint
        try:
            response = requests.get(f"{api_url}/health", timeout=10)
            if response.status_code == 200:
                checks.append(ValidationCheck(
                    name="health_endpoint",
                    category="API",
                    status="PASS",
                    message="Health endpoint responding"
                ))
            else:
                checks.append(ValidationCheck(
                    name="health_endpoint",
                    category="API",
                    status="FAIL",
                    message=f"Health endpoint returned {response.status_code}",
                    remediation="Check application logs and health check configuration"
                ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="health_endpoint",
                category="API",
                status="FAIL",
                message=f"Health endpoint unreachable: {e}",
                remediation="Verify service is running and accessible"
            ))

        # Test metrics endpoint
        try:
            response = requests.get(f"{api_url}/metrics", timeout=10)
            if response.status_code == 200:
                checks.append(ValidationCheck(
                    name="metrics_endpoint",
                    category="Monitoring",
                    status="PASS",
                    message="Metrics endpoint responding"
                ))
            else:
                checks.append(ValidationCheck(
                    name="metrics_endpoint",
                    category="Monitoring",
                    status="WARN",
                    message=f"Metrics endpoint returned {response.status_code}",
                    remediation="Check metrics endpoint configuration"
                ))
        except Exception as e:
            checks.append(ValidationCheck(
                name="metrics_endpoint",
                category="Monitoring",
                status="WARN",
                message=f"Metrics endpoint unreachable: {e}",
                remediation="Verify metrics endpoint is configured"
            ))

        return checks

    def run_all_validations(self, api_url: Optional[str] = None) -> List[ValidationCheck]:
        """Run all validation checks."""
        self.logger.info("Starting comprehensive deployment validation...")

        # Infrastructure validations
        self.add_result(self.validate_namespace())
        self.results.extend(self.validate_kubernetes_resources())
        self.results.extend(self.validate_deployment_health())
        self.results.extend(self.validate_resource_limits())

        # Security validations
        self.results.extend(self.validate_pod_security())
        self.results.extend(self.validate_network_policies())

        # Monitoring validations
        self.results.extend(self.validate_monitoring())

        # Helm validations
        self.results.extend(self.validate_helm_chart())

        # API validations (if URL provided)
        self.results.extend(self.validate_api_endpoints(api_url))

        return self.results

    def generate_report(self, output_file: str = "validation_report.json"):
        """Generate validation report."""
        # Count results by status
        status_counts = {}
        category_results = {}

        for result in self.results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1

            if result.category not in category_results:
                category_results[result.category] = []
            category_results[result.category].append(asdict(result))

        report = {
            'summary': {
                'total_checks': len(self.results),
                'status_counts': status_counts,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'namespace': self.namespace,
                'overall_status': 'PASS' if status_counts.get('FAIL', 0) == 0 else 'FAIL'
            },
            'categories': category_results,
            'recommendations': self._generate_recommendations()
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"Validation report saved to {output_file}")
        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        fails = [r for r in self.results if r.status == 'FAIL']
        warns = [r for r in self.results if r.status == 'WARN']

        if fails:
            recommendations.append("Address all FAILED checks before production deployment")

        if warns:
            recommendations.append("Review WARNING checks for potential improvements")

        # Specific recommendations
        security_fails = [r for r in fails if r.category == 'Security']
        if security_fails:
            recommendations.append("Security issues must be resolved for compliance")

        infra_fails = [r for r in fails if r.category == 'Infrastructure']
        if infra_fails:
            recommendations.append("Infrastructure issues prevent proper deployment")

        return recommendations

    def print_summary(self):
        """Print validation summary."""
        if not self.results:
            print("No validation results available")
            return

        status_counts = {}
        for result in self.results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1

        print("\n" + "="*60)
        print("DEPLOYMENT VALIDATION SUMMARY")
        print("="*60)
        print(f"Total Checks: {len(self.results)}")
        print(f"✅ Passed: {status_counts.get('PASS', 0)}")
        print(f"❌ Failed: {status_counts.get('FAIL', 0)}")
        print(f"⚠️  Warnings: {status_counts.get('WARN', 0)}")
        print(f"⏭️  Skipped: {status_counts.get('SKIP', 0)}")

        overall_status = "✅ PASS" if status_counts.get('FAIL', 0) == 0 else "❌ FAIL"
        print(f"\nOverall Status: {overall_status}")

        # Show failures and warnings
        failures = [r for r in self.results if r.status in ['FAIL', 'WARN']]
        if failures:
            print("\nIssues Found:")
            for failure in failures:
                print(f"  {failure.status}: {failure.category} - {failure.name}")
                print(f"    {failure.message}")
                if failure.remediation:
                    print(f"    💡 {failure.remediation}")

def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description='Enterprise Deployment Validator')
    parser.add_argument('--namespace', default='repo-scanner',
                       help='Kubernetes namespace to validate')
    parser.add_argument('--kubeconfig', help='Path to kubeconfig file')
    parser.add_argument('--api-url', help='API URL for endpoint validation')
    parser.add_argument('--output', default='validation_report.json',
                       help='Output file for validation report')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress detailed output')

    args = parser.parse_args()

    if not args.quiet:
        print("Repository Intelligence Scanner - Enterprise Deployment Validator")
        print("="*70)

    validator = DeploymentValidator(args.namespace, args.kubeconfig)
    results = validator.run_all_validations(args.api_url)

    if not args.quiet:
        validator.print_summary()

    report = validator.generate_report(args.output)

    # Exit with appropriate code
    fail_count = sum(1 for r in results if r.status == 'FAIL')
    sys.exit(0 if fail_count == 0 else 1)

if __name__ == "__main__":
    main()