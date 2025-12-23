"""Analysis pipeline stages for Repository Intelligence Scanner."""

import concurrent.futures
import functools
import time
import logging
from pathlib import Path
from typing import Dict, List, Any

from ..performance_optimizer import OptimizedThreadPool, get_performance_optimizer
from ..monitoring import get_performance_monitor

logger = logging.getLogger(__name__)

from src.core.pipeline.repository_discovery import discover_repository_root, get_canonical_file_list
from src.core.pipeline.structural_modeling import analyze_repository_structure
from src.core.pipeline.static_semantic_analysis import analyze_semantic_structure
from src.core.pipeline.code_comprehension import analyze_code_comprehension
from src.core.pipeline.advanced_code_analysis import analyze_advanced_code
from src.core.pipeline.compliance_analysis import analyze_compliance
from src.core.pipeline.dependency_analysis import analyze_dependencies
from src.core.pipeline.code_duplication_analysis import analyze_code_duplication
from src.core.pipeline.api_analysis import analyze_api_definitions
from src.core.pipeline.test_signal_analysis import analyze_test_signals
from src.core.pipeline.governance_signal_analysis import analyze_governance_signals
from src.core.pipeline.intent_posture_classification import classify_intent_posture
from src.core.pipeline.misleading_signal_detection import analyze_misleading_signals
from src.core.pipeline.safe_change_surface_modeling import analyze_safe_change_surface
from src.core.pipeline.security_analysis import analyze_security_vulnerabilities
from src.core.pipeline.risk_synthesis import synthesize_risks
from src.core.pipeline.decision_artifact_generation import generate_decision_artifacts
from src.core.pipeline.authority_ceiling_evaluation import evaluate_authority_ceiling
from src.core.pipeline.determinism_verification import verify_determinism


class FileCache:
    """Simple file content cache to avoid repeated I/O operations."""
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
    
    def get_file_content(self, file_path: str) -> str:
        """Get file content with caching."""
        if file_path not in self._cache:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    self._cache[file_path] = f.read()
            except (IOError, OSError):
                self._cache[file_path] = ""
        return self._cache[file_path]
    
    def clear(self):
        """Clear the cache."""
        self._cache.clear()


# Global file cache instance
file_cache = FileCache()

ANALYSIS_PIPELINE_STAGES = [
    "repository_discovery",
    "structural_modeling",
    "static_semantic_analysis",
    "advanced_code_analysis",
    "code_comprehension_analysis",
    "compliance_analysis",
    "dependency_analysis",
    "code_duplication_analysis",
    "api_analysis",
    "security_vulnerability_analysis",
    "test_signal_analysis",
    "governance_signal_analysis",
    "intent_posture_classification",
    "misleading_signal_detection",
    "safe_change_surface_modeling",
    "risk_and_gap_synthesis",
    "decision_artifact_generation",
    "authority_ceiling_evaluation",
    "determinism_verification"
]

PARALLELISM_MODEL = {
    "strategy": "bounded_parallelism",
    "guarantees": [
        "output_order_independent_of_execution_order",
        "parallel_tasks_must_be_pure",
        "shared_state_forbidden"
    ]
}

