"""Configuration for optional features that extend beyond core spec compliance."""

import os
from typing import Dict, Any

# Optional features configuration
# These features are not part of the core spec but can be enabled for advanced use cases
OPTIONAL_FEATURES_CONFIG = {
    # Web API server for remote access and CI/CD integration
    "api_server": {
        "enabled": os.getenv("REPO_SCANNER_ENABLE_API", "false").lower() == "true",
        "host": os.getenv("REPO_SCANNER_API_HOST", "localhost"),
        "port": int(os.getenv("REPO_SCANNER_API_PORT", "8000")),
        "workers": int(os.getenv("REPO_SCANNER_API_WORKERS", "1")),
    },

    # Health monitoring and 99.999% uptime tracking
    "health_monitoring": {
        "enabled": os.getenv("REPO_SCANNER_ENABLE_HEALTH", "false").lower() == "true",
        "uptime_sla_target": float(os.getenv("REPO_SCANNER_UPTIME_SLA", "99.999")),
        "health_check_interval": int(os.getenv("REPO_SCANNER_HEALTH_INTERVAL", "30")),
    },

    # Circuit breaker protection for external services
    "circuit_breakers": {
        "enabled": os.getenv("REPO_SCANNER_ENABLE_CIRCUIT_BREAKERS", "false").lower() == "true",
        "failure_threshold": int(os.getenv("REPO_SCANNER_CB_FAILURE_THRESHOLD", "5")),
        "recovery_timeout": int(os.getenv("REPO_SCANNER_CB_RECOVERY_TIMEOUT", "60")),
    },

    # Bounty scanning and analysis (requires external API access)
    "bounty_service": {
        "enabled": os.getenv("REPO_SCANNER_ENABLE_BOUNTIES", "false").lower() == "true",
        "api_url": os.getenv("REPO_SCANNER_BOUNTY_API_URL", "https://api.algora.io"),
        "api_key": os.getenv("REPO_SCANNER_BOUNTY_API_KEY", ""),
        "cache_ttl": int(os.getenv("REPO_SCANNER_BOUNTY_CACHE_TTL", "3600")),
    },

    # Advanced error handling and recovery strategies
    "error_handling": {
        "enabled": os.getenv("REPO_SCANNER_ENABLE_ERROR_HANDLING", "false").lower() == "true",
        "max_retries": int(os.getenv("REPO_SCANNER_MAX_RETRIES", "3")),
        "retry_delay": float(os.getenv("REPO_SCANNER_RETRY_DELAY", "1.0")),
    },

    # Graceful degradation for component failures
    "graceful_degradation": {
        "enabled": os.getenv("REPO_SCANNER_ENABLE_DEGRADATION", "false").lower() == "true",
        "degradation_timeout": int(os.getenv("REPO_SCANNER_DEGRADATION_TIMEOUT", "300")),
    },

    # Prometheus-compatible metrics collection
    "metrics": {
        "enabled": os.getenv("REPO_SCANNER_ENABLE_METRICS", "false").lower() == "true",
        "collection_interval": int(os.getenv("REPO_SCANNER_METRICS_INTERVAL", "60")),
        "retention_period": int(os.getenv("REPO_SCANNER_METRICS_RETENTION", "3600")),
    },
}

def is_feature_enabled(feature_name: str) -> bool:
    """Check if an optional feature is enabled."""
    return OPTIONAL_FEATURES_CONFIG.get(feature_name, {}).get("enabled", False)

def get_feature_config(feature_name: str) -> Dict[str, Any]:
    """Get configuration for a specific optional feature."""
    return OPTIONAL_FEATURES_CONFIG.get(feature_name, {})

def get_enabled_features() -> Dict[str, Dict[str, Any]]:
    """Get all enabled optional features."""
    return {name: config for name, config in OPTIONAL_FEATURES_CONFIG.items() if config["enabled"]}

def warn_about_spec_compliance():
    """Warn user about spec compliance when optional features are enabled."""
    enabled_features = get_enabled_features()
    if enabled_features:
        print("⚠️  WARNING: The following optional features are enabled, which may violate the core product spec:")
        for feature_name in enabled_features:
            print(f"   - {feature_name}: May introduce external dependencies or change offline-only operation")
        print("   Core spec requires: offline operation, no external services, controlled network access only")
        print("   Use these features at your own risk or update the spec accordingly.\n")