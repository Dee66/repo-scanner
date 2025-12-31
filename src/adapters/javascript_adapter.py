"""JavaScript/TypeScript language adapter for repository analysis."""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set

from .base_adapter import BaseLanguageAdapter


class JavaScriptAdapter(BaseLanguageAdapter):
    """Adapter for analyzing JavaScript and TypeScript repositories."""

    def __init__(self):
        super().__init__("javascript")
        # Common JavaScript/TypeScript file extensions
        self.file_extensions = ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']
        # Test file patterns
        self.test_patterns = [
            r'\.test\.',
            r'\.spec\.',
            r'__tests__',
            r'tests?',
            r'spec'
        ]

    def extract_ast(self, file_path: str) -> dict:
        """Extract AST-like information from JavaScript/TypeScript file using regex parsing."""
        if not isinstance(file_path, str) or not file_path:
            return {"error": "Invalid file path"}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (FileNotFoundError, UnicodeDecodeError) as e:
            return {"error": f"Failed to read file: {str(e)}"}

        ast_info = {
            "functions": [],
            "classes": [],
            "interfaces": [],
            "types": [],
            "imports": [],
            "exports": [],
            "react_components": [],
            "async_functions": [],
            "arrow_functions": [],
            "variables": [],
            "constants": []
        }

        # Extract regular functions
        function_pattern = r'(?:function\s+|(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?function\s+|(?:export\s+)?(?:async\s+)?function\s+)\s*(\w+)\s*\('
        ast_info["functions"] = re.findall(function_pattern, content)

        # Extract arrow functions (named ones)
        arrow_pattern = r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>'
        ast_info["arrow_functions"] = re.findall(arrow_pattern, content)

        # Extract classes
        class_pattern = r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)'
        ast_info["classes"] = re.findall(class_pattern, content)

        # Extract TypeScript interfaces
        interface_pattern = r'(?:export\s+)?interface\s+(\w+)'
        ast_info["interfaces"] = re.findall(interface_pattern, content)

        # Extract TypeScript types
        type_pattern = r'(?:export\s+)?type\s+(\w+)\s*='
        ast_info["types"] = re.findall(type_pattern, content)

        # Extract imports
        import_pattern = r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]'
        ast_info["imports"] = re.findall(import_pattern, content)

        # Extract exports
        export_pattern = r'export\s+(?:const|let|var|function|class|interface|type)\s+(\w+)'
        ast_info["exports"] = re.findall(export_pattern, content)

        # Extract React components (simplified - look for functions that return JSX)
        react_components = []
        # Look for arrow function components
        arrow_components = re.findall(r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\{', content)
        react_components.extend(arrow_components)

        # Look for function components
        func_components = re.findall(r'function\s+(\w+)\s*\([^)]*\)\s*\{[^}]*return\s*\(', content)
        react_components.extend(func_components)

        # Look for class components
        class_components = re.findall(r'class\s+(\w+)\s+extends\s+React\.Component', content)
        react_components.extend(class_components)

        ast_info["react_components"] = list(set(react_components))

        # Extract async functions
        async_pattern = r'async\s+(?:function\s+|(?:const|let|var)\s+\w+\s*=\s*)\s*(\w+)\s*\('
        ast_info["async_functions"] = re.findall(async_pattern, content)

        # Extract constants and variables
        const_pattern = r'(?:const|let|var)\s+(\w+)\s*[:=]'
        declarations = re.findall(const_pattern, content)
        # Filter out functions and classes already captured
        ast_info["variables"] = [decl for decl in declarations
                                if decl not in ast_info["functions"]
                                and decl not in ast_info["arrow_functions"]
                                and decl not in ast_info["classes"]
                                and decl not in ast_info["react_components"]]

        return ast_info

    def build_dependency_graph(self, root_path: str) -> dict:
        """Build dependency graph for JavaScript/TypeScript project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": "Invalid root path"}

        root_path = Path(root_path)

        # Look for package.json
        package_json_path = root_path / "package.json"
        if not package_json_path.exists():
            return {"error": "package.json not found"}

        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"error": f"Failed to parse package.json: {str(e)}"}

        dependencies = package_data.get("dependencies", {})
        dev_dependencies = package_data.get("devDependencies", {})
        peer_dependencies = package_data.get("peerDependencies", {})

        # Analyze source files for internal dependencies
        internal_deps = self._analyze_internal_dependencies(root_path)

        return {
            "dependencies": dependencies,
            "dev_dependencies": dev_dependencies,
            "peer_dependencies": peer_dependencies,
            "internal_dependencies": internal_deps,
            "scripts": package_data.get("scripts", {}),
            "package_name": package_data.get("name", ""),
            "version": package_data.get("version", "")
        }

    def _analyze_internal_dependencies(self, root_path: Path) -> dict:
        """Analyze internal file dependencies."""
        internal_deps = {}

        for ext in self.js_extensions:
            for js_file in root_path.rglob(f"*{ext}"):
                try:
                    with open(js_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Find relative imports
                    relative_imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', content)
                    relative_imports.extend(re.findall(r'import\s*\(\s*[\'"]([^\'"]+)[\'"]', content))
                    relative_imports.extend(re.findall(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]', content))

                    # Filter to relative imports only
                    relative_imports = [imp for imp in relative_imports
                                      if imp.startswith('./') or imp.startswith('../')]

                    if relative_imports:
                        rel_path = js_file.relative_to(root_path)
                        internal_deps[str(rel_path)] = relative_imports

                except (FileNotFoundError, UnicodeDecodeError):
                    continue

        return internal_deps

    def discover_tests(self, root_path: str) -> list:
        """Discover test files and functions in JavaScript/TypeScript project."""
        if not isinstance(root_path, str) or not root_path:
            return []

        root_path = Path(root_path)
        test_info = []

        for ext in self.js_extensions:
            for js_file in root_path.rglob(f"*{ext}"):
                try:
                    with open(js_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check if it's a test file based on path/name patterns
                    file_path_str = str(js_file)
                    is_test_file = any(pattern in file_path_str.lower() for pattern in self.test_patterns)

                    if is_test_file:
                        # Extract test functions
                        test_functions = []
                        test_functions.extend(re.findall(r'(?:describe|it|test)\s*\(\s*[\'"]([^\'"]+)[\'"]', content))
                        test_functions.extend(re.findall(r'(?:describe|it|test)\s*\(\s*[\'"]([^\'"]+)[\'"]', content))

                        test_info.append({
                            "file": str(js_file.relative_to(root_path)),
                            "type": "test_file",
                            "test_functions": test_functions,
                            "framework": self._detect_test_framework(content)
                        })

                except (FileNotFoundError, UnicodeDecodeError):
                    continue

        return test_info

    def _detect_test_framework(self, content: str) -> str:
        """Detect which test framework is being used."""
        if 'jest' in content.lower() or '@jest/' in content:
            return 'jest'
        elif 'mocha' in content.lower():
            return 'mocha'
        elif 'jasmine' in content.lower():
            return 'jasmine'
        elif 'vitest' in content.lower():
            return 'vitest'
        elif 'cypress' in content.lower():
            return 'cypress'
        else:
            return 'unknown'

    def extract_documentation(self, file_path: str) -> dict:
        """Extract documentation comments from JavaScript/TypeScript file."""
        if not isinstance(file_path, str) or not file_path:
            return {"error": "Invalid file path"}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except (FileNotFoundError, UnicodeDecodeError) as e:
            return {"error": f"Failed to read file: {str(e)}"}

        docs = {
            "function_docs": {},
            "class_docs": {},
            "interface_docs": {},
            "type_docs": {},
            "component_docs": {},
            "jsdoc_comments": []
        }

        current_doc = []
        in_doc = False

        for i, line in enumerate(lines):
            line = line.strip()

            # Start of JSDoc comment
            if line.startswith('/**'):
                in_doc = True
                current_doc.append(line[3:].strip())
            elif in_doc and line.startswith('*') and not line.startswith('*/'):
                current_doc.append(line[1:].strip())
            elif in_doc and line.startswith('*/'):
                # Process the collected documentation
                doc_text = " ".join(current_doc).strip()

                # Look ahead to find what this documentation is for
                found_target = False
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith('export ') and ('function ' in next_line or 'const ' in next_line or 'class ' in next_line):
                            # Extract function/component/class name
                            name_match = re.search(r'(?:function|const|class)\s+(\w+)', next_line)
                            if name_match:
                                name = name_match.group(1)
                                if 'class ' in next_line:
                                    docs["class_docs"][name] = doc_text
                                elif 'function ' in next_line or ('const ' in next_line and '=>' in next_line):
                                    docs["function_docs"][name] = doc_text
                                found_target = True
                                current_doc = []  # Reset for next documentation block
                                in_doc = False
                                break
            elif line.startswith('/**') and '*/' in line:
                # Single line JSDoc
                doc_text = line[3:-2].strip()
                docs["jsdoc_comments"].append(doc_text)

        return docs