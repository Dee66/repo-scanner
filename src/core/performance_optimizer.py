#!/usr/bin/env python3
"""
Performance Optimization Module

Provides performance enhancements for the Repository Intelligence Scanner including:
- Lazy loading of heavy libraries
- Model caching and memory optimization
- Parallel processing improvements
- Import optimization
"""

import os
import gc
import psutil
import logging
import threading
from typing import Dict, Any, Optional, List
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
import time

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Manages performance optimizations for the scanner."""

    def __init__(self):
        self.library_cache: Dict[str, Any] = {}
        self.model_cache: Dict[str, Any] = {}
        self.memory_monitor = MemoryMonitor()
        self.import_lock = threading.Lock()

    def lazy_import(self, module_name: str, import_path: str = None) -> Any:
        """
        Lazy import a module to avoid upfront loading costs.

        Args:
            module_name: Name to cache the module under
            import_path: Full import path (e.g., 'transformers.AutoTokenizer')

        Returns:
            The imported module/class
        """
        if module_name in self.library_cache:
            return self.library_cache[module_name]

        with self.import_lock:
            if module_name not in self.library_cache:
                try:
                    if import_path:
                        # Handle nested imports like 'transformers.AutoTokenizer'
                        parts = import_path.split('.')
                        module = __import__(parts[0], fromlist=[parts[1]])
                        for part in parts[1:]:
                            module = getattr(module, part)
                        self.library_cache[module_name] = module
                    else:
                        self.library_cache[module_name] = __import__(module_name)
                    logger.debug(f"Lazy loaded: {module_name}")
                except ImportError as e:
                    logger.warning(f"Failed to lazy import {module_name}: {e}")
                    raise

        return self.library_cache[module_name]

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage statistics."""
        return self.memory_monitor.get_usage()

    def optimize_memory(self):
        """Perform memory optimization."""
        # Clear any cached objects that can be recreated
        self.library_cache.clear()

        # Force garbage collection
        gc.collect()

        # Log memory usage
        usage = self.get_memory_usage()
        logger.info(f"Memory optimized - RSS: {usage['rss_mb']:.1f}MB, VMS: {usage['vms_mb']:.1f}MB")

class MemoryMonitor:
    """Monitors memory usage."""

    def __init__(self):
        self.process = psutil.Process(os.getpid())

    def get_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        memory_info = self.process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': self.process.memory_percent()
        }

class OptimizedThreadPool:
    """Optimized thread pool with performance monitoring."""

    def __init__(self, max_workers: int = None, thread_name_prefix: str = "scanner"):
        self.max_workers = max_workers or min(32, (os.cpu_count() or 1) * 2)
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix=thread_name_prefix
        )
        self.performance_stats = {
            'tasks_completed': 0,
            'total_time': 0.0,
            'avg_task_time': 0.0
        }

    def submit(self, fn, *args, **kwargs):
        """Submit a task with performance tracking."""
        start_time = time.time()

        def tracked_fn(*args, **kwargs):
            result = fn(*args, **kwargs)
            end_time = time.time()
            task_time = end_time - start_time

            with threading.Lock():
                self.performance_stats['tasks_completed'] += 1
                self.performance_stats['total_time'] += task_time
                self.performance_stats['avg_task_time'] = (
                    self.performance_stats['total_time'] /
                    self.performance_stats['tasks_completed']
                )

            return result

        return self.executor.submit(tracked_fn, *args, **kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return self.performance_stats.copy()

    def shutdown(self, wait: bool = True):
        """Shutdown the thread pool."""
        self.executor.shutdown(wait=wait)

class CachedModelLoader:
    """Caches loaded models to avoid repeated loading."""

    def __init__(self):
        self.loaded_models: Dict[str, Any] = {}
        self.model_metadata: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}

    def get_model(self, model_key: str, loader_func, *args, **kwargs):
        """
        Get a cached model or load it if not cached.

        Args:
            model_key: Unique key for the model
            loader_func: Function to load the model if not cached
            *args, **kwargs: Arguments for the loader function
        """
        current_time = time.time()

        # Check if model is cached and recently used
        if model_key in self.loaded_models:
            self.access_times[model_key] = current_time
            return self.loaded_models[model_key]

        # Load the model
        logger.info(f"Loading model: {model_key}")
        start_time = time.time()
        model = loader_func(*args, **kwargs)
        load_time = time.time() - start_time

        # Cache the model
        self.loaded_models[model_key] = model
        self.access_times[model_key] = current_time
        self.model_metadata[model_key] = {
            'load_time': load_time,
            'loaded_at': current_time,
            'size_estimate': self._estimate_model_size(model)
        }

        logger.info(f"Model {model_key} loaded in {load_time:.2f}s")
        return model

    def unload_unused_models(self, max_age_seconds: float = 300):
        """Unload models that haven't been used recently."""
        current_time = time.time()
        to_unload = []

        for model_key, last_access in self.access_times.items():
            if current_time - last_access > max_age_seconds:
                to_unload.append(model_key)

        for model_key in to_unload:
            if model_key in self.loaded_models:
                logger.info(f"Unloading unused model: {model_key}")
                del self.loaded_models[model_key]
                del self.access_times[model_key]
                del self.model_metadata[model_key]

    def _estimate_model_size(self, model) -> int:
        """Estimate the memory size of a model."""
        try:
            # Try to get size for PyTorch models
            if hasattr(model, 'parameters'):
                return sum(p.numel() * p.element_size() for p in model.parameters())
            # Try to get size for general objects
            elif hasattr(model, '__sizeof__'):
                return model.__sizeof__()
        except:
            pass
        return 0

# Global instances
_performance_optimizer = None
_cached_model_loader = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """Get the global performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer

def get_cached_model_loader() -> CachedModelLoader:
    """Get the global cached model loader instance."""
    global _cached_model_loader
    if _cached_model_loader is None:
        _cached_model_loader = CachedModelLoader()
    return _cached_model_loader

# Convenience functions
def lazy_import(module_name: str, import_path: str = None) -> Any:
    """Convenience function for lazy importing."""
    return get_performance_optimizer().lazy_import(module_name, import_path)

def get_memory_usage() -> Dict[str, Any]:
    """Convenience function for memory usage."""
    return get_performance_optimizer().get_memory_usage()

def optimize_memory():
    """Convenience function for memory optimization."""
    return get_performance_optimizer().optimize_memory()