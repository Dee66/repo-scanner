"""Tree-sitter based C++ language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import tree_sitter
from tree_sitter import Language

from .base_adapter import BaseLanguageAdapter


class TreeSitterCppAdapter(BaseLanguageAdapter):
    """Tree-sitter based adapter for analyzing C++ repositories."""

    def __init__(self):
        super().__init__("cpp")
        self.file_extensions = ['.cpp', '.cc', '.cxx', '.c++', '.h', '.hpp', '.hxx', '.h++']
        self._ast_cache = {}  # Cache for parsed ASTs
        self._max_cache_size = 100

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize tree-sitter parser for C++."""
        try:
            import tree_sitter_cpp
            self.language = tree_sitter.Language(tree_sitter_cpp.language())
            from tree_sitter import Parser
            self.parser = Parser()
            self.parser.language = self.language
            return True
        except ImportError:
            return super().initialize_parser(language_lib_path)

    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST from C++ file using tree-sitter."""
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
                result = {
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
                return result
            else:
                return {
                    "file_path": file_path,
                    **self._extract_with_regex(content)
                }

        except Exception as e:
            return {
                "file_path": file_path,
                "error": f"Failed to parse C++ file: {str(e)}",
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
        """Extract include directives from tree-sitter tree."""
        includes = []

        def traverse(node):
            if node.type == 'preproc_include':
                # Extract the included file path
                for child in node.children:
                    if child.type == 'string_literal' or child.type == 'system_lib_string':
                        include_path = child.text.decode('utf-8').strip('<>"')
                        includes.append({
                            "module": include_path,
                            "type": "include"
                        })
                    elif child.type == 'identifier':
                        # For #include <identifier> cases
                        include_path = child.text.decode('utf-8')
                        includes.append({
                            "module": include_path,
                            "type": "include"
                        })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return includes

    def _extract_classes(self, tree) -> List[Dict[str, Any]]:
        """Extract class/struct definitions from tree-sitter tree."""
        classes = []

        def traverse(node, parent_class=None):
            if node.type in ['class_specifier', 'struct_specifier']:
                class_name = None
                base_classes = []

                for child in node.children:
                    if child.type == 'type_identifier':
                        class_name = child.text.decode('utf-8')
                    elif child.type == 'base_class_clause':
                        # Extract base classes
                        for base_child in child.children:
                            if base_child.type == 'type_identifier':
                                base_classes.append(base_child.text.decode('utf-8'))

                if class_name:
                    classes.append({
                        "name": class_name,
                        "bases": base_classes,
                        "parent_class": parent_class,
                        "methods": []
                    })

            for child in node.children:
                traverse(child)

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
                    if child.type == 'function_declarator':
                        for decl_child in child.children:
                            if decl_child.type == 'identifier':
                                func_name = decl_child.text.decode('utf-8')
                            elif decl_child.type == 'parameter_list':
                                # Extract parameters
                                for param in decl_child.children:
                                    if param.type == 'parameter_declaration':
                                        param_name = None
                                        param_type = None
                                        for p_child in param.children:
                                            if p_child.type == 'type_identifier':
                                                param_type = p_child.text.decode('utf-8')
                                            elif p_child.type == 'identifier':
                                                param_name = p_child.text.decode('utf-8')
                                        if param_name and param_type:
                                            params.append({"name": param_name, "type": param_type})

                if func_name:
                    functions.append({
                        "name": func_name,
                        "parameters": params,
                        "return_type": None  # Could be extracted from declarator
                    })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return functions

    def _extract_methods(self, tree) -> List[Dict[str, Any]]:
        """Extract method definitions from tree-sitter tree."""
        methods = []

        def traverse(node, class_context=None):
            if node.type == 'function_definition':
                # Check if we're inside a class/struct
                if class_context:
                    func_name = None
                    params = []

                    for child in node.children:
                        if child.type == 'function_declarator':
                            for decl_child in child.children:
                                if decl_child.type == 'identifier':
                                    func_name = decl_child.text.decode('utf-8')
                                elif decl_child.type == 'parameter_list':
                                    for param in decl_child.children:
                                        if param.type == 'parameter_declaration':
                                            param_name = None
                                            param_type = None
                                            for p_child in param.children:
                                                if p_child.type == 'type_identifier':
                                                    param_type = p_child.text.decode('utf-8')
                                                elif p_child.type == 'identifier':
                                                    param_name = p_child.text.decode('utf-8')
                                            if param_name and param_type:
                                                params.append({"name": param_name, "type": param_type})

                    if func_name:
                        methods.append({
                            "name": func_name,
                            "class": class_context,
                            "parameters": params,
                            "return_type": None
                        })

            elif node.type in ['class_specifier', 'struct_specifier']:
                class_name = None
                for child in node.children:
                    if child.type == 'type_identifier':
                        class_name = child.text.decode('utf-8')
                        break

                # Traverse children with class context
                for child in node.children:
                    traverse(child, class_name)

            else:
                for child in node.children:
                    traverse(child, class_context)

        traverse(tree.root_node)
        return methods

    def _extract_variables(self, tree) -> List[Dict[str, Any]]:
        """Extract variable declarations from tree-sitter tree."""
        variables = []

        def traverse(node):
            if node.type == 'declaration':
                var_type = None
                var_names = []

                for child in node.children:
                    if child.type in ['primitive_type', 'type_identifier']:
                        var_type = child.text.decode('utf-8')
                    elif child.type == 'init_declarator':
                        for decl_child in child.children:
                            if decl_child.type == 'identifier':
                                var_names.append(decl_child.text.decode('utf-8'))

                for var_name in var_names:
                    variables.append({
                        "name": var_name,
                        "type": var_type
                    })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return variables

    def _calculate_complexity(self, tree) -> int:
        """Calculate cyclomatic complexity from tree-sitter tree."""
        complexity = 1  # Base complexity

        def traverse(node):
            nonlocal complexity
            # Increment for control flow statements
            if node.type in ['if_statement', 'for_statement', 'while_statement',
                           'do_statement', 'switch_statement', 'conditional_expression',
                           'catch_clause', '&&', '||']:
                complexity += 1

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return complexity

    def _extract_dependencies(self, tree) -> List[str]:
        """Extract dependencies from includes."""
        includes = self._extract_imports(tree)
        return [inc.get("module", "") for inc in includes if inc.get("module")]

    def _detect_unsafe_patterns(self, content: str, tree) -> List[Dict[str, Any]]:
        """Detect unsafe C++ patterns that could lead to security vulnerabilities."""
        unsafe_patterns = []

        # Pattern 1: Raw pointer usage (potential for memory leaks, null pointer dereference)
        pointer_patterns = [
            r'\b\w+\s*\*\s*\w+',  # Variable declarations with *
            r'new\s+\w+',         # new without delete
            r'malloc\s*\(',       # malloc calls
            r'free\s*\(',         # free calls (manual memory management)
        ]

        for pattern in pointer_patterns:
            for match in re.finditer(pattern, content):
                unsafe_patterns.append({
                    "type": "raw_pointer_usage",
                    "pattern": pattern,
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Raw pointer usage detected - consider using smart pointers",
                    "severity": "medium"
                })

        # Pattern 2: Unsafe type casting
        cast_patterns = [
            r'reinterpret_cast\s*<',
            r'const_cast\s*<',
            r'\(\w+\*\)',        # C-style casts to pointers
        ]

        for pattern in cast_patterns:
            for match in re.finditer(pattern, content):
                unsafe_patterns.append({
                    "type": "unsafe_cast",
                    "pattern": pattern,
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Unsafe type casting detected",
                    "severity": "high"
                })

        # Pattern 3: Array access without bounds checking
        array_patterns = [
            r'\w+\s*\[\s*\w+\s*\]',  # Array access
        ]

        for pattern in array_patterns:
            for match in re.finditer(pattern, content):
                unsafe_patterns.append({
                    "type": "unchecked_array_access",
                    "pattern": pattern,
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Array access without bounds checking",
                    "severity": "medium"
                })

        # Pattern 4: Use of unsafe C functions
        unsafe_functions = [
            'strcpy', 'strcat', 'sprintf', 'gets', 'scanf',
            'memcpy', 'memmove', 'memset'  # Without proper size checking
        ]

        for func in unsafe_functions:
            pattern = rf'\b{func}\s*\('
            for match in re.finditer(pattern, content):
                unsafe_patterns.append({
                    "type": "unsafe_function_call",
                    "pattern": func,
                    "line": content[:match.start()].count('\n') + 1,
                    "description": f"Call to unsafe function '{func}'",
                    "severity": "high"
                })

        # Pattern 5: Missing const correctness
        # This is harder to detect reliably, but we can look for some patterns
        mutable_patterns = [
            r'char\s*\*\s*\w+',  # Non-const char pointers
        ]

        for pattern in mutable_patterns:
            for match in re.finditer(pattern, content):
                unsafe_patterns.append({
                    "type": "mutable_pointer",
                    "pattern": pattern,
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Mutable pointer detected - consider const correctness",
                    "severity": "low"
                })

        return unsafe_patterns

    def build_dependency_graph(self, root_path: str) -> Dict[str, Any]:
        """Build dependency graph for C++ project."""
        graph = {"modules": {}, "dependencies": {}}

        try:
            root_path_obj = Path(root_path)

            for ext in self.file_extensions:
                for file_path in root_path_obj.rglob(f"*{ext}"):
                    if file_path.is_file():
                        try:
                            ast_info = self.extract_ast(str(file_path))
                            module_name = self._get_module_name(file_path, root_path_obj)

                            graph["modules"][module_name] = {
                                "file_path": str(file_path),
                                "classes": [cls["name"] for cls in ast_info.get("classes", [])],
                                "functions": [func["name"] for func in ast_info.get("functions", [])]
                            }

                            # Add dependencies
                            for inc in ast_info.get("includes", []):
                                if inc.get("module"):
                                    if module_name not in graph["dependencies"]:
                                        graph["dependencies"][module_name] = []
                                    if inc["module"] not in graph["dependencies"][module_name]:
                                        graph["dependencies"][module_name].append(inc["module"])

                        except Exception as e:
                            continue

            return graph

        except Exception as e:
            return {"error": f"Failed to build dependency graph: {str(e)}", "modules": {}, "dependencies": {}}

    def _get_module_name(self, file_path: Path, root_path: Path) -> str:
        """Get module name from file path."""
        try:
            relative_path = file_path.relative_to(root_path)
            module_name = str(relative_path.with_suffix(''))
            return module_name
        except ValueError:
            return str(file_path.with_suffix(''))