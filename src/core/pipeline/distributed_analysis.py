"""
Distributed Analysis Pipeline using Multiprocessing

This module provides distributed processing capabilities for large-scale repository analysis
using Python's multiprocessing for parallel execution across CPU cores.
"""

import logging
import time
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

from ..performance_optimizer import OptimizedThreadPool, get_performance_optimizer
from .analysis import _execute_standard_pipeline, _estimate_repository_complexity
from ..repository import RepositoryManager

logger = logging.getLogger(__name__)


def analyze_file_batch_worker(repo_path: str, file_batch: List[str],
                             analysis_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker function for analyzing a batch of files.

    This function runs in a separate process and performs synchronous analysis.
    """
    from ..analysis.ast_analysis import ASTAnalysisEngine

    worker_id = analysis_config.get('worker_id', 0)

    try:
        engine = ASTAnalysisEngine()
        results = []

        for file_path in file_batch:
            try:
                result = engine.analyze_file(file_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Worker {worker_id}: Error analyzing {file_path}: {e}")
                results.append({
                    "file_path": file_path,
                    "error": str(e),
                    "supported": False
                })

        return {
            "worker_id": worker_id,
            "files_processed": len(results),
            "results": results,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"Worker {worker_id}: Batch analysis failed: {e}")
        return {
            "worker_id": worker_id,
            "error": str(e),
            "status": "failed"
        }


class DistributedAnalysisPipeline:
    """
    Distributed analysis pipeline using multiprocessing for parallel processing.

    Provides enterprise-scale analysis capabilities for large repositories
    with automatic workload distribution across multiple processes.
    """

    def __init__(self, num_workers: int = None, worker_processes: int = 1):
        """
        Initialize distributed analysis pipeline.

        Args:
            num_workers: Number of worker processes (auto-detect if None)
            worker_processes: Processes per worker (for future scaling)
        """
        self.num_workers = num_workers or max(1, multiprocessing.cpu_count() // 2)
        self.worker_processes = worker_processes
        self.executor = None

        logger.info(f"Initialized multiprocessing pipeline with {self.num_workers} workers")

    def should_use_distributed(self, repo_path: str, file_list: List[str]) -> bool:
        """Determine if distributed analysis should be used."""
        # Use distributed analysis for:
        # - Very large repositories (> 1000 files)
        # - High complexity repositories
        # - When explicitly requested

        file_count = len(file_list)
        complexity = _estimate_repository_complexity(file_list)

        use_distributed = (
            file_count > 1000 or
            complexity > 200 or
            os.getenv('USE_DISTRIBUTED_ANALYSIS', '').lower() == 'true'
        )

        if use_distributed:
            logger.info(f"Using distributed analysis: {file_count} files, complexity {complexity}")

        return use_distributed

    def distribute_files(self, file_list: List[str], batch_size: int = 50) -> List[List[str]]:
        """Distribute files into batches for parallel processing."""
        batches = []
        for i in range(0, len(file_list), batch_size):
            batch = file_list[i:i + batch_size]
            batches.append(batch)
        return batches

    def execute_distributed_analysis(self, repo_path: str,
                                     file_list: List[str]) -> Dict[str, Any]:
        """
        Execute distributed analysis using multiprocessing.

        Args:
            repo_path: Path to the repository
            file_list: List of files to analyze

        Returns:
            Dict containing distributed analysis results
        """
        start_time = time.time()
        logger.info(f"Starting distributed analysis for {len(file_list)} files using {self.num_workers} processes")

        # Distribute files into batches
        file_batches = self.distribute_files(file_list)
        logger.info(f"Distributed into {len(file_batches)} batches across {self.num_workers} processes")

        # Create process pool executor
        self.executor = ProcessPoolExecutor(max_workers=self.num_workers)

        try:
            # Submit analysis tasks to worker processes
            analysis_futures = []
            batch_index = 0

            for batch in file_batches:
                analysis_config = {
                    "batch_size": len(batch),
                    "worker_id": batch_index % self.num_workers
                }

                # Submit task to process pool
                future = self.executor.submit(analyze_file_batch_worker, repo_path, batch, analysis_config)
                analysis_futures.append(future)
                batch_index += 1

            # Collect results
            all_results = []
            completed_batches = 0

            for future in as_completed(analysis_futures):
                try:
                    # Get result with timeout
                    batch_result = future.result(timeout=300)  # 5 minute timeout per batch
                    all_results.extend(batch_result.get("results", []))
                    completed_batches += 1

                    if completed_batches % 10 == 0:
                        logger.info(f"Completed {completed_batches}/{len(analysis_futures)} batches")

                except TimeoutError:
                    logger.error(f"Timeout waiting for batch result after 5 minutes")
                    continue
                except Exception as e:
                    logger.error(f"Failed to get batch result: {e}")
                    continue

            # Aggregate results
            aggregated_results = self._aggregate_distributed_results(all_results)

            execution_time = time.time() - start_time
            logger.info(f"Distributed analysis completed in {execution_time:.2f}s")

            return {
                "repository_path": repo_path,
                "analysis_type": "distributed",
                "total_files": len(file_list),
                "processed_files": len(all_results),
                "execution_time": execution_time,
                "workers_used": self.num_workers,
                "batches_processed": completed_batches,
                "results": all_results,
                "aggregated_results": aggregated_results
            }

        finally:
            # Clean up executor
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None

    def _aggregate_distributed_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from distributed analysis."""
        aggregated = {
            "total_files": len(results),
            "successful_analyses": 0,
            "failed_analyses": 0,
            "languages": {},
            "total_imports": 0,
            "total_classes": 0,
            "total_functions": 0,
            "total_methods": 0,
            "total_variables": 0,
            "average_complexity": 0,
            "max_complexity": 0,
            "errors": []
        }

        total_complexity = 0
        complexity_count = 0

        for result in results:
            if "error" in result and result.get("supported", False):
                aggregated["failed_analyses"] += 1
                aggregated["errors"].append({
                    "file": result["file_path"],
                    "error": result["error"]
                })
                continue

            if not result.get("supported", False):
                continue

            aggregated["successful_analyses"] += 1

            # Language statistics
            language = result.get("language", "unknown")
            aggregated["languages"][language] = aggregated["languages"].get(language, 0) + 1

            # Code metrics
            aggregated["total_imports"] += len(result.get("imports", []))
            aggregated["total_classes"] += len(result.get("classes", []))
            aggregated["total_functions"] += len(result.get("functions", []))
            aggregated["total_methods"] += len(result.get("methods", []))
            aggregated["total_variables"] += len(result.get("variables", []))

            # Complexity
            complexity = result.get("complexity", 0)
            if complexity > 0:
                total_complexity += complexity
                complexity_count += 1
                aggregated["max_complexity"] = max(aggregated["max_complexity"], complexity)

        # Calculate averages
        if complexity_count > 0:
            aggregated["average_complexity"] = total_complexity / complexity_count

        return aggregated

    def cleanup(self):
        """Clean up distributed resources."""
        logger.info("Cleaning up distributed analysis processes")

        if self.executor:
            try:
                self.executor.shutdown(wait=True)
                self.executor = None
                logger.info("Process pool executor shutdown completed")
            except Exception as e:
                logger.error(f"Error during executor cleanup: {e}")


def execute_distributed_pipeline(repository_path: str, file_list: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Execute the distributed analysis pipeline.

    This is the main entry point for distributed analysis.
    """
    # Create distributed pipeline
    pipeline = DistributedAnalysisPipeline()

    try:
        # Get repository information - use provided file_list or discover
        if file_list is None:
            from ..pipeline.repository_discovery import discover_repository_root, get_canonical_file_list
            repo_root = discover_repository_root(repository_path)
            file_list = get_canonical_file_list(repo_root)
        else:
            repo_root = repository_path  # Assume repository_path is repo_root when file_list provided

        # Check if distributed analysis should be used
        if not pipeline.should_use_distributed(repository_path, file_list):
            logger.info("Distributed analysis not needed, falling back to standard pipeline")
            # Fall back to standard pipeline
            from .analysis import _execute_standard_pipeline
            return _execute_standard_pipeline(repository_path, repo_root, file_list,
                                            time.time(), {"rss_mb": 0}, {})

        # Execute distributed analysis
        result = pipeline.execute_distributed_analysis(repository_path, file_list)

        # Add standard pipeline components for compatibility
        result.update({
            "repository_root": repo_root,
            "files": file_list,
            "structure": {"analysis_type": "distributed"},
            "semantic": {"analysis_type": "distributed"},
            "status": "distributed_pipeline_complete"
        })

        return result

    finally:
        # Clean up resources synchronously
        pipeline.cleanup()