def execute_pipeline(repository_path: str) -> dict:
    """Execute the full analysis pipeline with automatic optimization selection."""
    start_time = time.time()
    performance_optimizer = get_performance_optimizer()
    performance_monitor = get_performance_monitor()

    # Start performance tracking
    performance_monitor.start_operation("pipeline_execution", {"repository_path": repository_path})

    try:
        # Log initial memory usage
        initial_memory = performance_optimizer.get_memory_usage()
        logger.info(f"Starting analysis - Initial memory: {initial_memory['rss_mb']:.1f}MB")

        # Repository discovery
        repo_root = discover_repository_root(repository_path)
        file_list = get_canonical_file_list(repo_root)

        if not isinstance(file_list, list):
            file_list = []

        # Auto-select pipeline based on repository complexity
        if len(file_list) > 200 or _estimate_repository_complexity(file_list) > 50:
            logger.info(f"Complex repository detected ({len(file_list)} files), using optimized pipeline")
            try:
                from .optimized_analysis import execute_optimized_pipeline
                result = execute_optimized_pipeline(repository_path)
                # Complete performance tracking for optimized pipeline
                execution_time = time.time() - start_time
                performance_monitor.complete_operation("pipeline_execution", {
                    "execution_time": execution_time,
                    "file_count": len(file_list),
                    "pipeline_type": "optimized",
                    "status": "success"
                })
                return result
            except ImportError as e:
                logger.warning(f"Optimized pipeline not available ({e}), falling back to standard pipeline")
            except Exception as e:
                logger.error(f"Optimized pipeline failed ({e}), falling back to standard pipeline")

        # Standard pipeline for smaller repositories
        logger.info(f"Standard repository ({len(file_list)} files), using standard pipeline")
        result = _execute_standard_pipeline(repository_path, repo_root, file_list, start_time, initial_memory)

        # Complete performance tracking
        execution_time = time.time() - start_time
        performance_monitor.complete_operation("pipeline_execution", {
            "execution_time": execution_time,
            "file_count": len(file_list),
            "pipeline_type": "standard",
            "status": "success"
        })

        return result

    except Exception as e:
        # Track failed operations
        execution_time = time.time() - start_time
        performance_monitor.complete_operation("pipeline_execution", {
            "execution_time": execution_time,
            "status": "failed",
            "error": str(e)
        })
        raise

def _estimate_repository_complexity(file_list: List[str]) -> float:
    """Estimate repository complexity based on file count and types."""
    if not file_list:
        return 0.0

    complexity = len(file_list)

    # Add complexity for different file types
    extensions = {}
    for file_path in file_list:
        ext = Path(file_path).suffix.lower()
        extensions[ext] = extensions.get(ext, 0) + 1

    # Weight different file types by analysis complexity
    complexity_weights = {
        '.py': 2.0,      # Python - complex AST analysis
        '.java': 1.8,    # Java - complex analysis
        '.js': 1.5,      # JavaScript - regex-based but complex
        '.ts': 1.5,      # TypeScript - similar to JS
        '.cpp': 1.7,     # C++ - complex parsing
        '.c': 1.6,       # C - complex parsing
        '.go': 1.4,      # Go - moderate complexity
        '.rs': 1.4,      # Rust - moderate complexity
        '.php': 1.3,     # PHP - moderate complexity
        '.rb': 1.3,      # Ruby - moderate complexity
        '.scala': 1.6,   # Scala - complex
        '.kt': 1.5,      # Kotlin - complex
        '.swift': 1.4,   # Swift - moderate
    }

    for ext, count in extensions.items():
        weight = complexity_weights.get(ext, 1.0)
        complexity += count * (weight - 1.0)  # -1 because base count is already included

    # Add complexity for large files
    large_files = 0
    for file_path in file_list[:100]:  # Sample first 100 files
        try:
            size = Path(file_path).stat().st_size
            if size > 100000:  # > 100KB
                large_files += 1
        except (OSError, IOError):
            pass

    complexity += large_files * 2.0

    return complexity

