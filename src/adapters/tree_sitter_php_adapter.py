"""Tree-sitter based PHP language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import tree_sitter

from .base_adapter import BaseLanguageAdapter


class TreeSitterPHPAdapter(BaseLanguageAdapter):
    """Tree-sitter based adapter for analyzing PHP repositories."""

    def __init__(self):
        super().__init__("php")
        self.file_extensions = ['.php']

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize tree-sitter parser for PHP."""
        try:
            import tree_sitter_php
            self.language = tree_sitter.Language(tree_sitter_php.language_php())
            from tree_sitter import Parser
            self.parser = Parser()
            self.parser.language = self.language
            return True
        except ImportError:
            return super().initialize_parser(language_lib_path)

    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST from PHP file using tree-sitter."""
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
                "error": f"Failed to parse PHP file: {str(e)}",
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
        """Extract use statements and include/require from tree-sitter tree."""
        imports = []

        def traverse(node):
            if node.type in ['use_declaration', 'use_statement']:
                namespace = None
                alias = None

                for child in node.children:
                    if child.type == 'qualified_name':
                        namespace = child.text.decode('utf-8')
                    elif child.type == 'name':
                        if namespace is None:
                            namespace = child.text.decode('utf-8')
                        else:
                            alias = child.text.decode('utf-8')

                if namespace:
                    imports.append({
                        "module": namespace,
                        "alias": alias
                    })

            elif node.type in ['include_expression', 'include_once_expression',
                             'require_expression', 'require_once_expression']:
                # Handle include/require statements
                for child in node.children:
                    if child.type == 'string':
                        module = child.text.decode('utf-8').strip('"\'')

                        # Remove file extensions for module detection
                        if module.endswith(('.php', '.inc')):
                            module = module.rsplit('.', 1)[0]

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
            if node.type == 'class_declaration':
                class_name = None
                base_classes = []

                for child in node.children:
                    if child.type == 'name':
                        class_name = child.text.decode('utf-8')
                    elif child.type == 'base_clause':
                        for base in child.children:
                            if base.type == 'qualified_name':
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

            elif node.type == 'method_declaration' and parent_class:
                method_name = None
                for child in node.children:
                    if child.type == 'name':
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
        """Extract function definitions from tree-sitter tree."""
        functions = []

        def traverse(node):
            if node.type == 'function_definition':
                func_name = None
                params = []

                for child in node.children:
                    if child.type == 'name':
                        func_name = child.text.decode('utf-8')
                    elif child.type == 'formal_parameters':
                        for param in child.children:
                            if param.type == 'simple_parameter':
                                for param_part in param.children:
                                    if param_part.type == 'variable_name':
                                        param_name = param_part.text.decode('utf-8').lstrip('$')
                                        params.append(param_name)
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
            if node.type == 'assignment_expression':
                left_side = None
                for child in node.children:
                    if child.type == 'variable_name':
                        left_side = child.text.decode('utf-8').lstrip('$')
                        break
                if left_side:
                    variables.append({"name": left_side, "type": "assignment"})

            elif node.type == 'global_declaration':
                for child in node.children:
                    if child.type == 'variable_name':
                        var_name = child.text.decode('utf-8').lstrip('$')
                        variables.append({"name": var_name, "type": "global"})

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return variables

    def _extract_dependencies(self, tree) -> List[str]:
        """Extract dependencies from use statements and includes."""
        dependencies = []
        imports = self._extract_imports(tree)

        for imp in imports:
            if imp.get("module"):
                dependencies.append(imp["module"])

        return list(set(dependencies))

    def build_dependency_graph(self, root_path: str) -> Dict[str, Any]:
        """Build dependency graph for PHP project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": f"Invalid root path: {root_path}", "modules": {}, "dependencies": {}}

        try:
            graph = {"modules": {}, "dependencies": {}}
            root_path = Path(root_path)

            # Find all PHP files
            php_files = list(root_path.rglob("*.php"))

            for php_file in php_files:
                if php_file.is_file():
                    ast_info = self.extract_ast(str(php_file))
                    if "error" not in ast_info:
                        module_name = self._get_module_name(php_file, root_path)

                        graph["modules"][module_name] = {
                            "file_path": str(php_file),
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
        """Detect unsafe PHP patterns that could lead to security vulnerabilities."""
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

        # Pattern 2: unserialize() - deserialization vulnerability
        if 'unserialize(' in content:
            for match in re.finditer(r'\bunserialize\s*\(', content):
                unsafe_patterns.append({
                    "type": "deserialization_vulnerability",
                    "pattern": "unserialize()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of unserialize() can lead to remote code execution",
                    "severity": "high"
                })

        # Pattern 3: SQL injection potential
        if '$_' in content and ('mysql_' in content or 'mysqli_' in content or 'pdo' in content.lower()):
            for match in re.finditer(r'\$_(?:GET|POST|REQUEST|COOKIE)\[', content):
                unsafe_patterns.append({
                    "type": "sql_injection",
                    "pattern": "direct user input in SQL",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Direct use of user input in database queries - SQL injection risk",
                    "severity": "high"
                })

        # Pattern 4: Command injection
        if 'exec(' in content or 'system(' in content or 'shell_exec(' in content or 'passthru(' in content:
            for match in re.finditer(r'\b(exec|system|shell_exec|passthru)\s*\(', content):
                unsafe_patterns.append({
                    "type": "command_injection",
                    "pattern": f"{match.group(1)}()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": f"Use of {match.group(1)}() can lead to command injection",
                    "severity": "high"
                })

        # Pattern 5: File inclusion vulnerabilities
        if 'include(' in content or 'require(' in content or 'include_once(' in content or 'require_once(' in content:
            for match in re.finditer(r'\b(include|require|include_once|require_once)\s*\(', content):
                unsafe_patterns.append({
                    "type": "file_inclusion",
                    "pattern": f"{match.group(1)}()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": f"Use of {match.group(1)}() - potential remote file inclusion",
                    "severity": "high"
                })

        # Pattern 6: XSS potential
        if 'echo' in content and ('$_' in content or '$user' in content.lower()):
            for match in re.finditer(r'\becho\s+.*?\$_', content):
                unsafe_patterns.append({
                    "type": "xss_vulnerability",
                    "pattern": "echo with user input",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Direct output of user input - potential XSS vulnerability",
                    "severity": "medium"
                })

        # Pattern 7: Weak hash functions
        weak_hashes = ['md5(', 'sha1(']
        for hash_func in weak_hashes:
            if hash_func in content:
                for match in re.finditer(re.escape(hash_func), content):
                    unsafe_patterns.append({
                        "type": "weak_hash",
                        "pattern": hash_func.rstrip('('),
                        "line": content[:match.start()].count('\n') + 1,
                        "description": f"Use of weak hash function {hash_func.rstrip('(')}",
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

        # Pattern 9: Use of deprecated functions
        deprecated_funcs = ['mysql_', 'ereg', 'split']
        for func in deprecated_funcs:
            if func in content:
                for match in re.finditer(re.escape(func), content):
                    unsafe_patterns.append({
                        "type": "deprecated_api",
                        "pattern": func,
                        "line": content[:match.start()].count('\n') + 1,
                        "description": f"Use of deprecated function: {func}",
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
