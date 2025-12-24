"""Optimized Analysis Pipeline for Complex Repositories.

This module provides performance optimizations for large-scale repository analysis:
- Incremental analysis with caching
- Streaming file processing
- Enhanced parallelism
- Memory-efficient batching
"""

import asyncio
import concurrent.futures
import functools
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..performance_optimizer import OptimizedThreadPool, get_performance_optimizer, get_cached_model_loader

logger = logging.getLogger(__name__)

@dataclass
class AnalysisBatch:
    """Represents a batch of files for analysis."""
    files: List[str]
    batch_id: str
    priority: int = 0  # Higher priority = process first
    estimated_complexity: float = 1.0

@dataclass
class AnalysisCache:
    """Cache for analysis results."""
    cache_dir: Path
    max_age_hours: int = 24

    def __post_init__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_key(self, repo_path: str, file_list: List[str], analysis_type: str) -> str:
        """Generate cache key for analysis results."""
        content = f"{repo_path}:{sorted(file_list)}:{analysis_type}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis result."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        # Check if cache is too old
        if time.time() - cache_file.stat().st_mtime > self.max_age_hours * 3600:
            cache_file.unlink()
            return None

        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache analysis result."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(result, f, indent=2)
        except IOError:
            logger.warning(f"Failed to cache result for {cache_key}")

class StreamingFileProcessor:
    """Process files in streaming fashion to handle large repositories."""

    def __init__(self, batch_size: int = 50, max_concurrent: int = 4):
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.file_cache = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def process_files_streaming(self, file_list: List[str], processor_func, *args, **kwargs) -> List[Any]:
        """Process files in streaming batches."""
        if len(file_list) <= self.batch_size:
            # Small file set, process directly
            return await self._process_batch(file_list, processor_func, *args, **kwargs)

        # Large file set, process in batches
        batches = [file_list[i:i + self.batch_size] for i in range(0, len(file_list), self.batch_size)]
        tasks = []

        for batch in batches:
            task = asyncio.create_task(self._process_batch(batch, processor_func, *args, **kwargs))
            tasks.append(task)

        # Process batches with concurrency control
        results = []
        for task in asyncio.as_completed(tasks):
            batch_result = await task
            results.extend(batch_result)

        return results

    async def _process_batch(self, batch: List[str], processor_func, *args, **kwargs) -> List[Any]:
        """Process a single batch of files."""
        async with self.semaphore:
            try:
                # Read file contents concurrently
                content_tasks = []
                for file_path in batch:
                    task = asyncio.create_task(self._read_file_async(file_path))
                    content_tasks.append(task)

                contents = await asyncio.gather(*content_tasks, return_exceptions=True)

                # Process files
                valid_contents = [(fp, cnt) for fp, cnt in zip(batch, contents) if not isinstance(cnt, Exception)]
                if valid_contents:
                    return await asyncio.get_event_loop().run_in_executor(
                        None, processor_func, valid_contents, *args, **kwargs
                    )
                return []
            except Exception as e:
                logger.error(f"Batch processing failed: {e}")
                return []

    async def _read_file_async(self, file_path: str) -> str:
        """Read file content asynchronously."""
        if file_path in self.file_cache:
            return self.file_cache[file_path]

        def read_file():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except (IOError, OSError):
                return ""

        content = await asyncio.get_event_loop().run_in_executor(None, read_file)
        self.file_cache[file_path] = content
        return content

