"""
AST Analysis Engine

Multi-language Abstract Syntax Tree analysis engine for the Repository Intelligence Scanner.
Uses tree-sitter for high-performance parsing of 50+ programming languages.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor
import os

from .base import ASTAnalysisComponent
from ...adapters.language_adapter_manager import LanguageAdapterManager

logger = logging.getLogger(__name__)


class ASTAnalysisEngine(ASTAnalysisComponent):
    """
    Multi-language AST analysis engine using tree-sitter.

    Provides comprehensive code analysis including:
    - AST parsing and structure extraction
    - Import/dependency analysis
    - Code complexity calculation
    - Language-specific pattern detection
    - Security vulnerability scanning
    - Performance metrics
    """

    def __init__(self):
        super().__init__(
            name="AST Analysis Engine",
            description="Multi-language AST analysis using tree-sitter"
        )

        # Initialize language adapter manager
        self.adapter_manager = LanguageAdapterManager()

        # Analysis configuration
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_workers = min(32, os.cpu_count() * 2)  # Thread pool size

        # Supported file extensions cache
        self._supported_extensions: Optional[Set[str]] = None

        logger.info(f"AST Analysis Engine initialized with {len(self.adapter_manager.adapters)} language adapters")

    @property
    def supported_extensions(self) -> Set[str]:
        """Get all supported file extensions."""
        if self._supported_extensions is None:
            self._supported_extensions = set(self.adapter_manager.get_supported_extensions())
        return self._supported_extensions

    def is_supported_file(self, file_path: str) -> bool:
        """Check if a file is supported for analysis."""
        if not file_path:
            return False

        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return False

        # Check file size
        if path.stat().st_size > self.max_file_size:
            return False

        # Check extension
        return path.suffix.lower() in self.supported_extensions

    def analyze(self, repo_path: str, **kwargs) -> Dict[str, Any]:
        """
        Perform comprehensive AST analysis on a repository.

        Args:
            repo_path: Path to the repository to analyze
            **kwargs: Additional analysis parameters
                - include_patterns: List of file patterns to include
                - exclude_patterns: List of file patterns to exclude
                - max_files: Maximum number of files to analyze
                - parallel: Whether to use parallel processing

        Returns:
            Dict containing comprehensive AST analysis results
        """
        repo_path = Path(repo_path)
        if not repo_path.exists():
            return {
                "error": f"Repository path does not exist: {repo_path}",
                "repo_path": str(repo_path)
            }

        # Analysis parameters
        include_patterns = kwargs.get('include_patterns', ['**/*'])
        exclude_patterns = kwargs.get('exclude_patterns', [])
        max_files = kwargs.get('max_files', 10000)
        use_parallel = kwargs.get('parallel', True)

        logger.info(f"Starting AST analysis of repository: {repo_path}")

        # Find all supported files
        supported_files = self._find_supported_files(
            repo_path, include_patterns, exclude_patterns, max_files
        )

        logger.info(f"Found {len(supported_files)} supported files for analysis")

        # Analyze files
        if use_parallel and len(supported_files) > 10:
            analysis_results = self._analyze_files_parallel(supported_files)
        else:
            analysis_results = self._analyze_files_sequential(supported_files)

        # Aggregate results
        aggregated_results = self._aggregate_results(analysis_results, repo_path)

        logger.info(f"AST analysis completed for {len(supported_files)} files")

        return {
            "repo_path": str(repo_path),
            "total_files_analyzed": len(supported_files),
            "supported_files": [str(f) for f in supported_files],
            "analysis_results": analysis_results,
            "aggregated_results": aggregated_results,
            "metadata": {
                "engine_version": "1.0.0",
                "supported_languages": self.adapter_manager.get_supported_languages(),
                "supported_extensions": list(self.supported_extensions)
            }
        }

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a single file using AST parsing.

        Args:
            file_path: Path to the file to analyze

        Returns:
            Dict containing file analysis results
        """
        if not self.is_supported_file(file_path):
            return {
                "file_path": file_path,
                "error": "File not supported for analysis",
                "supported": False
            }

        try:
            # Get appropriate adapter
            adapter = self.adapter_manager.get_adapter_for_file(file_path)
            if not adapter:
                return {
                    "file_path": file_path,
                    "error": "No adapter available for file",
                    "supported": False
                }

            # Extract AST information
            ast_info = adapter.extract_ast(file_path)

            # Add file metadata
            file_path_obj = Path(file_path)
            ast_info.update({
                "file_path": file_path,
                "file_name": file_path_obj.name,
                "file_extension": file_path_obj.suffix.lower(),
                "file_size": file_path_obj.stat().st_size,
                "language": adapter.language_name,
                "supported": True
            })

            return ast_info

        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {
                "file_path": file_path,
                "error": str(e),
                "supported": True  # File type is supported, but analysis failed
            }

    def analyze_directory(self, dir_path: str, **kwargs) -> Dict[str, Any]:
        """
        Analyze all supported files in a directory.

        Args:
            dir_path: Path to the directory to analyze
            **kwargs: Additional analysis parameters

        Returns:
            Dict containing directory analysis results
        """
        # This is essentially the same as analyze() but focused on a directory
        return self.analyze(dir_path, **kwargs)

    def _find_supported_files(self, repo_path: Path,
                            include_patterns: List[str],
                            exclude_patterns: List[str],
                            max_files: int) -> List[Path]:
        """Find all supported files in the repository."""
        supported_files = []

        for root, dirs, files in os.walk(repo_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {
                'node_modules', '__pycache__', '.git', '.svn', '.hg',
                'build', 'dist', 'target', 'bin', 'obj', '.next', '.nuxt'
            }]

            for file in files:
                file_path = Path(root) / file

                # Check if file is supported
                if not self.is_supported_file(str(file_path)):
                    continue

                # Check include patterns
                included = any(file_path.match(pattern) for pattern in include_patterns)
                if not included:
                    continue

                # Check exclude patterns
                excluded = any(file_path.match(pattern) for pattern in exclude_patterns)
                if excluded:
                    continue

                supported_files.append(file_path)

                # Check max files limit
                if len(supported_files) >= max_files:
                    logger.warning(f"Reached maximum file limit: {max_files}")
                    return supported_files

        return supported_files

    def _analyze_files_sequential(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """Analyze files sequentially."""
        results = []
        for file_path in file_paths:
            result = self.analyze_file(str(file_path))
            results.append(result)
        return results

    def _analyze_files_parallel(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """Analyze files in parallel using thread pool."""
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.analyze_file, str(file_path)): file_path
                for file_path in file_paths
            }

            # Collect results as they complete
            for future in future_to_file:
                try:
                    result = future.result(timeout=30)  # 30 second timeout per file
                    results.append(result)
                except Exception as e:
                    file_path = future_to_file[future]
                    logger.error(f"Error analyzing {file_path}: {e}")
                    results.append({
                        "file_path": str(file_path),
                        "error": str(e),
                        "supported": True
                    })

        return results

    def _aggregate_results(self, analysis_results: List[Dict[str, Any]],
                          repo_path: Path) -> Dict[str, Any]:
        """Aggregate analysis results across all files."""
        aggregated = {
            "total_files": len(analysis_results),
            "successful_analyses": 0,
            "failed_analyses": 0,
            "languages": {},
            "total_imports": 0,
            "total_classes": 0,
            "total_functions": 0,
            "total_methods": 0,
            "total_variables": 0,
            "average_complexity": 0,
            "max_complexity": 0,
            "total_dependencies": set(),
            "errors": []
        }

        total_complexity = 0
        complexity_count = 0

        for result in analysis_results:
            if "error" in result and result.get("supported", False):
                aggregated["failed_analyses"] += 1
                aggregated["errors"].append({
                    "file": result["file_path"],
                    "error": result["error"]
                })
                continue

            if not result.get("supported", False):
                continue

            aggregated["successful_analyses"] += 1

            # Language statistics
            language = result.get("language", "unknown")
            aggregated["languages"][language] = aggregated["languages"].get(language, 0) + 1

            # Code metrics
            aggregated["total_imports"] += len(result.get("imports", []))
            aggregated["total_classes"] += len(result.get("classes", []))
            aggregated["total_functions"] += len(result.get("functions", []))
            aggregated["total_methods"] += len(result.get("methods", []))
            aggregated["total_variables"] += len(result.get("variables", []))

            # Complexity
            complexity = result.get("complexity", 0)
            if complexity > 0:
                total_complexity += complexity
                complexity_count += 1
                aggregated["max_complexity"] = max(aggregated["max_complexity"], complexity)

            # Dependencies
            dependencies = result.get("dependencies", [])
            aggregated["total_dependencies"].update(dependencies)

        # Calculate averages
        if complexity_count > 0:
            aggregated["average_complexity"] = total_complexity / complexity_count

        # Convert set to list for JSON serialization
        aggregated["total_dependencies"] = list(aggregated["total_dependencies"])

        return aggregated