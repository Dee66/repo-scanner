"""Tree-sitter based Swift language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import tree_sitter

from .base_adapter import BaseLanguageAdapter


class TreeSitterSwiftAdapter(BaseLanguageAdapter):
    """Tree-sitter based adapter for analyzing Swift repositories."""

    def __init__(self):
        super().__init__("swift")
        self.file_extensions = ['.swift']

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize tree-sitter parser for Swift."""
        try:
            import tree_sitter_swift
            self.language = tree_sitter.Language(tree_sitter_swift.language())
            from tree_sitter import Parser
            self.parser = Parser()
            self.parser.language = self.language
            return True
        except ImportError:
            return super().initialize_parser(language_lib_path)

    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST from Swift file using tree-sitter."""
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
                "dependencies": []
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
                return {
                    "file_path": file_path,
                    **self._extract_with_regex(content)
                }

        except Exception as e:
            return {
                "file_path": file_path,
                "error": f"Failed to parse Swift file: {str(e)}",
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
            if node.type == 'import_declaration':
                module = None

                for child in node.children:
                    if child.type == 'identifier':
                        module = child.text.decode('utf-8')
                        break

                if module:
                    imports.append({
                        "module": module,
                        "alias": None
                    })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return imports

    def _extract_classes(self, tree) -> List[Dict[str, Any]]:
        """Extract class/struct definitions from tree-sitter tree."""
        classes = []

        def traverse(node, parent_class=None):
            if node.type in ['class_declaration', 'struct_declaration']:
                class_name = None
                base_classes = []

                for child in node.children:
                    if child.type == 'type_identifier':
                        if class_name is None:
                            class_name = child.text.decode('utf-8')
                    elif child.type == 'inheritance_clause':
                        for base in child.children:
                            if base.type == 'type_identifier':
                                base_classes.append(base.text.decode('utf-8'))

                if class_name:
                    classes.append({
                        "name": class_name,
                        "bases": base_classes,
                        "parent_class": parent_class,
                        "methods": []
                    })

                # Continue traversal to find methods
                current_class = class_name if class_name else parent_class
                for child in node.children:
                    traverse(child, current_class)

            elif node.type == 'function_declaration' and parent_class:
                func_name = None
                for child in node.children:
                    if child.type == 'simple_identifier':
                        func_name = child.text.decode('utf-8')
                        break

                if func_name:
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
            if node.type == 'function_declaration':
                func_name = None
                params = []

                for child in node.children:
                    if child.type == 'simple_identifier':
                        func_name = child.text.decode('utf-8')
                    elif child.type == 'parameter_clause':
                        for param in child.children:
                            if param.type == 'parameter':
                                for param_part in param.children:
                                    if param_part.type == 'simple_identifier':
                                        params.append(param_part.text.decode('utf-8'))
                                        break

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
        """Extract variable declarations from tree-sitter tree."""
        variables = []

        def traverse(node):
            if node.type in ['property_declaration', 'constant_declaration']:
                for child in node.children:
                    if child.type == 'pattern':
                        for pattern_part in child.children:
                            if pattern_part.type == 'simple_identifier':
                                var_name = pattern_part.text.decode('utf-8')
                                variables.append({"name": var_name, "type": "property"})
                                break

            elif node.type == 'assignment':
                left_side = None
                for child in node.children:
                    if child.type == 'simple_identifier':
                        left_side = child.text.decode('utf-8')
                        break
                if left_side:
                    variables.append({"name": left_side, "type": "assignment"})

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return variables

    def _extract_dependencies(self, tree) -> List[str]:
        """Extract dependencies from import statements."""
        dependencies = []
        imports = self._extract_imports(tree)

        for imp in imports:
            if imp.get("module"):
                dependencies.append(imp["module"])

        return list(set(dependencies))

    def build_dependency_graph(self, root_path: str) -> Dict[str, Any]:
        """Build dependency graph for Swift project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": f"Invalid root path: {root_path}", "modules": {}, "dependencies": {}}

        try:
            graph = {"modules": {}, "dependencies": {}}
            root_path = Path(root_path)

            # Find all Swift files
            swift_files = list(root_path.rglob("*.swift"))

            for swift_file in swift_files:
                if swift_file.is_file():
                    ast_info = self.extract_ast(str(swift_file))
                    if "error" not in ast_info:
                        module_name = self._get_module_name(swift_file, root_path)

                        graph["modules"][module_name] = {
                            "file_path": str(swift_file),
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

    def _detect_unsafe_patterns(self, content: str, tree) -> List[Dict[str, Any]]:
        """Detect unsafe Swift patterns that could lead to security vulnerabilities."""
        unsafe_patterns = []

        # Pattern 1: Force unwrapping (!) - can cause runtime crashes
        if '!' in content:
            for match in re.finditer(r'\w+!\s*(?:\(|$)', content):
                unsafe_patterns.append({
                    "type": "force_unwrap",
                    "pattern": "force unwrap",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Force unwrapping optionals can cause runtime crashes",
                    "severity": "medium"
                })

        # Pattern 2: Implicitly unwrapped optionals - unsafe
        for match in re.finditer(r'\w+!\s*:', content):
            unsafe_patterns.append({
                "type": "implicit_unwrap",
                "pattern": "implicitly unwrapped optional",
                "line": content[:match.start()].count('\n') + 1,
                "description": "Implicitly unwrapped optionals are unsafe and can cause crashes",
                "severity": "medium"
            })

        # Pattern 3: Use of NSClassFromString - dynamic class loading
        if 'NSClassFromString' in content:
            for match in re.finditer(r'NSClassFromString', content):
                unsafe_patterns.append({
                    "type": "dynamic_class_loading",
                    "pattern": "NSClassFromString",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Dynamic class loading can be unsafe - validate class names",
                    "severity": "medium"
                })

        # Pattern 4: Use of performSelector - dynamic method invocation
        if 'performSelector' in content:
            for match in re.finditer(r'performSelector', content):
                unsafe_patterns.append({
                    "type": "dynamic_method_call",
                    "pattern": "performSelector",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "performSelector bypasses compile-time safety checks",
                    "severity": "high"
                })

        # Pattern 5: Insecure random number generation
        if 'arc4random' in content:
            for match in re.finditer(r'arc4random', content):
                unsafe_patterns.append({
                    "type": "weak_random",
                    "pattern": "arc4random",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "arc4random is cryptographically weak - use SecRandomCopyBytes",
                    "severity": "medium"
                })

        # Pattern 6: Hardcoded secrets
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'apiKey\s*=\s*["\'][^"\']+["\']'
        ]
        for pattern in secret_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                unsafe_patterns.append({
                    "type": "hardcoded_secret",
                    "pattern": "hardcoded credential",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Potential hardcoded secret or credential",
                    "severity": "high"
                })

        # Pattern 7: Use of try! - force try that can crash
        if 'try!' in content:
            for match in re.finditer(r'try!', content):
                unsafe_patterns.append({
                    "type": "force_try",
                    "pattern": "try!",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Force try can cause runtime crashes on errors",
                    "severity": "medium"
                })

        # Pattern 8: Insecure URL handling
        if 'URL(string:' in content and 'https://' not in content:
            for match in re.finditer(r'URL\(string:\s*["\'][^"\']*["\']', content):
                url_match = match.group(0)
                if 'http://' in url_match and 'https://' not in url_match:
                    unsafe_patterns.append({
                        "type": "insecure_url",
                        "pattern": "HTTP URL",
                        "line": content[:match.start()].count('\n') + 1,
                        "description": "Using HTTP instead of HTTPS - insecure communication",
                        "severity": "medium"
                    })

        # Pattern 9: Use of unsafe pointers
        if 'UnsafePointer' in content or 'UnsafeMutablePointer' in content:
            for match in re.finditer(r'Unsafe(?:Mutable)?Pointer', content):
                unsafe_patterns.append({
                    "type": "unsafe_pointer",
                    "pattern": match.group(0),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of unsafe pointers - manual memory management",
                    "severity": "high"
                })

        # Pattern 10: SQL injection potential
        if 'sqlite' in content.lower() and ('+' in content or 'string interpolation' in content):
            for match in re.finditer(r'"\s*SELECT.*\\\(.*\)"', content):
                unsafe_patterns.append({
                    "type": "sql_injection",
                    "pattern": "string interpolation in SQL",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "String interpolation in SQL queries - injection risk",
                    "severity": "high"
                })

        return unsafe_patterns

    def _get_module_name(self, file_path: Path, root_path: Path) -> str:
        """Get module name from file path."""
        try:
            relative_path = file_path.relative_to(root_path)
            module_name = str(relative_path.with_suffix(''))
            return module_name
        except ValueError:
            return str(file_path.with_suffix(''))
