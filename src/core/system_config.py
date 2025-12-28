"""System configuration for Repository Intelligence Scanner."""

import os

SYSTEM_CONFIG = {
    "name": "repository_intelligence_scanner",
    "version": "1.1.0",
    "classification": "decision_grade_repository_analysis",
    "authority_level": "bounded_senior_reviewer",
    "status": "canonical"
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
    }
}
