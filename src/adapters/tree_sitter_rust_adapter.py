"""Tree-sitter based Rust language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import tree_sitter
from tree_sitter import Language

from .base_adapter import BaseLanguageAdapter


class TreeSitterRustAdapter(BaseLanguageAdapter):
    """Tree-sitter based adapter for analyzing Rust repositories."""

    def __init__(self):
        super().__init__("rust")
        self.file_extensions = ['.rs']
        self._ast_cache = {}  # Cache for parsed ASTs
        self._max_cache_size = 100

    def initialize_parser(self, language_lib_path: Optional[str] = None) -> bool:
        """Initialize tree-sitter parser for Rust."""
        try:
            import tree_sitter_rust
            self.language = tree_sitter.Language(tree_sitter_rust.language())
            from tree_sitter import Parser
            self.parser = Parser()
            self.parser.language = self.language
            return True
        except ImportError:
            return super().initialize_parser(language_lib_path)

    def extract_ast(self, file_path: str) -> Dict[str, Any]:
        """Extract AST from Rust file using tree-sitter."""
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
            tree = self._parse_large_file_incrementally(content, file_path)
            if tree:
                return {
                    "file_path": file_path,
                    "imports": self._extract_imports(tree, content),
                    "classes": self._extract_structs(tree, content) + self._extract_enums(tree, content) + self._extract_traits(tree, content),  # Combine into classes
                    "functions": self._extract_functions(tree, content),
                    "methods": [],  # Rust doesn't have methods in the same way
                    "variables": self._extract_consts_and_statics(tree, content),  # const and static variables
                    "complexity": self._calculate_complexity(tree),
                    "dependencies": self._extract_dependencies(tree, content),
                    "unsafe_patterns": self._detect_unsafe_patterns(content, tree),
                    # Rust-specific advanced analysis
                    "unsafe_blocks": self._extract_unsafe_blocks(tree, content),
                    "lifetimes": self._extract_lifetimes(tree, content),
                    "generics": self._extract_generics(tree, content),
                    "attributes": self._extract_attributes(tree, content),
                    "impls": self._extract_impls(tree, content)
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
                "error": f"Failed to parse Rust file: {str(e)}",
                "imports": [],
                "classes": [],
                "functions": [],
                "methods": [],
                "variables": [],
                "complexity": 0,
                "dependencies": [],
                "unsafe_patterns": self._detect_unsafe_patterns(content, None),
                "unsafe_blocks": [],
                "lifetimes": [],
                "generics": [],
                "attributes": [],
                "impls": []
            }

    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content safely."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return None

    def _parse_with_tree_sitter(self, content: str, file_path: str = None) -> Optional[Any]:
        """Parse content with tree-sitter, with caching support."""
        if not self.parser:
            return None

        cache_key = self._get_cache_key(file_path or "unknown", content) if file_path else None
        
        # Check cache first
        if cache_key and cache_key in self._ast_cache:
            return self._ast_cache[cache_key]

        try:
            tree = self.parser.parse(bytes(content, 'utf-8'))
            
            # Cache the result
            if cache_key:
                if len(self._ast_cache) >= self._max_cache_size:
                    # Simple LRU: remove oldest entry
                    oldest_key = next(iter(self._ast_cache))
                    del self._ast_cache[oldest_key]
                self._ast_cache[cache_key] = tree
            
            return tree
        except Exception:
            return None

    def _get_cache_key(self, file_path: str, content: str) -> str:
        """Generate cache key based on file path and content hash."""
        import hashlib
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
        return f"{file_path}:{content_hash}"

    def _parse_large_file_incrementally(self, content: str, file_path: str = None) -> Optional[Any]:
        """Parse large files incrementally to avoid memory issues."""
        # For files larger than 1MB, parse in chunks
        if len(content) > 1024 * 1024:  # 1MB threshold
            # Simple approach: parse the first 500KB and last 500KB
            first_chunk = content[:512 * 1024]
            last_chunk = content[-512 * 1024:] if len(content) > 512 * 1024 else ""
            
            # Parse first chunk
            tree1 = self._parse_with_tree_sitter(first_chunk, f"{file_path}_first" if file_path else None)
            if tree1:
                return tree1
            
            # Fallback to last chunk if first fails
            if last_chunk:
                return self._parse_with_tree_sitter(last_chunk, f"{file_path}_last" if file_path else None)
        
        return self._parse_with_tree_sitter(content, file_path)

    def _extract_functions(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract function definitions from tree-sitter tree."""
        functions = []

        def traverse(node):
            if node.type == 'function_item':
                func_info = {
                    'name': '',
                    'line': node.start_point[0] + 1,
                    'parameters': [],
                    'return_type': None,
                    'visibility': 'private',
                    'async': False,
                    'unsafe': False
                }

                for child in node.children:
                    if child.type == 'identifier':
                        func_info['name'] = content[child.start_byte:child.end_byte]
                    elif child.type == 'parameters':
                        func_info['parameters'] = self._extract_parameters(child, content)
                    elif child.type == 'type_identifier' and child.parent.type == 'function_item':
                        func_info['return_type'] = content[child.start_byte:child.end_byte]
                    elif child.type == 'function_modifiers':
                        for modifier in child.children:
                            if modifier.type == 'async':
                                func_info['async'] = True
                            elif modifier.type == 'unsafe':
                                func_info['unsafe'] = True
                    elif child.type == 'pub':
                        func_info['visibility'] = 'public'

                if func_info['name']:
                    functions.append(func_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return functions

    def _extract_structs(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract struct definitions."""
        structs = []

        def traverse(node):
            if node.type == 'struct_item':
                struct_info = {
                    'name': '',
                    'line': node.start_point[0] + 1,
                    'fields': [],
                    'visibility': 'private',
                    'generic_params': []
                }

                for child in node.children:
                    if child.type == 'type_identifier':
                        struct_info['name'] = content[child.start_byte:child.end_byte]
                    elif child.type == 'field_declaration_list':
                        struct_info['fields'] = self._extract_struct_fields(child, content)
                    elif child.type == 'pub':
                        struct_info['visibility'] = 'public'
                    elif child.type == 'generic_parameter_list':
                        struct_info['generic_params'] = self._extract_generic_params(child, content)

                if struct_info['name']:
                    structs.append(struct_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return structs

    def _extract_enums(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract enum definitions."""
        enums = []

        def traverse(node):
            if node.type == 'enum_item':
                enum_info = {
                    'name': '',
                    'line': node.start_point[0] + 1,
                    'variants': [],
                    'visibility': 'private'
                }

                for child in node.children:
                    if child.type == 'type_identifier':
                        enum_info['name'] = content[child.start_byte:child.end_byte]
                    elif child.type == 'enum_variant_list':
                        enum_info['variants'] = self._extract_enum_variants(child, content)
                    elif child.type == 'pub':
                        enum_info['visibility'] = 'public'

                if enum_info['name']:
                    enums.append(enum_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return enums

    def _extract_traits(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract trait definitions."""
        traits = []

        def traverse(node):
            if node.type == 'trait_item':
                trait_info = {
                    'name': '',
                    'line': node.start_point[0] + 1,
                    'methods': [],
                    'visibility': 'private'
                }

                for child in node.children:
                    if child.type == 'type_identifier':
                        trait_info['name'] = content[child.start_byte:child.end_byte]
                    elif child.type == 'pub':
                        trait_info['visibility'] = 'public'

                if trait_info['name']:
                    traits.append(trait_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return traits

    def _extract_impls(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract impl blocks."""
        impls = []

        def traverse(node):
            if node.type == 'impl_item':
                impl_info = {
                    'line': node.start_point[0] + 1,
                    'trait': None,
                    'type': None,
                    'methods': []
                }

                for child in node.children:
                    if child.type == 'type_identifier':
                        if not impl_info['type']:
                            impl_info['type'] = content[child.start_byte:child.end_byte]
                        else:
                            impl_info['trait'] = content[child.start_byte:child.end_byte]

                impls.append(impl_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return impls

    def _extract_unsafe_blocks(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract unsafe code blocks and unsafe functions."""
        unsafe_blocks = []

        def traverse(node):
            if node.type == 'unsafe_block':
                unsafe_info = {
                    'line': node.start_point[0] + 1,
                    'end_line': node.end_point[0] + 1,
                    'content': content[node.start_byte:node.end_byte],
                    'type': 'block'
                }
                unsafe_blocks.append(unsafe_info)
            elif node.type == 'function_item':
                # Check if function has unsafe modifier
                for child in node.children:
                    if child.type == 'function_modifiers':
                        for modifier in child.children:
                            if modifier.type == 'unsafe':
                                unsafe_info = {
                                    'line': node.start_point[0] + 1,
                                    'end_line': node.end_point[0] + 1,
                                    'content': content[node.start_byte:node.end_byte],
                                    'type': 'function'
                                }
                                unsafe_blocks.append(unsafe_info)
                                break
                        break

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return unsafe_blocks

    def _extract_lifetimes(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract lifetime parameters."""
        lifetimes = []

        def traverse(node):
            if node.type == 'lifetime':
                lifetime_info = {
                    'name': content[node.start_byte:node.end_byte],
                    'line': node.start_point[0] + 1
                }
                lifetimes.append(lifetime_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return lifetimes

    def _extract_generics(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract generic type parameters."""
        generics = []

        def traverse(node):
            if node.type == 'type_parameters':
                for child in node.children:
                    if child.type == 'type_parameter':
                        for subchild in child.children:
                            if subchild.type == 'type_identifier':
                                generic_info = {
                                    'name': content[subchild.start_byte:subchild.end_byte],
                                    'line': subchild.start_point[0] + 1
                                }
                                generics.append(generic_info)
                                break

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return generics

    def _extract_attributes(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract attributes and derive macros."""
        attributes = []

        def traverse(node):
            if node.type in ['attribute_item', 'derive_attribute']:
                attr_info = {
                    'name': content[node.start_byte:node.end_byte].strip(),
                    'line': node.start_point[0] + 1,
                    'kind': node.type
                }
                attributes.append(attr_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return attributes

    def _extract_consts_and_statics(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract const and static variable declarations."""
        variables = []

        def traverse(node):
            if node.type in ['const_item', 'static_item']:
                var_info = {
                    'name': '',
                    'type': None,
                    'value': None,
                    'line': node.start_point[0] + 1,
                    'kind': node.type
                }

                for child in node.children:
                    if child.type == 'identifier':
                        var_info['name'] = content[child.start_byte:child.end_byte]
                    elif child.type in ['type_identifier', 'primitive_type']:
                        var_info['type'] = content[child.start_byte:child.end_byte]

                if var_info['name']:
                    variables.append(var_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return variables

    def _extract_macros(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract macro definitions."""
        macros = []

        def traverse(node):
            if node.type in ['macro_definition', 'macro_rules_definition']:
                macro_info = {
                    'name': '',
                    'line': node.start_point[0] + 1,
                    'kind': node.type
                }

                for child in node.children:
                    if child.type == 'identifier':
                        macro_info['name'] = content[child.start_byte:child.end_byte]
                        break

                if macro_info['name']:
                    macros.append(macro_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return macros

    def _extract_imports(self, tree, content: str) -> List[Dict[str, Any]]:
        """Extract use statements."""
        imports = []

        def traverse(node):
            if node.type == 'use_declaration':
                import_info = {
                    'line': node.start_point[0] + 1,
                    'path': '',
                    'alias': None
                }

                # Extract the full use path - find the path node
                for child in node.children:
                    if child.type == 'scoped_identifier' or child.type == 'identifier':
                        import_info['path'] = content[child.start_byte:child.end_byte]
                        break

                if import_info['path']:
                    imports.append(import_info)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return imports

    def _calculate_complexity(self, tree) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity

        def traverse(node):
            nonlocal complexity
            # Decision points in Rust
            if node.type in ['if_expression', 'match_expression', 'while_expression', 'loop_expression', 'for_expression']:
                complexity += 1
            elif node.type == 'binary_expression':
                # Logical operators
                op = content[node.start_byte:node.end_byte]
                if '&&' in op or '||' in op:
                    complexity += 1

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return complexity

    def _extract_dependencies(self, tree, content: str) -> List[str]:
        """Extract external crate dependencies from use statements."""
        dependencies = set()

        def traverse(node):
            if node.type == 'use_declaration':
                # Look for external crate imports (starting with crate name)
                path = content[node.start_byte:node.end_byte]
                if 'use ' in path:
                    path = path.split('use ')[1].split(';')[0].strip()
                    if '::' in path:
                        crate = path.split('::')[0]
                        if crate and not crate.startswith('std') and not crate.startswith('core'):
                            dependencies.add(crate)

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return list(dependencies)

    # Helper methods for extraction
    def _extract_parameters(self, node, content: str) -> List[Dict[str, Any]]:
        """Extract function parameters."""
        params = []
        for child in node.children:
            if child.type == 'parameter':
                param_info = {'name': '', 'type': None}
                for param_child in child.children:
                    if param_child.type == 'identifier':
                        param_info['name'] = content[param_child.start_byte:param_child.end_byte]
                    elif param_child.type == 'type_identifier':
                        param_info['type'] = content[param_child.start_byte:param_child.end_byte]
                if param_info['name']:
                    params.append(param_info)
        return params

    def _extract_struct_fields(self, node, content: str) -> List[Dict[str, Any]]:
        """Extract struct fields."""
        fields = []
        for child in node.children:
            if child.type == 'field_declaration':
                field_info = {'name': '', 'type': None, 'visibility': 'private'}
                for field_child in child.children:
                    if field_child.type == 'field_identifier':
                        field_info['name'] = content[field_child.start_byte:field_child.end_byte]
                    elif field_child.type == 'type_identifier':
                        field_info['type'] = content[field_child.start_byte:field_child.end_byte]
                    elif field_child.type == 'pub':
                        field_info['visibility'] = 'public'
                if field_info['name']:
                    fields.append(field_info)
        return fields

    def _extract_enum_variants(self, node, content: str) -> List[str]:
        """Extract enum variants."""
        variants = []
        for child in node.children:
            if child.type == 'enum_variant':
                for variant_child in child.children:
                    if variant_child.type == 'identifier':
                        variants.append(content[variant_child.start_byte:variant_child.end_byte])
                        break
        return variants

    def _extract_generic_params(self, node, content: str) -> List[str]:
        """Extract generic parameters."""
        params = []
        for child in node.children:
            if child.type == 'type_identifier':
                params.append(content[child.start_byte:child.end_byte])
        return params

    def build_dependency_graph(self, root_path: str) -> Dict[str, Any]:
        """Build dependency graph for Rust project."""
        graph = {
            "modules": {},
            "dependencies": {},
            "crates": []
        }

        # Find Cargo.toml
        cargo_toml = Path(root_path) / "Cargo.toml"
        if cargo_toml.exists():
            try:
                import toml
                cargo_data = toml.load(cargo_toml)
                
                # Extract crate dependencies
                dependencies = cargo_data.get("dependencies", {})
                graph["crates"] = list(dependencies.keys())
                graph["dependencies"] = dependencies
                
                # Extract workspace members if it's a workspace
                workspace = cargo_data.get("workspace", {})
                members = workspace.get("members", [])
                graph["workspace_members"] = members
                
            except ImportError:
                graph["error"] = "toml package not available"
            except Exception as e:
                graph["error"] = f"Failed to parse Cargo.toml: {str(e)}"

        # Scan for Rust files and build module graph
        rust_files = list(Path(root_path).rglob("*.rs"))
        for rust_file in rust_files:
            if rust_file.is_file():
                rel_path = rust_file.relative_to(root_path)
                module_name = str(rel_path).replace('.rs', '').replace('/', '::')
                graph["modules"][module_name] = {
                    "file": str(rel_path),
                    "imports": []
                }

        return graph

    def _detect_unsafe_patterns(self, content: str, tree) -> List[Dict[str, Any]]:
        """Detect unsafe Rust patterns that could lead to security vulnerabilities."""
        unsafe_patterns = []

        # Pattern 1: Use of unsafe blocks - can bypass Rust's safety guarantees
        if 'unsafe' in content:
            for match in re.finditer(r'\bunsafe\s*{', content):
                unsafe_patterns.append({
                    "type": "unsafe_block_usage",
                    "pattern": "unsafe block",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Use of unsafe block bypasses Rust's memory safety guarantees",
                    "severity": "medium",
                    "code": content[match.start():match.start() + 50].strip()
                })

        # Pattern 2: Raw pointer usage (*const T, *mut T)
        for match in re.finditer(r'\*\s*(?:const|mut)\s+\w+', content):
            unsafe_patterns.append({
                "type": "raw_pointer_usage",
                "pattern": "raw pointer",
                "line": content[:match.start()].count('\n') + 1,
                "description": "Raw pointer usage can lead to memory safety issues if not handled carefully",
                "severity": "medium",
                "code": content[match.start():match.start() + 30].strip()
            })

        # Pattern 3: Potential command injection with Command
        if 'Command::' in content:
            for match in re.finditer(r'Command::new\s*\(\s*[^)]+\)', content):
                unsafe_patterns.append({
                    "type": "command_injection",
                    "pattern": "Command::new",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Command execution without proper input validation can lead to command injection",
                    "severity": "high",
                    "code": content[match.start():match.start() + 50].strip()
                })

        # Pattern 4: Use of rand::thread_rng() for security-critical operations
        if 'thread_rng()' in content:
            for match in re.finditer(r'\bthread_rng\s*\(\s*\)', content):
                unsafe_patterns.append({
                    "type": "weak_random_generation",
                    "pattern": "thread_rng()",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "thread_rng() may not be suitable for cryptographic purposes",
                    "severity": "medium",
                    "code": content[match.start():match.start() + 20].strip()
                })

        # Pattern 5: Hardcoded secrets or API keys
        secret_patterns = [
            r'api[_-]?key\s*[:=]\s*["\'][^"\']+["\']',
            r'secret[_-]?key\s*[:=]\s*["\'][^"\']+["\']',
            r'password\s*[:=]\s*["\'][^"\']+["\']',
            r'token\s*[:=]\s*["\'][^"\']+["\']'
        ]
        for pattern in secret_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                unsafe_patterns.append({
                    "type": "hardcoded_secret",
                    "pattern": "hardcoded credential",
                    "line": content[:match.start()].count('\n') + 1,
                    "description": "Hardcoded credentials can be easily extracted from source code",
                    "severity": "high",
                    "code": content[match.start():match.start() + 50].strip()
                })

        # Pattern 6: Use of unwrap() or expect() without proper error handling
        for func in ['unwrap()', 'expect(']:
            escaped_func = re.escape(func)
            if func in content:
                for match in re.finditer(rf'\.{escaped_func}', content):
                    unsafe_patterns.append({
                        "type": "panic_on_error",
                        "pattern": f".{func}",
                        "line": content[:match.start()].count('\n') + 1,
                        "description": f"Use of .{func} can cause panics in production",
                        "severity": "low",
                        "code": content[match.start():match.start() + 30].strip()
                    })

        # Pattern 7: Potential SQL injection with string formatting
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE']
        for keyword in sql_keywords:
            if keyword in content:
                # Look for string concatenation or formatting near SQL keywords
                for match in re.finditer(rf'{keyword}.*\+|\{keyword}.*format!', content, re.IGNORECASE):
                    unsafe_patterns.append({
                        "type": "sql_injection",
                        "pattern": f"{keyword} with string operations",
                        "line": content[:match.start()].count('\n') + 1,
                        "description": "String operations with SQL queries can lead to SQL injection",
                        "severity": "high",
                        "code": content[match.start():match.start() + 60].strip()
                    })

        return unsafe_patterns

    def _extract_with_regex(self, content: str) -> Dict[str, Any]:
        """Fallback regex-based extraction when tree-sitter is not available."""
        # This would implement the same logic as the existing rust_adapter.py
        # For now, return minimal structure with all expected fields
        return {
            "imports": [],
            "classes": [],
            "functions": [],
            "methods": [],
            "variables": [],
            "complexity": 0,
            "dependencies": [],
            "unsafe_patterns": self._detect_unsafe_patterns(content, None),
            "unsafe_blocks": [],
            "lifetimes": [],
            "generics": [],
            "attributes": [],
            "impls": []
        }