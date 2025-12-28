"""Test environment provisioning and teardown."""

import os
import pytest


def test_environment_provisioning():
    """Test that test environment is properly provisioned."""
    assert os.environ.get('PYTEST_RUNNING') == '1'
    assert os.environ.get('TEST_ENVIRONMENT') == '1'
    assert 'PYTHONPATH' in os.environ


def test_working_directory():
    """Test that working directory is set correctly."""
    from pathlib import Path
    project_root = Path(__file__).parent.parent
    assert Path.cwd() == project_root or str(project_root) in os.environ.get('PYTHONPATH', '')


def test_dependencies_available():
    """Test that required dependencies are available."""
    import git
    import yaml
    # These should not raise ImportError
    assert git is not None
    assert yaml is not None