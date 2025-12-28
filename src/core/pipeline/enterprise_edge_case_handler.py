"""Enhanced Edge Case Handling for Complex Enterprise Repositories.

This module provides robust handling for edge cases that occur in large-scale,
complex enterprise repositories including memory management, timeout handling,
corruption detection, and performance optimization for extreme cases.
"""

import asyncio
import concurrent.futures
import functools
import hashlib
import logging
import os
import psutil
import signal
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple, Callable, Iterator
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, TimeoutError

logger = logging.getLogger(__name__)


@dataclass
class EdgeCaseConfig:
    """Configuration for edge case handling."""
    max_file_size_mb: int = 50  # Maximum individual file size
    max_memory_usage_mb: int = 2048  # Maximum memory usage
    analysis_timeout_seconds: int = 1800  # 30 minutes
    max_concurrent_threads: int = 8
    batch_size: int = 100  # Files per batch
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5  # Failures before circuit opens
    enable_adaptive_batching: bool = True


@dataclass
class EdgeCaseMetrics:
    """Metrics for edge case handling."""
    files_processed: int = 0
    files_skipped: int = 0
    timeouts_encountered: int = 0
    memory_peaks_mb: float = 0.0
    circuit_breaker_trips: int = 0
    encoding_errors: int = 0
    corruption_detected: int = 0
    large_files_skipped: int = 0


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise CircuitBreakerOpen("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise e


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class AdaptiveBatcher:
    """Adaptive batching system that adjusts batch sizes based on performance."""

    def __init__(self, initial_batch_size: int = 100, max_batch_size: int = 1000):
        self.current_batch_size = initial_batch_size
        self.max_batch_size = max_batch_size
        self.min_batch_size = 10
        self.performance_history: List[float] = []
        self.adjustment_factor = 1.2

    def get_batch_size(self) -> int:
        """Get current batch size."""
        return self.current_batch_size

    def record_performance(self, processing_time: float, success: bool):
        """Record performance metrics and adjust batch size."""
        self.performance_history.append(processing_time)

        # Keep only recent history
        if len(self.performance_history) > 10:
            self.performance_history.pop(0)

        if len(self.performance_history) >= 3:
            avg_time = sum(self.performance_history) / len(self.performance_history)

            if success and avg_time < 10.0:  # Good performance, increase batch size
                self.current_batch_size = min(
                    int(self.current_batch_size * self.adjustment_factor),
                    self.max_batch_size
                )
            elif not success or avg_time > 30.0:  # Poor performance, decrease batch size
                self.current_batch_size = max(
                    int(self.current_batch_size / self.adjustment_factor),
                    self.min_batch_size
                )


class MemoryManager:
    """Memory usage monitoring and management."""

    def __init__(self, max_memory_mb: int = 2048):
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()
        self.baseline_memory = self.get_current_memory_mb()

    def get_current_memory_mb(self) -> float:
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def check_memory_limit(self) -> bool:
        """Check if memory usage is within limits."""
        current = self.get_current_memory_mb()
        return current < self.max_memory_mb

    def get_memory_pressure(self) -> float:
        """Get memory pressure as a percentage of max allowed."""
        current = self.get_current_memory_mb()
        return (current / self.max_memory_mb) * 100

    @contextmanager
    def memory_guard(self):
        """Context manager that monitors memory usage."""
        start_memory = self.get_current_memory_mb()
        try:
            yield
        finally:
            end_memory = self.get_current_memory_mb()
            delta = end_memory - start_memory
            if delta > 100:  # Significant memory increase
                logger.warning(".1f")


class TimeoutManager:
    """Timeout management for long-running operations."""

    def __init__(self, default_timeout: int = 300):
        self.default_timeout = default_timeout

    @contextmanager
    def timeout_context(self, seconds: Optional[int] = None):
        """Context manager for timeout handling."""
        timeout = seconds or self.default_timeout

        def timeout_handler(signum, frame):
            raise TimeoutError(f"Operation timed out after {timeout} seconds")

        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)

        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