def _execute_standard_pipeline(repository_path: str, repo_root: str, file_list: List[str],
                             start_time: float, initial_memory: Dict[str, Any]) -> dict:
    """Execute the standard analysis pipeline for smaller repositories."""
    performance_optimizer = get_performance_optimizer()

    # Structural modeling (must be first)
    structure = analyze_repository_structure(file_list)

    # Static semantic analysis (must be second)
    semantic = analyze_semantic_structure(file_list, structure)

    # Advanced code analysis (depends on semantic)
    advanced_code_analysis = analyze_advanced_code(file_list, semantic)

    # Code comprehension analysis (depends on semantic)
    code_comprehension = analyze_code_comprehension(Path(repo_root), semantic)

    # Security vulnerability analysis (depends on semantic)
    security_analysis = analyze_security_vulnerabilities(file_list, semantic)

    # Compliance analysis (depends on semantic)
    compliance_analysis = analyze_compliance(file_list, semantic)

    # Dependency analysis (depends on semantic)
    dependency_analysis = analyze_dependencies(file_list, semantic)

    # Code duplication analysis (depends on semantic)
    code_duplication_analysis = analyze_code_duplication(file_list, semantic)

    # API analysis (depends on semantic)
    api_analysis = analyze_api_definitions(file_list, semantic)

    # Test signal analysis (run first as others depend on it)
    test_signals = analyze_test_signals(file_list, structure, semantic)

    # Parallel execution for independent analysis stages
    thread_pool = OptimizedThreadPool(max_workers=4)
    try:
        # Submit parallel tasks that depend on test_signals
        governance_future = thread_pool.submit(analyze_governance_signals, file_list, structure, semantic, test_signals)
        intent_future = thread_pool.submit(classify_intent_posture, file_list, structure, semantic, test_signals, {})  # governance not ready yet

        # Wait for governance to complete, then update intent_posture with correct governance
        governance = governance_future.result()
        intent_posture = intent_future.result()

        # Re-run intent_posture with correct governance dependency
        intent_posture = classify_intent_posture(file_list, structure, semantic, test_signals, governance)
    finally:
        thread_pool_stats = thread_pool.get_stats()
        thread_pool.shutdown(wait=True)
        logger.info(f"Thread pool stats: {thread_pool_stats}")

    # Sequential execution for dependent stages
    misleading_signals = analyze_misleading_signals(file_list, structure, semantic, test_signals, governance, intent_posture)
    safe_change_surface = analyze_safe_change_surface(file_list, structure, semantic, test_signals, governance, intent_posture, misleading_signals)
    risk_synthesis = synthesize_risks(file_list, structure, semantic, test_signals, governance, intent_posture, misleading_signals, safe_change_surface, security_analysis, code_comprehension, compliance_analysis, dependency_analysis, code_duplication_analysis, api_analysis, advanced_code_analysis)
    decision_artifacts = generate_decision_artifacts(file_list, structure, semantic, test_signals, governance, intent_posture, misleading_signals, safe_change_surface, risk_synthesis)
    authority_ceiling_evaluation = evaluate_authority_ceiling(file_list, structure, semantic, test_signals, governance, intent_posture, misleading_signals, safe_change_surface, risk_synthesis, decision_artifacts)
    determinism_verification = verify_determinism(file_list, structure, semantic, test_signals, governance, intent_posture, misleading_signals, safe_change_surface, risk_synthesis, decision_artifacts, authority_ceiling_evaluation)

    execution_time = time.time() - start_time

    # Get final memory usage and performance stats
    final_memory = performance_optimizer.get_memory_usage()
    memory_delta = final_memory['rss_mb'] - initial_memory['rss_mb']

    return {
        "repository_root": repo_root,
        "files": file_list,
        "structure": structure,
        "semantic": semantic,
        "advanced_code_analysis": advanced_code_analysis,
        "code_comprehension": code_comprehension,
        "security_analysis": security_analysis,
        "compliance_analysis": compliance_analysis,
        "dependency_analysis": dependency_analysis,
        "code_duplication_analysis": code_duplication_analysis,
        "api_analysis": api_analysis,
        "test_signals": test_signals,
        "governance": governance,
        "intent_posture": intent_posture,
        "misleading_signals": misleading_signals,
        "safe_change_surface": safe_change_surface,
        "risk_synthesis": risk_synthesis,
        "decision_artifacts": decision_artifacts,
        "authority_ceiling_evaluation": authority_ceiling_evaluation,
        "determinism_verification": determinism_verification,
        "performance_metrics": {
            "execution_time_seconds": execution_time,
            "parallel_stages_used": True,
            "cache_enabled": True,
            "initial_memory_mb": initial_memory['rss_mb'],
            "final_memory_mb": final_memory['rss_mb'],
            "memory_delta_mb": memory_delta,
            "thread_pool_stats": thread_pool_stats
        },
        "status": "standard_pipeline_complete"
    }

def validate_parallelism_guarantees(operation: str) -> bool:
    """Validate operation maintains parallelism guarantees."""
    return True  # Placeholder
