"""Tests for determinism verification."""

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import pytest


def create_test_repo(base_path):
    """Create a deterministic test repository."""
    repo_dir = base_path / "det_repo"
    repo_dir.mkdir()
    
    # Create files in a specific order to ensure determinism
    files = [
        ("README.md", "# Determinism Test\n\nThis repo tests determinism."),
        ("src/main.py", "def main():\n    print('Hello')\n\nif __name__ == '__main__':\n    main()"),
        ("src/utils.py", "def helper():\n    return 42"),
        ("tests/test_main.py", "def test_main():\n    assert True"),
        (".gitignore", "*.pyc\n__pycache__/\n.pytest_cache/"),
    ]
    
    for filename, content in files:
        file_path = repo_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
    
    return repo_dir


def get_file_hash(file_path):
    """Get SHA256 hash of a file."""
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def get_dir_hash(dir_path):
    """Get deterministic hash of all files in directory."""
    file_hashes = []
    for file_path in sorted(dir_path.rglob('*')):
        if file_path.is_file():
            rel_path = file_path.relative_to(dir_path)
            file_hashes.append(f"{rel_path}:{get_file_hash(file_path)}")
    
    combined = '\n'.join(file_hashes)
    return hashlib.sha256(combined.encode()).hexdigest()


def run_scanner_deterministic(repo_path, output_dir):
    """Run scanner and return hashes of outputs."""
    import sys
    from pathlib import Path
    
    cmd = [sys.executable, "-m", "src.cli", str(repo_path), "--output-dir", str(output_dir)]
    subprocess.run(cmd, check=True, capture_output=True, cwd=Path(__file__).parent.parent)
    
    md_hash = get_file_hash(output_dir / "scan_report.md")
    json_hash = get_file_hash(output_dir / "scan_report.json")
    
    return md_hash, json_hash


def test_determinism_multiple_runs(tmp_path):
    """Test that multiple runs produce identical outputs."""
    repo_dir = create_test_repo(tmp_path)
    
    # Run scanner multiple times
    hashes = []
    for i in range(3):
        output_dir = tmp_path / f"output_{i}"
        output_dir.mkdir()
        md_hash, json_hash = run_scanner_deterministic(repo_dir, output_dir)
        hashes.append((md_hash, json_hash))
    
    # All runs should produce identical hashes
    first_md, first_json = hashes[0]
    for md_hash, json_hash in hashes[1:]:
        assert md_hash == first_md, "Markdown output not deterministic"
        assert json_hash == first_json, "JSON output not deterministic"


def test_determinism_different_output_dirs(tmp_path):
    """Test determinism with different output directory names."""
    repo_dir = create_test_repo(tmp_path)
    
    # Run with different output directory names
    output1 = tmp_path / "run1"
    output2 = tmp_path / "run2"
    output1.mkdir()
    output2.mkdir()
    
    hash1_md, hash1_json = run_scanner_deterministic(repo_dir, output1)
    hash2_md, hash2_json = run_scanner_deterministic(repo_dir, output2)
    
    assert hash1_md == hash2_md, "Outputs differ with different output directories"
    assert hash1_json == hash2_json, "JSON outputs differ with different output directories"


def test_determinism_repository_content(tmp_path):
    """Test that outputs change when repository content changes."""
    repo_dir = tmp_path / "changing_repo"
    repo_dir.mkdir()
    
    # Create initial repo with different number of files
    (repo_dir / "file1.txt").write_text("initial")
    
    output1 = tmp_path / "output1"
    output1.mkdir()
    hash1_md, hash1_json = run_scanner_deterministic(repo_dir, output1)
    
    # Add another file to repository
    (repo_dir / "file2.txt").write_text("added")
    
    output2 = tmp_path / "output2"
    output2.mkdir()
    hash2_md, hash2_json = run_scanner_deterministic(repo_dir, output2)
    
    # Outputs should be different (different file count)
    assert hash1_md != hash2_md, "Outputs should change when repository changes"
    assert hash1_json != hash2_json, "JSON outputs should change when repository changes"


def test_determinism_json_canonical_sorting(tmp_path):
    """Test that JSON output uses canonical sorting."""
    repo_dir = create_test_repo(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    run_scanner_deterministic(repo_dir, output_dir)
    
    # Read JSON and check it's sorted
    with open(output_dir / "scan_report.json") as f:
        data = json.load(f)
    
    # Convert back to JSON with sorting
    sorted_json = json.dumps(data, sort_keys=True, indent=2)
    
    # Read the file content
    with open(output_dir / "scan_report.json") as f:
        file_content = f.read()
    
    # They should be identical (file should already be sorted)
    assert file_content.strip() == sorted_json.strip()


def test_determinism_no_timestamps(tmp_path):
    """Test that outputs don't contain timestamps."""
    repo_dir = create_test_repo(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    run_scanner_deterministic(repo_dir, output_dir)
    
    # Check that outputs don't contain current timestamp patterns
    md_content = (output_dir / "scan_report.md").read_text()
    json_content = (output_dir / "scan_report.json").read_text()
    
    # Should not contain actual timestamps (placeholder is used)
    assert "2025-12-23T00:00:00Z" in json_content  # Placeholder timestamp
    assert "30 days from generation" in md_content  # Placeholder in markdown
    
    # Should not contain current date/time (would indicate non-determinism)
    import datetime
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    # Allow the placeholder date but not current date if different
    if current_date != "2025-12-23":
        assert current_date not in md_content
        assert current_date not in json_content


def test_determinism_file_ordering(tmp_path):
    """Test that file lists are deterministically ordered."""
    repo_dir = tmp_path / "order_repo"
    repo_dir.mkdir()
    
    # Create files in random order
    files = ["z.txt", "a.txt", "m.txt", "b.txt"]
    for filename in files:
        (repo_dir / filename).write_text(f"content {filename}")
    
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    run_scanner_deterministic(repo_dir, output_dir)
    
    # Check JSON contains sorted files
    with open(output_dir / "scan_report.json") as f:
        data = json.load(f)
    
    files_scanned = data["summary"]["files_scanned"]
    assert files_scanned == 4
    
    # The files should be processed in sorted order internally
    # (though we can't directly check the internal file list from JSON yet)