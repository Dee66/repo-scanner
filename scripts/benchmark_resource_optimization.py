#!/usr/bin/env python3
"""
Resource Optimization Benchmark

Validates that EFF-031 optimizations achieve 20%+ resource usage reduction.
Compares baseline performance vs optimized pipeline.
"""

import time
import tempfile
import os
import psutil
import statistics
from pathlib import Path
from typing import Dict, List, Any
import logging

from src.core.pipeline.analysis import OptimizedAnalysisPipeline, AnalysisRequest
from src.core.pipeline.analysis import _execute_standard_pipeline, discover_repository_root, get_canonical_file_list
from src.core.performance_optimizer import get_performance_optimizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResourceBenchmark:
    """Benchmark for measuring resource optimization improvements."""

    def __init__(self):
        self.performance_optimizer = get_performance_optimizer()

    def create_test_repository(self, size: str = "medium") -> str:
        """Create a test repository with specified complexity."""
        temp_dir = tempfile.mkdtemp(prefix="repo_scanner_benchmark_")

        if size == "small":
            self._create_small_repo(temp_dir)
        elif size == "medium":
            self._create_medium_repo(temp_dir)
        elif size == "large":
            self._create_large_repo(temp_dir)

        return temp_dir

    def _create_small_repo(self, path: str):
        """Create a small test repository."""
        # Create a few Python files
        for i in range(5):
            with open(os.path.join(path, f'module_{i}.py'), 'w') as f:
                f.write(f'''
def function_{i}():
    """Test function {i}."""
    return {i}

class Class{i}:
    """Test class {i}."""
    def method(self):
        return "test"
''')

    def _create_medium_repo(self, path: str):
        """Create a medium test repository."""
        # Create multiple Python files with dependencies
        for i in range(20):
            with open(os.path.join(path, f'module_{i}.py'), 'w') as f:
                imports = [f"import module_{j}" for j in range(max(0, i-3), i)]
                functions = [f"def func_{i}_{j}(): return {j}" for j in range(10)]
                f.write('\n'.join(imports + [''] + functions))

        # Create some non-Python files
        for i in range(10):
            with open(os.path.join(path, f'document_{i}.md'), 'w') as f:
                f.write(f'# Document {i}\n\nThis is test content for document {i}.')

    def _create_large_repo(self, path: str):
        """Create a large test repository."""
        # Create many files with complex dependencies
        for i in range(100):
            with open(os.path.join(path, f'module_{i}.py'), 'w') as f:
                imports = [f"import module_{j}" for j in range(max(0, i-5), i)]
                functions = [f"def func_{i}_{j}(): return {j}" for j in range(20)]
                classes = [f"class Class{i}_{j}: pass" for j in range(5)]
                f.write('\n'.join(imports + [''] + functions + [''] + classes))

        # Create many documentation files
        for i in range(50):
            with open(os.path.join(path, f'doc_{i}.md'), 'w') as f:
                f.write(f'# Documentation {i}\n\n' + '\n'.join([f'## Section {j}' for j in range(10)]))

    def measure_baseline_performance(self, repo_path: str, runs: int = 3) -> Dict[str, Any]:
        """Measure baseline performance using the old pipeline."""
        logger.info("Measuring baseline performance...")

        results = []
        for run in range(runs):
            logger.info(f"Baseline run {run + 1}/{runs}")

            start_time = time.time()
            start_memory = self.performance_optimizer.get_memory_usage()['rss_mb']

            try:
                # Use the old function-based pipeline
                repo_root = discover_repository_root(repo_path)
                file_list = get_canonical_file_list(repo_root)
                if not isinstance(file_list, list):
                    file_list = []

                initial_memory = self.performance_optimizer.get_memory_usage()
                result = _execute_standard_pipeline(repo_path, repo_root, file_list, start_time, initial_memory, {})

                end_time = time.time()
                end_memory = self.performance_optimizer.get_memory_usage()['rss_mb']

                results.append({
                    'success': True,
                    'total_time': end_time - start_time,
                    'memory_usage_mb': end_memory - start_memory,
                    'peak_memory_mb': max(start_memory, end_memory)
                })

            except Exception as e:
                end_time = time.time()
                results.append({
                    'success': False,
                    'total_time': end_time - start_time,
                    'error': str(e)
                })

        return self._aggregate_results(results)

    def measure_optimized_performance(self, repo_path: str, runs: int = 3) -> Dict[str, Any]:
        """Measure optimized performance using the new pipeline."""
        logger.info("Measuring optimized performance...")

        results = []
        for run in range(runs):
            logger.info(f"Optimized run {run + 1}/{runs}")

            # Create analysis request
            request = AnalysisRequest(
                repository_path=repo_path,
                enable_caching=True,
                enable_profiling=True
            )

            # Create pipeline
            pipeline = OptimizedAnalysisPipeline()

            start_time = time.time()
            start_memory = self.performance_optimizer.get_memory_usage()['rss_mb']

            try:
                result = pipeline.execute(request)

                end_time = time.time()
                end_memory = self.performance_optimizer.get_memory_usage()['rss_mb']

                results.append({
                    'success': result.success,
                    'total_time': end_time - start_time,
                    'memory_usage_mb': end_memory - start_memory,
                    'peak_memory_mb': max(start_memory, end_memory),
                    'cache_hits': len(result.performance_metrics.get('cache_hits', []))
                })

            except Exception as e:
                end_time = time.time()
                results.append({
                    'success': False,
                    'total_time': end_time - start_time,
                    'error': str(e)
                })

        return self._aggregate_results(results)

    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate benchmark results."""
        successful_runs = [r for r in results if r['success']]

        if not successful_runs:
            return {
                'success_rate': 0.0,
                'avg_time': float('inf'),
                'avg_memory': float('inf'),
                'time_stddev': 0.0,
                'memory_stddev': 0.0
            }

        times = [r['total_time'] for r in successful_runs]
        memories = [r['memory_usage_mb'] for r in successful_runs]

        return {
            'success_rate': len(successful_runs) / len(results),
            'avg_time': statistics.mean(times),
            'avg_memory': statistics.mean(memories),
            'time_stddev': statistics.stdev(times) if len(times) > 1 else 0.0,
            'memory_stddev': statistics.stdev(memories) if len(memories) > 1 else 0.0,
            'runs': len(results)
        }

    def run_benchmark(self, repo_size: str = "medium") -> Dict[str, Any]:
        """Run complete benchmark comparing baseline vs optimized."""
        logger.info(f"Starting resource optimization benchmark with {repo_size} repository")

        # Create test repository
        repo_path = self.create_test_repository(repo_size)
        logger.info(f"Created test repository at {repo_path}")

        try:
            # Measure baseline
            baseline = self.measure_baseline_performance(repo_path)

            # Clear any caches between runs
            from src.core.pipeline.analysis import file_cache, analysis_cache
            file_cache.clear()
            analysis_cache.clear()

            # Measure optimized
            optimized = self.measure_optimized_performance(repo_path)

            # Calculate improvements
            improvements = self._calculate_improvements(baseline, optimized)

            results = {
                'repository_size': repo_size,
                'file_count': len(list(Path(repo_path).rglob('*'))),
                'baseline': baseline,
                'optimized': optimized,
                'improvements': improvements,
                'timestamp': time.time()
            }

            self._print_results(results)
            return results

        finally:
            # Cleanup
            import shutil
            shutil.rmtree(repo_path)

    def _calculate_improvements(self, baseline: Dict[str, Any], optimized: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance improvements."""
        improvements = {}

        if baseline['avg_time'] > 0 and optimized['avg_time'] > 0:
            time_improvement = (baseline['avg_time'] - optimized['avg_time']) / baseline['avg_time'] * 100
            improvements['time_percent'] = time_improvement
            improvements['time_reduction'] = baseline['avg_time'] - optimized['avg_time']

        if baseline['avg_memory'] > 0 and optimized['avg_memory'] > 0:
            memory_improvement = (baseline['avg_memory'] - optimized['avg_memory']) / baseline['avg_memory'] * 100
            improvements['memory_percent'] = memory_improvement
            improvements['memory_reduction'] = baseline['avg_memory'] - optimized['avg_memory']

        # Check if we meet the 20% target
        improvements['meets_target'] = (
            improvements.get('time_percent', 0) >= 20 or
            improvements.get('memory_percent', 0) >= 20
        )

        return improvements

    def _print_results(self, results: Dict[str, Any]):
        """Print benchmark results."""
        print("\n" + "="*60)
        print("RESOURCE OPTIMIZATION BENCHMARK RESULTS")
        print("="*60)

        print(f"Repository Size: {results['repository_size']}")
        print(f"File Count: {results['file_count']}")

        baseline = results['baseline']
        optimized = results['optimized']
        improvements = results['improvements']

        print("\nBASELINE PERFORMANCE:")
        print(f"- Average Time: {baseline['avg_time']:.3f}s")
        print(f"- Average Memory: {baseline['avg_memory']:.1f}MB")
        print(f"- Success Rate: {baseline['success_rate']*100:.1f}%")

        print("\nOPTIMIZED PERFORMANCE:")
        print(f"- Average Time: {optimized['avg_time']:.3f}s")
        print(f"- Average Memory: {optimized['avg_memory']:.1f}MB")
        print(f"- Success Rate: {optimized['success_rate']*100:.1f}%")

        print("\nIMPROVEMENTS:")
        if 'time_percent' in improvements:
            print(f"- Time Reduction: {improvements['time_percent']:.1f}% ({improvements['time_reduction']:.3f}s)")
        if 'memory_percent' in improvements:
            print(f"- Memory Reduction: {improvements['memory_percent']:.1f}% ({improvements['memory_reduction']:.1f}MB)")

        target_status = "✓ MET" if improvements.get('meets_target', False) else "✗ NOT MET"
        print(f"\nEFF-031 TARGET (20%+ reduction): {target_status}")

        print("="*60)

