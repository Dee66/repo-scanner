"""Base language adapter for repository analysis using tree-sitter."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pathlib import Path
import tree_sitter
from tree_sitter import Language, Parser
import logging

from src.core.security.malicious_repo_protection import MaliciousRepoProtection, SecurityLimits

logger = logging.getLogger(__name__)


class BaseLanguageAdapter(ABC):
    """Base class for language-specific adapters using tree-sitter."""

    def __init__(self, language_name: str):
        self.language_name = language_name
        self.parser: Optional[Parser] = None
        self.language: Optional[Language] = None
        self.file_extensions: List[str] = []

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize the tree-sitter parser for this language.

        Args:
            language_lib_path: Path to the compiled language library (.so file)

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            if language_lib_path and Path(language_lib_path).exists():
                self.language = Language(language_lib_path, self.language_name)
                self.parser = Parser()
                self.parser.language = self.language
                return True
            else:
                # Fallback to basic regex parsing if tree-sitter not available
                return False
        except Exception:
            return False

    def is_supported_file(self, file_path: str) -> bool:
        """Check if the file extension is supported by this adapter."""
        if not file_path:
            return False
        file_path_obj = Path(file_path)
        return file_path_obj.suffix.lower() in self.file_extensions

    @abstractmethod
    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST information from a source file.

        Args:
            file_path: Path to the source file

        Returns:
            Dict containing AST information with keys like:
            - file_path: str
            - imports: List[Dict]
            - classes: List[Dict]
            - functions: List[Dict]
            - methods: List[Dict]
            - variables: List[Dict]
            - complexity: int
            - dependencies: List[str]
            - error: str (if parsing failed)
        """
        pass

    @abstractmethod
    def build_dependency_graph(self, root_path: str) -> Dict[str, Any]:
        """Build dependency graph for the project.

        Args:
            root_path: Root path of the project

        Returns:
            Dict containing dependency graph with modules and their relationships
        """
        pass

    def _parse_with_tree_sitter(self, content: str) -> Optional[tree_sitter.Tree]:
        """Parse content using tree-sitter if available."""
        if self.parser:
            try:
                return self.parser.parse(bytes(content, 'utf-8'))
            except Exception:
                return None
        return None

    def _extract_with_regex(self, content: str) -> Dict[str, Any]:
        """Fallback regex-based extraction when tree-sitter is not available."""
        return {
            "imports": [],
            "classes": [],
            "functions": [],
            "methods": [],
            "variables": [],
            "complexity": 0,
            "dependencies": [],
            "unsafe_patterns": []
        }

    def _calculate_complexity(self, tree: Optional[tree_sitter.Tree]) -> int:
        """Calculate cyclomatic complexity from AST."""
        if not tree:
            return 0

        complexity = 1  # Base complexity

        def count_decisions(node):
            nonlocal complexity
            if node.type in ['if_statement', 'for_statement', 'while_statement',
                           'case_statement', 'catch_clause', 'conditional_expression']:
                complexity += 1
            for child in node.children:
                count_decisions(child)

        count_decisions(tree.root_node)
        return complexity

    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content safely with malicious content validation."""
        try:
            file_path_obj = Path(file_path)
            
            # Validate content safety
            try:
                # Create a temporary protection instance for this file
                # Use parent directory as repo root for validation
                protection = MaliciousRepoProtection(
                    repo_root=file_path_obj.parent,
                    limits=SecurityLimits()
                )
                
                if not protection.validate_file_safe(file_path_obj):
                    logger.warning("File failed safety validation: %s", file_path)
                    return None
                    
            except Exception as e:
                logger.error("Safety validation failed for %s: %s", file_path, e)
                return None
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Validate content
            try:
                if not protection.validate_file_content_safe(file_path_obj, content):
                    logger.warning("File content failed safety validation: %s", file_path)
                    return None
            except Exception as e:
                logger.error("Content safety validation failed for %s: %s", file_path, e)
                return None
                
            return content
            
        except (IOError, UnicodeDecodeError) as e:
            logger.debug("Could not read file %s: %s", file_path, e)
            return None
