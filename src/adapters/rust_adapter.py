"""Rust language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import tomllib  # Python 3.11+ for TOML parsing


class RustAdapter:
    """Adapter for analyzing Rust repositories."""

    def extract_ast(self, file_path: str) -> dict:
        """Extract AST-like information from Rust file using regex parsing."""
        if not isinstance(file_path, str) or not file_path:
            return {"error": "Invalid file path"}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (FileNotFoundError, UnicodeDecodeError) as e:
            return {"error": f"Failed to read file: {str(e)}"}

        ast_info = {
            "functions": [],
            "structs": [],
            "enums": [],
            "traits": [],
            "impls": [],
            "macros": [],
            "modules": [],
            "imports": []
        }

        # Extract functions
        function_pattern = r'fn\s+(\w+)\s*\([^)]*\)\s*(?:->\s*[^;{]+)?'
        ast_info["functions"] = re.findall(function_pattern, content)

        # Extract structs
        struct_pattern = r'struct\s+(\w+)'
        ast_info["structs"] = re.findall(struct_pattern, content)

        # Extract enums
        enum_pattern = r'enum\s+(\w+)'
        ast_info["enums"] = re.findall(enum_pattern, content)

        # Extract traits
        trait_pattern = r'trait\s+(\w+)'
        ast_info["traits"] = re.findall(trait_pattern, content)

        # Extract impl blocks - capture the implementing type
        impl_pattern = r'impl(?:<[^>]+>)?\s+(?:\w+::)*\w+\s+for\s+(\w+)'
        ast_info["impls"] = re.findall(impl_pattern, content)

        # Extract macro definitions
        macro_pattern = r'macro_rules!\s+(\w+)'
        ast_info["macros"] = re.findall(macro_pattern, content)

        # Extract modules
        mod_pattern = r'mod\s+(\w+)'
        ast_info["modules"] = re.findall(mod_pattern, content)

        # Extract imports (use statements)
        import_pattern = r'use\s+([^;]+);'
        ast_info["imports"] = re.findall(import_pattern, content)

        return ast_info

    def build_dependency_graph(self, root_path: str) -> dict:
        """Build dependency graph for Rust project from Cargo.toml."""
        if not isinstance(root_path, str) or not root_path:
            return {"error": "Invalid root path"}

        cargo_toml_path = Path(root_path) / "Cargo.toml"

        if not cargo_toml_path.exists():
            return {"error": "Cargo.toml not found"}

        try:
            with open(cargo_toml_path, 'rb') as f:
                cargo_data = tomllib.load(f)
        except Exception as e:
            return {"error": f"Failed to parse Cargo.toml: {str(e)}"}

        dependencies = {}

        # Extract dependencies from [dependencies] section
        if 'dependencies' in cargo_data:
            for dep, version in cargo_data['dependencies'].items():
                if isinstance(version, dict):
                    dependencies[dep] = version.get('version', str(version))
                else:
                    dependencies[dep] = str(version)

        # Extract dev-dependencies
        dev_dependencies = {}
        if 'dev-dependencies' in cargo_data:
            for dep, version in cargo_data['dev-dependencies'].items():
                if isinstance(version, dict):
                    dev_dependencies[dep] = version.get('version', str(version))
                else:
                    dev_dependencies[dep] = str(version)

        # Extract build-dependencies
        build_dependencies = {}
        if 'build-dependencies' in cargo_data:
            for dep, version in cargo_data['build-dependencies'].items():
                if isinstance(version, dict):
                    build_dependencies[dep] = version.get('version', str(version))
                else:
                    build_dependencies[dep] = str(version)

        return {
            "dependencies": dependencies,
            "dev_dependencies": dev_dependencies,
            "build_dependencies": build_dependencies,
            "workspace_members": cargo_data.get('workspace', {}).get('members', [])
        }

    def discover_tests(self, root_path: str) -> list:
        """Discover test files and functions in Rust project."""
        test_info = []

        # Find all .rs files
        for rs_file in Path(root_path).rglob("*.rs"):
            try:
                with open(rs_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check if file contains tests
                test_functions = re.findall(r'#\[test\]\s*fn\s+(\w+)', content)
                if test_functions:
                    test_info.append({
                        "file": str(rs_file.relative_to(root_path)),
                        "test_functions": test_functions
                    })

                # Check for integration tests (tests/ directory)
                if "tests/" in str(rs_file):
                    test_info.append({
                        "file": str(rs_file.relative_to(root_path)),
                        "type": "integration_test"
                    })

            except (FileNotFoundError, UnicodeDecodeError):
                continue

        return test_info

    def extract_documentation(self, file_path: str) -> dict:
        """Extract documentation comments from Rust file."""
        if not isinstance(file_path, str) or not file_path:
            return {"error": "Invalid file path"}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (FileNotFoundError, UnicodeDecodeError) as e:
            return {"error": f"Failed to read file: {str(e)}"}

        docs = {
            "module_docs": [],
            "function_docs": {},
            "struct_docs": {},
            "enum_docs": {},
            "trait_docs": {},
            "impl_docs": {}
        }

        current_doc = []
        in_doc = False

        for i, line in enumerate(lines):
            line = line.strip()

            # Start of documentation comment
            if line.startswith("///") or line.startswith("//!"):
                in_doc = True
                current_doc.append(line[3:].strip() if line.startswith("///") else line[3:].strip())
            elif in_doc and (line.startswith("///") or line.startswith("//!")):
                current_doc.append(line[3:].strip() if line.startswith("///") else line[3:].strip())
            else:
                if in_doc:
                    # Process the collected documentation
                    doc_text = " ".join(current_doc).strip()

        current_doc = []
        in_doc = False

        for i, line in enumerate(lines):
            line = line.strip()

            # Start of documentation comment
            if line.startswith("///") or line.startswith("//!"):
                in_doc = True
                current_doc.append(line[3:].strip() if line.startswith("///") else line[3:].strip())
            elif in_doc and (line.startswith("///") or line.startswith("//!")):
                current_doc.append(line[3:].strip() if line.startswith("///") else line[3:].strip())
            else:
                if in_doc:
                    # Process the collected documentation
                    doc_text = " ".join(current_doc).strip()

                    # Look ahead to find what this documentation is for
                    found_target = False
                    for j in range(i, min(i + 10, len(lines))):  # Look ahead up to 10 lines
                        next_line = lines[j].strip()
                        if next_line.startswith("pub fn "):
                            func_match = re.search(r'pub fn\s+(\w+)', next_line)
                            if func_match:
                                docs["function_docs"][func_match.group(1)] = doc_text
                                found_target = True
                                break
                        elif next_line.startswith("pub struct "):
                            struct_match = re.search(r'pub struct\s+(\w+)', next_line)
                            if struct_match:
                                docs["struct_docs"][struct_match.group(1)] = doc_text
                                found_target = True
                                break
                        elif next_line.startswith("pub enum "):
                            enum_match = re.search(r'pub enum\s+(\w+)', next_line)
                            if enum_match:
                                docs["enum_docs"][enum_match.group(1)] = doc_text
                                found_target = True
                                break
                        elif next_line.startswith("pub trait "):
                            trait_match = re.search(r'pub trait\s+(\w+)', next_line)
                            if trait_match:
                                docs["trait_docs"][trait_match.group(1)] = doc_text
                                found_target = True
                                break
                        elif next_line.startswith("impl"):
                            # For impl blocks, capture the implementing type
                            impl_match = re.search(r'impl(?:<[^>]+>)?\s+(?:\w+::)*\w+\s+for\s+(\w+)', next_line)
                            if impl_match:
                                docs["impl_docs"][impl_match.group(1)] = doc_text
                                found_target = True
                                break
                        elif next_line.startswith("fn ") and not next_line.startswith("pub fn "):
                            # Private functions
                            func_match = re.search(r'fn\s+(\w+)', next_line)
                            if func_match:
                                docs["function_docs"][func_match.group(1)] = doc_text
                                found_target = True
                                break
                        elif next_line == "" or next_line.startswith("//"):
                            continue  # Skip empty lines and regular comments
                        else:
                            break  # Stop looking if we hit something else

                    current_doc = []
                    in_doc = False

        return docs
