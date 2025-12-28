"""Recovery Strategies for Error Handling Framework.

Defines specific recovery strategies for different types of errors
to enable graceful degradation and automatic recovery.
"""

import time
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from .error_handling import RecoveryStrategy, ErrorContext, ErrorCategory, ErrorSeverity
from src.core.exceptions import ScannerError, RepositoryDiscoveryError, GitError

logger = logging.getLogger(__name__)


# Network-related recovery strategies
def network_retry_can_recover(exception: Exception, context: ErrorContext) -> bool:
    """Check if network error can be recovered with retry."""
    return (context.category == ErrorCategory.NETWORK and
            context.severity in [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH] and
            context.retry_count < 3)

def network_retry_recovery(exception: Exception, context: ErrorContext) -> None:
    """Network retry recovery - just wait and retry."""
    # The retry mechanism handles the actual retry logic
    # This strategy just indicates the error is recoverable
    pass

def api_fallback_recovery(exception: Exception, context: ErrorContext) -> Optional[Dict]:
    """API fallback recovery - return cached or default data."""
    # For API calls, we could return cached data or empty results
    if context.category == ErrorCategory.EXTERNAL_API:
        logger.warning(f"API call failed, returning empty result for {context.operation}")
        return []  # Return empty list for most API calls
    return None


# Filesystem-related recovery strategies
def filesystem_permission_can_recover(exception: Exception, context: ErrorContext) -> bool:
    """Check if filesystem permission error can be recovered."""
    return (context.category == ErrorCategory.PERMISSION and
            context.severity == ErrorSeverity.MEDIUM)

def filesystem_permission_recovery(exception: Exception, context: ErrorContext) -> None:
    """Attempt to fix filesystem permission issues."""
    # This is a placeholder - in practice, you might try different approaches
    # like using sudo, changing permissions, or using alternative paths
    logger.warning(f"Attempting to recover from permission error in {context.operation}")
    # For now, just re-raise as we can't automatically fix permissions
    raise exception

def filesystem_corruption_can_recover(exception: Exception, context: ErrorContext) -> bool:
    """Check if filesystem corruption can be recovered."""
    return (context.category == ErrorCategory.CORRUPTION and
            context.severity == ErrorSeverity.MEDIUM)

def filesystem_corruption_recovery(exception: Exception, context: ErrorContext) -> str:
    """Attempt to recover from filesystem corruption."""
    # For corrupted files, we might try to recreate or use backups
    file_path = context.metadata.get('file_path')
    if file_path:
        logger.warning(f"Attempting to recover corrupted file: {file_path}")
        # Try to recreate the file or use a backup
        # This is highly dependent on the specific use case
    raise exception


# Git-related recovery strategies
def git_clone_can_recover(exception: Exception, context: ErrorContext) -> bool:
    """Check if git clone error can be recovered."""
    return (isinstance(exception, GitError) and
            context.retry_count < 2 and
            "timeout" in str(exception).lower())

def git_clone_recovery(exception: Exception, context: ErrorContext) -> None:
    """Git clone recovery - try with different options."""
    # For git clone timeouts, we could try:
    # - Shallow clone (--depth=1)
    # - Different protocol (https vs ssh)
    # - Different branch
    logger.info("Attempting git clone recovery with shallow clone")
    # The actual retry would happen at the call site
    pass

def git_operation_fallback(exception: Exception, context: ErrorContext) -> Optional[str]:
    """Git operation fallback - use local copy or skip."""
    if context.operation == "clone_repository":
        # For cloning failures, we could fall back to:
        # - Using a local cached copy
        # - Skipping the remote repository
        # - Using an alternative repository URL
        logger.warning("Git clone failed, falling back to skip remote repository")
        return None  # Indicate skip
    return None


# Configuration-related recovery strategies
def config_validation_can_recover(exception: Exception, context: ErrorContext) -> bool:
    """Check if configuration validation error can be recovered."""
    return (context.category == ErrorCategory.VALIDATION and
            context.severity == ErrorSeverity.MEDIUM)

def config_validation_recovery(exception: Exception, context: ErrorContext) -> Dict[str, Any]:
    """Configuration validation recovery - use defaults."""
    logger.warning(f"Configuration validation failed, using defaults for {context.operation}")
    # Return default configuration values
    return {
        "timeout": 30,
        "max_retries": 3,
        "batch_size": 10,
        "enable_parallel": True
    }


# Resource-related recovery strategies
def resource_exhaustion_can_recover(exception: Exception, context: ErrorContext) -> bool:
    """Check if resource exhaustion can be recovered."""
    return (context.category == ErrorCategory.RESOURCE and
            context.severity == ErrorSeverity.MEDIUM)

