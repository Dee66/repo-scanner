"""Tree-sitter based C# language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import tree_sitter

from .base_adapter import BaseLanguageAdapter


class TreeSitterCSharpAdapter(BaseLanguageAdapter):
    """Tree-sitter based adapter for analyzing C# repositories."""

    def __init__(self):
        super().__init__("c_sharp")
        self.file_extensions = ['.cs']

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize tree-sitter parser for C#."""
        try:
            import tree_sitter_c_sharp
            self.language = tree_sitter.Language(tree_sitter_c_sharp.language())
            from tree_sitter import Parser
            self.parser = Parser()
            self.parser.language = self.language
            return True
        except ImportError:
            return super().initialize_parser(language_lib_path)

    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST from C# file using tree-sitter."""
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
                "error": f"Failed to parse C# file: {str(e)}",
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
        """Extract using statements from tree-sitter tree."""
        imports = []

        def traverse(node):
            if node.type == 'using_directive':
                namespace = None
                alias = None

                for child in node.children:
                    if child.type == 'qualified_name':
                        namespace = child.text.decode('utf-8')
                    elif child.type == 'identifier':
                        if namespace is None:
                            namespace = child.text.decode('utf-8')
                        else:
                            alias = child.text.decode('utf-8')

                if namespace:
                    imports.append({
                        "module": namespace,
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
            if node.type == 'class_declaration':
                class_name = None
                base_classes = []

                for child in node.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                    elif child.type == 'base_list':
                        for base in child.children:
                            if base.type == 'name' or base.type == 'qualified_name':
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
        """Extract method declarations from tree-sitter tree."""
        functions = []

        def traverse(node):
            if node.type == 'method_declaration':
                func_name = None
                params = []

                for child in node.children:
                    if child.type == 'name':
                        func_name = child.text.decode('utf-8')
                    elif child.type == 'parameter_list':
                        for param in child.children:
                            if param.type == 'parameter':
                                for param_part in param.children:
                                    if param_part.type == 'name':
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
            if node.type in ['variable_declaration', 'field_declaration']:
                for child in node.children:
                    if child.type == 'variable_declarator':
                        name = None
                        for part in child.children:
                            if part.type == 'name':
                                name = part.text.decode('utf-8')
                                break
                        if name:
                            variables.append({"name": name, "type": "variable"})

            elif node.type == 'assignment_expression':
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
        """Extract namespace dependencies from using statements."""
        dependencies = []
        imports = self._extract_imports(tree)

        for imp in imports:
            if imp.get("module"):
                dependencies.append(imp["module"])

        return list(set(dependencies))

    def build_dependency_graph(self, root_path: str) -> Dict[str, Any]:
        """Build dependency graph for C# project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": f"Invalid root path: {root_path}", "modules": {}, "dependencies": {}}

        try:
            graph = {"modules": {}, "dependencies": {}}
            root_path = Path(root_path)

            # Find all C# files
            cs_files = list(root_path.rglob("*.cs"))

            for cs_file in cs_files:
                if cs_file.is_file():
                    ast_info = self.extract_ast(str(cs_file))
                    if "error" not in ast_info:
                        module_name = self._get_module_name(cs_file, root_path)

                        graph["modules"][module_name] = {
                            "file_path": str(cs_file),
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
        """Detect unsafe C# patterns that could lead to security vulnerabilities."""
        unsafe_patterns = []

        # Pattern 1: unsafe blocks - direct memory manipulation
        if 'unsafe' in content:
            for match in re.finditer(r'\bunsafe\s*{', content):
                unsafe_patterns.append({
                    "type": "unsafe_block",
                    "pattern": "unsafe block",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of unsafe block for direct memory manipulation",
                    "severity": "high"
                })

        # Pattern 2: unsafe functions
        for match in re.finditer(r'\bunsafe\s+\w+\s+\w+\s*\(', content):
            unsafe_patterns.append({
                "type": "unsafe_function",
                "pattern": "unsafe function",
                "line": content[:match.start()].count('\n') + 1,
                "description": "Function declared as unsafe - allows pointer operations",
                "severity": "high"
            })

        # Pattern 3: Reflection usage - can bypass security
        if 'System.Reflection' in content or 'GetType()' in content or 'InvokeMember' in content:
            for match in re.finditer(r'(System\.Reflection|GetType\(\)|InvokeMember)', content):
                unsafe_patterns.append({
                    "type": "reflection_usage",
                    "pattern": match.group(1),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of reflection can bypass security controls",
                    "severity": "medium"
                })

        # Pattern 4: Dynamic code execution
        if 'System.CodeDom' in content or 'CSharpCodeProvider' in content:
            for match in re.finditer(r'(System\.CodeDom|CSharpCodeProvider)', content):
                unsafe_patterns.append({
                    "type": "dynamic_code_execution",
                    "pattern": match.group(1),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Dynamic code compilation/execution detected",
                    "severity": "high"
                })

        # Pattern 5: Unsafe type casting
        for match in re.finditer(r'\(\w+\)\s*\w+', content):
            cast_match = match.group(0)
            # Check if it's a potentially unsafe cast (not basic types)
            if not any(basic in cast_match for basic in ['(int)', '(string)', '(bool)', '(double)', '(float)']):
                unsafe_patterns.append({
                    "type": "unsafe_cast",
                    "pattern": cast_match,
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Potentially unsafe type casting",
                    "severity": "medium"
                })

        # Pattern 6: Pointer usage
        if '*' in content and 'unsafe' in content:
            for match in re.finditer(r'\w+\s*\*\s*\w+', content):
                unsafe_patterns.append({
                    "type": "pointer_usage",
                    "pattern": "pointer declaration",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Pointer usage in unsafe context",
                    "severity": "high"
                })

        # Pattern 7: External DLL calls without proper validation
        if 'DllImport' in content:
            for match in re.finditer(r'\[DllImport', content):
                unsafe_patterns.append({
                    "type": "external_dll_call",
                    "pattern": "DllImport",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "External DLL call - ensure proper validation",
                    "severity": "medium"
                })

        # Pattern 8: Use of obsolete/unsafe APIs
        obsolete_patterns = ['System.Web.Script.Serialization', 'BinaryFormatter']
        for pattern in obsolete_patterns:
            if pattern in content:
                for match in re.finditer(re.escape(pattern), content):
                    unsafe_patterns.append({
                        "type": "obsolete_api",
                        "pattern": pattern,
                        "line": content[:match.start()].count('\n') + 1,
                        "description": f"Use of obsolete/unsafe API: {pattern}",
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
