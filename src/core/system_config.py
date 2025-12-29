"""System configuration for Repository Intelligence Scanner."""

import os

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
