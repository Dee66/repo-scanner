"""Feature flag system for gradual rollout and A/B testing."""

import os
from typing import Dict, Any, Optional
from enum import Enum

class FeatureFlag(Enum):
    """Available feature flags."""
    ENHANCED_LOGGING = "enhanced_logging"
    ADVANCED_METRICS = "advanced_metrics"
    EXPERIMENTAL_ANALYSIS = "experimental_analysis"
    BETA_API_ENDPOINTS = "beta_api_endpoints"
    PERFORMANCE_MONITORING = "performance_monitoring"
    CRYPTOGRAPHIC_ANALYSIS = "cryptographic_analysis"
    SUPPLY_CHAIN_SECURITY = "supply_chain_security"
    SECURITY_TESTING_DEPTH = "security_testing_depth"
    ARCHITECTURAL_SECURITY = "architectural_security"
    THREAT_MODELING = "threat_modeling"
    COMPLIANCE_FRAMEWORKS = "compliance_frameworks"
    OPERATIONAL_SECURITY = "operational_security"
    PERFORMANCE_SECURITY_TRADEOFFS = "performance_security_tradeoffs"

class FeatureFlagManager:
    """Manages feature flags for gradual rollout."""

    def __init__(self):
        self.flags: Dict[str, bool] = {}
        self._load_flags()

    def _load_flags(self):
        """Load feature flags from environment variables."""
        # Default flags (can be overridden by environment)
        defaults = {
            FeatureFlag.ENHANCED_LOGGING.value: True,  # Generally safe
            FeatureFlag.ADVANCED_METRICS.value: False,  # Optional advanced feature
            FeatureFlag.EXPERIMENTAL_ANALYSIS.value: False,  # Experimental
            FeatureFlag.BETA_API_ENDPOINTS.value: False,  # Beta features
            FeatureFlag.PERFORMANCE_MONITORING.value: True,  # Generally useful
            FeatureFlag.CRYPTOGRAPHIC_ANALYSIS.value: False,  # New experimental feature
            FeatureFlag.SUPPLY_CHAIN_SECURITY.value: False,  # New experimental feature
            FeatureFlag.SECURITY_TESTING_DEPTH.value: False,  # New experimental feature
            FeatureFlag.ARCHITECTURAL_SECURITY.value: False,  # New experimental feature
            FeatureFlag.THREAT_MODELING.value: False,  # New experimental feature
            FeatureFlag.COMPLIANCE_FRAMEWORKS.value: False,  # New experimental feature
            FeatureFlag.OPERATIONAL_SECURITY.value: False,  # New experimental feature
            FeatureFlag.PERFORMANCE_SECURITY_TRADEOFFS.value: False,  # New experimental feature
        }

        # Load from environment variables
        for flag in FeatureFlag:
            env_var = f"FEATURE_{flag.value.upper()}"
            env_value = os.getenv(env_var)

            if env_value is not None:
                # Parse boolean values
                self.flags[flag.value] = env_value.lower() in ('true', '1', 'yes', 'on')
            else:
                self.flags[flag.value] = defaults.get(flag.value, False)

    def is_enabled(self, flag: FeatureFlag) -> bool:
        """Check if a feature flag is enabled."""
        return self.flags.get(flag.value, False)

    def enable(self, flag: FeatureFlag):
        """Enable a feature flag."""
        self.flags[flag.value] = True

    def disable(self, flag: FeatureFlag):
        """Disable a feature flag."""
        self.flags[flag.value] = False

    def get_all_flags(self) -> Dict[str, bool]:
        """Get all feature flags and their status."""
        return self.flags.copy()

    def get_rollout_percentage(self, flag: FeatureFlag) -> float:
        """Get rollout percentage for gradual deployment (simplified)."""
        if self.is_enabled(flag):
            return 100.0
        return 0.0

# Global instance
feature_flags = FeatureFlagManager()

def is_feature_enabled(flag: FeatureFlag) -> bool:
    """Convenience function to check if a feature is enabled."""
    return feature_flags.is_enabled(flag)

def get_feature_flags() -> Dict[str, bool]:
    """Get all feature flags."""
    return feature_flags.get_all_flags()