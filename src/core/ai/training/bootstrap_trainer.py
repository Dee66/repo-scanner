#!/usr/bin/env python3
"""
Bootstrap Training Script

Creates initial training datasets from repository code and trains lightweight models
for code understanding tasks. Optimized for offline operation and limited resources.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.ai.training.data_pipeline import TrainingDataPipeline
from src.core.ai.training.lightweight_trainer import LightweightTrainer, create_fallback_models

logger = logging.getLogger(__name__)

class BootstrapTrainer:
    """Handles bootstrap training of code understanding models."""

    def __init__(self, workspace_root: Path, registry_path: Path):
        self.workspace_root = workspace_root
        self.registry_path = registry_path
        self.data_pipeline = TrainingDataPipeline(registry_path / "training_data")
        self.lightweight_trainer = LightweightTrainer(registry_path)

        # Setup directories
        self.datasets_dir = registry_path / "datasets"
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    def create_bootstrap_datasets(self) -> Dict[str, Path]:
        """
        Create bootstrap training datasets from repository code.

        Returns:
            Dictionary mapping task names to dataset paths
        """
        logger.info("Creating bootstrap training datasets")

        datasets = {}

        try:
            # Extract code samples from the repository
            code_samples = self._extract_repository_samples()

            if not code_samples:
                logger.warning("No code samples found for training")
                return datasets

            # Create summarization dataset
            summary_dataset = self._create_summarization_dataset(code_samples)
            if summary_dataset:
                summary_path = self.datasets_dir / "bootstrap_summarization.json"
                with open(summary_path, 'w') as f:
                    json.dump(summary_dataset, f, indent=2)
                datasets['summarization'] = summary_path
                logger.info(f"Created summarization dataset with {len(summary_dataset['samples'])} samples")

            # Create classification dataset
            classification_dataset = self._create_classification_dataset(code_samples)
            if classification_dataset:
                classification_path = self.datasets_dir / "bootstrap_classification.json"
                with open(classification_path, 'w') as f:
                    json.dump(classification_dataset, f, indent=2)
                datasets['classification'] = classification_path
                logger.info(f"Created classification dataset with {len(classification_dataset['samples'])} samples")

        except Exception as e:
            logger.error(f"Failed to create bootstrap datasets: {e}")

        return datasets

    def _extract_repository_samples(self) -> List[Dict[str, Any]]:
        """Extract code samples from the repository."""
        samples = []

        # Language extensions to scan
        language_extensions = {
            'python': ['*.py'],
            'javascript': ['*.js', '*.jsx'],
            'typescript': ['*.ts', '*.tsx'],
            'java': ['*.java']
        }

        for language, patterns in language_extensions.items():
            for pattern in patterns:
                for code_file in self.workspace_root.rglob(pattern):
                    try:
                        with open(code_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        if len(content.strip()) < 100:  # Skip very small files
                            continue

                        # Create sample
                        sample = {
                            'file_path': str(code_file.relative_to(self.workspace_root)),
                            'language': language,
                            'content': content,
                            'size': len(content),
                            'lines': len(content.split('\n'))
                        }

                        samples.append(sample)

                    except Exception as e:
                        logger.warning(f"Failed to read {code_file}: {e}")
                        continue

        logger.info(f"Extracted {len(samples)} code samples from repository")
        return samples

    def _create_summarization_dataset(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create summarization training dataset."""
        training_samples = []

        for sample in samples:
            content = sample['content']
            file_path = sample['file_path']

            # Generate simple summary based on file characteristics
            summary = self._generate_simple_summary(content, file_path, sample['language'])

            training_sample = {
                'content': content[:2000],  # Limit content size
                'summary': summary,
                'file_path': file_path,
                'language': sample['language']
            }

            training_samples.append(training_sample)

        return {
            'task': 'summarization',
            'samples': training_samples,
            'created_at': '2024-01-01T00:00:00Z',
            'version': 'bootstrap-v1'
        }

    def _create_classification_dataset(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create classification training dataset."""
        training_samples = []

        for sample in samples:
            content = sample['content']
            file_path = sample['file_path']

            # Determine intent based on file path and content
            intent = self._classify_file_intent(file_path, content, sample['language'])

            training_sample = {
                'content': content[:1000],  # Limit content size
                'intent': intent,
                'file_path': file_path,
                'language': sample['language']
            }

            training_samples.append(training_sample)

        return {
            'task': 'classification',
            'samples': training_samples,
            'created_at': '2024-01-01T00:00:00Z',
            'version': 'bootstrap-v1'
        }

    def _generate_simple_summary(self, content: str, file_path: str, language: str = 'python') -> str:
        """Generate a simple summary for a code file."""
        lines = len(content.split('\n'))

        # Language-specific function/class counting
        if language == 'python':
            classes = content.count('class ')
            functions = content.count('def ')
            imports = content.count('import ') + content.count('from ')
        elif language in ['javascript', 'typescript']:
            classes = content.count('class ')
            functions = content.count('function ') + content.count('=>') + content.count('const ')  # Rough approximation
            imports = content.count('import ') + content.count('require(')
        elif language == 'java':
            classes = content.count('class ')
            functions = content.count('public ') + content.count('private ') + content.count('protected ')  # Rough method count
            imports = content.count('import ')
        else:
            classes = content.count('class ')
            functions = content.count('function ') + content.count('def ')
            imports = content.count('import ')

        summary_parts = []

        # Language-agnostic patterns
        if 'test' in file_path.lower() or 'spec' in file_path.lower():
            summary_parts.append("Test suite")
        elif any(word in file_path.lower() for word in ['config', 'settings', 'env']):
            summary_parts.append("Configuration module")
        elif any(word in file_path.lower() for word in ['util', 'helper', 'common', 'utils']):
            summary_parts.append("Utility module")
        elif 'main' in content.lower() or '__main__' in content or 'public static void main' in content:
            summary_parts.append("Main application entry point")
        elif classes > 0:
            summary_parts.append(f"Object-oriented module with {classes} classes")
        elif functions > 5:
            summary_parts.append(f"Utility module with {functions} functions")
        else:
            summary_parts.append("Code module")

        summary_parts.append(f"({lines} lines, {imports} imports)")

        return " ".join(summary_parts)

    def _classify_file_intent(self, file_path: str, content: str, language: str = 'python') -> str:
        """Classify the intent/purpose of a code file."""
        path_lower = file_path.lower()
        content_lower = content.lower()

        # Check file path patterns (language-agnostic)
        if 'test' in path_lower or 'spec' in path_lower:
            return 'test_code'
        elif any(word in path_lower for word in ['config', 'settings', 'constants', 'env']):
            return 'configuration'
        elif any(word in path_lower for word in ['util', 'helper', 'common', 'utils']):
            return 'utility_functions'

        # Language-specific content patterns
        if language == 'python':
            if 'def main' in content_lower or 'if __name__ == "__main__"' in content_lower:
                return 'application_entry_point'
            elif 'class.*Test' in content or 'def test_' in content:
                return 'test_code'
            elif 'import.*api' in content or 'endpoint' in content or 'route' in content:
                return 'api_service'
            elif 'data' in content_lower and ('model' in content_lower or 'schema' in content_lower):
                return 'data_processing'
            elif 'class ' in content and 'def __init__' in content:
                return 'object_oriented_module'

        elif language in ['javascript', 'typescript']:
            if 'function.*main' in content_lower or 'export.*default' in content_lower and ('app' in content_lower or 'server' in content_lower):
                return 'application_entry_point'
            elif 'describe(' in content or 'it(' in content or 'test(' in content:
                return 'test_code'
            elif 'import.*api' in content or 'endpoint' in content or 'route' in content or 'express' in content:
                return 'api_service'
            elif 'component' in content_lower and ('react' in content_lower or 'jsx' in content):
                return 'ui_component'
            elif 'class ' in content and 'extends' in content:
                return 'object_oriented_module'

        elif language == 'java':
            if 'public static void main' in content:
                return 'application_entry_point'
            elif '@Test' in content or 'Test' in content and 'class ' in content:
                return 'test_code'
            elif '@Controller' in content or '@Service' in content or 'spring' in content_lower:
                return 'api_service'
            elif 'class ' in content and 'implements' in content:
                return 'object_oriented_module'

        # Default classification
        return 'general_purpose'

    def train_bootstrap_models(self, datasets: Dict[str, Path]) -> List[str]:
        """
        Train lightweight models using bootstrap datasets.

        Args:
            datasets: Dictionary of task -> dataset_path mappings

        Returns:
            List of trained model identifiers
        """
        logger.info("Training bootstrap models")

        trained_models = []

        for task, dataset_path in datasets.items():
            try:
                logger.info(f"Training {task} model using {dataset_path}")

                # Perform lightweight fine-tuning
                model_id = self.lightweight_trainer.fine_tune_lightweight(
                    dataset_path=dataset_path,
                    task=task,
                    base_model="distilgpt2",  # Small, efficient model
                    num_epochs=1
                )

                if model_id:
                    trained_models.append(model_id)
                    logger.info(f"Successfully trained {task} model: {model_id}")
                else:
                    logger.warning(f"Failed to train {task} model")

            except Exception as e:
                logger.error(f"Error training {task} model: {e}")

        return trained_models

def main():
    """Main bootstrap training function."""
    logging.basicConfig(level=logging.INFO)

    # Setup paths
    workspace_root = Path("/home/dee/workspace/AI/Repo-Scanner")
    registry_path = workspace_root / "src" / "core" / "ai" / "registry"

    # Create bootstrap trainer
    trainer = BootstrapTrainer(workspace_root, registry_path)

    try:
        # Create bootstrap datasets
        logger.info("Step 1: Creating bootstrap datasets")
        datasets = trainer.create_bootstrap_datasets()

        if not datasets:
            logger.warning("No datasets created - falling back to pattern-based models")
            create_fallback_models(registry_path)
            return

        # Train models
        logger.info("Step 2: Training bootstrap models")
        trained_models = trainer.train_bootstrap_models(datasets)

        if trained_models:
            logger.info(f"Successfully trained {len(trained_models)} models: {trained_models}")
        else:
            logger.warning("No models trained - falling back to pattern-based models")
            create_fallback_models(registry_path)

        logger.info("Bootstrap training completed")

    except Exception as e:
        logger.error(f"Bootstrap training failed: {e}")
        # Fallback to pattern-based models
        create_fallback_models(registry_path)

if __name__ == "__main__":
    main()