"""Tree-sitter based Scala language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import tree_sitter

from .base_adapter import BaseLanguageAdapter


class TreeSitterScalaAdapter(BaseLanguageAdapter):
    """Tree-sitter based adapter for analyzing Scala repositories."""

    def __init__(self):
        super().__init__("scala")
        self.file_extensions = ['.scala']

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize tree-sitter parser for Scala."""
        try:
            import tree_sitter_scala
            self.language = tree_sitter.Language(tree_sitter_scala.language())
            from tree_sitter import Parser
            self.parser = Parser()
            self.parser.language = self.language
            return True
        except ImportError:
            return super().initialize_parser(language_lib_path)

    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST from Scala file using tree-sitter."""
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
                "error": f"Failed to parse Scala file: {str(e)}",
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
                    if child.type == 'stable_identifier':
                        module_parts = []
                        for part in child.children:
                            if part.type == 'identifier':
                                module_parts.append(part.text.decode('utf-8'))
                        module = '.'.join(module_parts)

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
        """Extract class/object/trait definitions from tree-sitter tree."""
        classes = []

        def traverse(node, parent_class=None):
            if node.type in ['class_definition', 'object_definition', 'trait_definition']:
                class_name = None
                base_classes = []

                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                    elif child.type == 'extends_clause':
                        for base in child.children:
                            if base.type == 'stable_identifier':
                                base_parts = []
                                for part in base.children:
                                    if part.type == 'identifier':
                                        base_parts.append(part.text.decode('utf-8'))
                                base_classes.append('.'.join(base_parts))

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

            elif node.type == 'function_definition' and parent_class:
                func_name = None
                for child in node.children:
                    if child.type == 'identifier':
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
            if node.type == 'function_definition':
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
            if node.type in ['val_definition', 'var_definition']:
                for child in node.children:
                    if child.type == 'pattern':
                        for pattern_part in child.children:
                            if pattern_part.type == 'identifier':
                                var_name = pattern_part.text.decode('utf-8')
                                variables.append({"name": var_name, "type": "variable"})
                                break

            elif node.type == 'assignment':
                left_side = None
                for child in node.children:
                    if child.type == 'identifier':
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
        """Build dependency graph for Scala project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": f"Invalid root path: {root_path}", "modules": {}, "dependencies": {}}

        try:
            graph = {"modules": {}, "dependencies": {}}
            root_path = Path(root_path)

            # Find all Scala files
            scala_files = list(root_path.rglob("*.scala"))

            for scala_file in scala_files:
                if scala_file.is_file():
                    ast_info = self.extract_ast(str(scala_file))
                    if "error" not in ast_info:
                        module_name = self._get_module_name(scala_file, root_path)

                        graph["modules"][module_name] = {
                            "file_path": str(scala_file),
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
        """Detect unsafe Scala patterns that could lead to security vulnerabilities."""
        unsafe_patterns = []

        # Pattern 1: Reflection usage
        if 'java.lang.reflect' in content or 'Class.forName' in content:
            for match in re.finditer(r'(java\.lang\.reflect|Class\.forName)', content):
                unsafe_patterns.append({
                    "type": "reflection_usage",
                    "pattern": match.group(1),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of reflection can bypass security controls",
                    "severity": "medium"
                })

        # Pattern 2: Dynamic code execution
        if 'eval(' in content or 'ToolBox' in content or 'scala.tools' in content:
            for match in re.finditer(r'\beval\(|ToolBox|scala\.tools', content):
                unsafe_patterns.append({
                    "type": "dynamic_code_execution",
                    "pattern": match.group(0),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Dynamic code execution detected",
                    "severity": "high"
                })

        # Pattern 3: SQL injection potential
        if 'executeQuery' in content or 'executeUpdate' in content or 'PreparedStatement' in content:
            for match in re.finditer(r'(executeQuery|executeUpdate|PreparedStatement)', content):
                unsafe_patterns.append({
                    "type": "sql_injection",
                    "pattern": match.group(1),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Database operations detected - ensure parameterized queries",
                    "severity": "medium"
                })

        # Pattern 4: Command injection
        if 'Runtime.getRuntime.exec' in content or 'ProcessBuilder' in content or 'sys.process' in content:
            for match in re.finditer(r'(Runtime\.getRuntime\.exec|ProcessBuilder|sys\.process)', content):
                unsafe_patterns.append({
                    "type": "command_injection",
                    "pattern": match.group(1),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Command execution detected - potential injection",
                    "severity": "high"
                })

        # Pattern 5: Insecure deserialization
        if 'ObjectInputStream' in content and 'readObject' in content:
            for match in re.finditer(r'ObjectInputStream.*readObject', content):
                unsafe_patterns.append({
                    "type": "deserialization_vulnerability",
                    "pattern": "ObjectInputStream.readObject",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Object deserialization can lead to remote code execution",
                    "severity": "high"
                })

        # Pattern 6: Weak hash functions
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

        # Pattern 7: Hardcoded secrets
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

        # Pattern 8: Use of asInstanceOf - unsafe casting
        if 'asInstanceOf' in content:
            for match in re.finditer(r'asInstanceOf', content):
                unsafe_patterns.append({
                    "type": "unsafe_cast",
                    "pattern": "asInstanceOf",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "asInstanceOf can cause ClassCastException - use pattern matching",
                    "severity": "medium"
                })

        # Pattern 9: Insecure random number generation
        if 'scala.util.Random' in content:
            for match in re.finditer(r'scala\.util\.Random', content):
                unsafe_patterns.append({
                    "type": "weak_random",
                    "pattern": "scala.util.Random",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of insecure random number generator",
                    "severity": "medium"
                })

        # Pattern 10: XML external entity vulnerability
        if 'XML.load' in content or 'scala.xml' in content:
            for match in re.finditer(r'XML\.load|scala\.xml', content):
                unsafe_patterns.append({
                    "type": "xxe_vulnerability",
                    "pattern": match.group(0),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "XML processing detected - ensure XXE protection",
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
