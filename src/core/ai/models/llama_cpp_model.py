#!/usr/bin/env python3
"""
Llama.cpp-based AI Model Implementation

Supports GGUF models for efficient CPU inference.
"""

import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False

from ..inference_pipeline import BaseAIModel, InferenceResult, ModelMetadata

logger = logging.getLogger(__name__)

class LlamaCppModel(BaseAIModel):
    """Llama.cpp-based model implementation for GGUF models."""

    def __init__(self, metadata: ModelMetadata, model_path: Path):
        super().__init__(metadata, model_path)
        self.model = None

        if not LLAMA_CPP_AVAILABLE:
            raise ImportError("llama-cpp-python library not available")

        # Find GGUF model file
        self.model_file = self._find_model_file()

    def _find_model_file(self) -> Optional[Path]:
        """Find the GGUF model file in the model directory."""
        for file_path in self.model_path.glob("*.gguf"):
            return file_path
        return None

    def load(self):
        """Load the llama.cpp model."""
        if self.loaded:
            return

        if not self.model_file:
            raise FileNotFoundError(f"No GGUF model file found in {self.model_path}")

        try:
            logger.info(f"Loading llama.cpp model: {self.metadata.name}")

            # Load model with optimized settings for CPU
            self.model = Llama(
                model_path=str(self.model_file),
                n_ctx=self.metadata.parameters.get('context_length', 2048),
                n_threads=self.metadata.parameters.get('threads', -1),  # Use all available threads
                n_batch=self.metadata.parameters.get('batch_size', 512),
                verbose=False
            )

            self.loaded = True
            logger.info(f"Successfully loaded llama.cpp model: {self.metadata.name}")

        except Exception as e:
            logger.error(f"Failed to load llama.cpp model: {e}")
            raise

    def unload(self):
        """Unload the model from memory."""
        if not self.loaded:
            return

        self.model = None
        self.loaded = False
        logger.info(f"Unloaded llama.cpp model: {self.metadata.name}")

    def infer(self, input_data: Any, **kwargs) -> InferenceResult:
        """Perform inference using llama.cpp."""
        if not self.loaded:
            raise RuntimeError("Model not loaded")

        start_time = time.time()

        try:
            if isinstance(input_data, str):
                result = self._infer_text(input_data, **kwargs)
            elif isinstance(input_data, dict):
                result = self._infer_structured(input_data, **kwargs)
            else:
                result = self._infer_generic(input_data, **kwargs)

            processing_time = time.time() - start_time

            return InferenceResult(
                model_name=self.metadata.name,
                model_version=self.metadata.version,
                input_hash=self.get_input_hash(input_data),
                output=result,
                confidence=self._estimate_confidence(result),
                processing_time=processing_time,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            )

        except Exception as e:
            logger.error(f"Inference failed: {e}")
            processing_time = time.time() - start_time
            return InferenceResult(
                model_name=self.metadata.name,
                model_version=self.metadata.version,
                input_hash=self.get_input_hash(input_data),
                output={"error": str(e)},
                confidence=0.0,
                processing_time=processing_time,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            )

    def _infer_text(self, text: str, **kwargs) -> Dict[str, Any]:
        """Perform text generation inference."""
        max_tokens = kwargs.get('max_tokens', 256)
        temperature = kwargs.get('temperature', 0.1)

        # Create prompt
        prompt = text

        # Generate response
        response = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            echo=False,
            stop=["\n\n", "###"]  # Common stop sequences
        )

        generated_text = response['choices'][0]['text'].strip()
        finish_reason = response['choices'][0]['finish_reason']

        return {
            "generated_text": generated_text,
            "input_length": len(text),
            "output_length": len(generated_text),
            "finish_reason": finish_reason,
            "usage": response.get('usage', {})
        }

    def _infer_structured(self, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Perform inference on structured data."""
        # Convert structured data to text format
        if 'task' in data and 'content' in data:
            task = data['task']
            content = data['content']

            if task == 'summarize':
                prompt = f"Summarize the following code:\n\n{content}\n\nSummary:"
            elif task == 'classify':
                prompt = f"Classify the following code by its main purpose:\n\n{content}\n\nClassification:"
            elif task == 'analyze':
                prompt = f"Analyze the following code for potential issues:\n\n{content}\n\nAnalysis:"
            else:
                prompt = f"Process the following content:\n\n{content}\n\nResponse:"
        else:
            # Generic structured data handling
            prompt = f"Process this data: {data}"

        return self._infer_text(prompt, **kwargs)

    def _infer_generic(self, data: Any, **kwargs) -> Dict[str, Any]:
        """Generic inference for unsupported input types."""
        text_data = str(data)
        return self._infer_text(text_data, **kwargs)

    def _estimate_confidence(self, result: Dict[str, Any]) -> float:
        """Estimate confidence score from inference result."""
        if "error" in result:
            return 0.0
        elif "finish_reason" in result:
            # Higher confidence for completed generations
            if result["finish_reason"] == "stop":
                return 0.85
            else:
                return 0.7
        else:
            return 0.8