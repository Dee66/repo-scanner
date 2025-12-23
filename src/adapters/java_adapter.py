"""Java language adapter for repository analysis."""


class JavaAdapter:
    """Adapter for analyzing Java repositories."""

    def extract_ast(self, file_path: str) -> dict:
        """Extract AST from Java file."""
        raise NotImplementedError

    def build_dependency_graph(self, root_path: str) -> dict:
        """Build dependency graph for Java project."""
        raise NotImplementedError

    def discover_tests(self, root_path: str) -> list:
        """Discover test files and functions."""
        raise NotImplementedError

    def extract_documentation(self, file_path: str) -> dict:
        """Extract documentation from Java file."""
        raise NotImplementedError
