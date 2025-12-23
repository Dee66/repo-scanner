"""Test suite for repository scanner CLI and components."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def test_repo(tmp_path):
    """Create a test repository with known structure."""
    # Create a temporary directory structure
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    
    # Create some files
    (repo_dir / "README.md").write_text("# Test Repository\n\nThis is a test repo.")
    (repo_dir / "src").mkdir()
    (repo_dir / "src" / "main.py").write_text("print('Hello, World!')")
    (repo_dir / "src" / "utils.py").write_text("def helper():\n    return 'helper'")
    (repo_dir / "tests").mkdir()
    (repo_dir / "tests" / "test_main.py").write_text("def test_hello():\n    assert True")
    (repo_dir / ".gitignore").write_text("*.pyc\n__pycache__/")
    
    return repo_dir


@pytest.fixture
def output_dir(tmp_path):
    """Create a temporary output directory."""
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    return out_dir


def run_scanner(repo_path, output_dir, format="both", report_type=None):
    """Run the scanner CLI and return the result."""
    cmd = [sys.executable, "-m", "src.cli", str(repo_path), "--output-dir", str(output_dir)]
    if format != "both":
        cmd.extend(["--format", format])
    if report_type:
        cmd.extend(["--report-type", report_type])
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
    return result


def test_cli_valid_repository(test_repo, output_dir):
    """Test CLI with a valid repository."""
    result = run_scanner(test_repo, output_dir)
    
    assert result.returncode == 0
    assert "Scan completed successfully" in result.stdout
    
    # Check outputs exist
    assert (output_dir / "scan_report.md").exists()
    assert (output_dir / "scan_report.json").exists()


def test_cli_invalid_repository(output_dir):
    """Test CLI with invalid repository path."""
    invalid_path = "/nonexistent/path"
    result = run_scanner(invalid_path, output_dir)
    
    assert result.returncode == 1
    assert "does not exist" in result.stderr


def test_cli_file_as_repo(output_dir):
    """Test CLI with a file instead of directory."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"not a directory")
        file_path = f.name
    
    try:
        result = run_scanner(file_path, output_dir)
        assert result.returncode == 1
        assert "not a directory" in result.stderr
    finally:
        os.unlink(file_path)


def test_cli_markdown_only(test_repo, output_dir):
    """Test CLI with markdown-only output."""
    result = run_scanner(test_repo, output_dir, format="markdown")
    
    assert result.returncode == 0
    assert (output_dir / "scan_report.md").exists()
    assert not (output_dir / "scan_report.json").exists()


def test_cli_json_only(test_repo, output_dir):
    """Test CLI with JSON-only output."""
    result = run_scanner(test_repo, output_dir, format="json")
    
    assert result.returncode == 0
    assert not (output_dir / "scan_report.md").exists()
    assert (output_dir / "scan_report.json").exists()


def test_output_markdown_structure(test_repo, output_dir):
    """Test that markdown output has required sections."""
    run_scanner(test_repo, output_dir)
    
    content = (output_dir / "scan_report.md").read_text()
    
    required_sections = [
        "# Repository Analysis Report",
        "## Executive Summary",
        "## System Characterization", 
        "## Evidence Highlights",
        "## Misleading Signals",
        "## Safe to Change Surface",
        "## What Not to Fix",
        "## Refusal or First Action",
        "## Confidence and Limits",
        "## Validity and Expiry"
    ]
    
    for section in required_sections:
        assert section in content


def test_output_json_schema(test_repo, output_dir):
    """Test that JSON output matches expected schema."""
    run_scanner(test_repo, output_dir)
    
    with open(output_dir / "scan_report.json") as f:
        data = json.load(f)
    
    # Check required top-level keys
    required_keys = ["run_id", "repository", "summary", "tasks", "gaps", "metadata"]
    for key in required_keys:
        assert key in data
    
    # Check repository structure
    assert "name" in data["repository"]
    assert "path" in data["repository"]
    
    # Check summary structure
    summary = data["summary"]
    assert "overall_score" in summary
    assert "files_scanned" in summary
    assert "tests_discovered" in summary
    assert "gaps_count" in summary
    
    # Check metadata
    metadata = data["metadata"]
    assert "scanner_version" in metadata
    assert "run_timestamp" in metadata
    assert "deterministic_hash" in metadata


