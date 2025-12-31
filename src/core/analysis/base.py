"""
Base Analysis Components

This module defines the base classes and interfaces for analysis components
in the Repository Intelligence Scanner.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class AnalysisComponent(ABC):
    """
    Base class for all analysis components.

    Analysis components are responsible for analyzing different aspects of
    repositories such as code quality, security, compliance, etc.
    """

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description or f"{name} analysis component"

    @abstractmethod
    def analyze(self, repo_path: str, **kwargs) -> Dict[str, Any]:
        """
        Perform analysis on a repository.

        Args:
            repo_path: Path to the repository to analyze
            **kwargs: Additional analysis parameters

        Returns:
            Dict containing analysis results
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Get component metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.__class__.__name__
        }


class ASTAnalysisComponent(AnalysisComponent):
    """
    Base class for AST-based analysis components.

    These components use Abstract Syntax Tree parsing to analyze code
    structure, dependencies, and patterns.
    """

    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)

    @abstractmethod
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a single file using AST parsing.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Dict containing file analysis results
        """
        pass

    @abstractmethod
    def analyze_directory(self, dir_path: str, **kwargs) -> Dict[str, Any]:
        """
        Analyze all files in a directory.

        Args:
            dir_path: Path to the directory to analyze
            **kwargs: Additional analysis parameters

        Returns:
            Dict containing directory analysis results
        """
        pass


class SecurityAnalysisComponent(AnalysisComponent):
    """
    Base class for security-focused analysis components.

    These components analyze code for security vulnerabilities,
    unsafe patterns, and compliance issues.
    """

    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)

    @abstractmethod
    def check_vulnerabilities(self, file_path: str) -> Dict[str, Any]:
        """
        Check for security vulnerabilities in a file.

        Args:
            file_path: Path to the file to check

        Returns:
            Dict containing vulnerability findings
        """
        pass


class PerformanceAnalysisComponent(AnalysisComponent):
    """
    Base class for performance analysis components.

    These components analyze code for performance bottlenecks,
    complexity issues, and optimization opportunities.
    """

    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)

    @abstractmethod
    def calculate_metrics(self, file_path: str) -> Dict[str, Any]:
        """
        Calculate performance metrics for a file.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Dict containing performance metrics
        """
        pass