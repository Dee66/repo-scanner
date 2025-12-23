#!/usr/bin/env python3
"""
AI Inference Pipeline for Repository Intelligence Scanner

Provides deterministic AI inference capabilities for offline operation.
Supports multiple model types and ensures reproducible results.
"""

import os
import json
import hashlib
import logging
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor

from ..performance_optimizer import OptimizedThreadPool, get_performance_optimizer

logger = logging.getLogger(__name__)

@dataclass
class ModelMetadata:
    """Metadata for AI models."""
    name: str
    version: str
    model_type: str  # 'llm', 'embedding', 'classifier'
    framework: str   # 'transformers', 'llama_cpp', 'ctransformers'
    parameters: Dict[str, Any]
    hash: str
    created_at: str
    description: str

@dataclass
class InferenceResult:
    """Result of AI inference operation."""
    model_name: str
    model_version: str
    input_hash: str
    output: Any
    confidence: float
    processing_time: float
    timestamp: str

class AIModelRegistry:
    """Registry for managing AI models and their metadata."""

    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.models_dir = registry_path / "models"
        self.metadata_dir = registry_path / "metadata"
        self.cache_dir = registry_path / "cache"

        # Create directories
        for dir_path in [self.models_dir, self.metadata_dir, self.cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        self._load_registry()

    def _load_registry(self):
        """Load model registry from disk."""
        self.registry: Dict[str, ModelMetadata] = {}

        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file) as f:
                    data = json.load(f)
                    model = ModelMetadata(**data)
                    self.registry[model.name] = model
            except Exception as e:
                logger.warning(f"Failed to load model metadata {metadata_file}: {e}")

    def register_model(self, metadata: ModelMetadata, model_path: Optional[Path] = None):
        """Register a new model in the registry."""
        # Save metadata
        metadata_file = self.metadata_dir / f"{metadata.name}.json"
        with open(metadata_file, 'w') as f:
            json.dump({
                'name': metadata.name,
                'version': metadata.version,
                'model_type': metadata.model_type,
                'framework': metadata.framework,
                'parameters': metadata.parameters,
                'hash': metadata.hash,
                'created_at': metadata.created_at,
                'description': metadata.description
            }, f, indent=2)

        # Move model file if provided
        if model_path and model_path.exists():
            target_path = self.models_dir / f"{metadata.name}-{metadata.version}"
            if model_path.is_file():
                target_path.mkdir(exist_ok=True)
                import shutil
                shutil.copy2(model_path, target_path / model_path.name)
            else:
                shutil.copytree(model_path, target_path, dirs_exist_ok=True)

        self.registry[metadata.name] = metadata
        logger.info(f"Registered model: {metadata.name} v{metadata.version}")

    def get_model(self, name: str) -> Optional[ModelMetadata]:
        """Get model metadata by name."""
        return self.registry.get(name)

    def list_models(self, model_type: Optional[str] = None) -> List[ModelMetadata]:
        """List all registered models, optionally filtered by type."""
        models = list(self.registry.values())
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        return models

class BaseAIModel(ABC):
    """Base class for AI models."""

    def __init__(self, metadata: ModelMetadata, model_path: Path):
        self.metadata = metadata
        self.model_path = model_path
        self.loaded = False

    @abstractmethod
    def load(self):
        """Load the model into memory."""
        pass

    @abstractmethod
    def unload(self):
        """Unload the model from memory."""
        pass

    @abstractmethod
    def infer(self, input_data: Any, **kwargs) -> InferenceResult:
        """Perform inference on input data."""
        pass

    def get_input_hash(self, input_data: Any) -> str:
        """Generate deterministic hash of input data."""
        if isinstance(input_data, str):
            content = input_data.encode('utf-8')
        elif isinstance(input_data, dict):
            content = json.dumps(input_data, sort_keys=True).encode('utf-8')
        elif isinstance(input_data, list):
            content = json.dumps(input_data, sort_keys=True).encode('utf-8')
        else:
            content = str(input_data).encode('utf-8')

        return hashlib.sha256(content).hexdigest()