class IncrementalAnalyzer:
    """Performs incremental analysis to avoid re-processing unchanged files."""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path("./.scanner_cache")
        self.analysis_cache = AnalysisCache(self.cache_dir / "analysis")
        self.file_hashes = self._load_file_hashes()

    def _load_file_hashes(self) -> Dict[str, str]:
        """Load previously computed file hashes."""
        hash_file = self.cache_dir / "file_hashes.json"
        if hash_file.exists():
            try:
                with open(hash_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_file_hashes(self):
        """Save current file hashes."""
        hash_file = self.cache_dir / "file_hashes.json"
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with open(hash_file, 'w') as f:
                json.dump(self.file_hashes, f)
        except IOError:
            logger.warning("Failed to save file hashes")

    def get_changed_files(self, file_list: List[str]) -> Tuple[List[str], List[str]]:
        """Get lists of changed and unchanged files."""
        changed = []
        unchanged = []

        for file_path in file_list:
            current_hash = self._compute_file_hash(file_path)
            if file_path not in self.file_hashes or self.file_hashes[file_path] != current_hash:
                changed.append(file_path)
                self.file_hashes[file_path] = current_hash
            else:
                unchanged.append(file_path)

        self._save_file_hashes()
        return changed, unchanged

    def _compute_file_hash(self, file_path: str) -> str:
        """Compute hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except (IOError, OSError):
            return ""

    def get_incremental_analysis(self, repo_path: str, analysis_type: str, full_file_list: List[str],
                               analysis_func, *args, **kwargs) -> Dict[str, Any]:
        """Perform incremental analysis, reusing cached results where possible."""
        changed_files, unchanged_files = self.get_changed_files(full_file_list)

        if not changed_files:
            # All files unchanged, try to use cached full analysis
            cache_key = self.analysis_cache.get_cache_key(repo_path, full_file_list, analysis_type)
            cached = self.analysis_cache.get_cached_result(cache_key)
            if cached:
                logger.info(f"Using cached {analysis_type} analysis for {len(full_file_list)} files")
                return cached

        # Need to run analysis on changed files
        logger.info(f"Running {analysis_type} analysis on {len(changed_files)} changed files")

        if changed_files == full_file_list:
            # All files changed, run full analysis
            result = analysis_func(full_file_list, *args, **kwargs)
        else:
            # Incremental analysis - this would need to be implemented per analysis type
            # For now, fall back to full analysis but mark as incremental opportunity
            logger.warning(f"Incremental {analysis_type} not implemented, running full analysis")
            result = analysis_func(full_file_list, *args, **kwargs)

        # Cache the result
        if changed_files:
            cache_key = self.analysis_cache.get_cache_key(repo_path, full_file_list, analysis_type)
            self.analysis_cache.cache_result(cache_key, result)

        return result

class OptimizedAnalysisPipeline:
    """Optimized analysis pipeline with performance enhancements."""

    def __init__(self, max_workers: int = 8, cache_dir: Path = None, enable_incremental: bool = True):
        self.max_workers = max_workers
        self.cache_dir = cache_dir or Path("./.scanner_cache")
        self.enable_incremental = enable_incremental
        self.repo_root = None  # Will be set during execution

        # Initialize components
        self.thread_pool = OptimizedThreadPool(max_workers=max_workers)
        self.streaming_processor = StreamingFileProcessor(batch_size=25, max_concurrent=max_workers)
        self.incremental_analyzer = IncrementalAnalyzer(self.cache_dir) if enable_incremental else None
        self.analysis_cache = AnalysisCache(self.cache_dir / "pipeline")

        # Performance tracking
        self.performance_stats = {
            'start_time': 0,
            'stages_completed': 0,
            'cache_hits': 0,
            'incremental_savings': 0
        }

    def execute_optimized_pipeline(self, repository_path: str) -> Dict[str, Any]:
        """Execute the optimized analysis pipeline."""
        self.performance_stats['start_time'] = time.time()
        performance_optimizer = get_performance_optimizer()

        logger.info(f"Starting optimized analysis pipeline for {repository_path}")

        # Initial setup
        initial_memory = performance_optimizer.get_memory_usage()
        self.repo_root = self._discover_repository(repository_path)
        file_list = self._get_file_list(self.repo_root)

        # Quick analysis for small repositories
        if len(file_list) < 100:
            logger.info(f"Small repository ({len(file_list)} files), using standard pipeline")
            return self._execute_standard_pipeline(repository_path)

        # Optimized analysis for large repositories
        logger.info(f"Large repository ({len(file_list)} files), using optimized pipeline")

        try:
            # Phase 1: Fast structural analysis
            structure = self._analyze_structure_optimized(file_list)

            # Phase 2: Parallel semantic analysis with streaming
            semantic = self._analyze_semantic_optimized(file_list, structure)

            # Phase 3: Advanced analysis with caching and parallelism
            advanced_results = self._analyze_advanced_parallel(file_list, structure, semantic)

            # Phase 4: Risk synthesis and final artifacts
            final_results = self._synthesize_results_optimized(file_list, structure, semantic, advanced_results)

            # Performance metrics
            execution_time = time.time() - self.performance_stats['start_time']
            final_memory = performance_optimizer.get_memory_usage()
            memory_delta = final_memory['rss_mb'] - initial_memory['rss_mb']

            result = {
                "repository_root": self.repo_root,
                "files": file_list,
                "structure": structure,
                "semantic": semantic,
                **advanced_results,
                **final_results,
                "performance_metrics": {
                    "execution_time_seconds": execution_time,
                    "pipeline_type": "optimized",
                    "cache_enabled": True,
                    "incremental_enabled": self.enable_incremental,
                    "parallel_workers": self.max_workers,
                    "initial_memory_mb": initial_memory['rss_mb'],
                    "final_memory_mb": final_memory['rss_mb'],
                    "memory_delta_mb": memory_delta,
                    "stages_completed": self.performance_stats['stages_completed'],
                    "cache_hits": self.performance_stats['cache_hits'],
                    "incremental_savings": self.performance_stats['incremental_savings']
                },
                "status": "optimized_pipeline_complete"
            }

            logger.info(f"Optimized pipeline completed in {execution_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Optimized pipeline failed: {e}")
            # Fallback to standard pipeline
            logger.info("Falling back to standard pipeline")
            return self._execute_standard_pipeline(repository_path)

    def _discover_repository(self, repository_path: str) -> str:
        """Repository discovery with caching."""
        from src.core.pipeline.repository_discovery import discover_repository_root
        return discover_repository_root(repository_path)

    def _get_file_list(self, repo_root: str) -> List[str]:
        """Get canonical file list with caching."""
        from src.core.pipeline.repository_discovery import get_canonical_file_list
        file_list = get_canonical_file_list(repo_root)
        return file_list if isinstance(file_list, list) else []

    def _analyze_structure_optimized(self, file_list: List[str]) -> Dict[str, Any]:
        """Fast structural analysis."""
        from src.core.pipeline.structural_modeling import analyze_repository_structure

        self.performance_stats['stages_completed'] += 1
        start_time = time.time()

        structure = analyze_repository_structure(file_list)

        logger.info(f"Structure analysis completed in {time.time() - start_time:.2f}s")
        return structure

    def _analyze_semantic_optimized(self, file_list: List[str], structure: Dict[str, Any]) -> Dict[str, Any]:
        """Optimized semantic analysis with streaming."""
        from src.core.pipeline.static_semantic_analysis import analyze_semantic_structure

        self.performance_stats['stages_completed'] += 1
        start_time = time.time()

        # Use incremental analysis if enabled
        if self.incremental_analyzer:
            semantic = self.incremental_analyzer.get_incremental_analysis(
                "", "semantic", file_list, analyze_semantic_structure, structure
            )
        else:
            semantic = analyze_semantic_structure(file_list, structure)

        logger.info(f"Semantic analysis completed in {time.time() - start_time:.2f}s")
        return semantic

    def _analyze_advanced_parallel(self, file_list: List[str], structure: Dict[str, Any],
                                semantic: Dict[str, Any]) -> Dict[str, Any]:
        """Advanced analysis with maximum parallelism."""
        self.performance_stats['stages_completed'] += 1
        start_time = time.time()

        # Define analysis tasks that can run in parallel
        analysis_tasks = {
            'advanced_code': self._run_advanced_code_analysis,
            'code_comprehension': self._run_code_comprehension_analysis,
            'security': self._run_security_analysis,
            'compliance': self._run_compliance_analysis,
            'dependencies': self._run_dependency_analysis,
            'duplication': self._run_duplication_analysis,
            'api': self._run_api_analysis,
            'test_signals': self._run_test_signal_analysis
        }

        # Submit all tasks to thread pool
        futures = {}
        for name, func in analysis_tasks.items():
            future = self.thread_pool.submit(func, file_list, structure, semantic)
            futures[name] = future

        # Collect results
        results = {}
        for name, future in futures.items():
            try:
                results[name] = future.result(timeout=300)  # 5 minute timeout per task
            except concurrent.futures.TimeoutError:
                logger.warning(f"{name} analysis timed out, skipping")
                results[name] = {}
            except Exception as e:
                logger.error(f"{name} analysis failed: {e}")
                results[name] = {}

        # Continue with dependent analyses
        governance = self._run_governance_analysis(file_list, structure, semantic, results['test_signals'])
        intent_posture = self._run_intent_analysis(file_list, structure, semantic, results['test_signals'], governance)

        results.update({
            'governance': governance,
            'intent_posture': intent_posture
        })

        logger.info(f"Advanced parallel analysis completed in {time.time() - start_time:.2f}s")
        return results

    def _synthesize_results_optimized(self, file_list: List[str], structure: Dict[str, Any],
                                   semantic: Dict[str, Any], advanced_results: Dict[str, Any]) -> Dict[str, Any]:
        """Final result synthesis with optimization."""
        self.performance_stats['stages_completed'] += 1
        start_time = time.time()

        # Run remaining sequential stages
        misleading_signals = self._run_misleading_signal_analysis(
            file_list, structure, semantic, advanced_results
        )

        safe_change_surface = self._run_safe_change_analysis(
            file_list, structure, semantic, advanced_results, misleading_signals
        )

        risk_synthesis = self._run_risk_synthesis(
            file_list, structure, semantic, advanced_results, misleading_signals, safe_change_surface
        )

        decision_artifacts = self._run_decision_artifact_generation(
            file_list, structure, semantic, advanced_results, misleading_signals,
            safe_change_surface, risk_synthesis
        )

        authority_evaluation = self._run_authority_evaluation(
            file_list, structure, semantic, advanced_results, misleading_signals,
            safe_change_surface, risk_synthesis, decision_artifacts
        )

        determinism = self._run_determinism_verification(
            file_list, structure, semantic, advanced_results, misleading_signals,
            safe_change_surface, risk_synthesis, decision_artifacts, authority_evaluation
        )

        logger.info(f"Result synthesis completed in {time.time() - start_time:.2f}s")

        return {
            'misleading_signals': misleading_signals,
            'safe_change_surface': safe_change_surface,
            'risk_synthesis': risk_synthesis,
            'decision_artifacts': decision_artifacts,
            'authority_ceiling_evaluation': authority_evaluation,
            'determinism_verification': determinism
        }

    def _execute_standard_pipeline(self, repository_path: str) -> Dict[str, Any]:
        """Fallback to standard pipeline for small repos or failures."""
        # Import and run the standard pipeline directly, not through the main dispatcher
        from .analysis import _execute_standard_pipeline as execute_standard
        from .repository_discovery import discover_repository_root, get_canonical_file_list
        from ..performance_optimizer import get_performance_optimizer
        
        # Get the required parameters
        repo_root = discover_repository_root(repository_path)
        file_list = get_canonical_file_list(repo_root)
        if not isinstance(file_list, list):
            file_list = []
        
        start_time = time.time()
        performance_optimizer = get_performance_optimizer()
        initial_memory = performance_optimizer.get_memory_usage()
        
        return execute_standard(repository_path, repo_root, file_list, start_time, initial_memory)

    # Individual analysis method stubs - these would delegate to the actual analysis modules
    def _run_advanced_code_analysis(self, file_list, structure, semantic):
        from src.core.pipeline.advanced_code_analysis import analyze_advanced_code
        return analyze_advanced_code(file_list, semantic)

    def _run_code_comprehension_analysis(self, file_list, structure, semantic):
        from src.core.pipeline.code_comprehension import analyze_code_comprehension
        return analyze_code_comprehension(Path(file_list[0]).parent if file_list else Path("."), semantic)

    def _run_security_analysis(self, file_list, structure, semantic):
        from src.core.pipeline.security_analysis import analyze_security_vulnerabilities
        return analyze_security_vulnerabilities(file_list, semantic)

    def _run_compliance_analysis(self, file_list, structure, semantic):
        from src.core.pipeline.compliance_analysis import analyze_compliance
        return analyze_compliance(file_list, semantic)

    def _run_dependency_analysis(self, file_list, structure, semantic):
        from src.core.pipeline.dependency_analysis import analyze_dependencies
        return analyze_dependencies(file_list, semantic)

    def _run_duplication_analysis(self, file_list, structure, semantic):
        from src.core.pipeline.code_duplication_analysis import analyze_code_duplication
        return analyze_code_duplication(file_list, semantic)

    def _run_api_analysis(self, file_list, structure, semantic):
        from src.core.pipeline.api_analysis import analyze_api_definitions
        return analyze_api_definitions(file_list, semantic)

    def _run_test_signal_analysis(self, file_list, structure, semantic):
        from src.core.pipeline.test_signal_analysis import analyze_test_signals
        return analyze_test_signals(file_list, structure, semantic)

    def _run_governance_analysis(self, file_list, structure, semantic, test_signals):
        from src.core.pipeline.governance_signal_analysis import analyze_governance_signals
        return analyze_governance_signals(file_list, structure, semantic, test_signals)

    def _run_intent_analysis(self, file_list, structure, semantic, test_signals, governance):
        from src.core.pipeline.intent_posture_classification import classify_intent_posture
        return classify_intent_posture(file_list, structure, semantic, test_signals, governance)

    def _run_misleading_signal_analysis(self, file_list, structure, semantic, advanced_results):
        from src.core.pipeline.misleading_signal_detection import analyze_misleading_signals
        return analyze_misleading_signals(
            file_list, structure, semantic,
            advanced_results['test_signals'],
            advanced_results['governance'],
            advanced_results['intent_posture']
        )

    def _run_safe_change_analysis(self, file_list, structure, semantic, advanced_results, misleading_signals):
        from src.core.pipeline.safe_change_surface_modeling import analyze_safe_change_surface
        return analyze_safe_change_surface(
            file_list, structure, semantic,
            advanced_results['test_signals'],
            advanced_results['governance'],
            advanced_results['intent_posture'],
            misleading_signals
        )

    def _run_risk_synthesis(self, file_list, structure, semantic, advanced_results, misleading_signals, safe_change_surface):
        from src.core.pipeline.risk_synthesis import synthesize_risks
        return synthesize_risks(
            file_list, structure, semantic,
            advanced_results['test_signals'],
            advanced_results['governance'],
            advanced_results['intent_posture'],
            misleading_signals, safe_change_surface,
            advanced_results['security'],
            advanced_results['code_comprehension'],
            advanced_results['compliance'],
            advanced_results['dependencies'],
            advanced_results['duplication'],
            advanced_results['api'],
            advanced_results['advanced_code']
        )

    def _run_decision_artifact_generation(self, file_list, structure, semantic, advanced_results,
                                        misleading_signals, safe_change_surface, risk_synthesis):
        from src.core.pipeline.decision_artifact_generation import generate_decision_artifacts
        return generate_decision_artifacts(
            file_list, structure, semantic,
            advanced_results['test_signals'],
            advanced_results['governance'],
            advanced_results['intent_posture'],
            misleading_signals, safe_change_surface, risk_synthesis
        )

    def _run_authority_evaluation(self, file_list, structure, semantic, advanced_results,
                                misleading_signals, safe_change_surface, risk_synthesis, decision_artifacts):
        from src.core.pipeline.authority_ceiling_evaluation import evaluate_authority_ceiling
        return evaluate_authority_ceiling(
            file_list, structure, semantic,
            advanced_results['test_signals'],
            advanced_results['governance'],
            advanced_results['intent_posture'],
            misleading_signals, safe_change_surface, risk_synthesis, decision_artifacts
        )

    def _run_determinism_verification(self, file_list, structure, semantic, advanced_results,
                                    misleading_signals, safe_change_surface, risk_synthesis,
                                    decision_artifacts, authority_evaluation):
        from src.core.pipeline.determinism_verification import verify_determinism
        return verify_determinism(
            file_list, structure, semantic,
            advanced_results['test_signals'],
            advanced_results['governance'],
            advanced_results['intent_posture'],
            misleading_signals, safe_change_surface, risk_synthesis,
            decision_artifacts, authority_evaluation
        )

def execute_optimized_pipeline(repository_path: str) -> Dict[str, Any]:
    """Entry point for optimized pipeline execution."""
    optimizer = OptimizedAnalysisPipeline(
        max_workers=8,
        enable_incremental=True
    )
    return optimizer.execute_optimized_pipeline(repository_path)