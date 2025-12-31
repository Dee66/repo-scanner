"""Tree-sitter based Python language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import tree_sitter
import tree_sitter
from tree_sitter import Language

from .base_adapter import BaseLanguageAdapter


class TreeSitterPythonAdapter(BaseLanguageAdapter):
    """Tree-sitter based adapter for analyzing Python repositories."""

    def __init__(self):
        super().__init__("python")
        self.file_extensions = ['.py']

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize tree-sitter parser for Python."""
        try:
            import tree_sitter_python
            self.language = tree_sitter.Language(tree_sitter_python.language())
            from tree_sitter import Parser
            self.parser = Parser()
            self.parser.language = self.language
            return True
        except ImportError:
            return super().initialize_parser(language_lib_path)

    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST from Python file using tree-sitter."""
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
                "dependencies": [],
                "unsafe_patterns": []
            }

        content = self._read_file_content(file_path)
        if content is None:
            return {
                "file_path": file_path,
                "error": "Failed to read file",
                "imports": [],
                "classes": [],
                "functions": [],
                "methods": [],
                "variables": [],
                "complexity": 0,
                "dependencies": [],
                "unsafe_patterns": []
            }

        try:
            tree = self._parse_with_tree_sitter(content)
            if tree:
                return {
                    "file_path": file_path,
                    "imports": self._extract_imports(tree),
                    "classes": self._extract_classes(tree),
                    "functions": self._extract_functions(tree),
                    "methods": self._extract_methods(tree),
                    "variables": self._extract_variables(tree),
                    "complexity": self._calculate_complexity(tree),
                    "dependencies": self._extract_dependencies(tree),
                    "unsafe_patterns": self._detect_unsafe_patterns(content, tree)
                }
            else:
                # Fallback to regex parsing
                return {
                    "file_path": file_path,
                    **self._extract_with_regex(content)
                }

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
                "dependencies": [],
                "unsafe_patterns": []
            }

    def _extract_imports(self, tree) -> List[Dict[str, Any]]:
        """Extract import statements from tree-sitter tree."""
        imports = []

        def traverse(node):
            if node.type == 'import_statement':
                # Handle 'import module' or 'import module.submodule'
                module_names = []
                for child in node.children:
                    if child.type == 'dotted_name':
                        name = child.text.decode('utf-8')
                        module_names.append({"module": name, "alias": None})
                    elif child.type == 'import_as_clause':
                        # Handle 'import module as alias'
                        for subchild in child.children:
                            if subchild.type == 'name':
                                alias = subchild.text.decode('utf-8')
                                if module_names:
                                    module_names[-1]["alias"] = alias
                imports.extend(module_names)

            elif node.type == 'import_from_statement':
                # Handle 'from module import ...'
                module_name = None
                imported_items = []

                for child in node.children:
                    if child.type == 'dotted_name':
                        module_name = child.text.decode('utf-8')
                    elif child.type == 'import_list':
                        for item in child.children:
                            if item.type == 'name':
                                imported_items.append({
                                    "name": item.text.decode('utf-8'),
                                    "alias": None
                                })
                            elif item.type == 'aliased_import':
                                name = None
                                alias = None
                                for subitem in item.children:
                                    if subitem.type == 'name':
                                        if name is None:
                                            name = subitem.text.decode('utf-8')
                                        else:
                                            alias = subitem.text.decode('utf-8')
                                if name:
                                    imported_items.append({"name": name, "alias": alias})

                for item in imported_items:
                    imports.append({
                        "module": module_name,
                        "name": item["name"],
                        "alias": item["alias"]
                    })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return imports

    def _extract_classes(self, tree) -> List[Dict[str, Any]]:
        """Extract class definitions from tree-sitter tree."""
        classes = []

        def traverse(node, parent_class=None):
            if node.type == 'class_definition':
                class_name = None
                base_classes = []

                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                    elif child.type == 'argument_list':
                        # Extract base classes
                        for arg in child.children:
                            if arg.type == 'name' or arg.type == 'dotted_name':
                                base_classes.append(arg.text.decode('utf-8'))

                if class_name:
                    classes.append({
                        "name": class_name,
                        "bases": base_classes,
                        "parent_class": parent_class,
                        "methods": []
                    })

                # Continue traversal to find nested classes and methods
                current_class = class_name if class_name else parent_class
                for child in node.children:
                    traverse(child, current_class)

            elif node.type == 'function_definition' and parent_class:
                # This is a method
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                        break

                if func_name:
                    # Find the class this method belongs to
                    for cls in classes:
                        if cls["name"] == parent_class:
                            cls["methods"].append(func_name)
                            break

            for child in node.children:
                traverse(child, parent_class)

        traverse(tree.root_node)
        return classes

    def _extract_functions(self, tree) -> List[Dict[str, Any]]:
        """Extract function definitions from tree-sitter tree."""
        functions = []

        def traverse(node):
            if node.type == 'function_definition':
                func_name = None
                params = []

                for child in node.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                    elif child.type == 'parameters':
                        for param in child.children:
                            if param.type == 'identifier':
                                params.append(param.text.decode('utf-8'))

                if func_name:
                    functions.append({
                        "name": func_name,
                        "parameters": params
                    })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return functions

    def _extract_methods(self, tree) -> List[Dict[str, Any]]:
        """Extract methods (functions inside classes) from tree-sitter tree."""
        methods = []
        classes = self._extract_classes(tree)

        for cls in classes:
            for method_name in cls.get("methods", []):
                methods.append({
                    "name": method_name,
                    "class": cls["name"]
                })

        return methods

    def _extract_variables(self, tree) -> List[Dict[str, Any]]:
        """Extract variable assignments from tree-sitter tree."""
        variables = []

        def traverse(node):
            if node.type == 'assignment':
                # Handle simple assignments like 'x = 1'
                targets = []
                for child in node.children:
                    if child.type == 'identifier':
                        targets.append(child.text.decode('utf-8'))
                    elif child.type == 'pattern_list':
                        for pattern in child.children:
                            if pattern.type == 'identifier':
                                targets.append(pattern.text.decode('utf-8'))

                for target in targets:
                    variables.append({"name": target, "type": "assignment"})

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return variables

    def _extract_dependencies(self, tree) -> List[str]:
        """Extract module dependencies from imports."""
        dependencies = []
        imports = self._extract_imports(tree)

        for imp in imports:
            if imp.get("module"):
                dependencies.append(imp["module"])

        return list(set(dependencies))

    def build_dependency_graph(self, root_path: str) -> Dict[str, Any]:
        """Build dependency graph for Python project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": f"Invalid root path: {root_path}", "modules": {}, "dependencies": {}}

        try:
            graph = {"modules": {}, "dependencies": {}}
            root_path = Path(root_path)

            # Find all Python files
            python_files = list(root_path.rglob("*.py"))

            for py_file in python_files:
                if py_file.is_file() and self.is_supported_file(str(py_file)):
                    ast_info = self.extract_ast(str(py_file))
                    if "error" not in ast_info:
                        module_name = self._get_module_name(py_file, root_path)

                        graph["modules"][module_name] = {
                            "file_path": str(py_file),
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

    def _get_module_name(self, file_path: Path, root_path: Path) -> str:
        """Get module name from file path."""
        try:
            relative_path = file_path.relative_to(root_path)
            module_name = str(relative_path.with_suffix('')).replace(os.sep, '.')
            return module_name
        except ValueError:
            return str(file_path.with_suffix('')).replace(os.sep, '.')

    def _detect_unsafe_patterns(self, content: str, tree) -> List[Dict[str, Any]]:
        """Detect unsafe Python patterns that could lead to security vulnerabilities."""
        unsafe_patterns = []

        # Pattern 1: Use of eval() and exec() - dynamic code execution
        for func in ['eval', 'exec']:
            if func + '(' in content:
                for match in re.finditer(rf'\b{func}\s*\(', content):
                    unsafe_patterns.append({
                        "type": "dynamic_code_execution",
                        "pattern": f"{func}()",
                        "line": content[:match.start()].count('\n') + 1,
                        "description": f"Use of {func}() for dynamic code execution - high security risk",
                        "severity": "high"
                    })

        # Pattern 2: Use of pickle - deserialization vulnerability
        if 'pickle' in content:
            for match in re.finditer(r'\bpickle\.(load|loads)', content):
                unsafe_patterns.append({
                    "type": "deserialization_vulnerability",
                    "pattern": f"pickle.{match.group(1)}",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Pickle deserialization can lead to remote code execution",
                    "severity": "high"
                })

        # Pattern 3: Use of subprocess with shell=True
        if 'subprocess' in content:
            for match in re.finditer(r'\bsubprocess\.(call|Popen|run|check_output)\s*\([^)]*shell\s*=\s*True', content):
                unsafe_patterns.append({
                    "type": "command_injection",
                    "pattern": "subprocess with shell=True",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "subprocess with shell=True can lead to command injection",
                    "severity": "high"
                })

        # Pattern 4: Use of os.system or os.popen
        for func in ['os.system', 'os.popen']:
            if func in content:
                for match in re.finditer(rf'\b{func}\s*\(', content):
                    unsafe_patterns.append({
                        "type": "command_injection",
                        "pattern": func,
                        "line": content[:match.start()].count('\n') + 1,
                        "description": f"{func} can lead to command injection attacks",
                        "severity": "high"
                    })

        # Pattern 5: Use of input() in Python 2 style (though this is Python 3)
        if 'input(' in content:
            for match in re.finditer(r'\binput\s*\(', content):
                unsafe_patterns.append({
                    "type": "unsafe_input",
                    "pattern": "input()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "input() evaluates user input as code - use input() instead",
                    "severity": "medium"
                })

        # Pattern 6: Use of assert statements in production code
        if 'assert ' in content:
            for match in re.finditer(r'\bassert\s+', content):
                unsafe_patterns.append({
                    "type": "debug_code",
                    "pattern": "assert statement",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Assert statements are removed with -O flag - not for production",
                    "severity": "low"
                })

        # Pattern 7: Use of yaml.load without Loader parameter
        if 'yaml' in content:
            for match in re.finditer(r'\byaml\.load\s*\(', content):
                unsafe_patterns.append({
                    "type": "deserialization_vulnerability",
                    "pattern": "yaml.load()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "yaml.load without safe Loader can execute arbitrary code",
                    "severity": "high"
                })

        return unsafe_patterns
