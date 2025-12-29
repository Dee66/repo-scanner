"""Python language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import astroid
from astroid import nodes


class PythonAdapter:
    """Adapter for analyzing Python repositories."""

    def extract_ast(self, file_path: str) -> dict:
        """Extract AST from Python file using astroid parser."""
        if not isinstance(file_path, str) or not file_path:
            return {
                "file_path": str(file_path) if file_path else "None",
                "error": f"Invalid file path: {file_path}",
                "imports": [],
                "classes": [],
                "functions": [],
                "methods": [],
                "variables": [],
                "complexity": 0,
                "dependencies": []
            }

        try:
            # Parse the Python file with astroid
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            module = astroid.parse(content)

            # Extract AST information
            ast_info = {
                "file_path": file_path,
                "imports": self._extract_imports(module),
                "classes": self._extract_classes(module),
                "functions": self._extract_functions(module),
                "methods": self._extract_methods(module),
                "variables": self._extract_variables(module),
                "complexity": self._calculate_complexity(module),
                "dependencies": self._extract_dependencies(module)
            }

            return ast_info

        except Exception as e:
            return {
                "file_path": file_path,
                "error": f"Failed to parse Python file: {str(e)}",
                "imports": [],
                "classes": [],
                "functions": [],
                "methods": [],
                "variables": [],
                "complexity": 0,
                "dependencies": []
            }

    def build_dependency_graph(self, root_path: str) -> dict:
        """Build dependency graph for Python project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": f"Invalid root path: {root_path}", "modules": {}, "dependencies": {}}

        try:
            graph = {"modules": {}, "dependencies": {}}
            root_path = Path(root_path)

            # Find all Python files
            python_files = list(root_path.rglob("*.py"))

            for py_file in python_files:
                if py_file.is_file():
                    try:
                        with open(str(py_file), 'r', encoding='utf-8') as f:
                            content = f.read()
                        module = astroid.parse(content)
                        module_name = self._get_module_name(py_file, root_path)

                        graph["modules"][module_name] = {
                            "file_path": str(py_file),
                            "imports": self._extract_imports(module),
                            "classes": [cls["name"] for cls in self._extract_classes(module)],
                            "functions": [func["name"] for func in self._extract_functions(module)]
                        }

                        # Add dependencies
                        for imp in self._extract_imports(module):
                            if imp.get("module"):
                                if module_name not in graph["dependencies"]:
                                    graph["dependencies"][module_name] = []
                                if imp["module"] not in graph["dependencies"][module_name]:
                                    graph["dependencies"][module_name].append(imp["module"])

                    except Exception as e:
                        # Skip files that can't be parsed
                        continue

            return graph

        except Exception as e:
            return {"error": f"Failed to build dependency graph: {str(e)}", "modules": {}, "dependencies": {}}

    def discover_tests(self, root_path: str) -> list:
        """Discover test files and functions."""
        if not isinstance(root_path, str) or not root_path:
            return []

        try:
            tests = []
            root_path = Path(root_path)

            # Find test files (unittest, pytest patterns)
            test_files = []
            test_files.extend(root_path.rglob("test_*.py"))
            test_files.extend(root_path.rglob("*_test.py"))
            test_files.extend(root_path.rglob("tests.py"))

            for test_file in test_files:
                if test_file.is_file():
                    try:
                        with open(str(test_file), 'r', encoding='utf-8') as f:
                            content = f.read()
                        module = astroid.parse(content)

                        # Find test functions/classes
                        for node in self._walk_tree(module):
                            if isinstance(node, nodes.FunctionDef) and node.name.startswith("test_"):
                                tests.append({
                                    "file_path": str(test_file),
                                    "type": "function",
                                    "name": node.name,
                                    "line": node.lineno
                                })

                        for node in self._walk_tree(module):
                            if isinstance(node, nodes.ClassDef) and node.name.startswith("Test"):
                                tests.append({
                                    "file_path": str(test_file),
                                    "type": "class",
                                    "name": node.name,
                                    "line": node.lineno
                                })

                    except Exception:
                        continue

            return tests

        except Exception as e:
            return []

    def extract_documentation(self, file_path: str) -> dict:
        """Extract documentation from Python file."""
        if not isinstance(file_path, str) or not file_path:
            return {"error": f"Invalid file path: {file_path}", "docstrings": {}}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            module = astroid.parse(content)
            docstrings = {}

            # Extract module docstring
            if module.doc_node:
                docstrings["module"] = module.doc_node.value

            # Extract function docstrings
            for node in self._walk_tree(module):
                if isinstance(node, nodes.FunctionDef) and node.doc_node:
                    if not isinstance(node.parent, nodes.ClassDef):
                        docstrings[f"function:{node.name}"] = node.doc_node.value

            # Extract class docstrings
            for node in self._walk_tree(module):
                if isinstance(node, nodes.ClassDef) and node.doc_node:
                    docstrings[f"class:{node.name}"] = node.doc_node.value

                # Extract method docstrings
                if isinstance(node, nodes.ClassDef):
                    for method in self._walk_tree(node):
                        if isinstance(method, nodes.FunctionDef) and method.doc_node:
                            docstrings[f"method:{node.name}.{method.name}"] = method.doc_node.value

            return {"docstrings": docstrings}

        except Exception as e:
            return {"error": f"Failed to extract documentation: {str(e)}", "docstrings": {}}

    def _extract_imports(self, module: nodes.Module) -> List[Dict[str, Any]]:
        """Extract import statements from AST."""
        imports = []

        def walk_tree(node):
            if isinstance(node, nodes.Import):
                if hasattr(node, 'names') and node.names:
                    for name, alias in node.names:
                        imports.append({
                            "module": name,
                            "alias": alias,
                            "type": "import"
                        })
            elif isinstance(node, nodes.ImportFrom):
                if hasattr(node, 'modname') and node.modname and hasattr(node, 'names') and node.names:
                    for name, alias in node.names:
                        imports.append({
                            "module": node.modname,
                            "name": name,
                            "alias": alias,
                            "type": "from_import"
                        })
            for child in node.get_children():
                walk_tree(child)

        walk_tree(module)
        return imports

    def _walk_tree(self, node):
        """Recursively walk the AST tree."""
        results = []
        results.append(node)
        for child in node.get_children():
            results.extend(self._walk_tree(child))
        return results

    def _extract_classes(self, module: nodes.Module) -> List[Dict[str, Any]]:
        """Extract class definitions from AST."""
        classes = []

        for node in self._walk_tree(module):
            if isinstance(node, nodes.ClassDef):
                methods = [n for n in self._walk_tree(node) if isinstance(n, nodes.FunctionDef)]
                attributes = [n for n in self._walk_tree(node) if isinstance(n, nodes.Assign)]
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "bases": [base.as_string() for base in (node.bases or [])],
                    "methods": len(methods),
                    "attributes": len(attributes)
                })

        return classes

    def _extract_functions(self, module: nodes.Module) -> List[Dict[str, Any]]:
        """Extract function definitions from AST."""
        functions = []

        for node in self._walk_tree(module):
            if isinstance(node, nodes.FunctionDef):
                # Skip methods (functions inside classes)
                if not isinstance(node.parent, nodes.ClassDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": len(node.args.args) if node.args and hasattr(node.args, 'args') else 0,
                        "decorators": [dec.as_string() for dec in (node.decorators or [])]
                    })

        return functions

    def _extract_methods(self, module: nodes.Module) -> List[Dict[str, Any]]:
        """Extract method definitions from AST."""
        methods = []

        for node in self._walk_tree(module):
            if isinstance(node, nodes.FunctionDef):
                if isinstance(node.parent, nodes.ClassDef):
                    methods.append({
                        "class": node.parent.name,
                        "name": node.name,
                        "line": node.lineno,
                        "args": len(node.args.args) if node.args and hasattr(node.args, 'args') else 0,
                        "decorators": [dec.as_string() for dec in (node.decorators or [])]
                    })

        return methods

    def _extract_variables(self, module: nodes.Module) -> List[Dict[str, Any]]:
        """Extract variable assignments from AST."""
        variables = []

        for node in self._walk_tree(module):
            if isinstance(node, nodes.Assign):
                for target in (node.targets or []):
                    if hasattr(target, 'name'):
                        variables.append({
                            "name": target.name,
                            "line": node.lineno,
                            "value_type": type(node.value).__name__
                        })

        return variables

    def _calculate_complexity(self, module: nodes.Module) -> int:
        """Calculate cyclomatic complexity of the module."""
        complexity = 0

        # Count control flow statements
        control_nodes = (nodes.If, nodes.For, nodes.While, nodes.Try)
        for node in self._walk_tree(module):
            if isinstance(node, control_nodes):
                complexity += 1

        # Count boolean operators
        for node in self._walk_tree(module):
            if isinstance(node, nodes.BoolOp):
                complexity += len(node.values) - 1

        return max(1, complexity)

    def _extract_dependencies(self, module: nodes.Module) -> List[str]:
        """Extract external dependencies from imports."""
        dependencies = set()

        for imp in self._extract_imports(module):
            if imp.get("module"):
                # Extract top-level package
                parts = imp["module"].split(".")
                if parts[0] not in {"os", "sys", "typing", "collections", "json", "re", "pathlib"}:
                    dependencies.add(parts[0])

        return list(dependencies)

    def _get_module_name(self, file_path: Path, root_path: Path) -> str:
        """Get module name relative to root path."""
        try:
            relative = file_path.relative_to(root_path)
            return str(relative.with_suffix("")).replace(os.sep, ".")
        except ValueError:
            return str(file_path.with_suffix("")).replace(os.sep, ".")
