"""Tree-sitter based Kotlin language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import tree_sitter

from .base_adapter import BaseLanguageAdapter


class TreeSitterKotlinAdapter(BaseLanguageAdapter):
    """Tree-sitter based adapter for analyzing Kotlin repositories."""

    def __init__(self):
        super().__init__("kotlin")
        self.file_extensions = ['.kt', '.kts']

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize tree-sitter parser for Kotlin."""
        try:
            import tree_sitter_kotlin
            self.language = tree_sitter.Language(tree_sitter_kotlin.language())
            from tree_sitter import Parser
            self.parser = Parser()
            self.parser.language = self.language
            return True
        except ImportError:
            return super().initialize_parser(language_lib_path)

    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST from Kotlin file using tree-sitter."""
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
                "error": f"Failed to parse Kotlin file: {str(e)}",
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
            if node.type == 'import_header':
                module = None
                alias = None

                for child in node.children:
                    if child.type == 'identifier':
                        if module is None:
                            module_parts = []
                            # Collect all identifier parts
                            current = child
                            while current:
                                if current.type == 'identifier':
                                    module_parts.insert(0, current.text.decode('utf-8'))
                                if current.next_sibling and current.next_sibling.type == 'dot':
                                    current = current.next_sibling.next_sibling
                                else:
                                    break
                            module = '.'.join(module_parts)
                        else:
                            alias = child.text.decode('utf-8')

                if module:
                    imports.append({
                        "module": module,
                        "alias": alias
                    })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return imports

    def _extract_classes(self, tree) -> List[Dict[str, Any]]:
        """Extract class definitions from tree-sitter tree."""
        classes = []

        def traverse(node, parent_class=None):
            if node.type in ['class_declaration', 'object_declaration']:
                class_name = None
                base_classes = []

                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                    elif child.type == 'inheritance':
                        for base in child.children:
                            if base.type == 'type':
                                for type_part in base.children:
                                    if type_part.type == 'simple_identifier':
                                        base_classes.append(type_part.text.decode('utf-8'))

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
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                    elif child.type == 'parameter_list':
                        for param in child.children:
                            if param.type == 'parameter':
                                for param_part in param.children:
                                    if param_part.type == 'identifier':
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
            if node.type == 'property_declaration':
                for child in node.children:
                    if child.type == 'variable_declaration':
                        for var_part in child.children:
                            if var_part.type == 'simple_identifier':
                                var_name = var_part.text.decode('utf-8')
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
        """Build dependency graph for Kotlin project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": f"Invalid root path: {root_path}", "modules": {}, "dependencies": {}}

        try:
            graph = {"modules": {}, "dependencies": {}}
            root_path = Path(root_path)

            # Find all Kotlin files
            kt_files = []
            for ext in self.file_extensions:
                kt_files.extend(list(root_path.rglob(f"*{ext}")))

            for kt_file in kt_files:
                if kt_file.is_file():
                    ast_info = self.extract_ast(str(kt_file))
                    if "error" not in ast_info:
                        module_name = self._get_module_name(kt_file, root_path)

                        graph["modules"][module_name] = {
                            "file_path": str(kt_file),
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
        """Detect unsafe Kotlin patterns that could lead to security vulnerabilities."""
        unsafe_patterns = []

        # Pattern 1: Use of !! (not-null assertion) - can cause NPE
        if '!!' in content:
            for match in re.finditer(r'\w+!!', content):
                unsafe_patterns.append({
                    "type": "not_null_assertion",
                    "pattern": "not-null assertion",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Not-null assertion can cause NullPointerException",
                    "severity": "medium"
                })

        # Pattern 2: Reflection usage
        if 'java.lang.reflect' in content or '::class.java' in content:
            for match in re.finditer(r'(java\.lang\.reflect|::class\.java)', content):
                unsafe_patterns.append({
                    "type": "reflection_usage",
                    "pattern": match.group(1),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of reflection can bypass security controls",
                    "severity": "medium"
                })

        # Pattern 3: Dynamic code execution
        if 'eval(' in content or 'ScriptEngine' in content:
            for match in re.finditer(r'\beval\(|ScriptEngine', content):
                unsafe_patterns.append({
                    "type": "dynamic_code_execution",
                    "pattern": match.group(0),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Dynamic code execution detected",
                    "severity": "high"
                })

        # Pattern 4: SQL injection potential
        if 'executeQuery' in content or 'executeUpdate' in content:
            for match in re.finditer(r'(executeQuery|executeUpdate)\s*\(\s*["\']', content):
                unsafe_patterns.append({
                    "type": "sql_injection",
                    "pattern": "string literal in SQL execution",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "String literals in SQL execution - potential injection",
                    "severity": "high"
                })

        # Pattern 5: Command injection
        if 'Runtime.getRuntime().exec' in content or 'ProcessBuilder' in content:
            for match in re.finditer(r'(Runtime\.getRuntime\(\)\.exec|ProcessBuilder)', content):
                unsafe_patterns.append({
                    "type": "command_injection",
                    "pattern": match.group(1),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Command execution detected - potential injection",
                    "severity": "high"
                })

        # Pattern 6: Insecure deserialization
        if 'ObjectInputStream' in content and 'readObject' in content:
            for match in re.finditer(r'ObjectInputStream.*readObject', content):
                unsafe_patterns.append({
                    "type": "deserialization_vulnerability",
                    "pattern": "ObjectInputStream.readObject",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Object deserialization can lead to remote code execution",
                    "severity": "high"
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

        # Pattern 9: Use of @SuppressWarnings - can hide security issues
        if '@SuppressWarnings' in content:
            for match in re.finditer(r'@SuppressWarnings', content):
                unsafe_patterns.append({
                    "type": "suppressed_warnings",
                    "pattern": "@SuppressWarnings",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Suppressing warnings can hide security issues",
                    "severity": "low"
                })

        # Pattern 10: Insecure random number generation
        if 'Random()' in content and 'java.util.Random' in content:
            for match in re.finditer(r'java\.util\.Random', content):
                unsafe_patterns.append({
                    "type": "weak_random",
                    "pattern": "java.util.Random",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of insecure random number generator",
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