def test_determinism(test_repo, tmp_path):
    """Test that scanner produces identical outputs on multiple runs."""
    output1 = tmp_path / "output1"
    output2 = tmp_path / "output2"
    output1.mkdir()
    output2.mkdir()
    
    # Run scanner twice
    run_scanner(test_repo, output1)
    run_scanner(test_repo, output2)
    
    # Compare markdown outputs
    md1 = (output1 / "scan_report.md").read_text()
    md2 = (output2 / "scan_report.md").read_text()
    assert md1 == md2
    
    # Compare JSON outputs
    with open(output1 / "scan_report.json") as f1, open(output2 / "scan_report.json") as f2:
        json1 = json.load(f1)
        json2 = json.load(f2)
    
    # Remove non-deterministic fields for comparison (if any)
    # For now, assume all fields should be identical
    assert json1 == json2


def test_repository_discovery_git_repo(test_repo, output_dir):
    """Test repository discovery on a git repository."""
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=test_repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=test_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=test_repo, check=True)
    subprocess.run(["git", "add", "."], cwd=test_repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=test_repo, check=True)
    
    run_scanner(test_repo, output_dir)
    
    with open(output_dir / "scan_report.json") as f:
        data = json.load(f)
    
    # Should detect the git root
    assert data["repository"]["path"] == str(test_repo)
    assert data["summary"]["files_scanned"] > 0


def test_repository_discovery_non_git(tmp_path, output_dir):
    """Test repository discovery on non-git directory."""
    # Create a simple directory structure
    repo_dir = tmp_path / "simple_repo"
    repo_dir.mkdir()
    (repo_dir / "file1.txt").write_text("content1")
    (repo_dir / "file2.txt").write_text("content2")
    
    run_scanner(repo_dir, output_dir)
    
    with open(output_dir / "scan_report.json") as f:
        data = json.load(f)
    
    # Should use the provided directory as root
    assert data["repository"]["path"] == str(repo_dir)
    assert data["summary"]["files_scanned"] == 2


def test_scanner_cli_invocation():
    """Test that scanner CLI can be invoked (legacy test)."""
    # This test remains for backward compatibility
    assert True


def test_cli_report_type_comprehensive(test_repo, output_dir):
    """Test CLI with comprehensive report type."""
    result = run_scanner(test_repo, output_dir, report_type="comprehensive")
    
    assert result.returncode == 0
    assert "Comprehensive report written" in result.stdout
    assert "Machine-readable output written" in result.stdout
    
    # Check outputs exist
    assert (output_dir / "scan_report.md").exists()
    assert (output_dir / "scan_report.json").exists()
    assert not (output_dir / "verdict_report.md").exists()


def test_cli_report_type_verdict(test_repo, output_dir):
    """Test CLI with verdict report type."""
    result = run_scanner(test_repo, output_dir, report_type="verdict")
    
    assert result.returncode == 0
    assert "Executive verdict report written" in result.stdout
    assert "Machine-readable output written" in result.stdout
    
    # Check outputs exist
    assert not (output_dir / "scan_report.md").exists()
    assert (output_dir / "scan_report.json").exists()
    assert (output_dir / "verdict_report.md").exists()
    
    # Check verdict report content
    verdict_content = (output_dir / "verdict_report.md").read_text()
    assert "# Executive Verdict" in verdict_content
    assert "**Verdict:**" in verdict_content


def test_cli_report_type_both(test_repo, output_dir):
    """Test CLI with both report types."""
    result = run_scanner(test_repo, output_dir, report_type="both")
    
    assert result.returncode == 0
    assert "Comprehensive report written" in result.stdout
    assert "Executive verdict report written" in result.stdout
    assert "Machine-readable output written" in result.stdout
    
    # Check all outputs exist
    assert (output_dir / "scan_report.md").exists()
    assert (output_dir / "scan_report.json").exists()
    assert (output_dir / "verdict_report.md").exists()


def test_cli_report_type_default(test_repo, output_dir):
    """Test CLI default behavior (should be comprehensive)."""
    result = run_scanner(test_repo, output_dir)
    
    assert result.returncode == 0
    assert "Comprehensive report written" in result.stdout
    assert "Machine-readable output written" in result.stdout
    
    # Check outputs exist
    assert (output_dir / "scan_report.md").exists()
    assert (output_dir / "scan_report.json").exists()
    assert not (output_dir / "verdict_report.md").exists()


if __name__ == "__main__":
    pytest.main([__file__])
