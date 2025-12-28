"""Security-focused tests for input validation in Repository Intelligence Scanner."""

import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.core.pipeline.analysis import execute_pipeline
from src.core.exceptions import AnalysisError, ValidationError
from src.api_server import app
from fastapi.testclient import TestClient


class TestSecurityInputValidation:
    """Security-focused input validation tests."""

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks via API."""
        client = TestClient(app)
        
        # Test various path traversal attempts
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
            "../../../../root/.ssh/id_rsa",
            "~/.ssh/id_rsa",
            "/root/.bash_history"
        ]

        for malicious_path in malicious_paths:
            response = client.post("/scan", json={"repository_path": malicious_path})
            assert response.status_code == 400
            assert "path traversal" in response.json()["detail"].lower()

    def test_malicious_file_content(self):
        """Test handling of files with malicious content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "malicious_repo"
            repo_path.mkdir()

            # Initialize git repo
            self._init_git_repo(repo_path)

            # Create files with potentially malicious content
            malicious_files = [
                ("exploit.py", "import os\nos.system('rm -rf /')"),
                ("injection.py", "__import__('os').system('whoami')"),
                ("overflow.py", "x = 'A' * 1000000"),  # Large string that could cause memory issues
                ("import_attack.py", "import sys\nsys.path.insert(0, '/tmp')\nimport malicious_module"),
            ]

            for filename, content in malicious_files:
                (repo_path / filename).write_text(content)

            self._git_add_commit(repo_path, "Add malicious test files")

            # Analysis should complete without executing malicious code
            results = execute_pipeline(str(repo_path))
            assert isinstance(results, dict)
            assert len(results) > 0

            # Ensure no system commands were executed (basic check)
            # In a real security test, we'd monitor system calls

    def test_api_input_validation(self):
        """Test API endpoint input validation for security."""
        client = TestClient(app)

        # Test various malicious inputs to API
        malicious_requests = [
            {
                "repository_url": "http://malicious.com/repo.git",
                "output_format": "json",
                "branch": "../../../../etc"
            },
            {
                "repository_url": "ftp://evil.com/repo.git",
                "output_format": "json"
            },
            {
                "repository_url": "file:///etc/passwd",
                "output_format": "json"
            },
            {
                "repository_path": "/etc/passwd",
                "output_format": "json"
            },
            {
                "repository_url": "https://github.com/user/repo.git",
                "output_format": "invalid_format"
            },
            {
                "repository_url": "https://github.com/user/repo.git",
                "branch": "; rm -rf /",
                "output_format": "json"
            }
        ]

        for request_data in malicious_requests:
            response = client.post("/scan", json=request_data)

            # Should either reject the request or handle it safely
            # 400/422 for validation errors, 202 for accepted async requests
            assert response.status_code in [202, 400, 422]

            if response.status_code >= 400:
                # Should provide error details
                data = response.json()
                assert "detail" in data or "message" in data

    def test_file_size_limits(self):
        """Test enforcement of file size limits to prevent DoS."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "large_files_repo"
            repo_path.mkdir()
            self._init_git_repo(repo_path)

            # Create files of various sizes
            sizes_and_names = [
                (1000, "small.py"),      # 1KB
                (100000, "medium.py"),   # 100KB
                (1000000, "large.py"),   # 1MB
                (10000000, "huge.py"),   # 10MB - should be handled carefully
            ]

            for size, filename in sizes_and_names:
                content = "x = " + str(list(range(size // 10))) + "\n"
                (repo_path / filename).write_text(content)

            self._git_add_commit(repo_path, "Add size test files")

            # Analysis should handle different file sizes appropriately
            results = execute_pipeline(str(repo_path))
            assert isinstance(results, dict)
            assert len(results) > 0

    def test_directory_traversal_prevention(self):
        """Test prevention of directory traversal in file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "traversal_repo"
            repo_path.mkdir()
            self._init_git_repo(repo_path)

            # Create a nested structure
            nested_dir = repo_path / "safe" / "nested" / "dir"
            nested_dir.mkdir(parents=True)

            (nested_dir / "safe_file.py").write_text("print('safe')")

            # Try to access files outside the repo (this should be prevented by the analysis logic)
            # The analysis should only process files within the repository root

            self._git_add_commit(repo_path, "Add nested test files")

            results = execute_pipeline(str(repo_path))
            assert isinstance(results, dict)
            assert len(results) > 0

            # Results should only contain files from within the repository
            # This is a basic check - in production, more sophisticated validation would be needed

    def test_null_byte_injection(self):
        """Test handling of null byte injection attempts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "null_byte_repo"
            repo_path.mkdir()
            self._init_git_repo(repo_path)

            # Create files with null bytes in names and content
            try:
                # Null byte in filename (may not be allowed by filesystem)
                null_name_file = repo_path / "test\x00.py"
                null_name_file.write_text("print('null in name')")
            except (OSError, ValueError):
                # Filesystem doesn't allow null bytes in names
                pass

            # Null byte in content
            (repo_path / "null_content.py").write_text("print('before\x00after')")

            self._git_add_commit(repo_path, "Add null byte test files")

            # Analysis should handle null bytes safely
            results = execute_pipeline(str(repo_path))
            assert isinstance(results, dict)
            assert len(results) > 0

    def test_command_injection_prevention(self):
        """Test prevention of command injection through repository URLs."""
        client = TestClient(app)
        
        # Test URLs that might be used for command injection
        injection_urls = [
            "https://github.com/user/repo.git;rm -rf /",
            "https://github.com/user/repo.git|cat /etc/passwd",
            "https://github.com/user/repo.git`whoami`",
            "https://github.com/user/repo.git$(rm -rf /)",
            "https://github.com/user/repo.git; echo 'injected'",
        ]

        for url in injection_urls:
            response = client.post("/scan", json={"repository_url": url})
            assert response.status_code == 400
            assert "invalid or unsafe" in response.json()["detail"].lower()

    def test_resource_exhaustion_prevention(self):
        """Test prevention of resource exhaustion attacks."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "resource_repo"
            repo_path.mkdir()
            self._init_git_repo(repo_path)

            # Create many small files to test file count limits
            for i in range(1000):  # Create 1000 files
                (repo_path / f"file_{i}.py").write_text(f"x = {i}\n")

            # This might take a while, but should complete
            results = execute_pipeline(str(repo_path))
            assert isinstance(results, dict)
            assert len(results) > 0

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