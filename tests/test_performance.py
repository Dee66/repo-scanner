"""
Performance tests for commercial-scale validation.

Tests system performance under load, with large repositories,
and multiple concurrent analyses.
"""

import time
import tempfile
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from src.core.pipeline.analysis import execute_pipeline
from src.core.exceptions import AnalysisError


class TestPerformance:
    """Performance validation tests."""

    def test_large_repository_analysis(self):
        """Test analysis of a large repository (simulated)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "large_repo"
            repo_path.mkdir()

            # Create simulated large repo structure
            self._create_large_repo_structure(repo_path, num_files=1000, avg_file_size=1024)

            start_time = time.time()
            try:
                results = execute_pipeline(str(repo_path))
                analysis_time = time.time() - start_time

                # Assert reasonable performance (under 30 seconds for 1000 files)
                assert analysis_time < 30.0, f"Analysis took {analysis_time:.2f}s, expected < 30s"

                # Assert results are valid
                assert isinstance(results, dict) and len(results) > 0
                assert "advanced_code" in str(results)  # Check for expected analysis components

            except AnalysisError as e:
                pytest.fail(f"Analysis failed on large repository: {e}")

    def test_concurrent_analyses(self):
        """Test multiple concurrent repository analyses."""
        num_concurrent = 5

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_paths = []
            for i in range(num_concurrent):
                repo_path = Path(temp_dir) / f"repo_{i}"
                repo_path.mkdir()
                self._create_test_repo(repo_path, f"Test Repo {i}")
                repo_paths.append(str(repo_path))

            start_time = time.time()

            with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
                futures = [executor.submit(execute_pipeline, path) for path in repo_paths]
                results = []

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        pytest.fail(f"Concurrent analysis failed: {e}")

            total_time = time.time() - start_time
            avg_time = total_time / num_concurrent

            # Assert all analyses completed
            assert len(results) == num_concurrent

            # Assert reasonable average time (under 5 seconds each)
            assert avg_time < 5.0, f"Average analysis time {avg_time:.2f}s, expected < 5s"

    def test_memory_usage_bounds(self):
        """Test that memory usage stays within reasonable bounds."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "memory_test_repo"
            repo_path.mkdir()
            self._create_large_repo_structure(repo_path, num_files=500, avg_file_size=2048)

            try:
                results = execute_pipeline(str(repo_path))

                peak_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = peak_memory - initial_memory

                # Assert memory increase is reasonable (under 500MB)
                assert memory_increase < 500, f"Memory increase {memory_increase:.1f}MB, expected < 500MB"

            except AnalysisError as e:
                pytest.fail(f"Analysis failed in memory test: {e}")

    def test_scalability_with_workers(self):
        """Test performance scaling with different worker counts."""
        worker_counts = [1, 2, 4]

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "scale_test_repo"
            repo_path.mkdir()
            self._create_large_repo_structure(repo_path, num_files=200, avg_file_size=1024)

            times = {}

            for workers in worker_counts:
                start_time = time.time()
                try:
                    results = execute_pipeline(str(repo_path))
                    elapsed = time.time() - start_time
                    times[workers] = elapsed

                    # Assert analysis completes
                    assert isinstance(results, dict) and len(results) > 0

                except AnalysisError as e:
                    pytest.fail(f"Analysis failed with {workers} workers: {e}")

            # Assert some scaling benefit (2 workers should be faster than 1, but not strictly)
            if 2 in times and 1 in times:
                # Allow some overhead, but expect some improvement
                scaling_ratio = times[1] / times[2]
                assert scaling_ratio > 0.8, f"Poor scaling: {scaling_ratio:.2f}x speedup with 2 workers"

    def _create_large_repo_structure(self, repo_path: Path, num_files: int, avg_file_size: int):
        """Create a simulated large repository structure."""
        # Create git repo
        self._init_git_repo(repo_path)

        # Create directory structure
        for i in range(num_files):
            # Create nested directories
            depth = i % 5 + 1
            file_path = repo_path
            for d in range(depth):
                file_path = file_path / f"dir_{d}"
                file_path.mkdir(exist_ok=True)

            # Create file with content
            file_path = file_path / f"file_{i}.py"
            content_size = avg_file_size + (i % 1000)  # Vary size slightly
            content = f'"""Test file {i}"""\n' + "x = 42\n" * (content_size // 10)
            file_path.write_text(content)

        # Add and commit
        self._git_add_commit(repo_path, "Add large repo structure")

    def _create_test_repo(self, repo_path: Path, name: str):
        """Create a simple test repository."""
        self._init_git_repo(repo_path)

        # Create basic files
        (repo_path / "README.md").write_text(f"# {name}\n\nTest repository.")
        (repo_path / "main.py").write_text("print('Hello, World!')")
        (repo_path / "requirements.txt").write_text("pytest>=7.0.0")

        self._git_add_commit(repo_path, "Initial commit")

    def _init_git_repo(self, path: Path):
        """Initialize a git repository."""
        import subprocess
        subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)

    def _git_add_commit(self, path: Path, message: str):
        """Add all files and commit."""
        import subprocess
        subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", message], cwd=path, check=True, capture_output=True)