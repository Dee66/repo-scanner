"""Integration tests for bounty hunting functionality."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
import pytest


class TestBountyIntegration:
    """Integration tests for bounty hunting CLI and service layer."""

    @pytest.fixture
    def test_repo(self, tmp_path):
        """Create a test repository with realistic structure."""
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Create basic project structure
        (repo_dir / "README.md").write_text("""# Test Repository

A test repository for bounty hunting integration tests.

## Features
- Feature 1
- Feature 2

## Contributing
Please read CONTRIBUTING.md for details.
""")

        (repo_dir / "CONTRIBUTING.md").write_text("""# Contributing

## Pull Request Process
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit PR
""")

        (repo_dir / "src").mkdir()
        (repo_dir / "src" / "__init__.py").write_text("")
        (repo_dir / "src" / "main.py").write_text("""
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")

        (repo_dir / "tests").mkdir()
        (repo_dir / "tests" / "__init__.py").write_text("")
        (repo_dir / "tests" / "test_main.py").write_text("""
import pytest
from src.main import main

def test_main(capsys):
    main()
    captured = capsys.readouterr()
    assert "Hello, World!" in captured.out
""")

        (repo_dir / "requirements.txt").write_text("pytest>=6.0.0\n")

        # Initialize git repository
        import subprocess
        subprocess.run(['git', 'init'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_dir, check=True)

        return repo_dir

    @pytest.fixture
    def sample_bounty_data(self):
        """Sample bounty data for testing."""
        return {
            "id": "test-bounty-001",
            "title": "Add logging feature",
            "description": "Implement comprehensive logging throughout the application",
            "reward": 500,
            "requirements": [
                "Add logging configuration",
                "Implement structured logging",
                "Add log levels",
                "Create log files"
            ],
            "technologies": ["Python", "logging"],
            "difficulty": "medium"
        }

    @pytest.fixture
    def sample_solution_code(self):
        """Sample solution code data for testing."""
        return {
            "implementation": {
                "files_to_modify": ["src/main.py", "src/__init__.py"],
                "new_files": ["src/logger.py", "config/logging.yaml"],
                "test_files": ["tests/test_logging.py"]
            },
            "code_changes": [
                {
                    "file": "src/main.py",
                    "changes": "Add logging import and initialization"
                }
            ]
        }

    def run_bounty_command(self, repo_path, bounty_data, output_dir, generate_solution=False, solution_code=None):
        """Run the bounty CLI command and return result."""
        cmd = [
            sys.executable, "-m", "src.cli", "--enable-bounties", "bounty",
            str(repo_path),
            "--bounty-data", json.dumps(bounty_data),
            "--output-dir", str(output_dir)
        ]

        if generate_solution and solution_code:
            cmd.extend(["--generate-solution", "--solution-code", json.dumps(solution_code)])

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        return result

    def run_validate_command(self, output_dir):
        """Run the validate CLI command and return result."""
        cmd = [
            sys.executable, "-m", "src.cli", "--enable-bounties", "validate",
            "--output-dir", str(output_dir)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        return result

    def test_bounty_assessment_basic(self, test_repo, sample_bounty_data, tmp_path, monkeypatch):
        """Test basic bounty assessment generation."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock the entire bounty service to avoid network calls
        mock_assessment = {
            "bounty_id": "test-bounty-001",
            "assessment_timestamp": "2024-01-01T00:00:00Z",
            "viability_score": 0.85,
            "components": {
                "maintainer_profile": {
                    "maintainer_responsiveness": 0.9,
                    "contribution_patterns": "active",
                    "expertise_alignment": 0.8
                },
                "profitability_triage": {
                    "reward_to_effort_ratio": 2.5,
                    "market_demand": 0.7,
                    "competition_level": 0.3
                }
            },
            "triage_decision": {
                "decision": "ACCEPT",
                "confidence": 0.85,
                "reasoning": "High maintainer responsiveness and good reward ratio"
            }
        }
        
        from unittest.mock import MagicMock
        mock_bounty_service = MagicMock()
        mock_bounty_service.analyze_bounty_opportunity.return_value = mock_assessment
        
        def mock_bounty_service_init(*args, **kwargs):
            return mock_bounty_service
            
        monkeypatch.setattr("src.optional.bounty.bounty_service.BountyService", mock_bounty_service_init)

        result = self.run_bounty_command(test_repo, sample_bounty_data, output_dir)

        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "Bounty analysis completed successfully" in result.stdout

        # Check output files
        assessment_file = output_dir / "bounty_assessment.json"
        assert assessment_file.exists(), "Bounty assessment file should be created"

        # Validate assessment content
        with open(assessment_file) as f:
            assessment = json.load(f)

        required_keys = [
            "bounty_id", "repository_url", "assessment_timestamp",
            "overall_recommendation", "components", "risk_factors",
            "success_probability", "estimated_effort", "next_steps"
        ]

        for key in required_keys:
            assert key in assessment, f"Missing required key: {key}"

        assert assessment["bounty_id"] == sample_bounty_data["id"]
        assert "file://" in assessment["repository_url"]
        assert isinstance(assessment["success_probability"], (int, float))
        assert 0.0 <= assessment["success_probability"] <= 1.0

    def test_bounty_solution_generation(self, test_repo, sample_bounty_data, sample_solution_code, tmp_path, monkeypatch):
        """Test bounty solution generation with PR content."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Mock execute_pipeline to avoid network calls
        mock_analysis_result = {
            "governance": {
                "maintainers": [
                    {"name": "test-maintainer", "email": "test@example.com", "role": "maintainer"}
                ],
                "contribution_guidelines": True,
                "code_of_conduct": True
            },
            "complexity": {"score": 5.0},
            "quality": {"score": 8.0}
        }
        monkeypatch.setattr("src.core.pipeline.analysis.execute_pipeline", lambda path: mock_analysis_result)

        result = self.run_bounty_command(
            test_repo, sample_bounty_data, output_dir,
            generate_solution=True, solution_code=sample_solution_code
        )

        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert "Bounty analysis completed successfully" in result.stdout

        # Check output files
        assessment_file = output_dir / "bounty_assessment.json"
        solution_file = output_dir / "bounty_solution.json"
        pr_file = output_dir / "pr_content.md"

        assert assessment_file.exists(), "Bounty assessment file should be created"
        assert solution_file.exists(), "Bounty solution file should be created"
        assert pr_file.exists(), "PR content file should be created"

        # Validate solution content
        with open(solution_file) as f:
            solution = json.load(f)

        required_keys = ["bounty_id", "pr_content", "integration_plan", "generated_at", "confidence_score"]
        for key in required_keys:
            assert key in solution, f"Missing required key: {key}"

        assert solution["bounty_id"] == sample_bounty_data["id"]
        assert "title" in solution["pr_content"]
        assert "description" in solution["pr_content"]
        assert "branch_name" in solution["pr_content"]
        assert isinstance(solution["confidence_score"], (int, float))

        # Validate PR content
        pr_content = pr_file.read_text()
        assert sample_bounty_data["title"] in pr_content
        assert "## Description" in pr_content
        assert "## Checklist" in pr_content

    def test_bounty_validation(self, tmp_path):
        """Test bounty accuracy validation."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = self.run_validate_command(output_dir)

        assert result.returncode == 0, f"Validation command failed: {result.stderr}"
        assert "Validation completed successfully" in result.stdout

        # Check output files
        report_file = output_dir / "bounty_accuracy_report.md"
        metrics_file = output_dir / "bounty_accuracy_metrics.json"

        assert report_file.exists(), "Accuracy report should be created"
        assert metrics_file.exists(), "Accuracy metrics should be created"

        # Validate metrics content
        with open(metrics_file) as f:
            metrics = json.load(f)

        assert "metrics" in metrics
        assert "validation" in metrics
        assert "errors" in metrics

    def test_bounty_invalid_data(self, test_repo, tmp_path, monkeypatch):
        """Test bounty command with invalid data."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        invalid_bounty_data = {"invalid": "data"}  # Missing required fields

        # Mock execute_pipeline to avoid network calls (though it shouldn't reach here)
        mock_analysis_result = {
            "governance": {
                "maintainers": [
                    {"name": "test-maintainer", "email": "test@example.com", "role": "maintainer"}
                ],
                "contribution_guidelines": True,
                "code_of_conduct": True
            },
            "complexity": {"score": 5.0},
            "quality": {"score": 8.0}
        }
        monkeypatch.setattr("src.core.pipeline.analysis.execute_pipeline", lambda path: mock_analysis_result)

        result = self.run_bounty_command(test_repo, invalid_bounty_data, output_dir)

        # Should fail gracefully
        assert result.returncode != 0, "Command should fail with invalid data"
        assert "Bounty data missing required field" in result.stdout

    def test_bounty_missing_solution_code(self, test_repo, sample_bounty_data, tmp_path):
        """Test bounty command with generate-solution but no solution code."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        cmd = [
            sys.executable, "-m", "src.cli", "--enable-bounties", "bounty",
            str(test_repo),
            "--bounty-data", json.dumps(sample_bounty_data),
            "--output-dir", str(output_dir),
            "--generate-solution"
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        # Should fail because solution code is required with --generate-solution
        assert result.returncode != 0, "Command should fail without solution code"
        assert "Solution code is required" in result.stdout

    def test_bounty_nonexistent_repo(self, sample_bounty_data, tmp_path, monkeypatch):
        """Test bounty command with nonexistent repository."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        nonexistent_repo = tmp_path / "nonexistent"

        # Mock execute_pipeline to avoid network calls (though it shouldn't reach here)
        mock_analysis_result = {
            "governance": {
                "maintainers": [
                    {"name": "test-maintainer", "email": "test@example.com", "role": "maintainer"}
                ],
                "contribution_guidelines": True,
                "code_of_conduct": True
            },
            "complexity": {"score": 5.0},
            "quality": {"score": 8.0}
        }
        monkeypatch.setattr("src.core.pipeline.analysis.execute_pipeline", lambda path: mock_analysis_result)

        result = self.run_bounty_command(nonexistent_repo, sample_bounty_data, output_dir)

        assert result.returncode != 0, "Command should fail with nonexistent repo"
        assert "does not exist" in result.stdout

    def test_bounty_file_as_repo(self, sample_bounty_data, tmp_path, monkeypatch):
        """Test bounty command with file instead of directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Create a file instead of directory
        file_repo = tmp_path / "file_repo"
        file_repo.write_text("not a directory")

        # Mock execute_pipeline to avoid network calls (though it shouldn't reach here)
        mock_analysis_result = {
            "governance": {
                "maintainers": [
                    {"name": "test-maintainer", "email": "test@example.com", "role": "maintainer"}
                ],
                "contribution_guidelines": True,
                "code_of_conduct": True
            },
            "complexity": {"score": 5.0},
            "quality": {"score": 8.0}
        }
        monkeypatch.setattr("src.core.pipeline.analysis.execute_pipeline", lambda path: mock_analysis_result)

        result = self.run_bounty_command(file_repo, sample_bounty_data, output_dir)

        assert result.returncode != 0, "Command should fail with file as repo"
        assert "not a directory" in result.stdout

    def test_fetch_bounties_method(self, monkeypatch):
        """Test the fetch_bounties method with mocked API."""
        from src.optional.bounty.bounty_service import BountyService

        # Mock the requests.post call
        mock_response = {
            "result": {
                "data": {
                    "items": [
                        {
                            "task": {
                                "repo_name": "test/repo",
                                "number": 1,
                                "title": "Test Bounty"
                            },
                            "description": "A test bounty",
                            "reward": {"amount": 100},
                            "status": "active",
                            "created_at": "2024-01-01T00:00:00Z"
                        }
                    ],
                    "next_cursor": None
                }
            }
        }

        def mock_post(url, json=None, **kwargs):
            class MockResponse:
                def __init__(self, json_data):
                    self.json_data = json_data
                def raise_for_status(self):
                    pass
                def json(self):
                    return self.json_data
            return MockResponse(mock_response)

        monkeypatch.setattr("src.optional.bounty.bounty_service.requests.post", mock_post)

        service = BountyService()
        bounties = service.fetch_bounties("testorg", limit=1, status="active")

        assert len(bounties) == 1
        bounty = bounties[0]
        assert bounty["id"] == "testorg/test/repo#1"
        assert bounty["title"] == "Test Bounty"
        assert bounty["description"] == "A test bounty"
        assert bounty["repo_name"] == "test/repo"

    def test_fetch_github_issues_method(self, monkeypatch):
        """Test the fetch_github_issues method with mocked API."""
        from src.optional.bounty.bounty_service import BountyService

        # Mock the requests.get call
        mock_response = [
            {
                "number": 1,
                "title": "Test Issue",
                "body": "A test issue",
                "created_at": "2024-01-01T00:00:00Z",
                "html_url": "https://github.com/test/repo/issues/1"
            }
        ]

        def mock_get(url, params=None, **kwargs):
            class MockResponse:
                def __init__(self, json_data):
                    self.json_data = json_data
                def raise_for_status(self):
                    pass
                def json(self):
                    return self.json_data
            return MockResponse(mock_response)

        monkeypatch.setattr("src.optional.bounty.bounty_service.requests.get", mock_get)

        service = BountyService()
        issues = service.fetch_github_issues("test/repo", labels="bounty", limit=1)

        assert len(issues) == 1
        issue = issues[0]
        assert issue["id"] == "test/repo#1"
        assert issue["title"] == "Test Issue"
        assert issue["description"] == "A test issue"
        assert issue["repo_name"] == "test/repo"