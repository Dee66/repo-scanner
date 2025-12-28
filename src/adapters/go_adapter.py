"""Go language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set


class GoAdapter:
    """Adapter for analyzing Go repositories."""

    def __init__(self):
        # Common Go file extensions
        self.go_extensions = {'.go'}
        # Test file patterns
        self.test_patterns = ['_test.go']

    def extract_ast(self, file_path: str) -> dict:
        """Extract AST-like information from Go file using regex parsing."""
        if not isinstance(file_path, str) or not file_path:
            return {"error": "Invalid file path"}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (FileNotFoundError, UnicodeDecodeError) as e:
            return {"error": f"Failed to read file: {str(e)}"}

        ast_info = {
            "functions": [],
            "methods": [],
            "structs": [],
            "interfaces": [],
            "types": [],
            "imports": [],
            "constants": [],
            "variables": [],
            "packages": []
        }

        # Extract package declaration
        package_match = re.search(r'package\s+(\w+)', content)
        if package_match:
            ast_info["packages"] = [package_match.group(1)]

        # Extract imports
        import_block = re.findall(r'import\s*\(\s*([^)]+)\s*\)', content, re.DOTALL)
        if import_block:
            # Multi-line import block
            for block in import_block:
                imports = re.findall(r'["\']([^"\']+)["\']', block)
                ast_info["imports"].extend(imports)
        else:
            # Single line imports
            single_imports = re.findall(r'import\s+["\']([^"\']+)["\']', content)
            ast_info["imports"].extend(single_imports)

        # Extract functions
        function_pattern = r'func\s+(\w+)\s*\('
        functions = re.findall(function_pattern, content)
        ast_info["functions"] = functions

        # Extract methods (functions with receivers)
        method_pattern = r'func\s*\([^)]+\)\s*(\w+)\s*\('
        methods = re.findall(method_pattern, content)
        ast_info["methods"] = methods

        # Extract structs
        struct_pattern = r'type\s+(\w+)\s+struct\s*\{'
        ast_info["structs"] = re.findall(struct_pattern, content)

        # Extract interfaces
        interface_pattern = r'type\s+(\w+)\s+interface\s*\{'
        ast_info["interfaces"] = re.findall(interface_pattern, content)

        # Extract type definitions
        type_pattern = r'type\s+(\w+)\s+(?!struct|interface|func)'
        types = re.findall(type_pattern, content)
        ast_info["types"] = types

        # Extract constants
        const_pattern = r'const\s+(\w+)\s*[:=]'
        ast_info["constants"] = re.findall(const_pattern, content)

        # Extract variables (var declarations)
        var_pattern = r'var\s+(\w+)\s*[:=]'
        ast_info["variables"] = re.findall(var_pattern, content)

        return ast_info

    def build_dependency_graph(self, root_path: str) -> dict:
        """Build dependency graph for Go project from go.mod."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": "Invalid root path"}

        root_path = Path(root_path)

        # Look for go.mod
        go_mod_path = root_path / "go.mod"
        if not go_mod_path.exists():
            return {"error": "go.mod not found"}

        try:
            with open(go_mod_path, 'r', encoding='utf-8') as f:
                go_mod_content = f.read()
        except (FileNotFoundError, UnicodeDecodeError) as e:
            return {"error": f"Failed to read go.mod: {str(e)}"}

        dependencies = {}
        module_name = ""

        # Extract module name
        module_match = re.search(r'module\s+([^\s]+)', go_mod_content)
        if module_match:
            module_name = module_match.group(1)

        # Extract require block
        require_block = re.search(r'require\s*\(\s*([^)]+)\s*\)', go_mod_content, re.DOTALL)
        if require_block:
            # Multi-line require block
            deps = re.findall(r'([^\s]+)\s+v[^\s]+', require_block.group(1))
            for dep in deps:
                dependencies[dep] = "latest"  # Version not extracted in this simple parser
        else:
            # Single line requires
            single_deps = re.findall(r'require\s+([^\s]+)\s+v[^\s]+', go_mod_content)
            for dep in single_deps:
                dependencies[dep] = "latest"

        # Analyze internal dependencies
        internal_deps = self._analyze_internal_dependencies(root_path)

        return {
            "module_name": module_name,
            "dependencies": dependencies,
            "internal_dependencies": internal_deps
        }

    def _analyze_internal_dependencies(self, root_path: Path) -> dict:
        """Analyze internal package dependencies."""
        internal_deps = {}

        for go_file in root_path.rglob("*.go"):
            try:
                with open(go_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Find imports from the same module
                imports = re.findall(r'import\s+["\']([^"\']+)["\']', content)
                imports.extend(re.findall(r'["\']([^"\']+)["\']', re.search(r'import\s*\(\s*([^)]+)\s*\)', content, re.DOTALL).group(1) if re.search(r'import\s*\(\s*([^)]+)\s*\)', content, re.DOTALL) else ""))

                # Filter to internal imports (relative or same module)
                internal_imports = [imp for imp in imports if imp.startswith('./') or imp.startswith('../') or not imp.startswith('golang.org/') and not imp.startswith('github.com/') and not imp.startswith('gopkg.in/')]

                if internal_imports:
                    rel_path = go_file.relative_to(root_path)
                    internal_deps[str(rel_path)] = internal_imports

            except (FileNotFoundError, UnicodeDecodeError):
                continue

        return internal_deps

    def discover_tests(self, root_path: str) -> list:
        """Discover test files and functions in Go project."""
        if not isinstance(root_path, str) or not root_path:
            return []

        root_path = Path(root_path)
        test_info = []

        for go_file in root_path.rglob("*.go"):
            if str(go_file).endswith('_test.go'):
                try:
                    with open(go_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Extract test functions
                    test_functions = re.findall(r'func\s+(Test\w+)\s*\(', content)
                    benchmark_functions = re.findall(r'func\s+(Benchmark\w+)\s*\(', content)
                    example_functions = re.findall(r'func\s+(Example\w+)\s*\(', content)

                    test_info.append({
                        "file": str(go_file.relative_to(root_path)),
                        "type": "test_file",
                        "test_functions": test_functions,
                        "benchmark_functions": benchmark_functions,
                        "example_functions": example_functions
                    })

                except (FileNotFoundError, UnicodeDecodeError):
                    continue

        return test_info

    def extract_documentation(self, file_path: str) -> dict:
        """Extract documentation comments from Go file."""
        if not isinstance(file_path, str) or not file_path:
            return {"error": "Invalid file path"}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (FileNotFoundError, UnicodeDecodeError) as e:
            return {"error": f"Failed to read file: {str(e)}"}

        docs = {
            "package_docs": [],
            "function_docs": {},
            "method_docs": {},
            "type_docs": {},
            "const_docs": {},
            "var_docs": {}
        }

        current_doc = []
        in_doc = False

        for i, line in enumerate(lines):
            line = line.strip()

            # Start of Go documentation comment
            if line.startswith('//') and not line.startswith('///'):
                in_doc = True
                current_doc.append(line[2:].strip())
            elif in_doc and line.startswith('//') and not line.startswith('///'):
                current_doc.append(line[2:].strip())
            else:
                if in_doc:
                    # Process the collected documentation
                    doc_text = " ".join(current_doc).strip()

                    # Look ahead to find what this documentation is for
                    found_target = False
                    for j in range(i, min(i + 5, len(lines))):
                        next_line = lines[j].strip()
                        if next_line.startswith('package '):
                            package_match = re.search(r'package\s+(\w+)', next_line)
                            if package_match:
                                docs["package_docs"].append(doc_text)
                                found_target = True
                                break
                        elif next_line.startswith('func '):
                            func_match = re.search(r'func\s+(?:\([^)]+\)\s*)?(\w+)\s*\(', next_line)
                            if func_match:
                                func_name = func_match.group(1)
                                if '(' in next_line and ')' in next_line[:next_line.find(func_name)]:
                                    docs["method_docs"][func_name] = doc_text
                                else:
                                    docs["function_docs"][func_name] = doc_text
                                found_target = True
                                break
                        elif next_line.startswith('type '):
                            type_match = re.search(r'type\s+(\w+)', next_line)
                            if type_match:
                                docs["type_docs"][type_match.group(1)] = doc_text
                                found_target = True
                                break
                        elif next_line.startswith('const '):
                            const_match = re.search(r'const\s+(\w+)', next_line)
                            if const_match:
                                docs["const_docs"][const_match.group(1)] = doc_text
                                found_target = True
                                break
                        elif next_line.startswith('var '):
                            var_match = re.search(r'var\s+(\w+)', next_line)
                            if var_match:
                                docs["var_docs"][var_match.group(1)] = doc_text
                                found_target = True
                                break
                        elif next_line == "" or not next_line:
                            continue
                        else:
                            break

                    current_doc = []
                    in_doc = False

        return docs