class FileIntegrityChecker:
    """File integrity and corruption detection."""

    def __init__(self):
        self.corruption_indicators = [
            b'\x00' * 100,  # Long sequences of null bytes
            b'\xff' * 100,  # Long sequences of FF bytes
        ]

    def check_file_integrity(self, file_path: str) -> Tuple[bool, str]:
        """Check if a file appears to be corrupted or truncated."""
        try:
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False, "empty_file"

            # Check for binary corruption indicators
            with open(file_path, 'rb') as f:
                sample = f.read(min(1024, file_size))

                for indicator in self.corruption_indicators:
                    if indicator in sample:
                        return False, "binary_corruption"

            # Try to read as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read(100)  # Just a small sample
            except UnicodeDecodeError:
                # File might be binary, which is OK for some analysis
                pass

            return True, "valid"

        except (OSError, IOError) as e:
            return False, f"io_error: {str(e)}"

    def is_text_file(self, file_path: str) -> bool:
        """Determine if a file is likely text-based."""
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(1024)

            # Count printable characters
            printable = sum(1 for byte in sample if 32 <= byte <= 126 or byte in (9, 10, 13))
            return (printable / len(sample)) > 0.8

        except (OSError, IOError):
            return False


class EnterpriseRepositoryHandler:
    """Enhanced handler for complex enterprise repositories."""

    def __init__(self, config: Optional[EdgeCaseConfig] = None):
        self.config = config or EdgeCaseConfig()
        self.metrics = EdgeCaseMetrics()
        self.circuit_breaker = CircuitBreaker(
            self.config.circuit_breaker_threshold
        ) if self.config.enable_circuit_breaker else None
        self.batcher = AdaptiveBatcher(
            self.config.batch_size
        ) if self.config.enable_adaptive_batching else None
        self.memory_manager = MemoryManager(self.config.max_memory_usage_mb)
        self.timeout_manager = TimeoutManager(self.config.analysis_timeout_seconds)
        self.integrity_checker = FileIntegrityChecker()

    def process_repository(self, repository_path: str, file_list: List[str]) -> Dict[str, Any]:
        """Process a repository with enhanced edge case handling."""
        start_time = time.time()
        logger.info(f"Starting enterprise repository processing for {len(file_list)} files")

        # Pre-processing: validate and filter files
        validated_files = self._validate_and_filter_files(file_list)

        # Process in batches with adaptive sizing
        results = []
        batch_size = self.batcher.get_batch_size() if self.batcher else self.config.batch_size

        for i in range(0, len(validated_files), batch_size):
            batch = validated_files[i:i + batch_size]

            try:
                with self.memory_manager.memory_guard():
                    with self.timeout_manager.timeout_context():
                        batch_result = self._process_batch(batch)
                        results.append(batch_result)

                        # Record performance for adaptive batching
                        if self.batcher:
                            self.batcher.record_performance(
                                time.time() - start_time, success=True
                            )

            except (TimeoutError, MemoryError) as e:
                logger.warning(f"Batch processing failed: {e}")
                self.metrics.timeouts_encountered += 1

                # Reduce batch size on failure
                if self.batcher:
                    self.batcher.record_performance(
                        time.time() - start_time, success=False
                    )
                    batch_size = self.batcher.get_batch_size()

            except Exception as e:
                logger.error(f"Unexpected error in batch processing: {e}")
                if self.circuit_breaker:
                    try:
                        self.circuit_breaker.call(lambda: None)  # Test circuit breaker
                    except CircuitBreakerOpen:
                        self.metrics.circuit_breaker_trips += 1
                        break

        # Post-processing: aggregate results
        final_result = self._aggregate_results(results)

        processing_time = time.time() - start_time
        logger.info(f"Enterprise repository processing completed in {processing_time:.2f}s")

        return {
            "results": final_result,
            "metrics": self._get_metrics_summary(),
            "edge_cases_handled": self._summarize_edge_cases()
        }

    def _validate_and_filter_files(self, file_list: List[str]) -> List[str]:
        """Validate and filter files for processing."""
        validated_files = []

        for file_path in file_list:
            # Check file size
            try:
                file_size_mb = os.path.getsize(file_path) / 1024 / 1024
                if file_size_mb > self.config.max_file_size_mb:
                    logger.warning(f"Skipping large file: {file_path} ({file_size_mb:.1f}MB)")
                    self.metrics.large_files_skipped += 1
                    continue
            except OSError:
                logger.warning(f"Cannot access file: {file_path}")
                self.metrics.files_skipped += 1
                continue

            # Check file integrity
            is_valid, reason = self.integrity_checker.check_file_integrity(file_path)
            if not is_valid:
                logger.warning(f"Skipping invalid file {file_path}: {reason}")
                self.metrics.corruption_detected += 1
                self.metrics.files_skipped += 1
                continue

            # Check encoding
            if not self._is_readable_file(file_path):
                logger.warning(f"Skipping unreadable file: {file_path}")
                self.metrics.encoding_errors += 1
                self.metrics.files_skipped += 1
                continue

            validated_files.append(file_path)
            self.metrics.files_processed += 1

        return validated_files

    def _process_batch(self, batch: List[str]) -> Dict[str, Any]:
        """Process a batch of files."""
        # This would integrate with the existing analysis pipeline
        # For now, return a placeholder result
        return {
            "batch_size": len(batch),
            "files": batch,
            "status": "processed"
        }

    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate batch results into final result."""
        return {
            "total_batches": len(results),
            "total_files_processed": sum(r.get("batch_size", 0) for r in results),
            "batch_results": results
        }

    def _is_readable_file(self, file_path: str) -> bool:
        """Check if a file can be read with current encoding handling."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='strict') as f:
                f.read(100)  # Test read
            return True
        except (UnicodeDecodeError, IOError):
            return False

    def _get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of edge case handling metrics."""
        return {
            "files_processed": self.metrics.files_processed,
            "files_skipped": self.metrics.files_skipped,
            "timeouts_encountered": self.metrics.timeouts_encountered,
            "memory_peaks_mb": self.metrics.memory_peaks_mb,
            "circuit_breaker_trips": self.metrics.circuit_breaker_trips,
            "encoding_errors": self.metrics.encoding_errors,
            "corruption_detected": self.metrics.corruption_detected,
            "large_files_skipped": self.metrics.large_files_skipped
        }

    def _summarize_edge_cases(self) -> Dict[str, Any]:
        """Summarize edge cases that were handled."""
        return {
            "memory_management": self.memory_manager.get_memory_pressure() < 90,
            "timeout_handling": self.metrics.timeouts_encountered == 0,
            "corruption_detection": self.metrics.corruption_detected > 0,
            "encoding_handling": self.metrics.encoding_errors == 0,
            "circuit_breaker_active": self.circuit_breaker is not None,
            "adaptive_batching": self.batcher is not None
        }


# Integration with existing pipeline
def enhance_pipeline_with_edge_case_handling(pipeline_func: Callable) -> Callable:
    """Decorator to enhance existing pipeline functions with edge case handling."""

    @functools.wraps(pipeline_func)
    def wrapper(*args, **kwargs):
        handler = EnterpriseRepositoryHandler()

        try:
            # Check memory before starting
            if not handler.memory_manager.check_memory_limit():
                logger.warning("Memory usage too high, attempting garbage collection")
                import gc
                gc.collect()

                if not handler.memory_manager.check_memory_limit():
                    raise MemoryError("Insufficient memory for analysis")

            # Execute with timeout protection
            with handler.timeout_manager.timeout_context():
                result = pipeline_func(*args, **kwargs)

            return result

        except TimeoutError:
            logger.error("Analysis timed out")
            return {"error": "analysis_timeout", "partial_results": {}}
        except MemoryError:
            logger.error("Analysis failed due to memory exhaustion")
            return {"error": "memory_exhaustion", "partial_results": {}}
        except Exception as e:
            logger.error(f"Analysis failed with unexpected error: {e}")
            return {"error": "unexpected_error", "details": str(e)}

    return wrapper