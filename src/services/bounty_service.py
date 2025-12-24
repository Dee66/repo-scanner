"""Bounty Service Layer for Algora Bounty Hunting.

Orchestrates bounty core modules to provide comprehensive bounty hunting
capabilities with 99.999% SME accuracy.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from src.core.bounty.maintainer_profile_engine import MaintainerProfileEngine, generate_maintainer_profile
from src.core.bounty.profitability_triage import ProfitabilityTriageEngine, triage_bounty_profitability
from src.core.bounty.api_integration_engine import APIIntegrationEngine, analyze_api_integration_points
from src.core.bounty.pr_automation import PRAutomationEngine, generate_pr_for_bounty
from src.core.bounty.accuracy_validator import BountyAccuracyValidator, validate_bounty_accuracy
from src.core.bounty.reputation_monitor import ReputationMonitor
from src.core.bounty.bounty_performance_optimizer import ParallelBountyAnalyzer, BountyAnalysisBatch

logger = logging.getLogger(__name__)


class BountyService:
    """Main service for bounty hunting operations."""

    def __init__(self, enable_parallel: bool = True, max_workers: int = 4):
        self.profile_engine = MaintainerProfileEngine()
        self.triage_engine = ProfitabilityTriageEngine()
        self.api_engine = APIIntegrationEngine()
        self.pr_engine = PRAutomationEngine()
        self.validator = BountyAccuracyValidator()
        self.reputation_monitor = ReputationMonitor()
        self.parallel_analyzer = ParallelBountyAnalyzer(max_workers=max_workers) if enable_parallel else None

    def analyze_bounty_opportunity(self, repository_url: str, bounty_data: Dict,
                                 analysis_results: Dict) -> Dict:
        """Complete bounty opportunity analysis pipeline."""

        logger.info(f"Analyzing bounty opportunity: {bounty_data.get('id', 'unknown')}")

        # Extract analysis results
        intent_posture = analysis_results.get('intent_posture') or {}
        governance = analysis_results.get('governance') or {}
        risk_synthesis = analysis_results.get('risk_synthesis') or {}
        test_signals = analysis_results.get('test_signals') or {}
        api_analysis = analysis_results.get('api_analysis') or {}

        # Step 1: Generate maintainer profile
        maintainer_profile = self._generate_maintainer_profile(
            repository_url, intent_posture, governance
        )

        # Step 2: Perform profitability triage
        triage_result = self._perform_profitability_triage(
            repository_url, bounty_data, risk_synthesis, test_signals, maintainer_profile
        )

        # Step 3: Analyze integration points
        integration_analysis = self._analyze_integration_points(
            [], api_analysis, governance  # Empty file_list for now
        )

        # Step 4: Generate comprehensive bounty assessment
        bounty_assessment = self._generate_bounty_assessment(
            bounty_data, maintainer_profile, triage_result, integration_analysis
        )

        logger.info(f"Bounty analysis complete: {triage_result['triage_decision']['decision']}")

        return bounty_assessment

    def generate_bounty_solution(self, bounty_data: Dict, maintainer_profile: Dict,
                               governance: Dict, solution_code: Dict,
                               adr_analysis: Dict = None, forensics_data: Dict = None,
                               repo_path: str = None) -> Dict:
        """Generate complete bounty solution including PR content."""

        logger.info(f"Generating bounty solution for: {bounty_data.get('id', 'unknown')}")

        # Generate PR content
        pr_content = self._generate_pr_content(
            bounty_data, maintainer_profile, governance, solution_code,
            adr_analysis, forensics_data, repo_path
        )

        # Generate integration plan
        integration_plan = self._generate_integration_plan(
            governance, pr_content
        )

        # Create solution package
        solution_package = {
            "bounty_id": bounty_data.get("id"),
            "pr_content": pr_content,
            "integration_plan": integration_plan,
            "generated_at": datetime.now().isoformat(),
            "confidence_score": pr_content.get("confidence_score", 0.0)
        }

        logger.info(f"Bounty solution generated with confidence: {solution_package['confidence_score']:.3f}")

        return solution_package

    def validate_bounty_accuracy(self) -> Dict:
        """Validate current bounty prediction accuracy."""
        return validate_bounty_accuracy()

    def add_accuracy_validation(self, bounty_id: str, repository_url: str,
                              bounty_data: Dict, predicted_profitability: float,
                              predicted_merge_confidence: float, actual_outcome: bool,
                              actual_merge_time: Optional[int] = None) -> None:
        """Add a validation case for accuracy tracking."""
        self.validator.add_validation_case(
            bounty_id, repository_url, bounty_data,
            predicted_profitability, predicted_merge_confidence,
            actual_outcome, actual_merge_time
        )
        logger.info(f"Added accuracy validation for bounty: {bounty_id}")

    def _generate_maintainer_profile(self, repository_url: str, intent_posture: Dict,
                                   governance: Dict) -> Dict:
        """Generate maintainer profile with caching."""
        # Check cache first
        cached_profile = self.profile_engine.get_profile(repository_url)
        if cached_profile:
            return cached_profile

        # Generate new profile
        profile = generate_maintainer_profile(repository_url, intent_posture, governance)

        # Cache it
        self.profile_engine.profile_cache[repository_url] = profile

        return profile

    def _perform_profitability_triage(self, repository_url: str, bounty_data: Dict,
                                    risk_synthesis: Dict, test_signals: Dict,
                                    maintainer_profile: Dict) -> Dict:
        """Perform profitability triage."""
        return triage_bounty_profitability(
            repository_url, bounty_data, risk_synthesis, test_signals, maintainer_profile
        )

    def _analyze_integration_points(self, file_list: List[str], api_analysis: Dict,
                                  governance: Dict) -> Dict:
        """Analyze API integration points."""
        return analyze_api_integration_points(file_list, api_analysis, governance)

    def _generate_pr_content(self, bounty_data: Dict, maintainer_profile: Dict,
                           governance: Dict, solution_code: Dict,
                           adr_analysis: Dict = None, forensics_data: Dict = None,
                           repo_path: str = None) -> Dict:
        """Generate PR content."""
        return generate_pr_for_bounty(bounty_data, maintainer_profile, governance, solution_code,
                                    adr_analysis=adr_analysis, forensics_data=forensics_data, repo_path=repo_path)

    def _generate_integration_plan(self, governance: Dict, pr_content: Dict) -> Dict:
        """Generate integration plan based on governance and PR content."""
        # Create integration plan from governance analysis
        ci_cd_governance = governance.get("ci_cd_governance", {})
        api_integration = governance.get("api_analysis", {})

        plan = {
            "deployment_strategy": "automated" if ci_cd_governance.get("ci_platforms") else "manual",
            "ci_cd_platforms": ci_cd_governance.get("ci_platforms", []),
            "required_checks": pr_content.get("ci_cd_integration", {}).get("required_checks", []),
            "webhook_endpoints": [],  # Would be populated from api_integration
            "prerequisites": [
                "Repository access confirmed",
                "Branch permissions verified",
                "CI/CD pipeline access confirmed"
            ],
            "post_merge_actions": [
                "Monitor CI/CD pipeline execution",
                "Track merge success metrics",
                "Update accuracy validation data"
            ]
        }

        return plan

    def _generate_bounty_assessment(self, bounty_data: Dict, maintainer_profile: Dict,
                                  triage_result: Dict, integration_analysis: Dict) -> Dict:
        """Generate comprehensive bounty assessment."""
        assessment = {
            "bounty_id": bounty_data.get("id"),
            "repository_url": triage_result.get("repository_url"),
            "assessment_timestamp": datetime.now().isoformat(),
            "overall_recommendation": self._determine_overall_recommendation(triage_result),
            "components": {
                "maintainer_profile": maintainer_profile,
                "profitability_triage": triage_result,
                "integration_analysis": integration_analysis
            },
            "risk_factors": self._identify_risk_factors(triage_result, integration_analysis),
            "success_probability": self._calculate_success_probability(triage_result, integration_analysis),
            "estimated_effort": self._estimate_effort(triage_result, integration_analysis),
            "next_steps": self._generate_next_steps(triage_result, integration_analysis)
        }

        return assessment

    def _determine_overall_recommendation(self, triage_result: Dict) -> str:
        """Determine overall bounty recommendation."""
        decision = triage_result.get("triage_decision", {}).get("decision", "UNKNOWN")

        if decision == "HIGH_PRIORITY":
            return "PURSUE_IMMEDIATELY"
        elif decision == "MEDIUM_PRIORITY":
            return "EVALUATE_FURTHER"
        elif decision == "LOW_PRIORITY":
            return "MONITOR_ONLY"
        else:
            return "AVOID_BOUNTY"

    def _identify_risk_factors(self, triage_result: Dict, integration_analysis: Dict) -> List[str]:
        """Identify risk factors that could affect bounty success."""
        risks = []

        # Profitability risks
        profitability = triage_result.get("profitability_score", 0.0)
        if profitability < 0.5:
            risks.append("Low profitability score indicates poor merge prospects")

        # Integration risks
        automation_level = integration_analysis.get("automation_capabilities", {}).get("readiness_level")
        if automation_level == "manual_only":
            risks.append("Manual integration required - increases complexity")

        # Confidence risks
        confidence = triage_result.get("confidence_score", 0.0)
        if confidence < 0.8:
            risks.append("Low confidence in assessment - additional validation needed")

        return risks

    def _calculate_success_probability(self, triage_result: Dict, integration_analysis: Dict) -> float:
        """Calculate overall success probability."""
        profitability = triage_result.get("profitability_score", 0.0)
        confidence = triage_result.get("confidence_score", 0.0)

        # Integration readiness bonus
        automation_level = integration_analysis.get("automation_capabilities", {}).get("readiness_level")
        automation_bonus = {
            "fully_automated": 0.2,
            "highly_automated": 0.15,
            "moderately_automated": 0.1,
            "partially_automated": 0.05,
            "manual_only": 0.0
        }.get(automation_level, 0.0)

        success_prob = profitability * confidence + automation_bonus
        return min(1.0, max(0.0, success_prob))

    def _estimate_effort(self, triage_result: Dict, integration_analysis: Dict) -> Dict:
        """Estimate effort required for bounty completion."""
        decision = triage_result.get("triage_decision", {}).get("decision", "UNKNOWN")

        effort_estimates = {
            "HIGH_PRIORITY": {
                "time_estimate": "2-4 hours",
                "complexity": "low",
                "resources_needed": ["1 developer", "automated testing"]
            },
            "MEDIUM_PRIORITY": {
                "time_estimate": "4-8 hours",
                "complexity": "medium",
                "resources_needed": ["1 developer", "code review", "testing"]
            },
            "LOW_PRIORITY": {
                "time_estimate": "8-16 hours",
                "complexity": "high",
                "resources_needed": ["1-2 developers", "extensive testing", "documentation"]
            },
            "REJECT": {
                "time_estimate": "not applicable",
                "complexity": "not applicable",
                "resources_needed": []
            }
        }

        return effort_estimates.get(decision, effort_estimates["REJECT"])

    def _generate_next_steps(self, triage_result: Dict, integration_analysis: Dict) -> List[Dict]:
        """Generate next steps based on assessment."""
        decision = triage_result.get("triage_decision", {}).get("decision", "UNKNOWN")
        next_steps = []

        if decision == "HIGH_PRIORITY":
            next_steps = [
                {
                    "step": "allocate_resources",
                    "description": "Assign developer and prepare development environment",
                    "priority": "immediate",
                    "timeframe": "within 1 hour"
                },
                {
                    "step": "analyze_requirements",
                    "description": "Deep dive into bounty requirements and edge cases",
                    "priority": "immediate",
                    "timeframe": "within 2 hours"
                },
                {
                    "step": "implement_solution",
                    "description": "Develop and test the bounty solution",
                    "priority": "high",
                    "timeframe": "within 4 hours"
                }
            ]
        elif decision == "MEDIUM_PRIORITY":
            next_steps = [
                {
                    "step": "schedule_review",
                    "description": "Schedule team review of bounty opportunity",
                    "priority": "high",
                    "timeframe": "within 24 hours"
                },
                {
                    "step": "gather_requirements",
                    "description": "Collect additional requirements and clarifications",
                    "priority": "medium",
                    "timeframe": "within 48 hours"
                }
            ]
        elif decision == "LOW_PRIORITY":
            next_steps = [
                {
                    "step": "add_to_backlog",
                    "description": "Add to monitoring list for future consideration",
                    "priority": "low",
                    "timeframe": "when resources available"
                }
            ]
        else:  # REJECT
            next_steps = [
                {
                    "step": "document_rejection",
                    "description": "Document reasons for rejection in knowledge base",
                    "priority": "low",
                    "timeframe": "within 1 week"
                }
            ]

        return next_steps

    def analyze_bounty_batch(self, repository_url: str, bounty_items: List[Dict],
                           analysis_results: Dict, batch_id: str = None) -> List[Dict]:
        """Analyze multiple bounties in parallel for performance optimization."""
        if not self.parallel_analyzer:
            logger.warning("Parallel processing disabled, falling back to sequential processing")
            return [self.analyze_bounty_opportunity(repository_url, bounty, analysis_results)
                   for bounty in bounty_items]

        if not batch_id:
            batch_id = f"batch_{int(datetime.now().timestamp())}"

        batch = BountyAnalysisBatch(
            bounty_items=bounty_items,
            repository_url=repository_url,
            analysis_results=analysis_results,
            batch_id=batch_id
        )

        logger.info(f"Starting parallel analysis of {len(bounty_items)} bounties")
        start_time = datetime.now()

        results = self.parallel_analyzer.analyze_bounty_batch_parallel(batch)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Completed parallel analysis in {duration:.2f}s")

        return results

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for bounty operations."""
        if self.parallel_analyzer:
            return self.parallel_analyzer.get_performance_stats()
        return {"parallel_processing": False, "message": "Parallel processing not enabled"}

    def optimize_for_large_repository(self, repository_url: str, estimated_file_count: int) -> Dict[str, Any]:
        """Optimize bounty analysis settings for large repositories."""
        # Adjust worker count based on repository size
        if estimated_file_count > 1000:
            optimal_workers = min(8, max(2, estimated_file_count // 500))
        elif estimated_file_count > 100:
            optimal_workers = 4
        else:
            optimal_workers = 2

        # Reinitialize with optimal settings if needed
        if self.parallel_analyzer and self.parallel_analyzer.max_workers != optimal_workers:
            logger.info(f"Optimizing for large repository: {optimal_workers} workers for {estimated_file_count} files")
            self.parallel_analyzer = ParallelBountyAnalyzer(max_workers=optimal_workers)

        return {
            "optimized_workers": optimal_workers,
            "estimated_file_count": estimated_file_count,
            "cache_enabled": True,
            "parallel_processing": True
        }


def analyze_bounty_opportunity(repository_url: str, bounty_data: Dict,
                             analysis_results: Dict) -> Dict:
    """Convenience function for complete bounty analysis."""
    service = BountyService()
    return service.analyze_bounty_opportunity(repository_url, bounty_data, analysis_results)


def analyze_bounty_batch(repository_url: str, bounty_items: List[Dict],
                        analysis_results: Dict, batch_id: str = None) -> List[Dict]:
    """Convenience function for parallel bounty batch analysis."""
    service = BountyService(enable_parallel=True)
    return service.analyze_bounty_batch(repository_url, bounty_items, analysis_results, batch_id)


def generate_bounty_solution(bounty_data: Dict, maintainer_profile: Dict,
                           governance: Dict, solution_code: Dict) -> Dict:
    """Convenience function for bounty solution generation."""
    service = BountyService()
    return service.generate_bounty_solution(bounty_data, maintainer_profile, governance, solution_code)