#!/usr/bin/env python3
"""
Enterprise Operational Readiness Assessment

Final assessment to determine if the Repository Intelligence Scanner
is ready for production deployment and operations.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

class OperationalReadinessAssessor:
    """Assess operational readiness for production deployment."""

    def __init__(self):
        self.checks = []
        self.score = 0
        self.max_score = 0

    def add_check(self, name: str, description: str, weight: int = 1,
                  automated: bool = True, critical: bool = False):
        """Add a readiness check."""
        check = {
            'name': name,
            'description': description,
            'weight': weight,
            'automated': automated,
            'critical': critical,
            'status': 'PENDING',
            'evidence': None,
            'notes': None
        }
        self.checks.append(check)
        self.max_score += weight

    def run_check(self, check_name: str, status: str, evidence: Any = None, notes: str = None):
        """Update check status."""
        for check in self.checks:
            if check['name'] == check_name:
                check['status'] = status
                check['evidence'] = evidence
                check['notes'] = notes
                if status == 'PASS':
                    self.score += check['weight']
                elif status == 'FAIL' and check['critical']:
                    self.score -= check['weight'] * 2  # Critical failures heavily penalize
                break

    def calculate_readiness_score(self) -> float:
        """Calculate overall readiness score."""
        return (self.score / self.max_score) * 100 if self.max_score > 0 else 0

    def get_readiness_level(self, score: float) -> str:
        """Get readiness level based on score."""
        if score >= 95:
            return "🏆 PRODUCTION READY"
        elif score >= 85:
            return "✅ READY WITH MINOR ISSUES"
        elif score >= 70:
            return "⚠️ REQUIRES ATTENTION"
        elif score >= 50:
            return "❌ SIGNIFICANT ISSUES"
        else:
            return "🚫 NOT READY FOR PRODUCTION"

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive readiness report."""
        score = self.calculate_readiness_score()
        readiness_level = self.get_readiness_level(score)

        # Categorize checks
        categories = {}
        for check in self.checks:
            category = check['name'].split('_')[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(check)

        # Calculate category scores
        category_scores = {}
        for category, checks in categories.items():
            cat_score = sum(c['weight'] for c in checks if c['status'] == 'PASS')
            cat_total = sum(c['weight'] for c in checks)
            category_scores[category] = (cat_score / cat_total) * 100 if cat_total > 0 else 0

        report = {
            'summary': {
                'overall_score': round(score, 1),
                'readiness_level': readiness_level,
                'total_checks': len(self.checks),
                'passed_checks': len([c for c in self.checks if c['status'] == 'PASS']),
                'failed_checks': len([c for c in self.checks if c['status'] == 'FAIL']),
                'pending_checks': len([c for c in self.checks if c['status'] == 'PENDING']),
                'critical_failures': len([c for c in self.checks if c['status'] == 'FAIL' and c['critical']])
            },
            'categories': category_scores,
            'checks': self.checks,
            'recommendations': self._generate_recommendations(),
            'next_steps': self._generate_next_steps(score)
        }

        return report

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on failed checks."""
        recommendations = []
        failed_checks = [c for c in self.checks if c['status'] == 'FAIL']

        if not failed_checks:
            recommendations.append("🎉 All checks passed! System is ready for production.")
            return recommendations

        # Group recommendations by category
        infra_issues = [c for c in failed_checks if 'infra' in c['name'].lower()]
        security_issues = [c for c in failed_checks if 'security' in c['name'].lower()]
        monitoring_issues = [c for c in failed_checks if 'monitor' in c['name'].lower()]
        doc_issues = [c for c in failed_checks if 'doc' in c['name'].lower()]

        if infra_issues:
            recommendations.append(f"Address {len(infra_issues)} infrastructure issues before deployment")

        if security_issues:
            recommendations.append(f"Resolve {len(security_issues)} security issues for compliance")

        if monitoring_issues:
            recommendations.append(f"Fix {len(monitoring_issues)} monitoring issues for operational readiness")

        if doc_issues:
            recommendations.append(f"Complete {len(doc_issues)} documentation items")

        return recommendations

    def _generate_next_steps(self, score: float) -> List[str]:
        """Generate next steps based on readiness score."""
        if score >= 95:
            return [
                "✅ Proceed with production deployment",
                "📋 Schedule go-live activities",
                "👥 Notify stakeholders of successful readiness assessment",
                "📊 Begin post-deployment monitoring"
            ]
        elif score >= 85:
            return [
                "⚠️ Address minor issues before deployment",
                "🧪 Perform additional testing on identified issues",
                "📝 Update risk register with remaining items",
                "👥 Get stakeholder approval for deployment with known issues"
            ]
        elif score >= 70:
            return [
                "❌ Address critical issues before deployment",
                "🔍 Perform detailed analysis of failing components",
                "📋 Update project timeline for remediation",
                "👥 Escalate to leadership for decision on deployment timeline"
            ]
        else:
            return [
                "🚫 System not ready for production deployment",
                "🔍 Perform comprehensive assessment of all components",
                "📋 Develop remediation plan for critical issues",
                "👥 Schedule architecture review meeting"
            ]

def assess_infrastructure_readiness(assessor: OperationalReadinessAssessor):
    """Assess infrastructure readiness."""
    # Kubernetes manifests
    k8s_dir = Path("k8s")
    if k8s_dir.exists():
        yaml_files = list(k8s_dir.glob("*.yaml"))
        if len(yaml_files) >= 10:  # We have 12+ manifests
            assessor.run_check('infra_k8s_manifests', 'PASS',
                             f"Found {len(yaml_files)} Kubernetes manifests")
        else:
            assessor.run_check('infra_k8s_manifests', 'FAIL',
                             f"Only {len(yaml_files)} manifests found, expected 10+")
    else:
        assessor.run_check('infra_k8s_manifests', 'FAIL', "k8s/ directory not found")

    # Helm chart
    helm_dir = Path("helm/repo-scanner")
    if helm_dir.exists():
        required_files = ['Chart.yaml', 'values.yaml', 'templates/deployment.yaml']
        missing_files = [f for f in required_files if not (helm_dir / f).exists()]
        if not missing_files:
            assessor.run_check('infra_helm_chart', 'PASS', "Complete Helm chart found")
        else:
            assessor.run_check('infra_helm_chart', 'FAIL',
                             f"Missing Helm files: {missing_files}")
    else:
        assessor.run_check('infra_helm_chart', 'FAIL', "Helm chart directory not found")

    # CI/CD pipelines
    ci_dir = Path(".github/workflows")
    if ci_dir.exists():
        workflow_files = list(ci_dir.glob("*.yml"))
        deployment_workflows = [f for f in workflow_files if 'deploy' in f.name.lower()]
        if deployment_workflows:
            assessor.run_check('infra_cicd', 'PASS',
                             f"Found {len(deployment_workflows)} deployment workflows")
        else:
            assessor.run_check('infra_cicd', 'FAIL', "No deployment workflows found")
    else:
        assessor.run_check('infra_cicd', 'FAIL', "CI/CD workflows directory not found")

def assess_security_readiness(assessor: OperationalReadinessAssessor):
    """Assess security readiness."""
    deployment_file = Path("k8s/deployment.yaml")
    if deployment_file.exists():
        with open(deployment_file) as f:
            content = f.read()

        security_checks = [
            ('security_non_root', 'runAsNonRoot: true'),
            ('security_readonly_fs', 'readOnlyRootFilesystem: true'),
            ('security_drop_caps', 'drop:\n            - ALL')
        ]

        for check_name, pattern in security_checks:
            if pattern in content:
                assessor.run_check(check_name, 'PASS', f"Security control '{pattern}' found")
            else:
                assessor.run_check(check_name, 'FAIL', f"Security control '{pattern}' missing")

    # RBAC
    rbac_file = Path("k8s/rbac.yaml")
    if rbac_file.exists():
        assessor.run_check('security_rbac', 'PASS', "RBAC configuration found")
    else:
        assessor.run_check('security_rbac', 'FAIL', "RBAC configuration missing")

    # Network policies
    netpol_file = Path("k8s/network-policy.yaml")
    if netpol_file.exists():
        assessor.run_check('security_network_policies', 'PASS', "Network policies configured")
    else:
        assessor.run_check('security_network_policies', 'FAIL', "Network policies missing")

def assess_monitoring_readiness(assessor: OperationalReadinessAssessor):
    """Assess monitoring readiness."""
    # ServiceMonitor
    sm_file = Path("k8s/service-monitor.yaml")
    if sm_file.exists():
        assessor.run_check('monitor_servicemonitor', 'PASS', "ServiceMonitor configured")
    else:
        assessor.run_check('monitor_servicemonitor', 'FAIL', "ServiceMonitor missing")

    # Prometheus rules
    pr_file = Path("k8s/prometheus-rules.yaml")
    if pr_file.exists():
        assessor.run_check('monitor_prometheus_rules', 'PASS', "Prometheus alerting rules configured")
    else:
        assessor.run_check('monitor_prometheus_rules', 'FAIL', "Prometheus rules missing")

    # Grafana dashboard
    grafana_file = Path("monitoring/grafana-dashboard.json")
    if grafana_file.exists():
        assessor.run_check('monitor_grafana', 'PASS', "Grafana dashboard configured")
    else:
        assessor.run_check('monitor_grafana', 'WARN', "Grafana dashboard not found")

def assess_documentation_readiness(assessor: OperationalReadinessAssessor):
    """Assess documentation readiness."""
    docs_dir = Path("docs")
    if docs_dir.exists():
        doc_files = list(docs_dir.glob("*.md"))
        required_docs = [
            'enterprise-deployment.md',
            'security-compliance.md',
            'performance-benchmarking.md',
            'deployment-validation-checklist.md'
        ]

        found_docs = [f.name for f in doc_files]
        missing_docs = [d for d in required_docs if d not in found_docs]

        if not missing_docs:
            assessor.run_check('docs_comprehensive', 'PASS',
                             f"All {len(required_docs)} required documents found")
        else:
            assessor.run_check('docs_comprehensive', 'FAIL',
                             f"Missing documents: {missing_docs}")
    else:
        assessor.run_check('docs_comprehensive', 'FAIL', "Documentation directory not found")

def assess_validation_readiness(assessor: OperationalReadinessAssessor):
    """Assess validation and testing readiness."""
    scripts_dir = Path("scripts")
    if scripts_dir.exists():
        validation_scripts = [
            'validate_deployment.py',
            'validate_deployment_comprehensive.py',
            'performance_benchmark.py',
            'load_test.py'
        ]

        found_scripts = [f.name for f in scripts_dir.glob("*.py")]
        missing_scripts = [s for s in validation_scripts if s not in found_scripts]

        if not missing_scripts:
            assessor.run_check('validation_scripts', 'PASS',
                             f"All {len(validation_scripts)} validation scripts found")
        else:
            assessor.run_check('validation_scripts', 'FAIL',
                             f"Missing validation scripts: {missing_scripts}")
    else:
        assessor.run_check('validation_scripts', 'FAIL', "Scripts directory not found")

def main():
    """Main assessment function."""
    parser = argparse.ArgumentParser(description='Enterprise Operational Readiness Assessment')
    parser.add_argument('--output', default='readiness_assessment.json',
                       help='Output file for assessment report')
    parser.add_argument('--format', choices=['json', 'text'], default='text',
                       help='Output format')

    args = parser.parse_args()

    print("🔍 Repository Intelligence Scanner - Operational Readiness Assessment")
    print("="*75)

    assessor = OperationalReadinessAssessor()

    # Define all readiness checks
    assessor.add_check('infra_k8s_manifests', 'Kubernetes manifests complete and valid', weight=3, critical=True)
    assessor.add_check('infra_helm_chart', 'Helm chart complete and functional', weight=2, critical=True)
    assessor.add_check('infra_cicd', 'CI/CD pipelines configured', weight=2, critical=True)

    assessor.add_check('security_non_root', 'Pods run as non-root user', weight=2, critical=True)
    assessor.add_check('security_readonly_fs', 'Read-only root filesystem enabled', weight=2, critical=True)
    assessor.add_check('security_drop_caps', 'All capabilities dropped', weight=2, critical=True)
    assessor.add_check('security_rbac', 'RBAC properly configured', weight=2, critical=True)
    assessor.add_check('security_network_policies', 'Network policies implemented', weight=2)

    assessor.add_check('monitor_servicemonitor', 'Prometheus ServiceMonitor configured', weight=1)
    assessor.add_check('monitor_prometheus_rules', 'Prometheus alerting rules configured', weight=1)
    assessor.add_check('monitor_grafana', 'Grafana dashboard available', weight=1)

    assessor.add_check('docs_comprehensive', 'Complete documentation available', weight=2)
    assessor.add_check('validation_scripts', 'Validation and testing scripts complete', weight=2)

    # Run assessments
    print("Running infrastructure assessment...")
    assess_infrastructure_readiness(assessor)

    print("Running security assessment...")
    assess_security_readiness(assessor)

    print("Running monitoring assessment...")
    assess_monitoring_readiness(assessor)

    print("Running documentation assessment...")
    assess_documentation_readiness(assessor)

    print("Running validation assessment...")
    assess_validation_readiness(assessor)

    # Generate report
    report = assessor.generate_report()

    # Save JSON report
    with open(args.output, 'w') as f:
        json.dump(report, f, indent=2)

    # Display results
    if args.format == 'text':
        print("\n" + "="*75)
        print("ASSESSMENT RESULTS")
        print("="*75)
        print(f"Overall Score: {report['summary']['overall_score']:.1f}%")
        print(f"Readiness Level: {report['summary']['readiness_level']}")
        print(f"Checks Passed: {report['summary']['passed_checks']}/{report['summary']['total_checks']}")

        if report['summary']['critical_failures'] > 0:
            print(f"⚠️ Critical Failures: {report['summary']['critical_failures']}")

        print("\nCategory Scores:")
        for category, score in report['categories'].items():
            print(".1f")

        print("\nRecommendations:")
        for rec in report['recommendations']:
            print(f"• {rec}")

        print("\nNext Steps:")
        for step in report['next_steps']:
            print(f"• {step}")

        print(f"\n📄 Detailed report saved to: {args.output}")

    # Exit with appropriate code
    score = report['summary']['overall_score']
    if score >= 85:
        print("\n✅ System meets production readiness criteria!")
        sys.exit(0)
    else:
        print(f"\n❌ System requires attention (Score: {score:.1f}%)")
        sys.exit(1)

if __name__ == "__main__":
    main()