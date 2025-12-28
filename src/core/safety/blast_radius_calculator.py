"""Blast Radius Calculation for Repository Intelligence Scanner.

The blast radius represents the scope and impact of potential changes or analysis
results. Unbounded blast radius scenarios occur when the system cannot determine
or limit the potential impact of its recommendations.
"""

from typing import Dict, List, Set, Optional
import re


class BlastRadiusCalculator:
    """Calculates blast radius for repository analysis scenarios."""

    def __init__(self):
        self.unbounded_indicators = [
            "global_dependencies",
            "shared_libraries",
            "api_changes",
            "database_schema_changes",
            "infrastructure_modifications",
            "cross_service_impacts",
            "external_system_dependencies"
        ]

    def calculate_blast_radius(self, repository_analysis: Dict) -> Dict:
        """Calculate the blast radius for a repository analysis.

        Returns a dict with:
        - bounded: bool - whether blast radius can be determined
        - radius_estimate: str - qualitative estimate (small/medium/large/unbounded)
        - impact_areas: List[str] - areas that would be affected
        - unbounded_reasons: List[str] - reasons why radius is unbounded
        - confidence_score: float - confidence in the calculation (0-1)
        """
        impact_areas = self._identify_impact_areas(repository_analysis)
        unbounded_reasons = self._check_unbounded_indicators(repository_analysis, impact_areas)

        bounded = len(unbounded_reasons) == 0
        radius_estimate = self._estimate_radius(impact_areas, unbounded_reasons)
        confidence_score = self._calculate_confidence(repository_analysis, impact_areas)

        return {
            "bounded": bounded,
            "radius_estimate": radius_estimate,
            "impact_areas": impact_areas,
            "unbounded_reasons": unbounded_reasons,
            "confidence_score": confidence_score,
            "requires_refusal": not bounded and confidence_score > 0.7
        }

    def _identify_impact_areas(self, analysis: Dict) -> List[str]:
        """Identify areas that would be impacted by changes."""
        areas = []

        # Check for API changes
        if self._has_api_changes(analysis):
            areas.append("public_api")
            areas.append("downstream_consumers")

        # Check for database changes
        if self._has_database_changes(analysis):
            areas.append("data_layer")
            areas.append("data_integrity")

        # Check for infrastructure changes
        if self._has_infrastructure_changes(analysis):
            areas.append("infrastructure")
            areas.append("deployment_processes")

        # Check for shared library usage
        if self._has_shared_library_usage(analysis):
            areas.append("dependent_services")
            areas.append("shared_components")

        # Check for cross-service dependencies
        if self._has_cross_service_dependencies(analysis):
            areas.append("service_mesh")
            areas.append("distributed_systems")

        return list(set(areas))  # Remove duplicates

    def _check_unbounded_indicators(self, analysis: Dict, impact_areas: List[str]) -> List[str]:
        """Check for indicators that make blast radius unbounded."""
        reasons = []

        # Cannot determine downstream consumers
        if "public_api" in impact_areas and not self._can_identify_consumers(analysis):
            reasons.append("cannot_identify_api_consumers")

        # Global database changes without migration strategy
        if "data_layer" in impact_areas and not self._has_migration_strategy(analysis):
            reasons.append("global_data_changes_without_migration")

        # Infrastructure changes affecting multiple environments
        if "infrastructure" in impact_areas and self._affects_multiple_environments(analysis):
            reasons.append("multi_environment_infrastructure_changes")

        # Shared libraries without version management
        if "shared_components" in impact_areas and not self._has_version_management(analysis):
            reasons.append("unversioned_shared_dependencies")

        # Distributed system changes without coordination
        if "distributed_systems" in impact_areas and not self._has_coordination_plan(analysis):
            reasons.append("distributed_changes_without_coordination")

        return reasons

    def _estimate_radius(self, impact_areas: List[str], unbounded_reasons: List[str]) -> str:
        """Estimate the blast radius qualitatively."""
        if len(unbounded_reasons) > 0:
            return "unbounded"

        area_count = len(impact_areas)
        if area_count <= 1:
            return "small"
        elif area_count <= 3:
            return "medium"
        else:
            return "large"

    def _calculate_confidence(self, analysis: Dict, impact_areas: List[str]) -> float:
        """Calculate confidence in blast radius calculation."""
        confidence = 0.5  # Base confidence

        # Increase confidence based on available data
        if analysis.get("dependency_analysis"):
            confidence += 0.2

        if analysis.get("api_analysis"):
            confidence += 0.1

        if analysis.get("governance_signals"):
            confidence += 0.1

        if analysis.get("test_coverage", {}).get("percentage", 0) > 70:
            confidence += 0.1

        return min(confidence, 1.0)

    def _has_api_changes(self, analysis: Dict) -> bool:
        """Check if analysis indicates API changes."""
        # Look for API-related files or changes
        files = analysis.get("file_list", [])
        return any("api" in f.lower() or "interface" in f.lower() for f in files)

    def _has_database_changes(self, analysis: Dict) -> bool:
        """Check if analysis indicates database changes."""
        files = analysis.get("file_list", [])
        return any("migration" in f.lower() or "schema" in f.lower() or "model" in f.lower() for f in files)

    def _has_infrastructure_changes(self, analysis: Dict) -> bool:
        """Check if analysis indicates infrastructure changes."""
        files = analysis.get("file_list", [])
        return any("docker" in f.lower() or "kubernetes" in f.lower() or "terraform" in f.lower() for f in files)

    def _has_shared_library_usage(self, analysis: Dict) -> bool:
        """Check if repository uses shared libraries."""
        dependencies = analysis.get("dependency_analysis", {})
        return len(dependencies.get("internal_dependencies", [])) > 0

    def _has_cross_service_dependencies(self, analysis: Dict) -> bool:
        """Check for cross-service dependencies."""
        # This would need more sophisticated analysis
        return False  # Placeholder

    def _can_identify_consumers(self, analysis: Dict) -> bool:
        """Check if API consumers can be identified."""
        # Check for consumer identification in analysis
        return analysis.get("api_analysis", {}).get("consumers_identified", False)

    def _has_migration_strategy(self, analysis: Dict) -> bool:
        """Check if database changes have migration strategy."""
        return "migration" in str(analysis.get("file_list", [])).lower()

    def _affects_multiple_environments(self, analysis: Dict) -> bool:
        """Check if changes affect multiple environments."""
        # Check for environment-specific configurations
        return len(analysis.get("deployment_configs", [])) > 1

    def _has_version_management(self, analysis: Dict) -> bool:
        """Check if dependencies have version management."""
        return "version" in str(analysis.get("dependency_analysis", {})).lower()

    def _has_coordination_plan(self, analysis: Dict) -> bool:
        """Check if distributed changes have coordination plan."""
        # Look for coordination documents
        files = analysis.get("file_list", [])
        return any("readme" in f.lower() or "deployment" in f.lower() for f in files)


def should_refuse_analysis(blast_radius_result: Dict) -> bool:
    """Determine if analysis should be refused based on blast radius."""
    return blast_radius_result.get("requires_refusal", False)


def generate_refusal_reason(blast_radius_result: Dict) -> str:
    """Generate a human-readable refusal reason."""
    if blast_radius_result["bounded"]:
        return "Analysis within acceptable blast radius"

    reasons = blast_radius_result["unbounded_reasons"]
    if not reasons:
        return "Blast radius calculation inconclusive"

    reason_map = {
        "cannot_identify_api_consumers": "Cannot identify all downstream consumers of API changes",
        "global_data_changes_without_migration": "Global data changes detected without migration strategy",
        "multi_environment_infrastructure_changes": "Infrastructure changes affect multiple environments",
        "unversioned_shared_dependencies": "Shared dependencies lack proper version management",
        "distributed_changes_without_coordination": "Distributed system changes lack coordination plan"
    }

    readable_reasons = [reason_map.get(r, r) for r in reasons]
    return f"Unbounded blast radius: {', '.join(readable_reasons)}"