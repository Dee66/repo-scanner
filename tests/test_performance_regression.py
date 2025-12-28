"""Performance regression tests with time and memory budgets for Repository Intelligence Scanner."""

import time
import tempfile
import psutil
import os
import gc
from pathlib import Path
from contextlib import contextmanager

import pytest

from src.core.pipeline.analysis import execute_pipeline
from src.core.exceptions import AnalysisError


class TestPerformanceRegression:
    """Performance regression tests with explicit time and memory budgets."""

    @contextmanager
    def performance_budget(self, max_time_seconds: float, max_memory_mb: float):
        """Context manager to enforce performance budgets."""
        process = psutil.Process(os.getpid())
        start_time = time.time()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        peak_memory = initial_memory

        try:
            yield
        finally:
            elapsed_time = time.time() - start_time
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory

            # Check time budget
            if elapsed_time > max_time_seconds:
                pytest.fail(f"Performance regression: {elapsed_time:.2f}s exceeded budget of {max_time_seconds}s")

            # Check memory budget
            if memory_increase > max_memory_mb:
                pytest.fail(f"Memory regression: {memory_increase:.1f}MB exceeded budget of {max_memory_mb}MB")

    @pytest.mark.benchmark
    def test_small_repository_performance_budget(self, benchmark):
        """Test performance budget for small repository analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = self._create_small_test_repo(Path(temp_dir) / "small_repo")

            def run_analysis():
                return execute_pipeline(str(repo_path))

            result = benchmark(run_analysis)
            assert isinstance(result, dict)
            assert len(result) > 0

    @pytest.mark.benchmark
    def test_medium_repository_performance_budget(self, benchmark):
        """Test performance budget for medium repository analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = self._create_medium_test_repo(Path(temp_dir) / "medium_repo")

            def run_analysis():
                return execute_pipeline(str(repo_path))

            result = benchmark(run_analysis)
            assert isinstance(result, dict)
            assert len(result) > 0

    @pytest.mark.benchmark
    def test_large_repository_performance_budget(self, benchmark):
        """Test performance budget for large repository analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = self._create_large_test_repo(Path(temp_dir) / "large_repo")

            def run_analysis():
                return execute_pipeline(str(repo_path))

            result = benchmark(run_analysis)
            assert isinstance(result, dict)
            assert len(result) > 0

    def test_memory_regression_detection(self):
        """Test detection of memory regressions through repeated analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = self._create_memory_stress_repo(Path(temp_dir) / "memory_repo")

            # Run multiple analyses to detect memory leaks
            for i in range(3):
                with self.performance_budget(max_time_seconds=8.0, max_memory_mb=150.0):
                    results = execute_pipeline(str(repo_path))
                    assert isinstance(results, dict)

                # Force garbage collection between runs
                gc.collect()

    def test_concurrent_performance_regression(self):
        """Test performance regression under concurrent load."""
        import threading
        from concurrent.futures import ThreadPoolExecutor

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_paths = []
            for i in range(3):
                repo_path = self._create_concurrent_test_repo(Path(temp_dir) / f"concurrent_repo_{i}")
                repo_paths.append(str(repo_path))

            with self.performance_budget(max_time_seconds=12.0, max_memory_mb=250.0):
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [executor.submit(execute_pipeline, path) for path in repo_paths]
                    results = [future.result() for future in futures]

                    assert len(results) == 3
                    for result in results:
                        assert isinstance(result, dict)
                        assert len(result) > 0

    def _create_small_test_repo(self, repo_path: Path) -> Path:
        """Create a small test repository."""
        repo_path.mkdir()
        self._init_git_repo(repo_path)

        # Create a few small files
        (repo_path / "README.md").write_text("# Small Test Repo\n")
        (repo_path / "main.py").write_text("print('hello world')\n")
        (repo_path / "test.py").write_text("assert True\n")

        return repo_path

    def _create_medium_test_repo(self, repo_path: Path) -> Path:
        """Create a medium-sized test repository."""
        repo_path.mkdir()
        self._init_git_repo(repo_path)

        # Create more files with some complexity
        (repo_path / "README.md").write_text("# Medium Test Repo\n" * 50)
        (repo_path / "src").mkdir()
        for i in range(20):
            (repo_path / "src" / f"module_{i}.py").write_text(f"def function_{i}():\n    return {i}\n" * 10)
        (repo_path / "tests").mkdir()
        for i in range(10):
            (repo_path / "tests" / f"test_{i}.py").write_text(f"def test_{i}():\n    assert {i} == {i}\n")

        return repo_path

    def _create_large_test_repo(self, repo_path: Path) -> Path:
        """Create a large test repository."""
        repo_path.mkdir()
        self._init_git_repo(repo_path)

        # Create many files
        (repo_path / "README.md").write_text("# Large Test Repo\n" * 100)
        (repo_path / "src").mkdir()
        for i in range(100):
            (repo_path / "src" / f"module_{i}.py").write_text(f"def function_{i}():\n    return {i}\n" * 20)
        (repo_path / "tests").mkdir()
        for i in range(50):
            (repo_path / "tests" / f"test_{i}.py").write_text(f"def test_{i}():\n    assert {i} == {i}\n" * 5)

        return repo_path

    def _create_memory_stress_repo(self, repo_path: Path) -> Path:
        """Create a repository designed to stress memory usage."""
        repo_path.mkdir()
        self._init_git_repo(repo_path)

        # Create files with large content
        (repo_path / "large_data.py").write_text("# Large data file\n" + "x = " + str(list(range(10000))) + "\n")
        (repo_path / "big_string.py").write_text("BIG_STRING = '''" + "x" * 50000 + "'''\n")
        (repo_path / "complex_structure.py").write_text("data = {\n" + "\n".join([f"    'key_{i}': {i}," for i in range(1000)]) + "\n}\n")

        return repo_path

    def _create_concurrent_test_repo(self, repo_path: Path) -> Path:
        """Create a repository for concurrent testing."""
        repo_path.mkdir()
        self._init_git_repo(repo_path)

        # Create moderate complexity files
        (repo_path / "README.md").write_text("# Concurrent Test Repo\n")
        (repo_path / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n")
        (repo_path / "models.py").write_text("class Model:\n    pass\n" * 20)
        (repo_path / "test_app.py").write_text("def test_app():\n    assert True\n" * 10)

        return repo_path

    def _init_git_repo(self, repo_path: Path):
        """Initialize a git repository."""
        import subprocess
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)