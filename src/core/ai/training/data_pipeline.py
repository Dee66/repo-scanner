#!/usr/bin/env python3
"""
Training Data Pipeline for Code Understanding Models

Prepares and processes code datasets for training AI models.
Supports multiple programming languages and various code understanding tasks.
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import re

logger = logging.getLogger(__name__)

@dataclass
class CodeSample:
    """Represents a code sample for training."""
    content: str
    language: str
    file_path: str
    summary: Optional[str] = None
    intent: Optional[str] = None
    complexity: Optional[str] = None
    patterns: Optional[List[str]] = None
    issues: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class TrainingDataset:
    """Represents a training dataset."""
    name: str
    version: str
    task: str  # 'summarization', 'classification', 'anomaly_detection'
    language: str
    samples: List[CodeSample]
    metadata: Dict[str, Any]

class TrainingDataPipeline:
    """Pipeline for preparing training data for code understanding models."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.raw_data_dir = data_dir / "raw"
        self.processed_data_dir = data_dir / "processed"
        self.datasets_dir = data_dir / "datasets"

        # Create directories
        for dir_path in [self.raw_data_dir, self.processed_data_dir, self.datasets_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Supported languages and their file extensions
        self.language_extensions = {
            'python': ['.py'],
            'javascript': ['.js', '.jsx', '.ts', '.tsx'],
            'java': ['.java'],
            'cpp': ['.cpp', '.cc', '.cxx', '.c++', '.hpp', '.h'],
            'c': ['.c', '.h'],
            'go': ['.go'],
            'rust': ['.rs'],
            'php': ['.php'],
            'ruby': ['.rb'],
            'scala': ['.scala'],
            'kotlin': ['.kt'],
            'swift': ['.swift'],
            'typescript': ['.ts', '.tsx']
        }

    def extract_code_samples(self, repository_path: Path, language: str = 'python') -> List[CodeSample]:
        """
        Extract code samples from a repository.

        Args:
            repository_path: Path to the repository
            language: Programming language to extract

        Returns:
            List of CodeSample objects
        """
        logger.info(f"Extracting {language} code samples from {repository_path}")

        extensions = self.language_extensions.get(language, [])
        if not extensions:
            logger.warning(f"No extensions defined for language: {language}")
            return []

        samples = []

        # Find all files with the specified extensions
        for ext in extensions:
            for file_path in repository_path.rglob(f"*{ext}"):
                if self._is_valid_code_file(file_path):
                    try:
                        sample = self._process_code_file(file_path, language)
                        if sample:
                            samples.append(sample)
                    except Exception as e:
                        logger.warning(f"Failed to process {file_path}: {e}")

        logger.info(f"Extracted {len(samples)} code samples")
        return samples

    def _is_valid_code_file(self, file_path: Path) -> bool:
        """Check if a file is a valid code file for training."""
        # Skip test files, generated files, and very small files
        if any(skip in str(file_path) for skip in ['test', 'spec', '__pycache__', 'node_modules', 'build', 'dist']):
            return False

        if file_path.stat().st_size < 100:  # Skip files smaller than 100 bytes
            return False

        return True

    def _process_code_file(self, file_path: Path, language: str) -> Optional[CodeSample]:
        """Process a single code file into a training sample."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            if not content.strip():
                return None

            # Basic content validation
            if len(content.split('\n')) < 3:  # Skip files with less than 3 lines
                return None

            # Extract basic metadata
            metadata = {
                'file_size': len(content),
                'line_count': len(content.split('\n')),
                'functions': self._count_functions(content, language),
                'classes': self._count_classes(content, language),
                'imports': self._count_imports(content, language)
            }

            return CodeSample(
                content=content,
                language=language,
                file_path=str(file_path),
                metadata=metadata
            )

        except Exception as e:
            logger.warning(f"Error processing {file_path}: {e}")
            return None

    def _count_functions(self, content: str, language: str) -> int:
        """Count function definitions in code."""
        patterns = {
            'python': r'\bdef\s+\w+\s*\(',
            'javascript': r'\bfunction\s+\w+\s*\(|const\s+\w+\s*=\s*\(|let\s+\w+\s*=\s*\(',
            'java': r'\b(public|private|protected)?\s*\w+\s+\w+\s*\(',
            'cpp': r'\b\w+\s+\w+\s*\(',
            'go': r'\bfunc\s+\w+\s*\(',
            'rust': r'\bfn\s+\w+\s*\(',
            'php': r'\bfunction\s+\w+\s*\('
        }

        pattern = patterns.get(language, r'\bfunction\s+\w+\s*\(')
        return len(re.findall(pattern, content))

    def _count_classes(self, content: str, language: str) -> int:
        """Count class definitions in code."""
        patterns = {
            'python': r'\bclass\s+\w+',
            'javascript': r'\bclass\s+\w+',
            'java': r'\bclass\s+\w+',
            'cpp': r'\bclass\s+\w+',
            'go': r'\btype\s+\w+\s+struct',
            'rust': r'\bstruct\s+\w+|enum\s+\w+|trait\s+\w+',
            'php': r'\bclass\s+\w+'
        }

        pattern = patterns.get(language, r'\bclass\s+\w+')
        return len(re.findall(pattern, content))

    def _count_imports(self, content: str, language: str) -> int:
        """Count import statements in code."""
        patterns = {
            'python': r'^\s*(import|from)\s+',
            'javascript': r'^\s*(import|require)\s*\(',
            'java': r'^\s*import\s+',
            'cpp': r'^\s*#include\s+',
            'go': r'^\s*import\s*\(',
            'rust': r'^\s*use\s+',
            'php': r'^\s*(use|require|include)\s+'
        }

        pattern = patterns.get(language, r'^\s*import\s+')
        return len(re.findall(pattern, content, re.MULTILINE))

    def generate_summarization_dataset(self, samples: List[CodeSample], dataset_name: str) -> TrainingDataset:
        """
        Generate a summarization training dataset.

        Args:
            samples: List of code samples
            dataset_name: Name for the dataset

        Returns:
            TrainingDataset for summarization
        """
        logger.info(f"Generating summarization dataset: {dataset_name}")

        processed_samples = []

        for sample in samples:
            if len(sample.content) > 5000:  # Skip very large files
                continue

            # Generate summary using heuristics
            summary = self._generate_code_summary(sample)

            if summary:
                sample.summary = summary
                processed_samples.append(sample)

        return TrainingDataset(
            name=dataset_name,
            version="1.0.0",
            task="summarization",
            language=samples[0].language if samples else "unknown",
            samples=processed_samples,
            metadata={
                'total_samples': len(processed_samples),
                'avg_content_length': sum(len(s.content) for s in processed_samples) / len(processed_samples) if processed_samples else 0,
                'language_distribution': self._get_language_distribution(processed_samples),
                'created_at': "2025-12-23T00:00:00Z"
            }
        )

    def _generate_code_summary(self, sample: CodeSample) -> Optional[str]:
        """Generate a summary for a code sample using heuristics."""
        content = sample.content
        metadata = sample.metadata or {}

        # Extract key information
        functions = metadata.get('functions', 0)
        classes = metadata.get('classes', 0)
        imports = metadata.get('imports', 0)
        lines = metadata.get('line_count', 0)

        # Build summary based on code structure
        summary_parts = []

        if classes > 0:
            summary_parts.append(f"Defines {classes} class{'es' if classes > 1 else ''}")

        if functions > 0:
            summary_parts.append(f"Contains {functions} function{'s' if functions > 1 else ''}")

        if imports > 0:
            summary_parts.append(f"Imports {imports} module{'s' if imports > 1 else ''}")

        # Add file size information
        if lines > 100:
            summary_parts.append("Large implementation file")
        elif lines > 50:
            summary_parts.append("Medium-sized code file")
        else:
            summary_parts.append("Small utility file")

        if summary_parts:
            return ". ".join(summary_parts) + "."
        else:
            return f"Code file with {lines} lines of {sample.language} code."

    def generate_classification_dataset(self, samples: List[CodeSample], dataset_name: str) -> TrainingDataset:
        """
        Generate a classification training dataset.

        Args:
            samples: List of code samples
            dataset_name: Name for the dataset

        Returns:
            TrainingDataset for classification
        """
        logger.info(f"Generating classification dataset: {dataset_name}")

        processed_samples = []

        for sample in samples:
            # Classify code intent
            intent = self._classify_code_intent(sample)

            if intent:
                sample.intent = intent
                processed_samples.append(sample)

        return TrainingDataset(
            name=dataset_name,
            version="1.0.0",
            task="classification",
            language=samples[0].language if samples else "unknown",
            samples=processed_samples,
            metadata={
                'total_samples': len(processed_samples),
                'intent_distribution': self._get_intent_distribution(processed_samples),
                'language': samples[0].language if samples else "unknown",
                'created_at': "2025-12-23T00:00:00Z"
            }
        )

    def _classify_code_intent(self, sample: CodeSample) -> Optional[str]:
        """Classify the intent/purpose of code."""
        content = sample.content.lower()
        metadata = sample.metadata or {}

        # Check for main entry points
        if 'def main' in content or 'if __name__ == "__main__"' in content:
            return "application_entry_point"
        elif 'class' in content and any(term in content for term in ['test', 'spec']):
            return "test_code"
        elif any(term in content for term in ['config', 'settings', 'constants']):
            return "configuration"
        elif any(term in content for term in ['util', 'helper', 'common']):
            return "utility_functions"
        elif metadata.get('classes', 0) > 0 and metadata.get('functions', 0) > 5:
            return "object_oriented_module"
        elif 'import' in content and 'def' in content:
            return "library_module"
        elif any(term in content for term in ['api', 'endpoint', 'route']):
            return "api_service"
        elif any(term in content for term in ['data', 'model', 'schema']):
            return "data_processing"
        else:
            return "general_purpose"

    def save_dataset(self, dataset: TrainingDataset, output_path: Optional[Path] = None):
        """Save a training dataset to disk."""
        if output_path is None:
            output_path = self.datasets_dir / f"{dataset.name}_{dataset.version}.json"

        # Convert to serializable format
        dataset_dict = {
            'name': dataset.name,
            'version': dataset.version,
            'task': dataset.task,
            'language': dataset.language,
            'metadata': dataset.metadata,
            'samples': [
                {
                    'content': sample.content,
                    'language': sample.language,
                    'file_path': sample.file_path,
                    'summary': sample.summary,
                    'intent': sample.intent,
                    'complexity': sample.complexity,
                    'patterns': sample.patterns,
                    'issues': sample.issues,
                    'metadata': sample.metadata
                } for sample in dataset.samples
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dataset_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved dataset to {output_path}")

    def load_dataset(self, dataset_path: Path) -> TrainingDataset:
        """Load a training dataset from disk."""
        with open(dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        samples = []
        for sample_data in data['samples']:
            samples.append(CodeSample(**sample_data))

        return TrainingDataset(
            name=data['name'],
            version=data['version'],
            task=data['task'],
            language=data['language'],
            samples=samples,
            metadata=data['metadata']
        )

    def _get_language_distribution(self, samples: List[CodeSample]) -> Dict[str, int]:
        """Get language distribution in samples."""
        distribution = {}
        for sample in samples:
            distribution[sample.language] = distribution.get(sample.language, 0) + 1
        return distribution

    def _get_intent_distribution(self, samples: List[CodeSample]) -> Dict[str, int]:
        """Get intent distribution in samples."""
        distribution = {}
        for sample in samples:
            if sample.intent:
                distribution[sample.intent] = distribution.get(sample.intent, 0) + 1
        return distribution

    def create_bootstrap_datasets(self, repository_path: Path):
        """Create initial training datasets from the repository itself."""
        logger.info("Creating bootstrap training datasets")

        # Extract Python samples (since this is a Python project)
        python_samples = self.extract_code_samples(repository_path, 'python')

        if python_samples:
            # Create summarization dataset
            summary_dataset = self.generate_summarization_dataset(
                python_samples,
                "bootstrap_python_summarization"
            )
            self.save_dataset(summary_dataset)

            # Create classification dataset
            classification_dataset = self.generate_classification_dataset(
                python_samples,
                "bootstrap_python_classification"
            )
            self.save_dataset(classification_dataset)

            logger.info(f"Created bootstrap datasets with {len(python_samples)} samples")
        else:
            logger.warning("No Python samples found for bootstrap datasets")