"""C++ language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set


class CppAdapter:
    """Adapter for analyzing C++ repositories."""

    def __init__(self):
        # Common C++ file extensions
        self.cpp_extensions = {'.cpp', '.cc', '.cxx', '.c++', '.h', '.hpp', '.hxx', '.h++'}
        # Test file patterns
        self.test_patterns = ['test', 'Test', 'TEST', '_test', '_Test']

    def extract_ast(self, file_path: str) -> dict:
        """Extract AST-like information from C++ file using regex parsing."""
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
            "structs": [],
            "namespaces": [],
            "includes": [],
            "templates": [],
            "macros": [],
            "typedefs": [],
            "enums": []
        }

        # Extract includes
        include_pattern = r'#include\s*[<"]([^>"]+)[>"]'
        ast_info["includes"] = re.findall(include_pattern, content)

        # Extract functions (simplified - doesn't handle complex signatures)
        function_pattern = r'(?:^|\s+)(?!class|struct|namespace|template|typedef|using|enum|if|for|while|do|switch|return|new|delete|throw|try|catch)(?:\w+(?:\s+|\*|\&))*\s+(\w+)\s*\([^)]*\)\s*(?:const)?\s*(?:override|final)?\s*(?:\{|;)'
        functions = re.findall(function_pattern, content, re.MULTILINE)
        ast_info["functions"] = list(set(functions))  # Remove duplicates

        # Extract classes
        class_pattern = r'(?:^|\s+)class\s+(\w+)'
        ast_info["classes"] = re.findall(class_pattern, content)

        # Extract structs
        struct_pattern = r'(?:^|\s+)struct\s+(\w+)'
        ast_info["structs"] = re.findall(struct_pattern, content)

        # Extract namespaces
        namespace_pattern = r'namespace\s+(\w+)'
        ast_info["namespaces"] = re.findall(namespace_pattern, content)

        # Extract templates
        template_pattern = r'template\s*<[^>]+>\s+(?:class|struct|typename)?\s*(\w+)'
        ast_info["templates"] = re.findall(template_pattern, content)

        # Extract typedefs
        typedef_pattern = r'typedef\s+.+?\s+(\w+)\s*;'
        ast_info["typedefs"] = re.findall(typedef_pattern, content, re.DOTALL)

        # Extract enums
        enum_pattern = r'enum\s+(?:class\s+)?(\w+)'
        ast_info["enums"] = re.findall(enum_pattern, content)

        # Extract macros (simple #define)
        macro_pattern = r'#define\s+(\w+)'
        ast_info["macros"] = re.findall(macro_pattern, content)

        return ast_info

    def build_dependency_graph(self, root_path: str) -> dict:
        """Build dependency graph for C++ project."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": "Invalid root path"}

        root_path = Path(root_path)

        # Look for common C++ build files
        build_files = [
            root_path / "CMakeLists.txt",
            root_path / "Makefile",
            root_path / "makefile",
            root_path / ".vscode" / "c_cpp_properties.json"
        ]

        dependencies = {}
        build_system = "unknown"

        # Try CMake first
        cmake_file = root_path / "CMakeLists.txt"
        if cmake_file.exists():
            try:
                with open(cmake_file, 'r', encoding='utf-8') as f:
                    cmake_content = f.read()

                build_system = "cmake"

                # Extract CMake dependencies (simplified)
                find_package_pattern = r'find_package\s*\(\s*(\w+)'
                packages = re.findall(find_package_pattern, cmake_content, re.IGNORECASE)
                for package in packages:
                    dependencies[package.lower()] = "latest"

            except (FileNotFoundError, UnicodeDecodeError):
                pass

        # Analyze header includes across all files
        header_deps = self._analyze_header_dependencies(root_path)

        return {
            "build_system": build_system,
            "external_dependencies": dependencies,
            "header_dependencies": header_deps
        }

    def _analyze_header_dependencies(self, root_path: Path) -> dict:
        """Analyze header file dependencies."""
        header_deps = {}

        for cpp_file in root_path.rglob("*"):
            if cpp_file.suffix in self.cpp_extensions:
                try:
                    with open(cpp_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Find local includes
                    local_includes = re.findall(r'#include\s*"([^"]+)"', content)

                    if local_includes:
                        rel_path = cpp_file.relative_to(root_path)
                        header_deps[str(rel_path)] = local_includes

                except (FileNotFoundError, UnicodeDecodeError):
                    continue

        return header_deps

    def discover_tests(self, root_path: str) -> list:
        """Discover test files and functions in C++ project."""
        if not isinstance(root_path, str) or not root_path:
            return []

        root_path = Path(root_path)
        test_info = []

        for cpp_file in root_path.rglob("*"):
            if cpp_file.suffix in self.cpp_extensions:
                file_name = cpp_file.name.lower()
                is_test_file = any(pattern.lower() in file_name for pattern in self.test_patterns)

                if is_test_file:
                    try:
                        with open(cpp_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Look for common test patterns
                        test_functions = []

                        # Google Test
                        test_functions.extend(re.findall(r'TEST\s*\(\s*[^,]+,\s*([^)]+)\s*\)', content))
                        test_functions.extend(re.findall(r'TEST_F\s*\(\s*[^,]+,\s*([^)]+)\s*\)', content))

                        # Catch2
                        test_functions.extend(re.findall(r'TEST_CASE\s*\(\s*["\']([^"\']+)["\']', content))

                        # Boost.Test
                        test_functions.extend(re.findall(r'BOOST_AUTO_TEST_CASE\s*\(\s*([^)]+)\s*\)', content))

                        # Simple function-based tests
                        test_functions.extend(re.findall(r'void\s+(test_\w+|Test\w+)\s*\(', content))

                        test_info.append({
                            "file": str(cpp_file.relative_to(root_path)),
                            "type": "test_file",
                            "test_functions": list(set(test_functions)),  # Remove duplicates
                            "framework": self._detect_test_framework(content)
                        })

                    except (FileNotFoundError, UnicodeDecodeError):
                        continue

        return test_info

    def _detect_test_framework(self, content: str) -> str:
        """Detect which test framework is being used."""
        if 'gtest' in content.lower() or 'GTEST' in content or 'TEST(' in content:
            return 'google_test'
        elif 'catch' in content.lower() or 'CATCH' in content:
            return 'catch2'
        elif 'boost' in content.lower() and 'test' in content.lower():
            return 'boost_test'
        elif 'doctest' in content.lower():
            return 'doctest'
        else:
            return 'unknown'

    def extract_documentation(self, file_path: str) -> dict:
        """Extract documentation comments from C++ file."""
        if not isinstance(file_path, str) or not file_path:
            return {"error": "Invalid file path"}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (FileNotFoundError, UnicodeDecodeError) as e:
            return {"error": f"Failed to read file: {str(e)}"}

        docs = {
            "function_docs": {},
            "class_docs": {},
            "struct_docs": {},
            "namespace_docs": {},
            "file_docs": []
        }

        current_doc = []
        in_doc = False

        for i, line in enumerate(lines):
            line = line.strip()

            # Start of Doxygen/JSDoc style comment
            if line.startswith('/**') or (line.startswith('/*') and '*/' not in line):
                in_doc = True
                if line.startswith('/**'):
                    current_doc.append(line[3:].strip())
                else:
                    current_doc.append(line[2:].strip())
            elif line.startswith('///') or (line.startswith('//') and not line.startswith('////')):
                in_doc = True
                current_doc.append(line[3:].strip())
            elif in_doc and (line.startswith('*') or line.startswith('///') or (line.startswith('//') and not line.startswith('////'))):
                if line.startswith('*'):
                    current_doc.append(line[1:].strip())
                elif line.startswith('///'):
                    current_doc.append(line[3:].strip())
                else:
                    current_doc.append(line[2:].strip())
            elif in_doc and (line.endswith('*/') or not line):
                if line.endswith('*/'):
                    current_doc.append(line[:-2].strip())
                # Process the collected documentation
                doc_text = " ".join(current_doc).strip()

                # Look ahead to find what this documentation is for
                found_target = False
                for j in range(i + 1, min(i + 10, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith('class '):
                        class_match = re.search(r'class\s+(\w+)', next_line)
                        if class_match:
                            docs["class_docs"][class_match.group(1)] = doc_text
                            found_target = True
                            break
                    elif next_line.startswith('struct '):
                        struct_match = re.search(r'struct\s+(\w+)', next_line)
                        if struct_match:
                            docs["struct_docs"][struct_match.group(1)] = doc_text
                            found_target = True
                            break
                    elif next_line.startswith('namespace '):
                        namespace_match = re.search(r'namespace\s+(\w+)', next_line)
                        if namespace_match:
                            docs["namespace_docs"][namespace_match.group(1)] = doc_text
                            found_target = True
                            break
                    elif re.search(r'\w+(?:\s+|\*|\&)+\w+\s*\([^)]*\)', next_line):
                        # Function signature
                        func_match = re.search(r'(\w+)\s*\(', next_line)
                        if func_match:
                            docs["function_docs"][func_match.group(1)] = doc_text
                            found_target = True
                            break
                    elif next_line == "" or next_line.startswith('//'):
                        continue
                    else:
                        break

                current_doc = []
                in_doc = False

        return docs