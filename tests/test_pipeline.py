"""Tests for analysis pipeline."""

import tempfile
from pathlib import Path

from src.core.pipeline.analysis import execute_pipeline


def test_execute_pipeline_basic(tmp_path):
    """Test basic pipeline execution."""
    # Create a simple test repository
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    (repo_dir / "file1.txt").write_text("content1")
    (repo_dir / "file2.txt").write_text("content2")
    
    result = execute_pipeline(str(repo_dir))
    
    assert isinstance(result, dict)
    assert "repository_root" in result
    assert "files" in result
    assert "status" in result
    
    assert result["repository_root"] == str(repo_dir)
    assert len(result["files"]) == 2
    assert any("file1.txt" in f for f in result["files"])
    assert any("file2.txt" in f for f in result["files"])


def test_execute_pipeline_git_repo(tmp_path):
    """Test pipeline execution on git repository."""
    import subprocess
    
    # Create and initialize git repo
    repo_dir = tmp_path / "git_repo"
    repo_dir.mkdir()
    
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    
    # Create files
    (repo_dir / "README.md").write_text("# Test")
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "main.py").write_text("print('hello')")
    
    result = execute_pipeline(str(repo_dir))
    
    assert result["repository_root"] == str(repo_dir)
    # Git repo includes .git files, so more than 3
    assert len(result["files"]) >= 3
    assert any("README.md" in f for f in result["files"])
    assert any("src/main.py" in f for f in result["files"])


def test_execute_pipeline_empty_repo(tmp_path):
    """Test pipeline execution on empty repository."""
    repo_dir = tmp_path / "empty_repo"
    repo_dir.mkdir()
    
    result = execute_pipeline(str(repo_dir))
    
    assert result["repository_root"] == str(repo_dir)
    assert result["files"] == []
    assert result["status"] == "standard_pipeline_complete"


def test_execute_pipeline_nested_structure(tmp_path):
    """Test pipeline execution with nested directory structure."""
    repo_dir = tmp_path / "nested_repo"
    repo_dir.mkdir()
    
    # Create nested structure
    (repo_dir / "docs").mkdir()
    (repo_dir / "docs" / "readme.txt").write_text("docs")
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "code.py").write_text("code")
    (repo_dir / "tests").mkdir()
    (repo_dir / "tests" / "test.py").write_text("test")
    
    result = execute_pipeline(str(repo_dir))
    
    assert result["repository_root"] == str(repo_dir)
    assert len(result["files"]) == 3
    assert any("docs/readme.txt" in f for f in result["files"])
    assert any("src/code.py" in f for f in result["files"])
    assert any("tests/test.py" in f for f in result["files"])


def test_execute_pipeline_file_sorting(tmp_path):
    """Test that pipeline returns deterministically sorted files."""
    repo_dir = tmp_path / "sort_repo"
    repo_dir.mkdir()
    
    # Create files in non-alphabetical order
    files = ["z.txt", "a.txt", "m.txt"]
    for filename in files:
        (repo_dir / filename).write_text(f"content of {filename}")
    
    result = execute_pipeline(str(repo_dir))
    
    # Files should be sorted - extract filenames from absolute paths
    filenames = [Path(f).name for f in result["files"]]
    assert filenames == ["a.txt", "m.txt", "z.txt"]


def test_execute_pipeline_subdirectory_start(tmp_path):
    """Test pipeline execution starting from subdirectory."""
    repo_dir = tmp_path / "main_repo"
    repo_dir.mkdir()
    
    (repo_dir / "root_file.txt").write_text("root")
    sub_dir = repo_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "sub_file.txt").write_text("sub")
    
    # Start from subdirectory
    result = execute_pipeline(str(sub_dir))
    
    # For non-git repos, uses the provided path as root
    assert result["repository_root"] == str(sub_dir)
    assert len(result["files"]) == 1
    assert any("sub_file.txt" in f for f in result["files"])


def test_execute_pipeline_resource_limits_and_degradation(tmp_path, monkeypatch):
    """Test resource limits and graceful degradation."""
    from src.core.resource_manager import get_resource_manager, DegradationLevel

    # Create a test repository
    repo_dir = tmp_path / "resource_test_repo"
    repo_dir.mkdir()
    (repo_dir / "test.py").write_text("print('hello world')")

    # Get resource manager and directly set degradation level
    resource_manager = get_resource_manager()
    resource_manager.degradation_level = DegradationLevel.LIGHT  # Simulate light degradation

    # Execute pipeline
    result = execute_pipeline(str(repo_dir))

    # Verify pipeline completed successfully
    assert result["status"] == "standard_pipeline_complete"
    assert "performance_metrics" in result
    assert "degradation_config" in result["performance_metrics"]

    # Check that degradation config reflects light degradation
    degradation_config = result["performance_metrics"]["degradation_config"]
    assert degradation_config["max_threads"] == 2  # Reduced from 4
    assert degradation_config["batch_size"] == 25  # Reduced from 50
    assert not degradation_config["skip_optional_stages"]  # Not yet skipping

    # Verify optional stages were still executed (light degradation)
    assert "code_duplication_analysis" in result
    assert "api_analysis" in result
    assert result["code_duplication_analysis"] != {"status": "skipped_due_to_degradation"}
    assert result["api_analysis"] != {"status": "skipped_due_to_degradation"}


def test_execute_pipeline_critical_degradation(tmp_path, monkeypatch):
    """Test critical resource degradation with stage skipping."""
    from src.core.resource_manager import get_resource_manager, DegradationLevel

    # Create a test repository
    repo_dir = tmp_path / "critical_test_repo"
    repo_dir.mkdir()
    (repo_dir / "test.py").write_text("print('hello world')")

    # Get resource manager and directly set critical degradation level
    resource_manager = get_resource_manager()
    resource_manager.degradation_level = DegradationLevel.CRITICAL  # Simulate critical degradation

    # Execute pipeline
    result = execute_pipeline(str(repo_dir))

    # Verify pipeline completed successfully despite critical resource usage
    assert result["status"] == "standard_pipeline_complete"

    # Check that degradation config reflects critical degradation
    degradation_config = result["performance_metrics"]["degradation_config"]
    assert degradation_config["max_threads"] == 1  # Minimized
    assert degradation_config["batch_size"] == 5   # Minimized
    assert degradation_config["skip_optional_stages"]  # Should skip optional stages

    # Verify optional stages were skipped
    assert result["code_duplication_analysis"] == {"status": "skipped_due_to_degradation"}
    assert result["api_analysis"] == {"status": "skipped_due_to_degradation"}