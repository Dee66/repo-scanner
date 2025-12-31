"""Tree-sitter based JavaScript/TypeScript language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import tree_sitter

from .base_adapter import BaseLanguageAdapter


class TreeSitterJavaScriptAdapter(BaseLanguageAdapter):
    """Tree-sitter based adapter for analyzing JavaScript and TypeScript repositories."""

    def __init__(self, language_name: str = "javascript"):
        super().__init__(language_name)
        if language_name == "javascript":
            self.file_extensions = ['.js', '.jsx', '.mjs', '.cjs']
        elif language_name == "typescript":
            self.file_extensions = ['.ts', '.tsx']
        else:
            self.file_extensions = ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize tree-sitter parser for JavaScript/TypeScript."""
        try:
            if self.language_name == "typescript":
                import tree_sitter_typescript
                self.language = tree_sitter.Language(tree_sitter_typescript.language_typescript())
            else:
                import tree_sitter_javascript
                self.language = tree_sitter.Language(tree_sitter_javascript.language())

            from tree_sitter import Parser
            self.parser = Parser()
            self.parser.language = self.language
            return True
        except ImportError:
            return super().initialize_parser(language_lib_path)

    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST from JavaScript/TypeScript file using tree-sitter."""
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
                "error": f"Failed to parse {self.language_name} file: {str(e)}",
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
            if node.type in ['import_statement', 'import_declaration']:
                # Handle ES6 imports: import { foo } from 'module'
                # Handle CommonJS: const foo = require('module')
                source = None
                specifiers = []

                for child in node.children:
                    if child.type == 'string':
                        source = child.text.decode('utf-8').strip('"\'')

                    elif child.type == 'import_clause':
                        for specifier in child.children:
                            if specifier.type in ['named_imports', 'namespace_import']:
                                for spec in specifier.children:
                                    if spec.type == 'import_specifier':
                                        name = None
                                        alias = None
                                        for part in spec.children:
                                            if part.type == 'name':
                                                if name is None:
                                                    name = part.text.decode('utf-8')
                                                else:
                                                    alias = part.text.decode('utf-8')
                                        if name:
                                            specifiers.append({"name": name, "alias": alias})
                                    elif spec.type == 'namespace_import':
                                        # import * as foo
                                        alias = None
                                        for part in spec.children:
                                            if part.type == 'name':
                                                alias = part.text.decode('utf-8')
                                        specifiers.append({"name": "*", "alias": alias})

                if source:
                    for spec in specifiers:
                        imports.append({
                            "module": source,
                            "name": spec["name"],
                            "alias": spec["alias"]
                        })

            elif node.type == 'call_expression':
                # Handle CommonJS require() calls
                if self._is_require_call(node):
                    module_name = self._extract_require_module(node)
                    if module_name:
                        imports.append({
                            "module": module_name,
                            "name": None,
                            "alias": None
                        })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return imports

    def _is_require_call(self, node) -> bool:
        """Check if a call expression is a require() call."""
        for child in node.children:
            if child.type == 'identifier' and child.text.decode('utf-8') == 'require':
                return True
        return False

    def _extract_require_module(self, node) -> Optional[str]:
        """Extract module name from require() call."""
        for child in node.children:
            if child.type == 'arguments':
                for arg in child.children:
                    if arg.type == 'string':
                        return arg.text.decode('utf-8').strip('"\'')

        return None

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
                    elif child.type == 'class_heritage':
                        # Extract base classes
                        for heritage in child.children:
                            if heritage.type == 'name':
                                base_classes.append(heritage.text.decode('utf-8'))

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

            elif node.type == 'method_definition' and parent_class:
                # This is a method
                method_name = None
                for child in node.children:
                    if child.type == 'property_identifier':
                        method_name = child.text.decode('utf-8')
                        break

                if method_name:
                    # Find the class this method belongs to
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
            if node.type in ['function_declaration', 'function_expression', 'arrow_function']:
                func_name = None
                params = []

                for child in node.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                    elif child.type == 'formal_parameters':
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
        """Extract variable declarations from tree-sitter tree."""
        variables = []

        def traverse(node):
            if node.type in ['variable_declaration', 'lexical_declaration']:
                for child in node.children:
                    if child.type == 'variable_declarator':
                        name = None
                        for part in child.children:
                            if part.type == 'identifier':
                                name = part.text.decode('utf-8')
                                break
                        if name:
                            variables.append({"name": name, "type": "variable"})

            elif node.type == 'assignment_expression':
                # Handle assignments like 'x = 1'
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
        """Extract module dependencies from imports."""
        dependencies = []
        imports = self._extract_imports(tree)

        for imp in imports:
            if imp.get("module"):
                dependencies.append(imp["module"])

        return list(set(dependencies))

    def build_dependency_graph(self, root_path: str) -> Dict[str, Any]:
        """Build dependency graph for JavaScript/TypeScript project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": f"Invalid root path: {root_path}", "modules": {}, "dependencies": {}}

        try:
            graph = {"modules": {}, "dependencies": {}}
            root_path = Path(root_path)

            # Find all JS/TS files
            js_files = []
            for ext in self.file_extensions:
                js_files.extend(list(root_path.rglob(f"*{ext}")))

            for js_file in js_files:
                if js_file.is_file():
                    ast_info = self.extract_ast(str(js_file))
                    if "error" not in ast_info:
                        module_name = self._get_module_name(js_file, root_path)

                        graph["modules"][module_name] = {
                            "file_path": str(js_file),
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
        """Detect unsafe JavaScript patterns that could lead to security vulnerabilities."""
        unsafe_patterns = []

        # Pattern 1: Use of eval() - dynamic code execution
        if 'eval(' in content:
            for match in re.finditer(r'\beval\s*\(', content):
                unsafe_patterns.append({
                    "type": "dynamic_code_execution",
                    "pattern": "eval()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of eval() for dynamic code execution - high security risk",
                    "severity": "high"
                })

        # Pattern 2: innerHTML assignment - XSS vulnerability
        if 'innerHTML' in content:
            for match in re.finditer(r'\.innerHTML\s*=', content):
                unsafe_patterns.append({
                    "type": "xss_vulnerability",
                    "pattern": "innerHTML assignment",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Direct innerHTML assignment can lead to XSS attacks",
                    "severity": "high"
                })

        # Pattern 3: document.write() - can lead to XSS
        if 'document.write' in content:
            for match in re.finditer(r'\bdocument\.write\s*\(', content):
                unsafe_patterns.append({
                    "type": "dom_manipulation",
                    "pattern": "document.write()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "document.write() can lead to XSS and performance issues",
                    "severity": "medium"
                })

        # Pattern 4: Use of Function constructor
        if 'new Function' in content:
            for match in re.finditer(r'\bnew\s+Function\s*\(', content):
                unsafe_patterns.append({
                    "type": "dynamic_code_execution",
                    "pattern": "new Function()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Function constructor creates code from strings - security risk",
                    "severity": "high"
                })

        # Pattern 5: setTimeout/setInterval with string code
        for func in ['setTimeout', 'setInterval']:
            pattern = rf'\b{func}\s*\(\s*["\']'
            for match in re.finditer(pattern, content):
                unsafe_patterns.append({
                    "type": "dynamic_code_execution",
                    "pattern": f"{func} with string",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": f"{func} with string argument executes code dynamically",
                    "severity": "medium"
                })

        # Pattern 6: Prototype pollution potential
        if '__proto__' in content or 'constructor.prototype' in content:
            for match in re.finditer(r'(__proto__|constructor\.prototype)', content):
                unsafe_patterns.append({
                    "type": "prototype_pollution",
                    "pattern": match.group(1),
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Potential prototype pollution vulnerability",
                    "severity": "high"
                })

        # Pattern 7: Use of localStorage/sessionStorage without validation
        for storage in ['localStorage', 'sessionStorage']:
            if storage in content:
                for match in re.finditer(rf'\b{storage}\.setItem\s*\(', content):
                    unsafe_patterns.append({
                        "type": "storage_manipulation",
                        "pattern": f"{storage}.setItem",
                        "line": content[:match.start()].count('\n') + 1,
                        "description": f"Direct {storage} manipulation - consider input validation",
                        "severity": "low"
                    })

        return unsafe_patterns
