"""
A/B Testing Framework for Analysis Improvements
Enables systematic comparison of analysis algorithm improvements
"""

import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import statistics
try:
    import scipy.stats as stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    print("⚠️  scipy not available - statistical analysis will be limited")

from ..pipeline.analysis import execute_pipeline


class ExperimentStatus(Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class VariantType(Enum):
    CONTROL = "control"
    TREATMENT = "treatment"


@dataclass
class ExperimentVariant:
    """Configuration for an experiment variant"""
    name: str
    type: VariantType
    config: Dict[str, Any]
    description: str = ""

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "type": self.type.value
        }


@dataclass
class ExperimentResult:
    """Result from running a single experiment trial"""
    variant_name: str
    repository_url: str
    success: bool
    analysis_time: float
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class StatisticalAnalysis:
    """Statistical analysis of experiment results"""
    variant_a: str
    variant_b: str
    metric_name: str
    mean_a: float
    mean_b: float
    std_a: float
    std_b: float
    sample_size_a: int
    sample_size_b: int
    p_value: float
    effect_size: float
    confidence_interval: Tuple[float, float]
    significant: bool

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "confidence_interval": list(self.confidence_interval)
        }


class ABTestingFramework:
    """
    A/B Testing Framework for Repository Analysis Improvements

    Enables data-driven optimization by systematically comparing
    different analysis configurations and algorithms.
    """

    def __init__(self, experiments_dir: str = "experiments"):
        self.experiments_dir = Path(experiments_dir)
        self.experiments_dir.mkdir(exist_ok=True)

    def create_experiment(self,
                         name: str,
                         description: str,
                         control_variant: ExperimentVariant,
                         treatment_variants: List[ExperimentVariant],
                         test_repositories: List[str],
                         metrics: List[str] = None) -> str:
        """
        Create a new A/B experiment

        Args:
            name: Experiment name
            description: Experiment description
            control_variant: Baseline configuration
            treatment_variants: Alternative configurations to test
            test_repositories: List of repository URLs to test on
            metrics: Metrics to track (default: success_rate, analysis_time)

        Returns:
            Experiment ID
        """
        if metrics is None:
            metrics = ["success_rate", "analysis_time"]

        experiment_id = f"{name.lower().replace(' ', '_')}_{int(time.time())}"

        experiment_data = {
            "id": experiment_id,
            "name": name,
            "description": description,
            "status": ExperimentStatus.DRAFT.value,
            "created_at": datetime.now().isoformat(),
            "variants": [control_variant.to_dict()] + [v.to_dict() for v in treatment_variants],
            "test_repositories": test_repositories,
            "metrics": metrics,
            "results": [],
            "analysis": None
        }

        experiment_file = self.experiments_dir / f"{experiment_id}.json"
        with open(experiment_file, 'w') as f:
            json.dump(experiment_data, f, indent=2)

        return experiment_id

    def run_experiment(self, experiment_id: str) -> bool:
        """
        Execute an A/B experiment

        Args:
            experiment_id: ID of experiment to run

        Returns:
            True if experiment completed successfully
        """
        experiment_file = self.experiments_dir / f"{experiment_id}.json"

        if not experiment_file.exists():
            raise ValueError(f"Experiment {experiment_id} not found")

        # Load experiment
        with open(experiment_file, 'r') as f:
            experiment = json.load(f)

        # Update status to running
        experiment["status"] = ExperimentStatus.RUNNING.value
        experiment["started_at"] = datetime.now().isoformat()

        # Run trials for each variant and repository
        results = []
        for variant_data in experiment["variants"]:
            variant = ExperimentVariant(**variant_data)
            variant_results = self._run_variant_trials(variant, experiment["test_repositories"])
            results.extend(variant_results)

        experiment["results"] = [r.to_dict() for r in results]
        experiment["completed_at"] = datetime.now().isoformat()
        experiment["status"] = ExperimentStatus.COMPLETED.value

        # Perform statistical analysis
        experiment["analysis"] = self._analyze_results(results, experiment["metrics"])

        # Save updated experiment
        with open(experiment_file, 'w') as f:
            json.dump(experiment, f, indent=2)

        return True

    def _run_variant_trials(self, variant: ExperimentVariant, repositories: List[str]) -> List[ExperimentResult]:
        """Run analysis trials for a specific variant"""
        results = []

        for repo_url in repositories:
            try:
                # Apply variant configuration (this would modify global config)
                self._apply_variant_config(variant)

                # Run analysis using execute_pipeline
                start_time = time.time()
                result = execute_pipeline(repo_url)
                analysis_time = time.time() - start_time

                # Determine success based on result
                success = result.get('success', False) if isinstance(result, dict) else bool(result)

                result_obj = ExperimentResult(
                    variant_name=variant.name,
                    repository_url=repo_url,
                    success=success,
                    analysis_time=analysis_time,
                    metrics={"success": 1.0 if success else 0.0}
                )

            except Exception as e:
                result_obj = ExperimentResult(
                    variant_name=variant.name,
                    repository_url=repo_url,
                    success=False,
                    analysis_time=0.0,
                    error_message=str(e),
                    metrics={"success": 0.0}
                )

            results.append(result_obj)

        return results

    def _apply_variant_config(self, variant: ExperimentVariant):
        """Apply variant-specific configuration to the analysis pipeline"""
        # This would modify pipeline behavior based on variant config
        # For now, we'll implement basic config overrides
        for key, value in variant.config.items():
            if hasattr(self.pipeline, key):
                setattr(self.pipeline, key, value)

    def _analyze_results(self, results: List[ExperimentResult], metrics: List[str]) -> Dict:
        """Perform statistical analysis on experiment results"""
        analysis = {}

        # Group results by variant
        variant_results = {}
        for result in results:
            if result.variant_name not in variant_results:
                variant_results[result.variant_name] = []
            variant_results[result.variant_name].append(result)

        # Analyze each metric
        for metric in metrics:
            metric_analysis = self._analyze_metric(variant_results, metric)
            analysis[metric] = [a.to_dict() for a in metric_analysis]

        return analysis

    def _analyze_metric(self, variant_results: Dict[str, List[ExperimentResult]], metric: str) -> List[StatisticalAnalysis]:
        """Analyze a specific metric across variants"""
        analyses = []
        variant_names = list(variant_results.keys())

        for i in range(len(variant_names)):
            for j in range(i + 1, len(variant_names)):
                variant_a = variant_names[i]
                variant_b = variant_names[j]

                values_a = [getattr(r, metric) if hasattr(r, metric) else r.metrics.get(metric, 0)
                           for r in variant_results[variant_a]]
                values_b = [getattr(r, metric) if hasattr(r, metric) else r.metrics.get(metric, 0)
                           for r in variant_results[variant_b]]

                if len(values_a) < 2 or len(values_b) < 2:
                    continue  # Need at least 2 samples for statistical test

                # Calculate statistics
                mean_a = statistics.mean(values_a)
                mean_b = statistics.mean(values_b)
                std_a = statistics.stdev(values_a) if len(values_a) > 1 else 0
                std_b = statistics.stdev(values_b) if len(values_b) > 1 else 0

                # Perform t-test (use scipy if available, otherwise simplified calculation)
                if HAS_SCIPY and len(values_a) > 1 and len(values_b) > 1:
                    t_stat, p_value = stats.ttest_ind(values_a, values_b)
                else:
                    # Simplified t-test calculation
                    if len(values_a) > 1 and len(values_b) > 1:
                        mean_diff = mean_a - mean_b
                        se_diff = ((std_a ** 2 / len(values_a)) + (std_b ** 2 / len(values_b))) ** 0.5
                        t_stat = mean_diff / se_diff if se_diff > 0 else 0
                        # Approximate p-value (this is a simplification)
                        p_value = 0.05 if abs(t_stat) > 2 else 0.5
                    else:
                        p_value = 1.0  # No statistical test possible

                # Calculate effect size (Cohen's d)
                pooled_std = ((std_a ** 2 + std_b ** 2) / 2) ** 0.5
                effect_size = abs(mean_a - mean_b) / pooled_std if pooled_std > 0 else 0

                # Calculate confidence interval
                se_diff = ((std_a ** 2 / len(values_a)) + (std_b ** 2 / len(values_b))) ** 0.5
                ci_lower = (mean_a - mean_b) - 1.96 * se_diff
                ci_upper = (mean_a - mean_b) + 1.96 * se_diff

                analysis = StatisticalAnalysis(
                    variant_a=variant_a,
                    variant_b=variant_b,
                    metric_name=metric,
                    mean_a=mean_a,
                    mean_b=mean_b,
                    std_a=std_a,
                    std_b=std_b,
                    sample_size_a=len(values_a),
                    sample_size_b=len(values_b),
                    p_value=p_value,
                    effect_size=effect_size,
                    confidence_interval=(ci_lower, ci_upper),
                    significant=p_value < 0.05
                )

                analyses.append(analysis)

        return analyses

    def get_experiment_report(self, experiment_id: str) -> Dict:
        """Generate a comprehensive report for an experiment"""
        experiment_file = self.experiments_dir / f"{experiment_id}.json"

        if not experiment_file.exists():
            raise ValueError(f"Experiment {experiment_id} not found")

        with open(experiment_file, 'r') as f:
            experiment = json.load(f)

        return experiment

    def list_experiments(self) -> List[Dict]:
        """List all experiments"""
        experiments = []
        for exp_file in self.experiments_dir.glob("*.json"):
            with open(exp_file, 'r') as f:
                exp = json.load(f)
                experiments.append({
                    "id": exp["id"],
                    "name": exp["name"],
                    "status": exp["status"],
                    "created_at": exp["created_at"]
                })

        return experiments