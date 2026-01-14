"""
Repository Intelligence Scanner - System Configuration Module

This module defines the core system identity, configuration, and operational parameters
for the deterministic repository analysis tool.
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass
import os


class SystemClassification(Enum):
    """Explicit system classification for the repository intelligence scanner."""
    DETERMINISTIC_REPOSITORY_ANALYSIS_TOOL = "deterministic_repository_analysis_tool"


class AuthorityLevel(Enum):
    """Authority levels for system operation."""
    STANDARD = "standard"
    ELEVATED = "elevated"
    MAXIMUM = "maximum"


class SystemStatus(Enum):
    """Current operational status of the system."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"
    MAINTENANCE = "maintenance"


@dataclass
class SystemConfig:
    """
    Core system configuration with identity and operational parameters.

    This class encapsulates all system-level configuration required for
    deterministic repository analysis operations.
    """
    # System Identity
    name: str = "Repository Intelligence Scanner"
    version: str = "2.0.0"
    classification: SystemClassification = SystemClassification.DETERMINISTIC_REPOSITORY_ANALYSIS_TOOL

    # Authority and Status
    authority_level: AuthorityLevel = AuthorityLevel.STANDARD
    status: SystemStatus = SystemStatus.DEVELOPMENT

    # Operational Parameters
    max_complexity: int = 1000000  # Maximum repository complexity score
    timeout_seconds: int = 300     # Default analysis timeout
    enable_debug: bool = False     # Debug mode flag

    @classmethod
    def from_env(cls) -> 'SystemConfig':
        """Create configuration from environment variables."""
        config = cls()

        # Override from environment if set
        if os.getenv('RIS_NAME'):
            config.name = os.getenv('RIS_NAME')
        if os.getenv('RIS_VERSION'):
            config.version = os.getenv('RIS_VERSION')
        if os.getenv('RIS_AUTHORITY_LEVEL'):
            try:
                config.authority_level = AuthorityLevel(os.getenv('RIS_AUTHORITY_LEVEL'))
            except ValueError:
                pass  # Keep default
        if os.getenv('RIS_STATUS'):
            try:
                config.status = SystemStatus(os.getenv('RIS_STATUS'))
            except ValueError:
                pass  # Keep default
        if os.getenv('RIS_MAX_COMPLEXITY'):
            try:
                config.max_complexity = int(os.getenv('RIS_MAX_COMPLEXITY'))
            except ValueError:
                pass
        if os.getenv('RIS_TIMEOUT'):
            try:
                config.timeout_seconds = int(os.getenv('RIS_TIMEOUT'))
            except ValueError:
                pass
        if os.getenv('RIS_DEBUG'):
            config.enable_debug = os.getenv('RIS_DEBUG').lower() in ('true', '1', 'yes')

        return config

    def to_dict(self) -> dict:
        """Convert configuration to dictionary for serialization."""
        return {
            'name': self.name,
            'version': self.version,
            'classification': self.classification.value,
            'authority_level': self.authority_level.value,
            'status': self.status.value,
            'max_complexity': self.max_complexity,
            'timeout_seconds': self.timeout_seconds,
            'enable_debug': self.enable_debug
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SystemConfig':
        """Create configuration from dictionary."""
        config = cls()
        config.name = data.get('name', config.name)
        config.version = data.get('version', config.version)
        try:
            config.classification = SystemClassification(data.get('classification', config.classification.value))
        except ValueError:
            pass
        try:
            config.authority_level = AuthorityLevel(data.get('authority_level', config.authority_level.value))
        except ValueError:
            pass
        try:
            config.status = SystemStatus(data.get('status', config.status.value))
        except ValueError:
            pass
        config.max_complexity = data.get('max_complexity', config.max_complexity)
        config.timeout_seconds = data.get('timeout_seconds', config.timeout_seconds)
        config.enable_debug = data.get('enable_debug', config.enable_debug)
        return config


# Global system configuration instance
_system_config: Optional[SystemConfig] = None


def get_system_config() -> SystemConfig:
    """Get the global system configuration instance."""
    global _system_config
    if _system_config is None:
        _system_config = SystemConfig.from_env()
    return _system_config


def set_system_config(config: SystemConfig) -> None:
    """Set the global system configuration instance."""
    global _system_config
    _system_config = config


def reset_system_config() -> None:
    """Reset the global system configuration to defaults."""
    global _system_config
    _system_config = None


# Legacy compatibility - keeping existing structure for backward compatibility
SYSTEM_CONFIG = {
    "name": "repository_intelligence_scanner",
    "version": "1.1.0",
    "classification": "decision_grade_repository_analysis",
    "authority_level": "bounded_senior_reviewer",
    "status": "canonical"
}

# Explicit non-claims: What this system does NOT do
EXPLICIT_NON_CLAIMS = {
    "no_execution": "This system does not execute, run, or interpret any application code",
    "no_business_correctness": "This system does not assess business logic correctness or validate business requirements",
    "no_defect_finding": "This system does not find, identify, or report software defects or bugs",
    "no_human_replacement": "This system does not replace human judgment, review, or decision-making",
    "no_forced_action": "This system does not force, require, or mandate any specific actions or changes"
}

# Core promise: What this system DOES guarantee
CORE_PROMISE = {
    "auditable_repository_snapshots": "This system provides deterministic, reproducible snapshots of repository structure and content that can be audited and verified"
}

# Non-promise limitations: What this system does NOT guarantee
NON_PROMISE_LIMITATIONS = {
    "no_completeness_guarantees": "This system does not guarantee complete coverage of all repository aspects or comprehensive analysis",
    "no_intent_coverage": "This system does not assess or guarantee coverage of human intent, requirements, or business objectives",
    "no_security_coverage": "This system does not provide security analysis, vulnerability assessment, or security guarantees",
    "no_fitness_guarantees": "This system does not guarantee fitness for any particular purpose or provide suitability assurances"
}

# Data usage limits and monitoring
DATA_USAGE_CONFIG = {
    "limits": {
        "manual_scans": {
            "max_files": int(os.getenv("REPO_SCANNER_MAX_FILES", "10000")),
            "max_size_mb": int(os.getenv("REPO_SCANNER_MAX_SIZE_MB", "500"))
        },
        "automated_scans": {
            "max_files": int(os.getenv("REPO_SCANNER_CI_MAX_FILES", "5000")),
            "max_size_mb": int(os.getenv("REPO_SCANNER_CI_MAX_SIZE_MB", "100"))
        }
    },
    "monitoring": {
        "track_large_files_threshold_mb": 50,
        "log_usage_stats": True,
        "ci_stricter_limits": True
    },
    "performance": {
        "cpu_threshold_percent": 80,
        "memory_threshold_percent": 85,
        "disk_threshold_percent": 90,
        "load_average_multiplier": 2.0,
        "response_time_ms_threshold": 5000
    }
}