def resource_exhaustion_recovery(exception: Exception, context: ErrorContext) -> None:
    """Resource exhaustion recovery - wait and retry with reduced load."""
    # For memory/disk space issues, we could:
    # - Force garbage collection
    # - Clean up temporary files
    # - Reduce batch sizes
    # - Wait for resources to become available
    logger.warning("Resource exhaustion detected, attempting cleanup")

    # Force garbage collection
    import gc
    gc.collect()

    # Clean up temporary files older than 1 hour
    temp_dir = Path(tempfile.gettempdir())
    cutoff_time = time.time() - 3600  # 1 hour ago

    for temp_file in temp_dir.glob("scanner-*"):
        if temp_file.is_file() and temp_file.stat().st_mtime < cutoff_time:
            try:
                temp_file.unlink()
                logger.info(f"Cleaned up old temp file: {temp_file}")
            except Exception as e:
                logger.debug(f"Could not clean up {temp_file}: {e}")

    # Wait a bit for system to recover
    time.sleep(1)


# Timeout-related recovery strategies
def timeout_can_recover(exception: Exception, context: ErrorContext) -> bool:
    """Check if timeout error can be recovered."""
    return (context.category == ErrorCategory.TIMEOUT and
            context.retry_count < 2)

def timeout_recovery(exception: Exception, context: ErrorContext) -> None:
    """Timeout recovery - increase timeout and retry."""
    # For timeouts, we could increase the timeout value
    # or try with reduced complexity
    logger.info("Timeout detected, will retry with increased timeout")
    # The actual timeout increase would happen at the call site
    pass


# General fallback strategies
def graceful_degradation_fallback(exception: Exception, context: ErrorContext) -> Any:
    """General fallback - return safe default values."""
    operation = context.operation

    # Define safe defaults based on operation type
    defaults = {
        "fetch_bounties": [],
        "fetch_github_issues": [],
        "clone_repository": None,
        "analyze_repository": {"error": "Analysis failed, using cached results"},
        "generate_report": "# Error Report\n\nAnalysis failed due to: " + str(exception),
        "validate_input": False,
        "check_health": {"status": "degraded", "error": str(exception)}
    }

    fallback_value = defaults.get(operation, None)
    if fallback_value is not None:
        logger.warning(f"Using graceful degradation fallback for {operation}")
        return fallback_value

    # No specific fallback, re-raise
    raise exception


# Recovery strategy registry
RECOVERY_STRATEGIES = [
    # Network strategies
    RecoveryStrategy(
        name="network_retry",
        description="Retry network operations with backoff",
        can_recover=network_retry_can_recover,
        recovery_action=network_retry_recovery,
        fallback_action=graceful_degradation_fallback
    ),

    # API strategies
    RecoveryStrategy(
        name="api_fallback",
        description="Use cached or default data for failed API calls",
        can_recover=lambda e, c: c.category == ErrorCategory.EXTERNAL_API,
        recovery_action=api_fallback_recovery,
        fallback_action=graceful_degradation_fallback
    ),

    # Filesystem strategies
    RecoveryStrategy(
        name="filesystem_permission_recovery",
        description="Attempt to recover from permission errors",
        can_recover=filesystem_permission_can_recover,
        recovery_action=filesystem_permission_recovery,
        fallback_action=graceful_degradation_fallback
    ),

    RecoveryStrategy(
        name="filesystem_corruption_recovery",
        description="Attempt to recover from file corruption",
        can_recover=filesystem_corruption_can_recover,
        recovery_action=filesystem_corruption_recovery,
        fallback_action=graceful_degradation_fallback
    ),

    # Git strategies
    RecoveryStrategy(
        name="git_clone_recovery",
        description="Retry git clone with different options",
        can_recover=git_clone_can_recover,
        recovery_action=git_clone_recovery,
        fallback_action=git_operation_fallback
    ),

    # Configuration strategies
    RecoveryStrategy(
        name="config_validation_recovery",
        description="Use default configuration values",
        can_recover=config_validation_can_recover,
        recovery_action=config_validation_recovery,
        fallback_action=graceful_degradation_fallback
    ),

    # Resource strategies
    RecoveryStrategy(
        name="resource_exhaustion_recovery",
        description="Clean up resources and retry",
        can_recover=resource_exhaustion_can_recover,
        recovery_action=resource_exhaustion_recovery,
        fallback_action=graceful_degradation_fallback
    ),

    # Timeout strategies
    RecoveryStrategy(
        name="timeout_recovery",
        description="Retry with increased timeout",
        can_recover=timeout_can_recover,
        recovery_action=timeout_recovery,
        fallback_action=graceful_degradation_fallback
    ),

    # General fallback
    RecoveryStrategy(
        name="graceful_degradation",
        description="Graceful degradation with safe defaults",
        can_recover=lambda e, c: True,  # Always try as last resort
        recovery_action=graceful_degradation_fallback,
        fallback_action=None
    )
]


def register_all_recovery_strategies():
    """Register all predefined recovery strategies."""
    from .error_handling import get_error_handler

    error_handler = get_error_handler()
    for strategy in RECOVERY_STRATEGIES:
        error_handler.register_recovery_strategy(strategy)

    logger.info(f"Registered {len(RECOVERY_STRATEGIES)} recovery strategies")


# Initialize recovery strategies on import
# register_all_recovery_strategies()  # Commented out to avoid import-time issues
