"""Language adapter manager for coordinating multiple language adapters."""

from typing import Dict, List, Optional, Any, Type
from pathlib import Path

from .base_adapter import BaseLanguageAdapter
from .tree_sitter_python_adapter import TreeSitterPythonAdapter
from .tree_sitter_javascript_adapter import TreeSitterJavaScriptAdapter
from .tree_sitter_csharp_adapter import TreeSitterCSharpAdapter
from .tree_sitter_php_adapter import TreeSitterPHPAdapter
from .tree_sitter_ruby_adapter import TreeSitterRubyAdapter
from .tree_sitter_swift_adapter import TreeSitterSwiftAdapter
from .tree_sitter_kotlin_adapter import TreeSitterKotlinAdapter
from .tree_sitter_scala_adapter import TreeSitterScalaAdapter
from .tree_sitter_cpp_adapter import TreeSitterCppAdapter
from .tree_sitter_rust_adapter import TreeSitterRustAdapter

# Legacy adapters (optional imports)
try:
    from .python_adapter import PythonAdapter
except ImportError:
    PythonAdapter = None
try:
    from .java_adapter import JavaAdapter
except ImportError:
    JavaAdapter = None
try:
    from .javascript_adapter import JavaScriptAdapter
except ImportError:
    JavaScriptAdapter = None
try:
    from .rust_adapter import RustAdapter
except ImportError:
    RustAdapter = None
try:
    from .go_adapter import GoAdapter
except ImportError:
    GoAdapter = None
try:
    from .cpp_adapter import CppAdapter
except ImportError:
    CppAdapter = None


class LanguageAdapterManager:
    """Manager for coordinating multiple language adapters."""

    def __init__(self):
        self.adapters: Dict[str, BaseLanguageAdapter] = {}
        self._initialize_adapters()

    def _initialize_adapters(self):
        """Initialize all available language adapters."""
        # Tree-sitter based adapters (preferred)
        tree_sitter_adapters = [
            TreeSitterPythonAdapter(),
            TreeSitterJavaScriptAdapter("javascript"),
            TreeSitterJavaScriptAdapter("typescript"),
            TreeSitterCSharpAdapter(),
            TreeSitterPHPAdapter(),
            TreeSitterRubyAdapter(),
            TreeSitterSwiftAdapter(),
            TreeSitterKotlinAdapter(),
            TreeSitterScalaAdapter(),
            TreeSitterCppAdapter(),
            TreeSitterRustAdapter(),
        ]

        # Legacy adapters (fallback) - only load if dependencies available
        legacy_adapters = []
        if PythonAdapter:
            legacy_adapters.append(PythonAdapter())
        if JavaAdapter:
            legacy_adapters.append(JavaAdapter())
        if JavaScriptAdapter:
            legacy_adapters.append(JavaScriptAdapter())
        if RustAdapter:
            legacy_adapters.append(RustAdapter())
        if GoAdapter:
            legacy_adapters.append(GoAdapter())
        if CppAdapter:
            legacy_adapters.append(CppAdapter())

        # Register tree-sitter adapters first (higher priority)
        for adapter in tree_sitter_adapters:
            if adapter.initialize_parser():
                for ext in adapter.file_extensions:
                    self.adapters[ext] = adapter

        # Register legacy adapters for extensions not covered by tree-sitter
        for adapter in legacy_adapters:
            for ext in adapter.file_extensions:
                if ext not in self.adapters:
                    self.adapters[ext] = adapter

    def get_adapter_for_file(self, file_path: str) -> Optional[BaseLanguageAdapter]:
        """Get the appropriate adapter for a file based on its extension."""
        if not file_path:
            return None

        file_path_obj = Path(file_path)
        extension = file_path_obj.suffix.lower()

        return self.adapters.get(extension)

    def get_supported_extensions(self) -> List[str]:
        """Get list of all supported file extensions."""
        return list(self.adapters.keys())

    def get_supported_languages(self) -> List[str]:
        """Get list of all supported languages."""
        languages = set()
        for adapter in self.adapters.values():
            languages.add(adapter.language_name)
        return sorted(list(languages))

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single file using the appropriate adapter."""
        adapter = self.get_adapter_for_file(file_path)
        if adapter:
            return adapter.extract_ast(file_path)
        else:
            return {
                "file_path": file_path,
                "error": f"No adapter available for file extension: {Path(file_path).suffix}",
                "imports": [],
                "classes": [],
                "functions": [],
                "methods": [],
                "variables": [],
                "complexity": 0,
                "dependencies": []
            }

    def build_project_dependency_graph(self, root_path: str) -> Dict[str, Any]:
        """Build dependency graph for an entire project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": f"Invalid root path: {root_path}", "modules": {}, "dependencies": {}}

        try:
            graph = {"modules": {}, "dependencies": {}}
            root_path_obj = Path(root_path)

            # Collect all supported files
            supported_files = []
            for ext in self.adapters.keys():
                supported_files.extend(list(root_path_obj.rglob(f"*{ext}")))

            # Analyze each file with its appropriate adapter
            for file_path in supported_files:
                if file_path.is_file():
                    adapter = self.get_adapter_for_file(str(file_path))
                    if adapter:
                        ast_info = adapter.extract_ast(str(file_path))
                        if "error" not in ast_info:
                            module_name = adapter._get_module_name(file_path, root_path_obj)

                            graph["modules"][module_name] = {
                                "file_path": str(file_path),
                                "language": adapter.language_name,
                                "imports": ast_info.get("imports", []),
                                "classes": [cls["name"] for cls in ast_info.get("classes", [])],
                                "functions": [func["name"] for func in ast_info.get("functions", [])]
                            }

                            # Add dependencies
                            for imp in ast_info.get("imports", []):
                                if imp.get("module"):
                                    if module_name not in graph["dependencies"]:
                                        graph["dependencies"][module_name] = []
                                    if imp["module"] not in graph["dependencies"][module_name]:
                                        graph["dependencies"][module_name].append(imp["module"])

            return graph

        except Exception as e:
            return {"error": f"Failed to build dependency graph: {str(e)}", "modules": {}, "dependencies": {}}

    def get_language_statistics(self, root_path: str) -> Dict[str, Any]:
        """Get statistics about languages used in a project."""
        stats = {}
        root_path_obj = Path(root_path)

        for ext, adapter in self.adapters.items():
            files = list(root_path_obj.rglob(f"*{ext}"))
            if files:
                lang = adapter.language_name
                if lang not in stats:
                    stats[lang] = {"count": 0, "extensions": []}
                stats[lang]["count"] += len(files)
                if ext not in stats[lang]["extensions"]:
                    stats[lang]["extensions"].append(ext)

        return stats
