#!/usr/bin/env python3
"""
Model Training Framework for Code Understanding

Provides training capabilities for fine-tuning AI models on code understanding tasks.
Supports offline training with prepared datasets.
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import tempfile

try:
    from transformers import (
        AutoTokenizer, AutoModelForCausalLM, AutoModelForSequenceClassification,
        TrainingArguments, Trainer, DataCollatorForLanguageModeling,
        DataCollatorWithPadding
    )
    import torch
    from torch.utils.data import Dataset
    import datasets
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Transformers not available - training will be limited")

logger = logging.getLogger(__name__)

@dataclass
class TrainingConfig:
    """Configuration for model training."""
    task: str
    base_model: str
    output_dir: Path
    num_epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 2e-5
    max_length: int = 512
    save_steps: int = 500
    eval_steps: int = 500
    logging_steps: int = 100
    gradient_accumulation_steps: int = 4
    fp16: bool = False
    local_rank: int = -1

class CodeDataset(Dataset):
    """Dataset class for code understanding tasks."""

    def __init__(self, samples: List[Dict[str, Any]], tokenizer, task: str, max_length: int = 512):
        self.samples = samples
        self.tokenizer = tokenizer
        self.task = task
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]

        if self.task == "summarization":
            return self._prepare_summarization_sample(sample)
        elif self.task == "classification":
            return self._prepare_classification_sample(sample)
        else:
            return self._prepare_generic_sample(sample)

    def _prepare_summarization_sample(self, sample):
        """Prepare sample for summarization task."""
        content = sample.get('content', '')
        summary = sample.get('summary', '')

        # Truncate content if too long
        if len(content) > self.max_length * 4:  # Allow longer input for summarization
            content = content[:self.max_length * 4]

        # Format as instruction tuning
        instruction = f"Summarize the following code:\n\n{content}\n\nSummary:"
        full_text = f"{instruction}{summary}"

        tokenized = self.tokenizer(
            full_text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        return {
            'input_ids': tokenized['input_ids'].squeeze(),
            'attention_mask': tokenized['attention_mask'].squeeze(),
            'labels': tokenized['input_ids'].squeeze()
        }

    def _prepare_classification_sample(self, sample):
        """Prepare sample for classification task."""
        content = sample.get('content', '')
        intent = sample.get('intent', '')

        # Truncate content
        content = content[:self.max_length]

        tokenized = self.tokenizer(
            content,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        # Convert intent to label (simplified mapping)
        label_map = {
            'application_entry_point': 0,
            'test_code': 1,
            'configuration': 2,
            'utility_functions': 3,
            'object_oriented_module': 4,
            'library_module': 5,
            'api_service': 6,
            'data_processing': 7,
            'general_purpose': 8
        }
        label = label_map.get(intent, 8)  # Default to general_purpose

        return {
            'input_ids': tokenized['input_ids'].squeeze(),
            'attention_mask': tokenized['attention_mask'].squeeze(),
            'labels': label
        }

    def _prepare_generic_sample(self, sample):
        """Prepare sample for generic tasks."""
        content = sample.get('content', '')

        tokenized = self.tokenizer(
            content,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )

        return {
            'input_ids': tokenized['input_ids'].squeeze(),
            'attention_mask': tokenized['attention_mask'].squeeze(),
            'labels': tokenized['input_ids'].squeeze()
        }

class ModelTrainer:
    """Handles training of AI models for code understanding."""

    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self.models_dir = registry_path / "models"
        self.metadata_dir = registry_path / "metadata"

        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Transformers library required for training")

    def train_summarization_model(self, dataset_path: Path, config: TrainingConfig) -> str:
        """
        Train a code summarization model.

        Args:
            dataset_path: Path to training dataset
            config: Training configuration

        Returns:
            Model name/version identifier
        """
        logger.info(f"Training summarization model with config: {config}")

        # Load dataset
        with open(dataset_path) as f:
            dataset_data = json.load(f)

        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(config.base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(config.base_model)

        # Prepare training data
        train_samples = dataset_data['samples']
        train_dataset = CodeDataset(train_samples, tokenizer, "summarization", config.max_length)

        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(config.output_dir),
            num_train_epochs=config.num_epochs,
            per_device_train_batch_size=config.batch_size,
            learning_rate=config.learning_rate,
            save_steps=config.save_steps,
            save_total_limit=2,
            evaluation_strategy="steps" if len(train_samples) > 100 else "no",
            eval_steps=config.eval_steps,
            logging_steps=config.logging_steps,
            gradient_accumulation_steps=config.gradient_accumulation_steps,
            fp16=config.fp16,
            local_rank=config.local_rank,
            load_best_model_at_end=True,
            metric_for_best_model="loss",
            greater_is_better=False,
        )

        # Data collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer,
            mlm=False  # Causal LM, not masked LM
        )

        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            data_collator=data_collator,
        )

        # Train
        logger.info("Starting training...")
        trainer.train()

        # Save model
        model_name = f"code-summary-{int(time.time())}"
        model_version = "1.0.0"
        model_path = self.models_dir / f"{model_name}-{model_version}"

        trainer.save_model(str(model_path))
        tokenizer.save_pretrained(str(model_path))

        # Register model
        self._register_trained_model(model_name, model_version, config, dataset_data)

        logger.info(f"Training completed. Model saved as {model_name}")
        return f"{model_name}-{model_version}"

    def train_classification_model(self, dataset_path: Path, config: TrainingConfig) -> str:
        """
        Train a code classification model.

        Args:
            dataset_path: Path to training dataset
            config: Training configuration

        Returns:
            Model name/version identifier
        """
        logger.info(f"Training classification model with config: {config}")

        # Load dataset
        with open(dataset_path) as f:
            dataset_data = json.load(f)

        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(config.base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # For classification, we need to know number of labels
        num_labels = len(set(s.get('intent', 'general_purpose') for s in dataset_data['samples']))
        model = AutoModelForSequenceClassification.from_pretrained(
            config.base_model,
            num_labels=num_labels
        )

        # Prepare training data
        train_samples = dataset_data['samples']
        train_dataset = CodeDataset(train_samples, tokenizer, "classification", config.max_length)

        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(config.output_dir),
            num_train_epochs=config.num_epochs,
            per_device_train_batch_size=config.batch_size,
            learning_rate=config.learning_rate,
            save_steps=config.save_steps,
            save_total_limit=2,
            evaluation_strategy="steps" if len(train_samples) > 100 else "no",
            eval_steps=config.eval_steps,
            logging_steps=config.logging_steps,
            gradient_accumulation_steps=config.gradient_accumulation_steps,
            fp16=config.fp16,
            local_rank=config.local_rank,
            load_best_model_at_end=True,
            metric_for_best_model="accuracy",
        )

        # Data collator
        data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            data_collator=data_collator,
        )

        # Train
        logger.info("Starting training...")
        trainer.train()

        # Save model
        model_name = f"code-classifier-{int(time.time())}"
        model_version = "1.0.0"
        model_path = self.models_dir / f"{model_name}-{model_version}"

        trainer.save_model(str(model_path))
        tokenizer.save_pretrained(str(model_path))

        # Register model
        self._register_trained_model(model_name, model_version, config, dataset_data)

        logger.info(f"Training completed. Model saved as {model_name}")
        return f"{model_name}-{model_version}"

    def _register_trained_model(self, name: str, version: str, config: TrainingConfig,
                               dataset_info: Dict[str, Any]):
        """Register a trained model in the registry."""
        from ..inference_pipeline import ModelMetadata

        metadata = ModelMetadata(
            name=name,
            version=version,
            model_type=config.task,
            framework="transformers",
            parameters={
                'base_model': config.base_model,
                'max_length': config.max_length,
                'num_epochs': config.num_epochs,
                'batch_size': config.batch_size,
                'learning_rate': config.learning_rate,
                'training_samples': len(dataset_info.get('samples', [])),
                'language': dataset_info.get('language', 'unknown')
            },
            hash=f"trained-{name}-{version}",
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            description=f"Trained {config.task} model based on {config.base_model}"
        )

        # Save metadata
        from ..inference_pipeline import AIModelRegistry
        registry = AIModelRegistry(self.registry_path)
        registry.register_model(metadata)

    def create_training_config(self, task: str, base_model: str = "microsoft/DialoGPT-small") -> TrainingConfig:
        """
        Create a default training configuration.

        Args:
            task: Training task ('summarization', 'classification')
            base_model: Base model to fine-tune

        Returns:
            TrainingConfig object
        """
        output_dir = Path(tempfile.mkdtemp()) / f"training_{task}_{int(time.time())}"

        return TrainingConfig(
            task=task,
            base_model=base_model,
            output_dir=output_dir,
            num_epochs=2,  # Reduced for faster iteration
            batch_size=2,  # Smaller batch size for limited resources
            learning_rate=5e-5,
            max_length=256,  # Shorter for code snippets
            save_steps=1000,
            eval_steps=1000,
            logging_steps=500,
            gradient_accumulation_steps=8,
            fp16=torch.cuda.is_available(),  # Use FP16 if GPU available
        )

def train_bootstrap_models(data_dir: Path, registry_path: Path):
    """
    Train initial models using bootstrap datasets.

    Args:
        data_dir: Path to training data directory
        registry_path: Path to model registry
    """
    logger.info("Training bootstrap models")

    trainer = ModelTrainer(registry_path)

    # Find bootstrap datasets
    datasets_dir = data_dir / "datasets"
    summary_dataset = None
    classification_dataset = None

    for dataset_file in datasets_dir.glob("bootstrap_*.json"):
        if "summarization" in str(dataset_file):
            summary_dataset = dataset_file
        elif "classification" in str(dataset_file):
            classification_dataset = dataset_file

    # Train summarization model
    if summary_dataset and summary_dataset.exists():
        try:
            config = trainer.create_training_config("summarization")
            model_id = trainer.train_summarization_model(summary_dataset, config)
            logger.info(f"Trained summarization model: {model_id}")
        except Exception as e:
            logger.error(f"Failed to train summarization model: {e}")

    # Train classification model
    if classification_dataset and classification_dataset.exists():
        try:
            config = trainer.create_training_config("classification")
            model_id = trainer.train_classification_model(classification_dataset, config)
            logger.info(f"Trained classification model: {model_id}")
        except Exception as e:
            logger.error(f"Failed to train classification model: {e}")

    logger.info("Bootstrap model training completed")