class InferencePipeline:
    """Main pipeline for AI inference operations."""

    def __init__(self, registry_path: Path):
        self.registry = AIModelRegistry(registry_path)
        self.loaded_models: Dict[str, BaseAIModel] = {}
        self.cache: Dict[str, InferenceResult] = {}
        self.performance_optimizer = get_performance_optimizer()
        self.thread_pool = OptimizedThreadPool(max_workers=2)  # Limit concurrent model loading
        self.inference_stats = {
            'total_inferences': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_time': 0.0
        }

    def load_model(self, model_name: str) -> bool:
        """Load a model into memory."""
        if model_name in self.loaded_models:
            return True

        metadata = self.registry.get_model(model_name)
        if not metadata:
            logger.error(f"Model {model_name} not found in registry")
            return False

        # Determine model path
        model_path = self.registry.models_dir / f"{model_name}-{metadata.version}"

        try:
            # Import appropriate model class based on framework
            if metadata.framework in ['transformers', 'lightweight_transformers']:
                from .models.transformers_model import TransformersModel
                model = TransformersModel(metadata, model_path)
            elif metadata.framework == 'llama_cpp':
                from .models.llama_cpp_model import LlamaCppModel
                model = LlamaCppModel(metadata, model_path)
            else:
                logger.error(f"Unsupported framework: {metadata.framework}")
                return False

            model.load()
            self.loaded_models[model_name] = model
            logger.info(f"Loaded model: {model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False

    def unload_model(self, model_name: str):
        """Unload a model from memory."""
        if model_name in self.loaded_models:
            self.loaded_models[model_name].unload()
            del self.loaded_models[model_name]
            logger.info(f"Unloaded model: {model_name}")

    def infer(self, model_name: str, input_data: Any, use_cache: bool = True, **kwargs) -> Optional[InferenceResult]:
        """Perform inference with caching and performance monitoring."""
        start_time = time.time()

        # Load model if needed (with thread pool optimization)
        if model_name not in self.loaded_models:
            if not self.load_model(model_name):
                return None

        model = self.loaded_models[model_name]
        input_hash = model.get_input_hash(input_data)
        cache_key = f"{model_name}:{input_hash}"

        # Check cache
        if use_cache and cache_key in self.cache:
            self.inference_stats['cache_hits'] += 1
            self.inference_stats['total_inferences'] += 1
            inference_time = time.time() - start_time
            self.inference_stats['total_time'] += inference_time
            logger.debug(f"Cache hit for {cache_key} in {inference_time:.3f}s")
            return self.cache[cache_key]

        # Perform inference
        result = model.infer(input_data, **kwargs)

        # Update stats
        self.inference_stats['cache_misses'] += 1
        self.inference_stats['total_inferences'] += 1
        inference_time = time.time() - start_time
        self.inference_stats['total_time'] += inference_time

        # Cache result
        if use_cache:
            self.cache[cache_key] = result

        logger.debug(f"Inference completed for {model_name} in {inference_time:.3f}s")
        return result

    async def infer_async(self, model_name: str, input_data: Any, use_cache: bool = True, **kwargs) -> Optional[InferenceResult]:
        """Perform async inference with caching and performance monitoring."""
        # Run inference in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool.executor,
            self.infer,
            model_name,
            input_data,
            use_cache,
            kwargs
        )

    async def infer_batch_async(self, model_name: str, input_batch: List[Any], use_cache: bool = True, **kwargs) -> List[Optional[InferenceResult]]:
        """Perform batch inference asynchronously."""
        tasks = [
            self.infer_async(model_name, input_data, use_cache, **kwargs)
            for input_data in input_batch
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_available_models(self, model_type: Optional[str] = None) -> List[str]:
        """Get list of available model names."""
        models = self.registry.list_models(model_type)
        return [m.name for m in models]

    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a model."""
        metadata = self.registry.get_model(model_name)
        if not metadata:
            return None

        return {
            'name': metadata.name,
            'version': metadata.version,
            'type': metadata.model_type,
            'framework': metadata.framework,
            'parameters': metadata.parameters,
            'description': metadata.description,
            'loaded': model_name in self.loaded_models
        }

# Global pipeline instance
_pipeline_instance: Optional[InferencePipeline] = None

def get_ai_pipeline(registry_path: Optional[Path] = None) -> InferencePipeline:
    """Get the global AI inference pipeline instance."""
    global _pipeline_instance

    if _pipeline_instance is None:
        if registry_path is None:
            # Default registry path
            registry_path = Path(__file__).parent / "registry"
        _pipeline_instance = InferencePipeline(registry_path)

    return _pipeline_instance