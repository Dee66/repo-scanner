"""API Integration Engine for Algora Bounty Hunting.

Extends API analysis capabilities to detect webhooks, integration points,
and automated submission mechanisms for seamless bounty integration.
"""

from typing import Dict, List, Set, Optional
from urllib.parse import urlparse
import re
from datetime import datetime


class APIIntegrationEngine:
    """Engine for analyzing API integration points for bounty automation."""

    def __init__(self):
        self.webhook_patterns = {
            'github_webhooks': [
                r'webhook', r'payload', r'signature.*verify',
                r'x-hub-signature', r'github-event'
            ],
            'ci_cd_webhooks': [
                r'ci\.cd', r'pipeline.*trigger', r'build.*hook',
                r'deploy.*hook', r'automation.*trigger'
            ],
            'api_endpoints': [
                r'/api/', r'/webhook/', r'/integration/',
                r'pulls', r'issues', r'releases'
            ]
        }

        self.integration_frameworks = {
            'github_actions': ['.github/workflows/', 'action.yml', 'action.yaml'],
            'jenkins': ['Jenkinsfile', 'jenkins', '.jenkins'],
            'circle_ci': ['.circleci/', 'circle.yml'],
            'travis_ci': ['.travis.yml', 'travis'],
            'webhook_receivers': ['webhook.py', 'hooks.py', 'integrations.py']
        }

    def analyze_integration_points(self, file_list: List[str], api_analysis: Dict,
                                 governance: Dict) -> Dict:
        """Analyze repository for integration points and webhook capabilities."""

        integration_analysis = {
            "webhook_endpoints": self._detect_webhook_endpoints(file_list, api_analysis),
            "ci_cd_integrations": self._detect_ci_cd_integrations(file_list),
            "api_integration_points": self._detect_api_integration_points(api_analysis),
            "automation_capabilities": self._assess_automation_capabilities(file_list, governance),
            "submission_mechanisms": self._identify_submission_mechanisms(file_list),
            "high_alpha_targets": self._identify_high_alpha_targets(api_analysis, file_list),
            "integration_confidence": 0.0,
            "integration_score": 0.0,
            "analyzed_at": datetime.now().isoformat()
        }

        # Calculate integration scores
        integration_analysis["integration_score"] = self._calculate_integration_score(integration_analysis)
        integration_analysis["integration_confidence"] = self._calculate_integration_confidence(integration_analysis)

        return integration_analysis

    def _detect_webhook_endpoints(self, file_list: List[str], api_analysis: Dict) -> List[Dict]:
        """Detect webhook endpoints and their configurations."""
        webhook_endpoints = []

        # Check API analysis for webhook endpoints
        api_endpoints = api_analysis.get("api_endpoints", [])
        for endpoint in api_endpoints:
            if isinstance(endpoint, dict):
                url = endpoint.get("url", "")
                if any(pattern in url.lower() for pattern in ['webhook', 'hook', 'payload']):
                    webhook_endpoints.append({
                        "url": url,
                        "method": endpoint.get("method", "POST"),
                        "purpose": "webhook_receiver",
                        "security": endpoint.get("security", []),
                        "confidence": 0.8
                    })

        # Scan files for webhook patterns
        for file_path in file_list:
            if self._file_contains_webhook_patterns(file_path):
                webhook_endpoints.append({
                    "file": file_path,
                    "purpose": "webhook_handler",
                    "type": self._classify_webhook_file(file_path),
                    "confidence": 0.7
                })

        return webhook_endpoints

    def _detect_ci_cd_integrations(self, file_list: List[str]) -> List[Dict]:
        """Detect CI/CD integration configurations."""
        ci_cd_integrations = []

        for framework, patterns in self.integration_frameworks.items():
            if framework in ['github_actions', 'jenkins', 'circle_ci', 'travis_ci']:
                for file_path in file_list:
                    if any(pattern in file_path for pattern in patterns):
                        ci_cd_integrations.append({
                            "framework": framework,
                            "file": file_path,
                            "capabilities": self._analyze_ci_cd_capabilities(file_path, framework),
                            "confidence": 0.9
                        })
                        break  # Only add once per framework

        return ci_cd_integrations

    def _detect_api_integration_points(self, api_analysis: Dict) -> List[Dict]:
        """Detect API endpoints suitable for integration."""
        integration_points = []

        api_endpoints = api_analysis.get("api_endpoints", [])
        for endpoint in api_endpoints:
            if isinstance(endpoint, dict):
                url = endpoint.get("url", "")
                method = endpoint.get("method", "")

                # Check if endpoint is suitable for bounty integration
                if self._is_integration_suitable_endpoint(url, method):
                    integration_points.append({
                        "url": url,
                        "method": method,
                        "purpose": self._classify_integration_purpose(url),
                        "authentication": endpoint.get("security", []),
                        "rate_limits": endpoint.get("rate_limiting", {}),
                        "confidence": 0.8
                    })

        return integration_points

    def _assess_automation_capabilities(self, file_list: List[str], governance: Dict) -> Dict:
        """Assess the repository's automation capabilities."""
        automation_score = 0.0
        capabilities = []

        # Check for CI/CD presence
        ci_cd_governance = governance.get("ci_cd_governance", {})
        if ci_cd_governance.get("ci_platforms"):
            automation_score += 0.3
            capabilities.append("ci_cd_pipeline")

        # Check for webhook handlers
        webhook_files = [f for f in file_list if 'webhook' in f.lower() or 'hook' in f.lower()]
        if webhook_files:
            automation_score += 0.2
            capabilities.append("webhook_handlers")

        # Check for API clients or integration libraries
        api_client_files = [f for f in file_list if 'client' in f.lower() or 'integration' in f.lower()]
        if api_client_files:
            automation_score += 0.2
            capabilities.append("api_clients")

        # Check for automation scripts
        automation_scripts = [f for f in file_list if 'automate' in f.lower() or 'script' in f.lower()]
        if automation_scripts:
            automation_score += 0.1
            capabilities.append("automation_scripts")

        return {
            "automation_score": automation_score,
            "capabilities": capabilities,
            "readiness_level": self._score_to_readiness_level(automation_score)
        }

    def _identify_submission_mechanisms(self, file_list: List[str]) -> List[Dict]:
        """Identify mechanisms for automated submission."""
        mechanisms = []

        # Look for GitHub API usage
        github_api_files = [f for f in file_list if 'github' in f.lower() and ('api' in f.lower() or 'client' in f.lower())]
        if github_api_files:
            mechanisms.append({
                "type": "github_api_client",
                "files": github_api_files,
                "capabilities": ["pr_creation", "issue_management", "release_automation"],
                "confidence": 0.8
            })

        # Look for webhook-based submissions
        webhook_submissions = [f for f in file_list if 'submit' in f.lower() and ('webhook' in f.lower() or 'hook' in f.lower())]
        if webhook_submissions:
            mechanisms.append({
                "type": "webhook_submission",
                "files": webhook_submissions,
                "capabilities": ["automated_pr_submission", "status_updates"],
                "confidence": 0.7
            })

        # Look for CI/CD based submissions
        ci_cd_submissions = [f for f in file_list if 'deploy' in f.lower() or 'publish' in f.lower()]
        if ci_cd_submissions:
            mechanisms.append({
                "type": "ci_cd_deployment",
                "files": ci_cd_submissions,
                "capabilities": ["automated_deployment", "integration_testing"],
                "confidence": 0.6
            })

        return mechanisms

    def _identify_high_alpha_targets(self, api_analysis: Dict, file_list: List[str]) -> List[Dict]:
        """Identify high-value API targets that would be attractive for bounties."""
        high_alpha_targets = []

        api_endpoints = api_analysis.get("api_endpoints", [])

        for endpoint in api_endpoints:
            if isinstance(endpoint, dict):
                url = endpoint.get("url", "")
                method = endpoint.get("method", "")
                security = endpoint.get("security", [])

                # Calculate alpha score based on various factors
                alpha_score = self._calculate_endpoint_alpha_score(url, method, security, file_list)

                if alpha_score >= 0.7:  # Only include high-alpha targets
                    high_alpha_targets.append({
                        "url": url,
                        "method": method,
                        "alpha_score": alpha_score,
                        "security_level": self._assess_security_level(security),
                        "complexity": self._assess_endpoint_complexity(url, method),
                        "bounty_potential": self._assess_bounty_potential(url, method, security),
                        "integration_complexity": self._assess_integration_complexity(url, file_list),
                        "confidence": 0.85
                    })

        # Sort by alpha score descending
        high_alpha_targets.sort(key=lambda x: x["alpha_score"], reverse=True)

        return high_alpha_targets

    def _calculate_endpoint_alpha_score(self, url: str, method: str, security: List[str], file_list: List[str]) -> float:
        """Calculate the alpha score for an endpoint (higher = more valuable for bounties)."""
        score = 0.5  # Base score

        url_lower = url.lower()

        # High-value endpoints
        if any(pattern in url_lower for pattern in ['/admin', '/config', '/settings', '/system']):
            score += 0.3  # Administrative endpoints

        if any(pattern in url_lower for pattern in ['/api/v', '/webhook', '/integration']):
            score += 0.2  # API and integration endpoints

        if any(pattern in url_lower for pattern in ['/auth', '/login', '/token', '/oauth']):
            score += 0.25  # Authentication endpoints

        if any(pattern in url_lower for pattern in ['/upload', '/import', '/export', '/data']):
            score += 0.15  # Data handling endpoints

        # Method-based scoring
        if method in ['POST', 'PUT', 'PATCH']:
            score += 0.1  # Write operations are more valuable

        if method == 'DELETE':
            score += 0.2  # Delete operations are high-risk/high-reward

        # Security-based scoring (more security = higher complexity = higher alpha)
        security_complexity = len(security) * 0.1
        score += min(security_complexity, 0.2)  # Cap at 0.2

        # File-based scoring (endpoints with extensive file handling)
        relevant_files = [f for f in file_list if any(keyword in f.lower() for keyword in
                        ['auth', 'security', 'admin', 'config', url.split('/')[-1]])]
        file_bonus = min(len(relevant_files) * 0.05, 0.15)
        score += file_bonus

        return min(score, 1.0)  # Cap at 1.0

    def _assess_security_level(self, security: List[str]) -> str:
        """Assess the security level of an endpoint."""
        if not security:
            return "none"

        security_features = len(security)
        if security_features >= 3:
            return "high"
        elif security_features >= 2:
            return "medium"
        else:
            return "low"

    def _assess_endpoint_complexity(self, url: str, method: str) -> str:
        """Assess the complexity of implementing against an endpoint."""
        complexity_score = 0

        # URL complexity
        path_segments = len([s for s in url.split('/') if s])
        complexity_score += min(path_segments * 0.1, 0.3)

        # Method complexity
        if method in ['POST', 'PUT', 'PATCH']:
            complexity_score += 0.2
        if method == 'DELETE':
            complexity_score += 0.3

        # Query parameter complexity
        if '?' in url:
            complexity_score += 0.2

        if complexity_score >= 0.6:
            return "high"
        elif complexity_score >= 0.3:
            return "medium"
        else:
            return "low"

    def _assess_bounty_potential(self, url: str, method: str, security: List[str]) -> str:
        """Assess the bounty potential of an endpoint."""
        potential_score = 0

        url_lower = url.lower()

        # High-impact endpoints
        if any(word in url_lower for word in ['admin', 'root', 'system', 'config']):
            potential_score += 0.4

        if any(word in url_lower for word in ['auth', 'login', 'token']):
            potential_score += 0.3

        if method == 'DELETE':
            potential_score += 0.2

        # Security features increase potential
        potential_score += len(security) * 0.1

        if potential_score >= 0.7:
            return "critical"
        elif potential_score >= 0.4:
            return "high"
        elif potential_score >= 0.2:
            return "medium"
        else:
            return "low"

    def _assess_integration_complexity(self, url: str, file_list: List[str]) -> str:
        """Assess how complex it would be to integrate with this endpoint."""
        complexity = "medium"

        # Check if there are existing integration files
        endpoint_name = url.split('/')[-1] or url.split('/')[-2]
        related_files = [f for f in file_list if endpoint_name.lower() in f.lower()]

        if related_files:
            complexity = "low"  # Existing integration code
        elif any('integration' in f.lower() or 'client' in f.lower() for f in file_list):
            complexity = "medium"  # Some integration infrastructure exists
        else:
            complexity = "high"  # No existing integration infrastructure

        return complexity

    def _file_contains_webhook_patterns(self, file_path: str) -> bool:
        """Check if a file contains webhook-related patterns."""
        # This would typically read the file content, but for now we'll use filename patterns
        file_lower = file_path.lower()
        return any(pattern in file_lower for pattern_list in self.webhook_patterns.values() for pattern in pattern_list)

    def _classify_webhook_file(self, file_path: str) -> str:
        """Classify the type of webhook file."""
        file_lower = file_path.lower()

        if 'github' in file_lower:
            return 'github_webhook'
        elif any(ci in file_lower for ci in ['ci', 'cd', 'pipeline', 'jenkins', 'circle']):
            return 'ci_cd_webhook'
        elif 'api' in file_lower:
            return 'api_webhook'
        else:
            return 'generic_webhook'

    def _analyze_ci_cd_capabilities(self, file_path: str, framework: str) -> List[str]:
        """Analyze CI/CD capabilities for a specific framework."""
        capabilities = []

        if framework == 'github_actions':
            capabilities = ["automated_testing", "deployment", "pr_validation", "release_automation"]
        elif framework == 'jenkins':
            capabilities = ["build_automation", "deployment", "notification_systems", "plugin_ecosystem"]
        elif framework == 'circle_ci':
            capabilities = ["parallel_execution", "docker_support", "artifact_management"]
        elif framework == 'travis_ci':
            capabilities = ["multi_os_testing", "deployment", "notification_systems"]

        return capabilities

    def _is_integration_suitable_endpoint(self, url: str, method: str) -> bool:
        """Determine if an endpoint is suitable for bounty integration."""
        url_lower = url.lower()

        # Suitable endpoints for bounty operations
        suitable_patterns = [
            '/pulls', '/issues', '/releases', '/webhooks',
            '/api/v', '/integrations', '/automations'
        ]

        # Suitable HTTP methods
        suitable_methods = ['POST', 'PUT', 'PATCH']

        return (any(pattern in url_lower for pattern in suitable_patterns) and
                method in suitable_methods)

    def _classify_integration_purpose(self, url: str) -> str:
        """Classify the purpose of an integration endpoint."""
        url_lower = url.lower()

        if 'pull' in url_lower:
            return 'pr_management'
        elif 'issue' in url_lower:
            return 'issue_tracking'
        elif 'release' in url_lower:
            return 'release_management'
        elif 'webhook' in url_lower:
            return 'event_handling'
        elif 'integration' in url_lower:
            return 'third_party_integration'
        else:
            return 'general_api'

    def _calculate_integration_score(self, integration_analysis: Dict) -> float:
        """Calculate overall integration capability score."""
        score = 0.0

        # Webhook endpoints (30% weight)
        webhook_count = len(integration_analysis.get("webhook_endpoints", []))
        score += min(webhook_count * 0.1, 0.3)

        # CI/CD integrations (25% weight)
        ci_cd_count = len(integration_analysis.get("ci_cd_integrations", []))
        score += min(ci_cd_count * 0.25, 0.25)

        # API integration points (25% weight)
        api_points = len(integration_analysis.get("api_integration_points", []))
        score += min(api_points * 0.083, 0.25)  # 0.25 / 3 max points

        # Automation capabilities (20% weight)
        automation_score = integration_analysis.get("automation_capabilities", {}).get("automation_score", 0.0)
        score += automation_score * 0.2

        return min(score, 1.0)

    def _calculate_integration_confidence(self, integration_analysis: Dict) -> float:
        """Calculate confidence in integration analysis."""
        confidence_factors = []

        # Data completeness
        if integration_analysis.get("webhook_endpoints"):
            confidence_factors.append(0.9)
        if integration_analysis.get("ci_cd_integrations"):
            confidence_factors.append(0.8)
        if integration_analysis.get("api_integration_points"):
            confidence_factors.append(0.8)
        if integration_analysis.get("automation_capabilities"):
            confidence_factors.append(0.7)

        if not confidence_factors:
            return 0.3

        # Use harmonic mean for conservative confidence
        return len(confidence_factors) / sum(1/c for c in confidence_factors)

    def _score_to_readiness_level(self, score: float) -> str:
        """Convert automation score to readiness level."""
        if score >= 0.8:
            return "fully_automated"
        elif score >= 0.6:
            return "highly_automated"
        elif score >= 0.4:
            return "moderately_automated"
        elif score >= 0.2:
            return "partially_automated"
        else:
            return "manual_only"

    def generate_integration_plan(self, integration_analysis: Dict, bounty_requirements: Dict) -> Dict:
        """Generate a plan for integrating bounty solutions."""
        plan = {
            "integration_strategy": self._determine_integration_strategy(integration_analysis),
            "required_steps": self._generate_integration_steps(integration_analysis, bounty_requirements),
            "estimated_effort": self._estimate_integration_effort(integration_analysis),
            "risk_assessment": self._assess_integration_risks(integration_analysis),
            "generated_at": datetime.now().isoformat()
        }

        return plan

    def _determine_integration_strategy(self, integration_analysis: Dict) -> str:
        """Determine the optimal integration strategy."""
        automation_level = integration_analysis.get("automation_capabilities", {}).get("readiness_level", "manual_only")

        if automation_level in ["fully_automated", "highly_automated"]:
            return "full_automation"
        elif automation_level == "moderately_automated":
            return "semi_automation"
        else:
            return "manual_integration"

    def _generate_integration_steps(self, integration_analysis: Dict, bounty_requirements: Dict) -> List[Dict]:
        """Generate step-by-step integration plan."""
        steps = []

        strategy = self._determine_integration_strategy(integration_analysis)

        if strategy == "full_automation":
            steps.extend([
                {
                    "step": "setup_api_client",
                    "description": "Configure automated API client for bounty submissions",
                    "effort": "low",
                    "dependencies": []
                },
                {
                    "step": "configure_webhooks",
                    "description": "Set up webhook handlers for status updates",
                    "effort": "medium",
                    "dependencies": ["setup_api_client"]
                },
                {
                    "step": "integrate_ci_cd",
                    "description": "Connect to existing CI/CD pipeline for automated deployment",
                    "effort": "medium",
                    "dependencies": ["configure_webhooks"]
                }
            ])
        elif strategy == "semi_automation":
            steps.extend([
                {
                    "step": "manual_api_setup",
                    "description": "Manually configure API endpoints for bounty operations",
                    "effort": "medium",
                    "dependencies": []
                },
                {
                    "step": "automated_monitoring",
                    "description": "Set up automated monitoring and status tracking",
                    "effort": "low",
                    "dependencies": ["manual_api_setup"]
                }
            ])
        else:  # manual_integration
            steps.extend([
                {
                    "step": "manual_submission",
                    "description": "Perform manual bounty submission and monitoring",
                    "effort": "high",
                    "dependencies": []
                }
            ])

        return steps

    def _estimate_integration_effort(self, integration_analysis: Dict) -> Dict:
        """Estimate the effort required for integration."""
        automation_level = integration_analysis.get("automation_capabilities", {}).get("readiness_level", "manual_only")

        effort_estimates = {
            "fully_automated": {"time": "1-2 hours", "complexity": "low"},
            "highly_automated": {"time": "2-4 hours", "complexity": "medium"},
            "moderately_automated": {"time": "4-8 hours", "complexity": "medium"},
            "partially_automated": {"time": "8-16 hours", "complexity": "high"},
            "manual_only": {"time": "16-40 hours", "complexity": "high"}
        }

        return effort_estimates.get(automation_level, {"time": "unknown", "complexity": "unknown"})

    def _assess_integration_risks(self, integration_analysis: Dict) -> List[Dict]:
        """Assess risks associated with integration approach."""
        risks = []

        automation_level = integration_analysis.get("automation_capabilities", {}).get("readiness_level", "manual_only")

        if automation_level == "manual_only":
            risks.append({
                "risk": "human_error",
                "level": "high",
                "description": "Manual processes increase risk of submission errors",
                "mitigation": "Implement validation checklists and peer review"
            })

        webhook_count = len(integration_analysis.get("webhook_endpoints", []))
        if webhook_count == 0:
            risks.append({
                "risk": "no_webhook_support",
                "level": "medium",
                "description": "Lack of webhook support may limit automation capabilities",
                "mitigation": "Implement polling-based status monitoring"
            })

        return risks


def analyze_api_integration_points(file_list: List[str], api_analysis: Dict,
                                 governance: Dict) -> Dict:
    """Convenience function for API integration analysis."""
    engine = APIIntegrationEngine()
    return engine.analyze_integration_points(file_list, api_analysis, governance)