def main():
    """Main benchmark execution."""
    benchmark = ResourceBenchmark()

    # Run benchmarks for different repository sizes
    sizes = ["small", "medium", "large"]

    all_results = {}
    for size in sizes:
        try:
            result = benchmark.run_benchmark(size)
            all_results[size] = result
        except Exception as e:
            logger.error(f"Benchmark failed for {size} repository: {e}")
            all_results[size] = {'error': str(e)}

    # Summary
    print("\n" + "="*60)
    print("BENCHMARK SUMMARY")
    print("="*60)

    targets_met = 0
    for size, result in all_results.items():
        if 'error' in result:
            print(f"{size.upper()}: ERROR - {result['error']}")
        else:
            improvements = result['improvements']
            target_met = improvements.get('meets_target', False)
            if target_met:
                targets_met += 1
            status = "✓ TARGET MET" if target_met else "✗ TARGET NOT MET"
            time_imp = improvements.get('time_percent', 0)
            mem_imp = improvements.get('memory_percent', 0)
            print(f"{size.upper()}: {status} (Time: {time_imp:.1f}%, Memory: {mem_imp:.1f}%)")

    print(f"\nOVERALL: {targets_met}/{len(sizes)} repository sizes met the 20%+ optimization target")

if __name__ == "__main__":
    main()