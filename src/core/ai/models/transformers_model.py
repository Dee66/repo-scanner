#!/usr/bin/env python3
"""
Transformers-based AI Model Implementation

Supports Hugging Face transformers models for offline inference.
"""

import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from ...performance_optimizer import lazy_import, get_cached_model_loader

# Lazy import transformers components
TRANSFORMERS_AVAILABLE = True
try:
    # Test import without loading full library
    import transformers
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from ..inference_pipeline import BaseAIModel, InferenceResult, ModelMetadata

logger = logging.getLogger(__name__)

class TransformersModel(BaseAIModel):
    """Transformers-based model implementation."""

    def __init__(self, metadata: ModelMetadata, model_path: Path):
        super().__init__(metadata, model_path)
        self.model = None
        self.tokenizer = None
        self.device = "cpu"  # Default to CPU for offline operation
        self.use_pattern_fallback = False
        self.model_cache = get_cached_model_loader()

        if not TRANSFORMERS_AVAILABLE:
            self.use_pattern_fallback = True
            logger.warning("Transformers not available, using pattern-based fallback")

    def load(self):
        """Load the transformers model with caching and lazy loading."""
        if self.loaded:
            return

        if self.use_pattern_fallback:
            self.loaded = True
            logger.info(f"Using pattern-based fallback for model: {self.metadata.name}")
            return

        try:
            logger.info(f"Loading transformers model: {self.metadata.name}")

            # Use cached model loader
            model_key = f"{self.metadata.name}-{self.metadata.version}"

            def _load_model():
                # Lazy import transformers components
                AutoTokenizer = lazy_import('AutoTokenizer', 'transformers.AutoTokenizer')
                AutoModelForCausalLM = lazy_import('AutoModelForCausalLM', 'transformers.AutoModelForCausalLM')
                AutoModelForSequenceClassification = lazy_import('AutoModelForSequenceClassification', 'transformers.AutoModelForSequenceClassification')
                torch = lazy_import('torch')

                # Determine model type and load accordingly
                if self.metadata.model_type == 'llm':
                    self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
                    self.model = AutoModelForCausalLM.from_pretrained(str(self.model_path))
                elif self.metadata.model_type == 'classifier':
                    self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
                    self.model = AutoModelForSequenceClassification.from_pretrained(str(self.model_path))
                else:
                    raise ValueError(f"Unsupported model type: {self.metadata.model_type}")

                # Move to device if available
                if torch.cuda.is_available():
                    self.device = "cuda"
                    self.model.to(self.device)

                return {
                    'model': self.model,
                    'tokenizer': self.tokenizer,
                    'device': self.device
                }

            # Get cached model
            cached_data = self.model_cache.get_model(model_key, _load_model)
            self.model = cached_data['model']
            self.tokenizer = cached_data['tokenizer']
            self.device = cached_data['device']

            self.loaded = True
            logger.info(f"Successfully loaded model: {self.metadata.name}")

        except Exception as e:
            logger.warning(f"Failed to load transformers model {self.metadata.name}: {e}")
            self.use_pattern_fallback = True
            self.loaded = True

    def unload(self):
        """Unload the model from memory."""
        if not self.loaded:
            return

        self.model = None
        self.tokenizer = None
        if hasattr(self, 'pipeline'):
            delattr(self, 'pipeline')
        self.loaded = False
        logger.info(f"Unloaded model: {self.metadata.name}")

    def infer(self, input_data: Any, **kwargs) -> InferenceResult:
        """Perform inference using the transformers model or pattern fallback."""
        if not self.loaded:
            raise RuntimeError("Model not loaded")

        start_time = time.time()

        try:
            if self.use_pattern_fallback:
                result = self._infer_pattern_based(input_data, **kwargs)
            elif self.metadata.model_type == "llm":
                result = self._infer_llm(input_data, **kwargs)
            elif self.metadata.model_type == "classifier":
                result = self._infer_classifier(input_data, **kwargs)
            else:
                result = self._infer_pipeline(input_data, **kwargs)

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

    def _infer_llm(self, input_data: str, **kwargs) -> Dict[str, Any]:
        """Perform LLM inference."""
        max_length = kwargs.get('max_length', 512)
        temperature = kwargs.get('temperature', 0.1)  # Low temperature for deterministic results

        inputs = self.tokenizer(input_data, return_tensors="pt", truncation=True, max_length=max_length)
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=max_length,
                temperature=temperature,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id,
                num_return_sequences=1
            )

        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        return {
            "generated_text": generated_text,
            "input_length": len(input_data),
            "output_length": len(generated_text)
        }

    def _infer_classifier(self, input_data: str, **kwargs) -> Dict[str, Any]:
        """Perform classification inference."""
        inputs = self.tokenizer(input_data, return_tensors="pt", truncation=True, padding=True)
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.softmax(outputs.logits, dim=-1)
            predicted_class = torch.argmax(predictions, dim=-1).item()
            confidence = predictions[0][predicted_class].item()

        # Get class labels if available
        id2label = getattr(self.model.config, 'id2label', {})
        predicted_label = id2label.get(predicted_class, f"class_{predicted_class}")

        return {
            "predicted_class": predicted_class,
            "predicted_label": predicted_label,
            "confidence": confidence,
            "all_probabilities": predictions[0].tolist()
        }

    def _infer_pipeline(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """Perform inference using transformers pipeline."""
        if not hasattr(self, 'pipeline'):
            raise RuntimeError("Pipeline not available")

        result = self.pipeline(input_data, **kwargs)
        return {"result": result}

    def _infer_pattern_based(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """Perform pattern-based inference as fallback."""
        from ..training.lightweight_trainer import get_pattern_model

        pattern_model = get_pattern_model()

        if self.metadata.model_type == "llm" or "summarization" in self.metadata.name:
            # Use summarization patterns
            summary = pattern_model.summarize_code(str(input_data))
            return {"summary": summary, "method": "pattern_based"}
        elif self.metadata.model_type == "classifier" or "classification" in self.metadata.name:
            # Use classification patterns
            intent = pattern_model.classify_code(str(input_data))
            return {"intent": intent, "method": "pattern_based"}
        else:
            return {"result": f"Pattern-based analysis of: {str(input_data)[:100]}...", "method": "pattern_based"}

    def _estimate_confidence(self, result: Dict[str, Any]) -> float:
        """Estimate confidence score from inference result."""
        if "confidence" in result:
            return result["confidence"]
        elif "all_probabilities" in result:
            return max(result["all_probabilities"])
        elif "error" in result:
            return 0.0
        else:
            # Default confidence for LLM generation
            return 0.8