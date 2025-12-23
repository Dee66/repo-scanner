#!/usr/bin/env python3
"""
AI Registry Setup Script

Initializes the AI model registry with placeholder models for offline operation.
This allows the system to function even when actual AI models are not available.
"""

import json
from pathlib import Path
from ..ai.inference_pipeline import ModelMetadata, AIModelRegistry

def setup_ai_registry(registry_path: Path = None):
    """Set up the AI model registry with placeholder models."""

    if registry_path is None:
        registry_path = Path(__file__).parent.parent / "ai" / "registry"

    registry = AIModelRegistry(registry_path)

    # Define placeholder models for different capabilities
    placeholder_models = [
        {
            "name": "code-summary-model",
            "version": "1.0.0",
            "model_type": "llm",
            "framework": "transformers",
            "parameters": {
                "model_size": "placeholder",
                "context_length": 2048,
                "capabilities": ["code_summarization", "documentation"]
            },
            "hash": "placeholder-hash-summary",
            "created_at": "2025-12-23T00:00:00Z",
            "description": "Placeholder model for code summarization and documentation generation"
        },
        {
            "name": "code-classifier-model",
            "version": "1.0.0",
            "model_type": "classifier",
            "framework": "transformers",
            "parameters": {
                "model_size": "placeholder",
                "classes": ["utility", "application", "library", "framework", "tool"],
                "capabilities": ["intent_classification", "code_categorization"]
            },
            "hash": "placeholder-hash-classifier",
            "created_at": "2025-12-23T00:00:00Z",
            "description": "Placeholder model for code intent classification and categorization"
        },
        {
            "name": "security-pattern-model",
            "version": "1.0.0",
            "model_type": "llm",
            "framework": "llama_cpp",
            "parameters": {
                "model_size": "placeholder",
                "context_length": 4096,
                "capabilities": ["security_analysis", "vulnerability_detection", "pattern_recognition"]
            },
            "hash": "placeholder-hash-security",
            "created_at": "2025-12-23T00:00:00Z",
            "description": "Placeholder model for security pattern analysis and vulnerability detection"
        }
    ]

    # Register placeholder models
    for model_config in placeholder_models:
        metadata = ModelMetadata(**model_config)
        registry.register_model(metadata)

        print(f"Registered placeholder model: {metadata.name} v{metadata.version}")

    print(f"AI registry setup complete. Registry path: {registry_path}")
    print(f"Registered {len(placeholder_models)} placeholder models")

    return registry

if __name__ == "__main__":
    setup_ai_registry()