"""Tree-sitter based Ruby language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import tree_sitter

from .base_adapter import BaseLanguageAdapter


class TreeSitterRubyAdapter(BaseLanguageAdapter):
    """Tree-sitter based adapter for analyzing Ruby repositories."""

    def __init__(self):
        super().__init__("ruby")
        self.file_extensions = ['.rb']

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize tree-sitter parser for Ruby."""
        try:
            import tree_sitter_ruby
            self.language = tree_sitter.Language(tree_sitter_ruby.language())
            from tree_sitter import Parser
            self.parser = Parser()
            self.parser.language = self.language
            return True
        except ImportError:
            return super().initialize_parser(language_lib_path)

    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST from Ruby file using tree-sitter."""
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
                "error": f"Failed to parse Ruby file: {str(e)}",
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
        """Extract require statements from tree-sitter tree."""
        imports = []

        def traverse(node):
            if node.type == 'require':
                # Handle require 'module'
                for child in node.children:
                    if child.type == 'string':
                        module = child.text.decode('utf-8').strip('"\'')

                        # Remove .rb extension if present
                        if module.endswith('.rb'):
                            module = module[:-3]

                        imports.append({
                            "module": module,
                            "alias": None
                        })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return imports

    def _extract_classes(self, tree) -> List[Dict[str, Any]]:
        """Extract class definitions from tree-sitter tree."""
        classes = []

        def traverse(node, parent_class=None):
            if node.type == 'class':
                class_name = None
                base_classes = []

                for child in node.children:
                    if child.type == 'constant':
                        if class_name is None:
                            class_name = child.text.decode('utf-8')
                        else:
                            base_classes.append(child.text.decode('utf-8'))
                    elif child.type == 'superclass':
                        for base in child.children:
                            if base.type == 'constant':
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

            elif node.type == 'method' and parent_class:
                method_name = None
                for child in node.children:
                    if child.type == 'identifier':
                        method_name = child.text.decode('utf-8')
                        break

                if method_name:
                    for cls in classes:
                        if cls["name"] == parent_class:
                            cls["methods"].append(method_name)
                            break

            for child in node.children:
                traverse(child, parent_class)

        traverse(tree.root_node)
        return classes

    def _extract_functions(self, tree) -> List[Dict[str, Any]]:
        """Extract method definitions from tree-sitter tree."""
        functions = []

        def traverse(node):
            if node.type == 'method':
                func_name = None
                params = []

                for child in node.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                    elif child.type == 'method_parameters':
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
                left_side = None
                for child in node.children:
                    if child.type == 'identifier':
                        left_side = child.text.decode('utf-8')
                        break
                if left_side:
                    variables.append({"name": left_side, "type": "assignment"})

            elif node.type == 'global_variable':
                var_name = node.text.decode('utf-8')
                variables.append({"name": var_name, "type": "global"})

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return variables

    def _extract_dependencies(self, tree) -> List[str]:
        """Extract dependencies from require statements."""
        dependencies = []
        imports = self._extract_imports(tree)

        for imp in imports:
            if imp.get("module"):
                dependencies.append(imp["module"])

        return list(set(dependencies))

    def build_dependency_graph(self, root_path: str) -> Dict[str, Any]:
        """Build dependency graph for Ruby project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": f"Invalid root path: {root_path}", "modules": {}, "dependencies": {}}

        try:
            graph = {"modules": {}, "dependencies": {}}
            root_path = Path(root_path)

            # Find all Ruby files
            rb_files = list(root_path.rglob("*.rb"))

            for rb_file in rb_files:
                if rb_file.is_file():
                    ast_info = self.extract_ast(str(rb_file))
                    if "error" not in ast_info:
                        module_name = self._get_module_name(rb_file, root_path)

                        graph["modules"][module_name] = {
                            "file_path": str(rb_file),
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
        """Detect unsafe Ruby patterns that could lead to security vulnerabilities."""
        unsafe_patterns = []

        # Pattern 1: eval() - dynamic code execution
        if 'eval(' in content:
            for match in re.finditer(r'\beval\s*\(', content):
                unsafe_patterns.append({
                    "type": "dynamic_code_execution",
                    "pattern": "eval()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of eval() for dynamic code execution - high security risk",
                    "severity": "high"
                })

        # Pattern 2: system() and backticks - command injection
        if 'system(' in content or '`' in content:
            for match in re.finditer(r'\bsystem\s*\(', content):
                unsafe_patterns.append({
                    "type": "command_injection",
                    "pattern": "system()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of system() can lead to command injection",
                    "severity": "high"
                })
            for match in re.finditer(r'`[^`]*`', content):
                unsafe_patterns.append({
                    "type": "command_injection",
                    "pattern": "backticks",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of backticks for command execution - injection risk",
                    "severity": "high"
                })

        # Pattern 3: YAML.load() - deserialization vulnerability
        if 'YAML.load' in content:
            for match in re.finditer(r'YAML\.load', content):
                unsafe_patterns.append({
                    "type": "deserialization_vulnerability",
                    "pattern": "YAML.load",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "YAML.load can lead to remote code execution - use YAML.safe_load",
                    "severity": "high"
                })

        # Pattern 4: Marshal.load() - deserialization vulnerability
        if 'Marshal.load' in content:
            for match in re.finditer(r'Marshal\.load', content):
                unsafe_patterns.append({
                    "type": "deserialization_vulnerability",
                    "pattern": "Marshal.load",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Marshal.load can lead to remote code execution",
                    "severity": "high"
                })

        # Pattern 5: SQL injection potential
        if 'ActiveRecord' in content or 'where(' in content:
            for match in re.finditer(r'where\s*\(\s*["\'][^"\']*\s*\+', content):
                unsafe_patterns.append({
                    "type": "sql_injection",
                    "pattern": "string concatenation in where",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "String concatenation in database queries - SQL injection risk",
                    "severity": "high"
                })

        # Pattern 6: XSS potential in Rails
        if 'html_safe' in content or 'raw(' in content:
            for match in re.finditer(r'\.html_safe|\braw\s*\(', content):
                unsafe_patterns.append({
                    "type": "xss_vulnerability",
                    "pattern": match.group(0),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Marking content as safe can lead to XSS - ensure proper sanitization",
                    "severity": "medium"
                })

        # Pattern 7: Weak hash functions
        weak_hashes = ['MD5', 'SHA1']
        for hash_func in weak_hashes:
            if hash_func in content:
                for match in re.finditer(re.escape(hash_func), content):
                    unsafe_patterns.append({
                        "type": "weak_hash",
                        "pattern": hash_func,
                        "line": content[:match.start()].count('\n') + 1,
                        "description": f"Use of weak hash function {hash_func}",
                        "severity": "medium"
                    })

        # Pattern 8: Hardcoded secrets
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']'
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

        # Pattern 9: Use of send() - potential security issue
        if '.send(' in content:
            for match in re.finditer(r'\.send\s*\(', content):
                unsafe_patterns.append({
                    "type": "dynamic_method_call",
                    "pattern": "send()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of send() can bypass encapsulation and lead to security issues",
                    "severity": "medium"
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
