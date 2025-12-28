"""Java language adapter for repository analysis."""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
import javalang


class JavaAdapter:
    """Adapter for analyzing Java repositories."""

    def extract_ast(self, file_path: str) -> dict:
        """Extract AST from Java file using javalang parser."""
        if not isinstance(file_path, str) or not file_path:
            return {
                "file_path": str(file_path) if file_path else "None",
                "error": f"Invalid file path: {file_path}",
                "package": None,
                "imports": [],
                "classes": [],
                "interfaces": [],
                "enums": [],
                "methods": [],
                "fields": [],
                "annotations": [],
                "complexity": 0,
                "dependencies": []
            }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the Java file
            tree = javalang.parse.parse(content)

            # Extract AST information
            ast_info = {
                "file_path": file_path,
                "package": tree.package.name if tree.package else None,
                "imports": [],
                "classes": [],
                "interfaces": [],
                "enums": [],
                "methods": [],
                "fields": [],
                "annotations": [],
                "complexity": self._calculate_complexity(tree),
                "dependencies": self._extract_dependencies(content)
            }

            # Extract package
            if tree.package:
                ast_info["package"] = tree.package.name

            # Extract imports
            for import_decl in tree.imports:
                ast_info["imports"].append({
                    "name": import_decl.path,
                    "static": import_decl.static,
                    "wildcard": import_decl.wildcard
                })

            # Extract type declarations (classes, interfaces, enums)
            for type_decl in tree.types:
                if isinstance(type_decl, javalang.tree.ClassDeclaration):
                    ast_info["classes"].append(self._extract_class_info(type_decl, file_path))
                elif isinstance(type_decl, javalang.tree.InterfaceDeclaration):
                    ast_info["interfaces"].append(self._extract_interface_info(type_decl, file_path))
                elif isinstance(type_decl, javalang.tree.EnumDeclaration):
                    ast_info["enums"].append(self._extract_enum_info(type_decl, file_path))

            return ast_info

        except (javalang.parser.JavaSyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
            return {
                "file_path": file_path,
                "error": f"Failed to parse Java file: {str(e)}",
                "package": None,
                "imports": [],
                "classes": [],
                "interfaces": [],
                "enums": [],
                "methods": [],
                "fields": [],
                "annotations": [],
                "complexity": 0,
                "dependencies": []
            }

    def _extract_class_info(self, class_decl: javalang.tree.ClassDeclaration, file_path: str) -> Dict:
        """Extract information from a class declaration."""
        methods = []
        fields = []
        annotations = []

        # Extract annotations
        if hasattr(class_decl, 'annotations') and class_decl.annotations:
            annotations = [ann.name for ann in class_decl.annotations]

        # Extract methods and fields from body
        for member in class_decl.body:
            if isinstance(member, javalang.tree.MethodDeclaration):
                methods.append({
                    "name": member.name,
                    "return_type": str(member.type) if hasattr(member, 'type') and member.type else "void",
                    "parameters": [
                        {"name": param.name, "type": str(param.type) if hasattr(param, 'type') and param.type else "Object"}
                        for param in member.parameters
                    ] if hasattr(member, 'parameters') else [],
                    "modifiers": [mod for mod in member.modifiers if mod],
                    "annotations": [ann.name for ann in member.annotations] if hasattr(member, 'annotations') and member.annotations else []
                })
            elif isinstance(member, javalang.tree.FieldDeclaration):
                # Field declarations can have multiple declarators
                for declarator in member.declarators:
                    fields.append({
                        "name": declarator.name,
                        "type": str(member.type) if hasattr(member, 'type') and member.type else "Object",
                        "modifiers": [mod for mod in member.modifiers if mod],
                        "annotations": [ann.name for ann in member.annotations] if hasattr(member, 'annotations') and member.annotations else []
                    })
            elif isinstance(member, javalang.tree.ConstructorDeclaration):
                # Constructors are also methods
                methods.append({
                    "name": member.name,  # Constructor name is the class name
                    "return_type": "void",  # Constructors don't have return type
                    "parameters": [
                        {"name": param.name, "type": str(param.type) if hasattr(param, 'type') and param.type else "Object"}
                        for param in member.parameters
                    ] if hasattr(member, 'parameters') else [],
                    "modifiers": [mod for mod in member.modifiers if mod],
                    "annotations": [ann.name for ann in member.annotations] if hasattr(member, 'annotations') and member.annotations else [],
                    "is_constructor": True
                })

        return {
            "name": class_decl.name,
            "file_path": file_path,
            "modifiers": [mod for mod in class_decl.modifiers if mod],
            "extends": class_decl.extends.name if class_decl.extends else None,
            "implements": [impl.name for impl in class_decl.implements] if class_decl.implements else [],
            "annotations": annotations,
            "methods": methods,
            "fields": fields,
            "method_count": len(methods),
            "field_count": len(fields)
        }

    def _extract_interface_info(self, interface_decl: javalang.tree.InterfaceDeclaration, file_path: str) -> Dict:
        """Extract information from an interface declaration."""
        methods = []

        # Extract methods
        for member in interface_decl.body:
            if isinstance(member, javalang.tree.MethodDeclaration):
                methods.append({
                    "name": member.name,
                    "return_type": str(member.type) if member.type else "void",
                    "parameters": [
                        {"name": param.name, "type": str(param.type) if param.type else "Object"}
                        for param in member.parameters
                    ],
                    "modifiers": [mod for mod in member.modifiers if mod],
                    "default": hasattr(member, 'body') and member.body is not None
                })

        return {
            "name": interface_decl.name,
            "file_path": file_path,
            "modifiers": [mod for mod in interface_decl.modifiers if mod],
            "extends": [ext.name for ext in interface_decl.extends] if interface_decl.extends else [],
            "methods": methods,
            "method_count": len(methods)
        }

    def _extract_enum_info(self, enum_decl: javalang.tree.EnumDeclaration, file_path: str) -> Dict:
        """Extract information from an enum declaration."""
        constants = []

        # Extract enum constants
        for constant in enum_decl.body.constants:
            constants.append({
                "name": constant.name,
                "arguments": len(constant.arguments) if constant.arguments else 0
            })

        return {
            "name": enum_decl.name,
            "file_path": file_path,
            "modifiers": [mod for mod in enum_decl.modifiers if mod],
            "implements": [impl.name for impl in enum_decl.implements] if enum_decl.implements else [],
            "constants": constants,
            "constant_count": len(constants)
        }

    def _calculate_complexity(self, tree: javalang.tree.CompilationUnit) -> int:
        """Calculate cyclomatic complexity of the Java file."""
        complexity = 1  # Base complexity

        # Count control flow statements
        for node in tree:
            if hasattr(node, 'body') and node.body:
                for stmt in node.body:
                    if isinstance(stmt, (javalang.tree.IfStatement, javalang.tree.ForStatement,
                                      javalang.tree.WhileStatement, javalang.tree.DoStatement,
                                      javalang.tree.SwitchStatement, javalang.tree.TryStatement)):
                        complexity += 1
                        # Add complexity for else-if chains
                        if isinstance(stmt, javalang.tree.IfStatement) and stmt.else_statement:
                            current = stmt.else_statement
                            while isinstance(current, javalang.tree.IfStatement):
                                complexity += 1
                                current = current.else_statement

        return complexity

    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract dependencies from import statements."""
        dependencies = []

        # Find all import statements
        import_pattern = r'import\s+(?:static\s+)?([^;]+);'
        matches = re.findall(import_pattern, content)

        for match in matches:
            # Remove static keyword if present
            dep = match.replace('static ', '')
            # Get the base package (first part before first dot)
            base_package = dep.split('.')[0]
            if base_package not in ['java', 'javax', 'com.sun', 'sun', 'org.w3c', 'org.xml'] and base_package not in dependencies:
                dependencies.append(base_package)

        return dependencies

        return dependencies

    def build_dependency_graph(self, root_path: str) -> dict:
        """Build dependency graph for Java project."""
        if not isinstance(root_path, str) or not root_path:
            return {
                "packages": {},
                "classes": {},
                "external_dependencies": [],
                "internal_dependencies": {},
                "circular_dependencies": [],
                "dependency_depth": {},
                "maven_dependencies": {"dependencies": [], "plugins": [], "parent": None, "properties": {}}
            }
        dependency_graph = {
            "packages": {},
            "classes": {},
            "external_dependencies": set(),
            "internal_dependencies": {},
            "circular_dependencies": [],
            "dependency_depth": {},
            "maven_dependencies": self._analyze_maven_dependencies(root_path)
        }

        # Find all Java files
        java_files = []
        for root, dirs, files in os.walk(root_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in ['.git', 'target', 'build', 'out', 'node_modules', '.gradle']]

            for file in files:
                if file.endswith('.java'):
                    java_files.append(os.path.join(root, file))

        # Analyze each Java file
        for java_file in java_files:
            try:
                ast_info = self.extract_ast(java_file)

                if ast_info.get("error"):
                    continue

                # Build package structure
                package_name = ast_info.get("package", "default")
                if package_name not in dependency_graph["packages"]:
                    dependency_graph["packages"][package_name] = {
                        "classes": [],
                        "interfaces": [],
                        "enums": [],
                        "dependencies": set()
                    }

                # Add classes to package
                for cls in ast_info.get("classes", []):
                    class_name = f"{package_name}.{cls['name']}"
                    dependency_graph["packages"][package_name]["classes"].append(class_name)
                    dependency_graph["classes"][class_name] = {
                        "file": java_file,
                        "package": package_name,
                        "extends": cls.get("extends"),
                        "implements": cls.get("implements", []),
                        "methods": cls.get("methods", []),
                        "fields": cls.get("fields", []),
                        "dependencies": set()
                    }

                    # Track inheritance dependencies
                    if cls.get("extends"):
                        dependency_graph["classes"][class_name]["dependencies"].add(cls["extends"])
                    for interface in cls.get("implements", []):
                        dependency_graph["classes"][class_name]["dependencies"].add(interface)

                # Add interfaces to package
                for interface in ast_info.get("interfaces", []):
                    interface_name = f"{package_name}.{interface['name']}"
                    dependency_graph["packages"][package_name]["interfaces"].append(interface_name)

                # Add enums to package
                for enum in ast_info.get("enums", []):
                    enum_name = f"{package_name}.{enum['name']}"
                    dependency_graph["packages"][package_name]["enums"].append(enum_name)

                # Track external dependencies
                for dep in ast_info.get("dependencies", []):
                    dependency_graph["external_dependencies"].add(dep)

                # Track internal dependencies from imports
                for import_info in ast_info.get("imports", []):
                    import_path = import_info["name"]
                    if not import_path.startswith(('java.', 'javax.', 'com.sun.', 'sun.', 'org.w3c.', 'org.xml.')):
                        # This is an internal or external dependency
                        if package_name in dependency_graph["internal_dependencies"]:
                            dependency_graph["internal_dependencies"][package_name].add(import_path)
                        else:
                            dependency_graph["internal_dependencies"][package_name] = {import_path}

            except Exception as e:
                continue

        # Convert sets to lists for JSON serialization
        dependency_graph["external_dependencies"] = list(dependency_graph["external_dependencies"])

        # Calculate dependency depth
        dependency_graph["dependency_depth"] = self._calculate_dependency_depth(dependency_graph)

        # Detect circular dependencies
        dependency_graph["circular_dependencies"] = self._detect_circular_dependencies(dependency_graph)

        return dependency_graph

    def _analyze_maven_dependencies(self, root_path: str) -> Dict:
        """Analyze Maven pom.xml for project dependencies."""
        maven_deps = {
            "dependencies": [],
            "plugins": [],
            "parent": None,
            "properties": {}
        }

        pom_file = os.path.join(root_path, "pom.xml")
        if not os.path.exists(pom_file):
            return maven_deps

        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(pom_file)
            root = tree.getroot()

            # Define namespace
            ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}

            # Extract parent information
            parent = root.find('.//mvn:parent', ns)
            if parent is not None:
                group_id = parent.find('mvn:groupId', ns)
                artifact_id = parent.find('mvn:artifactId', ns)
                version = parent.find('mvn:version', ns)
                if group_id is not None and artifact_id is not None:
                    maven_deps["parent"] = {
                        "group_id": group_id.text,
                        "artifact_id": artifact_id.text,
                        "version": version.text if version is not None else None
                    }

            # Extract dependencies
            dependencies = root.findall('.//mvn:dependencies/mvn:dependency', ns)
            for dep in dependencies:
                group_id = dep.find('mvn:groupId', ns)
                artifact_id = dep.find('mvn:artifactId', ns)
                version = dep.find('mvn:version', ns)
                scope = dep.find('mvn:scope', ns)

                if group_id is not None and artifact_id is not None:
                    maven_deps["dependencies"].append({
                        "group_id": group_id.text,
                        "artifact_id": artifact_id.text,
                        "version": version.text if version is not None else None,
                        "scope": scope.text if scope is not None else "compile"
                    })

            # Extract plugins
            plugins = root.findall('.//mvn:build/mvn:plugins/mvn:plugin', ns)
            for plugin in plugins:
                group_id = plugin.find('mvn:groupId', ns)
                artifact_id = plugin.find('mvn:artifactId', ns)
                version = plugin.find('mvn:version', ns)

                if group_id is not None and artifact_id is not None:
                    maven_deps["plugins"].append({
                        "group_id": group_id.text,
                        "artifact_id": artifact_id.text,
                        "version": version.text if version is not None else None
                    })

        except (ET.ParseError, FileNotFoundError):
            pass

        return maven_deps

    def _calculate_dependency_depth(self, dependency_graph: Dict) -> Dict:
        """Calculate the depth of dependencies for each package."""
        depth_map = {}

        def calculate_depth(package_name: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()

            if package_name in visited:
                return 0  # Circular dependency, return 0 to avoid infinite recursion

            visited.add(package_name)

            if package_name not in dependency_graph.get("internal_dependencies", {}):
                return 0

            max_depth = 0
            for dep in dependency_graph["internal_dependencies"][package_name]:
                # Extract package name from full class name
                dep_package = dep.split('.')[0] if '.' in dep else dep
                if dep_package != package_name:  # Avoid self-reference
                    dep_depth = calculate_depth(dep_package, visited.copy())
                    max_depth = max(max_depth, dep_depth + 1)

            return max_depth

        for package_name in dependency_graph.get("packages", {}):
            depth_map[package_name] = calculate_depth(package_name)

        return depth_map

    def _detect_circular_dependencies(self, dependency_graph: Dict) -> List[List[str]]:
        """Detect circular dependencies between packages."""
        circular_deps = []

        def find_cycles(package_name: str, path: List[str], visited: Set[str]):
            if package_name in path:
                # Found a cycle
                cycle_start = path.index(package_name)
                cycle = path[cycle_start:] + [package_name]
                if cycle not in circular_deps:
                    circular_deps.append(cycle)
                return

            if package_name in visited:
                return

            visited.add(package_name)
            path.append(package_name)

            if package_name in dependency_graph.get("internal_dependencies", {}):
                for dep in dependency_graph["internal_dependencies"][package_name]:
                    dep_package = dep.split('.')[0] if '.' in dep else dep
                    find_cycles(dep_package, path.copy(), visited.copy())

            path.pop()

        visited = set()
        for package_name in dependency_graph.get("packages", {}):
            if package_name not in visited:
                find_cycles(package_name, [], visited)

        return circular_deps

        return circular_deps

    def discover_tests(self, root_path: str) -> list:
        """Discover test files and functions in Java project."""
        if not isinstance(root_path, str) or not root_path:
            return {"test_files": [], "test_methods": [], "total_test_files": 0, "total_test_methods": 0}
        test_files = []
        test_methods = []

        # Find test files (JUnit, TestNG patterns)
        for root, dirs, files in os.walk(root_path):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in ['.git', 'target', 'build', 'out', 'node_modules', '.gradle']]

            for file in files:
                if file.endswith('.java') and ('test' in file.lower() or 'spec' in file.lower()):
                    file_path = os.path.join(root, file)
                    test_files.append({
                        "file_path": file_path,
                        "type": "junit" if "junit" in file.lower() else "testng" if "testng" in file.lower() else "unknown",
                        "relative_path": os.path.relpath(file_path, root_path)
                    })

                    # Extract test methods from the file
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Find test methods (JUnit @Test, TestNG @Test)
                        test_method_pattern = r'@\s*Test\s*\n\s*(?:public\s+)?(?:void\s+)?(\w+)\s*\('
                        matches = re.findall(test_method_pattern, content, re.MULTILINE)

                        for method_name in matches:
                            test_methods.append({
                                "file_path": file_path,
                                "method_name": method_name,
                                "framework": "junit" if "@Test" in content and "junit" in content.lower() else "testng"
                            })

                    except (UnicodeDecodeError, FileNotFoundError):
                        continue

        return {
            "test_files": test_files,
            "test_methods": test_methods,
            "total_test_files": len(test_files),
            "total_test_methods": len(test_methods)
        }

    def extract_documentation(self, file_path: str) -> dict:
        """Extract documentation from Java file (Javadoc comments)."""
        if not isinstance(file_path, str) or not file_path:
            return {
                "file_path": str(file_path) if file_path else "None",
                "class_docs": [],
                "method_docs": [],
                "field_docs": [],
                "total_javadoc_comments": 0
            }
        documentation = {
            "file_path": file_path,
            "class_docs": [],
            "method_docs": [],
            "field_docs": [],
            "total_javadoc_comments": 0
        }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find Javadoc comments (/** ... */)
            javadoc_pattern = r'/\*\*\s*\n(?:\s*\*\s*[^*]*\n)*\s*\*/'
            javadocs = re.findall(javadoc_pattern, content, re.MULTILINE)

            documentation["total_javadoc_comments"] = len(javadocs)

            # Extract class documentation
            class_pattern = r'/\*\*\s*\n(?:\s*\*\s*[^*]*\n)*\s*\*/\s*(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?class\s+(\w+)'
            class_matches = re.findall(class_pattern, content, re.MULTILINE)

            for class_name in class_matches:
                documentation["class_docs"].append({
                    "class_name": class_name,
                    "has_javadoc": True
                })

            # Extract method documentation
            method_pattern = r'/\*\*\s*\n(?:\s*\*\s*[^*]*\n)*\s*\*/\s*\n*(?:public\s+|private\s+|protected\s+)?(?:static\s+|final\s+|abstract\s+)?(?:\w+\s+)+\s*(\w+)\s*\('
            method_matches = re.findall(method_pattern, content, re.MULTILINE)

            for method_name in method_matches:
                documentation["method_docs"].append({
                    "method_name": method_name,
                    "has_javadoc": True
                })

            # Extract field documentation
            field_pattern = r'/\*\*\s*\n(?:\s*\*\s*[^*]*\n)*\s*\*/\s*\n*(?:public\s+|private\s+|protected\s+)?(?:static\s+|final\s+)?(?:\w+\s+)+\s*(\w+)\s*[;=]'
            field_matches = re.findall(field_pattern, content, re.MULTILINE)

            for field_name in field_matches:
                documentation["field_docs"].append({
                    "field_name": field_name,
                    "has_javadoc": True
                })

        except (UnicodeDecodeError, FileNotFoundError):
            pass

        return documentation
