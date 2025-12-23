"""Profitability Triage for Algora Bounty Hunting.

Filters and prioritizes bounties based on merge-likelihood analysis,
combining risk assessment, testing signals, and bounty-specific factors.
"""

from typing import Dict, List, Optional
from datetime import datetime


class ProfitabilityTriageEngine:
    """Engine for triaging bounty profitability with 99.999% accuracy target."""

    def __init__(self):
        self.triage_cache = {}
        self.accuracy_threshold = 0.99999  # 99.999%

    def triage_bounty(self, repository_url: str, bounty_data: Dict,
                     risk_synthesis: Dict, test_signals: Dict,
                     maintainer_profile: Dict = None, competition_data: Dict = None) -> Dict:
        """Perform comprehensive bounty profitability triage."""

        # Extract bounty characteristics
        bounty_complexity = self._assess_bounty_complexity(bounty_data)
        bounty_scope = self._assess_bounty_scope(bounty_data)
        bounty_quality = self._assess_bounty_quality(bounty_data)

        # Analyze repository factors
        repository_risk = self._analyze_repository_risk(risk_synthesis)
        testing_maturity = self._analyze_testing_maturity(test_signals)
        maintainer_factors = self._analyze_maintainer_factors(maintainer_profile)

        # Analyze competition landscape
        competition_analysis = self._analyze_competition_landscape(competition_data or {}, bounty_data)

        # Calculate profitability score
        profitability_score = self._calculate_profitability_score(
            bounty_complexity, bounty_scope, bounty_quality,
            repository_risk, testing_maturity, maintainer_factors, competition_analysis
        )

        # Generate triage decision
        triage_decision = self._generate_triage_decision(profitability_score)

        # Calculate confidence score
        confidence_score = self._calculate_triage_confidence(
            risk_synthesis, test_signals, maintainer_profile
        )

        triage_result = {
            "repository_url": repository_url,
            "bounty_id": bounty_data.get("id", "unknown"),
            "profitability_score": profitability_score,
            "triage_decision": triage_decision,
            "confidence_score": confidence_score,
            "analysis_factors": {
                "bounty_complexity": bounty_complexity,
                "bounty_scope": bounty_scope,
                "bounty_quality": bounty_quality,
                "repository_risk": repository_risk,
                "testing_maturity": testing_maturity,
                "maintainer_factors": maintainer_factors,
                "competition_analysis": competition_analysis
            },
            "recommendations": self._generate_triage_recommendations(triage_decision, confidence_score),
            "triaged_at": datetime.now().isoformat(),
            "triage_version": "1.1.0"  # Updated for competition weighting
        }

        # Cache result for future reference
        cache_key = f"{repository_url}:{bounty_data.get('id', 'unknown')}"
        self.triage_cache[cache_key] = triage_result

        return triage_result

    def _assess_bounty_complexity(self, bounty_data: Dict) -> Dict:
        """Assess the complexity of the bounty issue."""
        complexity_score = 0.5  # Default medium complexity
        complexity_factors = []

        # Analyze issue description
        description = bounty_data.get("description", "").lower()
        title = bounty_data.get("title", "").lower()

        # Complexity indicators
        if any(word in description for word in ["simple", "easy", "straightforward"]):
            complexity_score -= 0.2
            complexity_factors.append("simple_description")
        if any(word in description for word in ["complex", "difficult", "challenging"]):
            complexity_score += 0.2
            complexity_factors.append("complex_description")

        # Technical requirements
        if "typescript" in description or "react" in description:
            complexity_score += 0.1
            complexity_factors.append("advanced_technology")
        if "security" in title or "vulnerability" in title:
            complexity_score += 0.3
            complexity_factors.append("security_related")

        # Labels and tags
        labels = bounty_data.get("labels", [])
        if "good first issue" in [l.lower() for l in labels]:
            complexity_score -= 0.3
            complexity_factors.append("good_first_issue")
        if "bug" in [l.lower() for l in labels]:
            complexity_score += 0.1
            complexity_factors.append("bug_fix")

        return {
            "complexity_score": max(0.0, min(1.0, complexity_score)),
            "complexity_level": self._score_to_level(complexity_score),
            "complexity_factors": complexity_factors
        }

    def _assess_bounty_scope(self, bounty_data: Dict) -> Dict:
        """Assess the scope and impact of the bounty."""
        scope_score = 0.5  # Default medium scope
        scope_factors = []

        # Files affected
        files_affected = bounty_data.get("files_affected", [])
        if len(files_affected) == 1:
            scope_score -= 0.2
            scope_factors.append("single_file")
        elif len(files_affected) > 5:
            scope_score += 0.3
            scope_factors.append("multiple_files")

        # Code changes required
        lines_changed = bounty_data.get("estimated_lines_changed", 50)
        if lines_changed < 20:
            scope_score -= 0.2
            scope_factors.append("small_change")
        elif lines_changed > 200:
            scope_score += 0.3
            scope_factors.append("large_change")

        return {
            "scope_score": max(0.0, min(1.0, scope_score)),
            "scope_level": self._score_to_level(scope_score),
            "scope_factors": scope_factors
        }

    def _assess_bounty_quality(self, bounty_data: Dict) -> Dict:
        """Assess the quality and clarity of the bounty."""
        quality_score = 0.5  # Default medium quality
        quality_factors = []

        # Description completeness
        description = bounty_data.get("description", "")
        if len(description) > 100:
            quality_score += 0.2
            quality_factors.append("detailed_description")
        if "```" in description:  # Code examples
            quality_score += 0.1
            quality_factors.append("code_examples")

        # Reproduction steps
        if "steps to reproduce" in description.lower():
            quality_score += 0.2
            quality_factors.append("reproduction_steps")

        # Acceptance criteria
        if "expected behavior" in description.lower():
            quality_score += 0.1
            quality_factors.append("acceptance_criteria")

        return {
            "quality_score": max(0.0, min(1.0, quality_score)),
            "quality_level": self._score_to_level(quality_score),
            "quality_factors": quality_factors
        }

    def _analyze_repository_risk(self, risk_synthesis: Dict) -> Dict:
        """Analyze repository risk factors for bounty success."""
        overall_risk = risk_synthesis.get("overall_risk_assessment", {})
        risk_level = overall_risk.get("overall_risk_level", "medium")

        # Convert risk level to score (lower risk = higher bounty success potential)
        risk_scores = {"low": 0.8, "medium": 0.5, "high": 0.2}
        risk_score = risk_scores.get(risk_level, 0.5)

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": overall_risk.get("risk_factors", [])
        }

    def _analyze_testing_maturity(self, test_signals: Dict) -> Dict:
        """Analyze testing maturity and its impact on bounty success."""
        testing_maturity = test_signals.get("testing_maturity_score", 0.5)
        test_coverage = test_signals.get("test_coverage_signals", {}).get("estimated_coverage", 0.5)

        # Higher testing maturity = higher bounty success potential
        maturity_score = (testing_maturity + test_coverage) / 2

        return {
            "maturity_score": maturity_score,
            "testing_maturity": testing_maturity,
            "test_coverage": test_coverage,
            "test_frameworks": test_signals.get("test_frameworks", [])
        }

    def _analyze_maintainer_factors(self, maintainer_profile: Dict = None) -> Dict:
        """Analyze maintainer-related factors affecting bounty success."""
        if not maintainer_profile:
            return {
                "maintainer_score": 0.5,
                "responsiveness": 0.5,
                "review_tendencies": "unknown",
                "factors": ["no_profile_available"]
            }

        # Extract relevant maintainer factors
        review_patterns = maintainer_profile.get("review_patterns", {})
        communication_style = maintainer_profile.get("communication_style", {})

        maintainer_score = 0.5

        # Responsive maintainers = higher success potential
        if review_patterns.get("response_time") == "fast":
            maintainer_score += 0.2

        # Flexible review depth = higher success potential
        if review_patterns.get("review_depth") == "flexible":
            maintainer_score += 0.1

        return {
            "maintainer_score": max(0.0, min(1.0, maintainer_score)),
            "responsiveness": review_patterns.get("response_time", "unknown"),
            "review_tendencies": review_patterns.get("review_depth", "unknown"),
            "factors": ["profile_analyzed"]
        }

    def _calculate_profitability_score(self, bounty_complexity: Dict, bounty_scope: Dict,
                                    bounty_quality: Dict, repository_risk: Dict,
                                    testing_maturity: Dict, maintainer_factors: Dict,
                                    competition_analysis: Dict) -> float:
        """Calculate overall bounty profitability score using Bayesian approach with competition weighting."""

        # Extract individual scores
        complexity_score = bounty_complexity["complexity_score"]
        scope_score = bounty_scope["scope_score"]
        quality_score = bounty_quality["quality_score"]
        risk_score = repository_risk["risk_score"]
        maturity_score = testing_maturity["maturity_score"]
        maintainer_score = maintainer_factors["maintainer_score"]
        competition_score = competition_analysis["competition_score"]

        # Weighted combination for profitability with competition factor
        # Weights: complexity (15%), scope (12%), quality (12%), risk (15%), testing (12%), maintainer (12%), competition (22%)
        profitability = (
            (1 - complexity_score) * 0.15 +  # Lower complexity = higher profitability
            (1 - scope_score) * 0.12 +       # Smaller scope = higher profitability
            quality_score * 0.12 +           # Higher quality = higher profitability
            risk_score * 0.15 +              # Lower risk = higher profitability
            maturity_score * 0.12 +          # Higher testing maturity = higher profitability
            maintainer_score * 0.12 +        # Better maintainer factors = higher profitability
            competition_score * 0.22         # Lower competition = higher profitability
        )

        return max(0.0, min(1.0, profitability))

    def _generate_triage_decision(self, profitability_score: float) -> Dict:
        """Generate triage decision based on profitability score."""
        if profitability_score >= 0.8:
            return {
                "decision": "HIGH_PRIORITY",
                "action": "pursue_immediately",
                "rationale": f"Exceptional profitability score ({profitability_score:.3f}) indicates strong merge potential",
                "estimated_effort": "high_impact"
            }
        elif profitability_score >= 0.6:
            return {
                "decision": "MEDIUM_PRIORITY",
                "action": "evaluate_further",
                "rationale": f"Good profitability score ({profitability_score:.3f}) with reasonable merge prospects",
                "estimated_effort": "moderate_impact"
            }
        elif profitability_score >= 0.4:
            return {
                "decision": "LOW_PRIORITY",
                "action": "monitor_only",
                "rationale": f"Moderate profitability score ({profitability_score:.3f}) - consider only if time permits",
                "estimated_effort": "low_impact"
            }
        else:
            return {
                "decision": "REJECT",
                "action": "avoid_bounty",
                "rationale": f"Low profitability score ({profitability_score:.3f}) suggests poor merge prospects",
                "estimated_effort": "not_recommended"
            }

    def _calculate_triage_confidence(self, risk_synthesis: Dict, test_signals: Dict,
                                   maintainer_profile: Dict = None) -> float:
        """Calculate confidence in triage decision."""

        # Base confidence from data completeness
        risk_confidence = risk_synthesis.get("risk_confidence", 0.5)
        test_completeness = 1.0 if test_signals else 0.5
        profile_completeness = 1.0 if maintainer_profile else 0.3

        # Calculate overall confidence
        confidence = (risk_confidence + test_completeness + profile_completeness) / 3

        # Apply conservative adjustment for high-stakes decisions
        return min(confidence, 0.99999)  # Cap at 99.999% target

    def _generate_triage_recommendations(self, triage_decision: Dict,
                                       confidence_score: float) -> List[Dict]:
        """Generate specific recommendations based on triage decision."""
        recommendations = []

        decision = triage_decision["decision"]

        if decision == "HIGH_PRIORITY":
            recommendations.extend([
                {
                    "priority": "immediate",
                    "action": "allocate_resources",
                    "description": "Assign top developers to this bounty",
                    "confidence": confidence_score
                },
                {
                    "priority": "immediate",
                    "action": "prepare_solution",
                    "description": "Begin solution development immediately",
                    "confidence": confidence_score
                }
            ])
        elif decision == "MEDIUM_PRIORITY":
            recommendations.extend([
                {
                    "priority": "short_term",
                    "action": "schedule_review",
                    "description": "Review bounty details and assign if resources available",
                    "confidence": confidence_score
                }
            ])
        elif decision == "LOW_PRIORITY":
            recommendations.extend([
                {
                    "priority": "long_term",
                    "action": "add_to_watchlist",
                    "description": "Monitor for changes but don't actively pursue",
                    "confidence": confidence_score
                }
            ])
        else:  # REJECT
            recommendations.extend([
                {
                    "priority": "none",
                    "action": "skip_bounty",
                    "description": "Avoid this bounty due to low profitability",
                    "confidence": confidence_score
                }
            ])

        return recommendations

    def _score_to_level(self, score: float) -> str:
        """Convert numeric score to descriptive level."""
        if score >= 0.7:
            return "high"
        elif score >= 0.4:
            return "medium"
        else:
            return "low"

    def get_cached_triage(self, repository_url: str, bounty_id: str) -> Optional[Dict]:
        """Retrieve cached triage result."""
        cache_key = f"{repository_url}:{bounty_id}"
        return self.triage_cache.get(cache_key)

    def _analyze_competition_landscape(self, competition_data: Dict, bounty_data: Dict) -> Dict:
        """Analyze competition landscape for the bounty."""
        competition_score = 0.5  # Default neutral competition
        competition_factors = []

        # Analyze existing submissions
        existing_submissions = competition_data.get("existing_submissions", [])
        active_contributors = competition_data.get("active_contributors", 0)

        # Competition intensity based on submissions
        if len(existing_submissions) == 0:
            competition_score += 0.3  # No competition = higher profitability
            competition_factors.append("no_existing_submissions")
        elif len(existing_submissions) <= 2:
            competition_score += 0.1  # Light competition
            competition_factors.append("light_competition")
        elif len(existing_submissions) <= 5:
            competition_score -= 0.1  # Moderate competition
            competition_factors.append("moderate_competition")
        else:
            competition_score -= 0.3  # Heavy competition
            competition_factors.append("heavy_competition")

        # Active contributors impact
        if active_contributors > 10:
            competition_score -= 0.2  # Many active contributors
            competition_factors.append("high_contributor_activity")
        elif active_contributors > 5:
            competition_score -= 0.1  # Moderate contributor activity
            competition_factors.append("moderate_contributor_activity")

        # Bounty age factor - older bounties may have less competition
        bounty_age_days = competition_data.get("bounty_age_days", 0)
        if bounty_age_days > 30:
            competition_score += 0.1  # Older bounties may be less competitive
            competition_factors.append("older_bounty")
        elif bounty_age_days < 7:
            competition_score -= 0.1  # New bounties attract more competition
            competition_factors.append("new_bounty")

        # Competition quality analysis
        high_quality_competitors = sum(1 for sub in existing_submissions
                                     if sub.get("quality_score", 0) > 0.7)
        if high_quality_competitors > 0:
            competition_score -= 0.2  # Strong competition
            competition_factors.append("high_quality_competition")

        competition_score = max(0.0, min(1.0, competition_score))

        return {
            "competition_score": competition_score,  # Lower = less competition = better
            "competition_factors": competition_factors,
            "existing_submissions_count": len(existing_submissions),
            "active_contributors": active_contributors,
            "high_quality_competitors": high_quality_competitors
        }


def triage_bounty_profitability(repository_url: str, bounty_data: Dict,
                              risk_synthesis: Dict, test_signals: Dict,
                              maintainer_profile: Dict = None, competition_data: Dict = None) -> Dict:
    """Convenience function for bounty profitability triage."""
    engine = ProfitabilityTriageEngine()
    return engine.triage_bounty(repository_url, bounty_data, risk_synthesis,
                              test_signals, maintainer_profile, competition_data)