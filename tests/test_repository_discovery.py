"""Tests for repository discovery functionality."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from src.core.pipeline.repository_discovery import discover_repository_root, get_canonical_file_list


def test_discover_repository_root_git(tmp_path):
    """Test repository root discovery with git repository."""
    # Create a git repository
    repo_dir = tmp_path / "git_repo"
    repo_dir.mkdir()
    
    # Initialize git
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    
    # Create files
    (repo_dir / "file1.txt").write_text("content1")
    (repo_dir / "subdir").mkdir()
    (repo_dir / "subdir" / "file2.txt").write_text("content2")
    
    # Test from root
    root = discover_repository_root(str(repo_dir))
    assert root == str(repo_dir)
    
    # Test from subdirectory
    root_from_sub = discover_repository_root(str(repo_dir / "subdir"))
    assert root_from_sub == str(repo_dir)


def test_discover_repository_root_non_git(tmp_path):
    """Test repository root discovery without git."""
    # Create a simple directory
    repo_dir = tmp_path / "simple_repo"
    repo_dir.mkdir()
    (repo_dir / "file1.txt").write_text("content1")
    
    # Should return the provided path
    root = discover_repository_root(str(repo_dir))
    assert root == str(repo_dir)


def test_get_canonical_file_list(tmp_path):
    """Test canonical file list generation."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    # Create files with different names to test sorting
    files = ["zebra.txt", "alpha.txt", "beta.txt"]
    for filename in files:
        (repo_dir / filename).write_text(f"content of {filename}")
    
    # Create subdirectory with files
    subdir = repo_dir / "subdir"
    subdir.mkdir()
    (subdir / "gamma.txt").write_text("gamma content")
    
    file_list = get_canonical_file_list(str(repo_dir))
    
    # Should be sorted bytewise - check that filenames appear in correct order
    filenames = [Path(f).name for f in file_list]
    expected_filenames = ["alpha.txt", "beta.txt", "gamma.txt", "zebra.txt"]
    assert filenames == expected_filenames
    
    # Check that paths are absolute
    assert all(Path(f).is_absolute() for f in file_list)


def test_get_canonical_file_list_empty(tmp_path):
    """Test canonical file list with empty directory."""
    repo_dir = tmp_path / "empty_repo"
    repo_dir.mkdir()
    
    file_list = get_canonical_file_list(str(repo_dir))
    assert file_list == []


def test_get_canonical_file_list_nested(tmp_path):
    """Test canonical file list with deeply nested structure."""
    repo_dir = tmp_path / "nested_repo"
    repo_dir.mkdir()
    
    # Create nested structure
    (repo_dir / "a").mkdir()
    (repo_dir / "a" / "b").mkdir()
    (repo_dir / "a" / "b" / "c").mkdir()
    (repo_dir / "a" / "b" / "c" / "deep.txt").write_text("deep")
    (repo_dir / "top.txt").write_text("top")
    
    file_list = get_canonical_file_list(str(repo_dir))
    
    # Check filenames in correct order
    filenames = [str(Path(f).relative_to(repo_dir)) for f in file_list]
    expected = ["a/b/c/deep.txt", "top.txt"]
    assert filenames == expected


def test_discover_repository_root_invalid_path():
    """Test repository root discovery with invalid path."""
    from src.core.exceptions import RepositoryDiscoveryError
    import pytest
    
    with pytest.raises(RepositoryDiscoveryError):
        discover_repository_root("/nonexistent/path")


def test_get_canonical_file_list_invalid_path():
    """Test canonical file list with invalid path."""
    result = get_canonical_file_list("/nonexistent/path")
    assert result == []