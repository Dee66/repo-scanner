"""Style Analyzer Engine for Algora Bounty Hunting.

Analyzes git commit history to infer code style preferences, focusing on
import hygiene and code grafting patterns. Generates style profiles that
demonstrate deep understanding of project conventions.
"""

from typing import Dict, List, Optional, Any, Tuple
import os
from pathlib import Path
from datetime import datetime
import re
from collections import defaultdict, Counter
import ast
import git
from git import Repo


class StyleAnalyzer:
    """Engine for analyzing code style from git history."""

    def __init__(self):
        self.repo_cache = {}  # Cache for style analysis
        self.commit_limit = 10  # Analyze last 10 commits

    def analyze_repository_style(self, repo_path: str) -> Dict[str, Any]:
        """Analyze git history to infer code style preferences.

        Args:
            repo_path: Path to the git repository

        Returns:
            Dictionary containing style analysis results
        """
        try:
            repo = Repo(repo_path)
        except git.InvalidGitRepositoryError:
            return {}

        # Cache analysis to avoid repeated computation
        cache_key = repo_path
        if cache_key in self.repo_cache:
            return self.repo_cache[cache_key]

        # Get recent commits
        commits = list(repo.iter_commits('HEAD', max_count=self.commit_limit))
        if not commits:
            return {"error": "No commits found"}

        style_profile = self._analyze_commits_for_style(repo, commits)

        # Cache result
        self.repo_cache[cache_key] = style_profile
        return style_profile

    def _analyze_commits_for_style(self, repo: Repo, commits: List[git.Commit]) -> Dict[str, Any]:
        """Analyze commits for style patterns."""
        import_patterns = defaultdict(Counter)
        code_patterns = defaultdict(Counter)

        for commit in commits:
            # Get files changed in this commit
            if commit.parents:
                diff = commit.parents[0].diff(commit, create_patch=True)
            else:
                # Initial commit
                diff = commit.diff(git.NULL_TREE, create_patch=True)

            for diff_item in diff:
                if diff_item.a_path and diff_item.a_path.endswith('.py'):
                    # Analyze the changed Python file
                    try:
                        file_content = repo.git.show(f"{commit.hexsha}:{diff_item.a_path}")
                        self._analyze_file_style(file_content, import_patterns, code_patterns)
                    except git.GitCommandError:
                        # File might not exist in this commit
                        continue

        return {
            "import_hygiene": self._summarize_import_patterns(import_patterns),
            "code_grafting": self._summarize_code_patterns(code_patterns),
            "confidence": min(1.0, len(commits) / self.commit_limit)
        }

    def _analyze_file_style(self, content: str, import_patterns: Dict, code_patterns: Dict):
        """Analyze a single file's style."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return

        # Analyze imports
        self._analyze_imports(tree, import_patterns)

        # Analyze code structure
        self._analyze_code_structure(tree, code_patterns)

    def _analyze_imports(self, tree: ast.AST, import_patterns: Dict):
        """Analyze import organization and hygiene."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)

        if not imports:
            return

        # Check import grouping
        stdlib_imports = []
        third_party_imports = []
        local_imports = []

        for imp in imports:
            if isinstance(imp, ast.Import):
                for alias in imp.names:
                    module = alias.name.split('.')[0]
                    if self._is_stdlib_module(module):
                        stdlib_imports.append(imp)
                    elif '.' in alias.name:
                        local_imports.append(imp)
                    else:
                        third_party_imports.append(imp)
            elif isinstance(imp, ast.ImportFrom):
                module = imp.module.split('.')[0] if imp.module else ''
                if self._is_stdlib_module(module):
                    stdlib_imports.append(imp)
                elif imp.level > 0:
                    local_imports.append(imp)
                else:
                    third_party_imports.append(imp)

        # Check for blank lines between groups
        import_lines = [imp.lineno for imp in imports]
        import_lines.sort()

        has_blank_lines = False
        for i in range(len(import_lines) - 1):
            if import_lines[i+1] - import_lines[i] > 1:
                has_blank_lines = True
                break

        import_patterns["grouping"]["separated_groups"] += int(has_blank_lines)
        import_patterns["grouping"]["total_files"] += 1

        # Count import types
        import_patterns["types"]["stdlib"] += len(stdlib_imports)
        import_patterns["types"]["third_party"] += len(third_party_imports)
        import_patterns["types"]["local"] += len(local_imports)

    def _analyze_code_structure(self, tree: ast.AST, code_patterns: Dict):
        """Analyze code structure patterns for grafting."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check function naming
                if node.name.startswith('_'):
                    code_patterns["function_naming"]["private"] += 1
                else:
                    code_patterns["function_naming"]["public"] += 1

                # Check docstrings
                if ast.get_docstring(node):
                    code_patterns["documentation"]["has_docstring"] += 1
                else:
                    code_patterns["documentation"]["no_docstring"] += 1

            elif isinstance(node, ast.ClassDef):
                # Check class naming
                if node.name[0].isupper():
                    code_patterns["class_naming"]["pascal_case"] += 1
                else:
                    code_patterns["class_naming"]["other"] += 1

    def _is_stdlib_module(self, module: str) -> bool:
        """Check if a module is part of Python standard library."""
        stdlib_modules = {
            'abc', 'argparse', 'ast', 'asyncio', 'base64', 'collections', 'contextlib',
            'copy', 'csv', 'datetime', 'enum', 'functools', 'hashlib', 'heapq', 'html',
            'http', 'inspect', 'io', 'itertools', 'json', 'logging', 'math', 'os',
            'pathlib', 'pickle', 'platform', 'random', 're', 'shutil', 'socket',
            'sqlite3', 'ssl', 'string', 'subprocess', 'sys', 'tempfile', 'threading',
            'time', 'typing', 'unittest', 'urllib', 'uuid', 'warnings', 'weakref',
            'xml', 'zipfile'
        }
        return module in stdlib_modules

    def _summarize_import_patterns(self, patterns: Dict) -> Dict[str, Any]:
        """Summarize import patterns into preferences."""
        summary = {}

        if patterns["grouping"]["total_files"] > 0:
            separation_ratio = patterns["grouping"]["separated_groups"] / patterns["grouping"]["total_files"]
            summary["import_grouping"] = "separated" if separation_ratio > 0.5 else "mixed"

        total_imports = sum(patterns["types"].values())
        if total_imports > 0:
            summary["import_preference"] = {
                "stdlib_ratio": patterns["types"]["stdlib"] / total_imports,
                "third_party_ratio": patterns["types"]["third_party"] / total_imports,
                "local_ratio": patterns["types"]["local"] / total_imports
            }

        return summary

    def _summarize_code_patterns(self, patterns: Dict) -> Dict[str, Any]:
        """Summarize code patterns into preferences."""
        summary = {}

        # Function naming
        total_funcs = sum(patterns["function_naming"].values())
        if total_funcs > 0:
            private_ratio = patterns["function_naming"]["private"] / total_funcs
            summary["function_naming"] = "prefers_private" if private_ratio > 0.3 else "balanced"

        # Documentation
        total_docs = sum(patterns["documentation"].values())
        if total_docs > 0:
            doc_ratio = patterns["documentation"]["has_docstring"] / total_docs
            summary["documentation"] = "well_documented" if doc_ratio > 0.7 else "minimal"

        # Class naming
        total_classes = sum(patterns["class_naming"].values())
        if total_classes > 0:
            pascal_ratio = patterns["class_naming"]["pascal_case"] / total_classes
            summary["class_naming"] = "pascal_case" if pascal_ratio > 0.8 else "mixed"

        return summary