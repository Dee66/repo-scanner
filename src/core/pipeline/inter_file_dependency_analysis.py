"""Inter-file Dependency Analysis for Repository Intelligence Scanner.

This module analyzes dependencies between files in a codebase to detect
architectural patterns and relationships.
"""

from typing import Dict, List, Set, Tuple, Optional
import os
import re
from pathlib import Path


class InterFileDependencyAnalyzer:
    """Analyzes dependencies between files in a codebase."""

    def __init__(self):
        self.file_dependencies = {}  # file -> set of files it depends on
        self.reverse_dependencies = {}  # file -> set of files that depend on it
        self.dependency_graph = {}

    def analyze_inter_file_dependencies(self, file_list: List[str], semantic_analysis: Dict) -> Dict:
        """Analyze dependencies between files in the codebase."""
        # Build dependency graph
        self._build_dependency_graph(file_list, semantic_analysis)

        # Analyze architectural patterns
        architectural_patterns = self._detect_architectural_patterns()

        # Calculate dependency metrics
        dependency_metrics = self._calculate_dependency_metrics()

        return {
            "dependency_graph": self.dependency_graph,
            "architectural_patterns": architectural_patterns,
            "dependency_metrics": dependency_metrics,
            "file_dependencies": self.file_dependencies,
            "reverse_dependencies": self.reverse_dependencies
        }

    def _build_dependency_graph(self, file_list: List[str], semantic_analysis: Dict):
        """Build a graph of dependencies between files."""
        # Initialize dependency tracking
        for file_path in file_list:
            self.file_dependencies[file_path] = set()
            self.reverse_dependencies[file_path] = set()

        # Analyze Python files
        python_files = [f for f in file_list if f.endswith('.py')]
        self._analyze_python_dependencies(python_files, semantic_analysis)

        # Analyze JavaScript/TypeScript files
        js_files = [f for f in file_list if f.endswith(('.js', '.ts', '.jsx', '.tsx'))]
        self._analyze_javascript_dependencies(js_files, semantic_analysis)

        # Analyze Java files
        java_files = [f for f in file_list if f.endswith('.java')]
        self._analyze_java_dependencies(java_files, semantic_analysis)

        # Build reverse dependencies
        self._build_reverse_dependencies()

    def _analyze_python_dependencies(self, python_files: List[str], semantic_analysis: Dict):
        """Analyze dependencies in Python files."""
        python_analysis = semantic_analysis.get('python_analysis', {})

        for file_path in python_files:
            imports = self._extract_python_imports(file_path, python_analysis)
            self.file_dependencies[file_path] = imports

    def _analyze_javascript_dependencies(self, js_files: List[str], semantic_analysis: Dict):
        """Analyze dependencies in JavaScript/TypeScript files."""
        js_analysis = semantic_analysis.get('javascript_analysis', {})

        for file_path in js_files:
            imports = self._extract_javascript_imports(file_path, js_analysis)
            self.file_dependencies[file_path] = imports

    def _analyze_java_dependencies(self, java_files: List[str], semantic_analysis: Dict):
        """Analyze dependencies in Java files."""
        java_analysis = semantic_analysis.get('java_analysis', {})

        for file_path in java_files:
            imports = self._extract_java_imports(file_path, java_analysis)
            self.file_dependencies[file_path] = imports

    def _extract_python_imports(self, file_path: str, python_analysis: Dict) -> Set[str]:
        """Extract imports from a Python file."""
        imports = set()

        # Get file-specific analysis
        file_analysis = python_analysis.get(file_path, {})
        file_imports = file_analysis.get('imports', [])

        for import_info in file_imports:
            if isinstance(import_info, dict):
                module = import_info.get('module', '')
                if module and '.' in module:
                    # Try to resolve module to file
                    resolved_file = self._resolve_python_module_to_file(module, file_path)
                    if resolved_file:
                        imports.add(resolved_file)

        return imports

    def _extract_javascript_imports(self, file_path: str, js_analysis: Dict) -> Set[str]:
        """Extract imports from a JavaScript/TypeScript file."""
        imports = set()

        # Get file-specific analysis
        file_analysis = js_analysis.get(file_path, {})
        file_imports = file_analysis.get('imports', [])

        for import_info in file_imports:
            if isinstance(import_info, dict):
                source = import_info.get('source', '')
                if source.startswith('./') or source.startswith('../'):
                    # Relative import
                    resolved_file = self._resolve_relative_import(source, file_path)
                    if resolved_file:
                        imports.add(resolved_file)

        return imports

    def _extract_java_imports(self, file_path: str, java_analysis: Dict) -> Set[str]:
        """Extract imports from a Java file."""
        imports = set()

        # Get file-specific analysis
        file_analysis = java_analysis.get(file_path, {})
        file_imports = file_analysis.get('imports', [])

        for import_stmt in file_imports:
            if isinstance(import_stmt, str):
                # Try to resolve import to file
                resolved_file = self._resolve_java_import_to_file(import_stmt, file_path)
                if resolved_file:
                    imports.add(resolved_file)

        return imports

    def _resolve_python_module_to_file(self, module: str, importing_file: str) -> Optional[str]:
        """Resolve a Python module import to a file path."""
        # This is a simplified resolver - in practice would need more sophisticated logic
        base_path = os.path.dirname(importing_file)
        module_parts = module.split('.')

        # Try different file extensions
        for ext in ['.py', '/__init__.py']:
            candidate = os.path.join(base_path, *module_parts) + ext
            if os.path.exists(candidate):
                return candidate

        return None

    def _resolve_relative_import(self, import_path: str, importing_file: str) -> Optional[str]:
        """Resolve a relative import to a file path."""
        base_dir = os.path.dirname(importing_file)
        resolved_path = os.path.normpath(os.path.join(base_dir, import_path))

        # Try different extensions
        for ext in ['', '.js', '.ts', '.jsx', '.tsx', '/index.js', '/index.ts']:
            candidate = resolved_path + ext
            if os.path.exists(candidate):
                return candidate

        return None

    def _resolve_java_import_to_file(self, import_stmt: str, importing_file: str) -> Optional[str]:
        """Resolve a Java import to a file path."""
        # Extract class name from import
        if import_stmt.endswith('.*'):
            return None  # Package import

        class_name = import_stmt.split('.')[-1]
        package_path = import_stmt[:-len(class_name)-1]  # Remove class name and dot

        # Convert package to path
        package_parts = package_path.split('.')
        candidate = os.path.join(*package_parts, class_name + '.java')

        # This is simplified - would need classpath resolution in practice
        return candidate if os.path.exists(candidate) else None

    def _build_reverse_dependencies(self):
        """Build reverse dependency mapping."""
        for file_path, deps in self.file_dependencies.items():
            for dep in deps:
                if dep not in self.reverse_dependencies:
                    self.reverse_dependencies[dep] = set()
                self.reverse_dependencies[dep].add(file_path)

    def _detect_architectural_patterns(self) -> Dict:
        """Detect architectural patterns from dependency analysis."""
        patterns = {
            "layered_architecture": self._detect_layered_architecture(),
            "microservices": self._detect_microservices_pattern(),
            "shared_libraries": self._detect_shared_libraries(),
            "circular_dependencies": self._detect_circular_dependencies(),
            "high_coupling_files": self._detect_high_coupling_files()
        }

        return patterns

    def _detect_layered_architecture(self) -> Dict:
        """Detect layered architecture patterns."""
        # Simple heuristic: look for common layer naming patterns
        layers = {
            "presentation": [],
            "business": [],
            "data": []
        }

        for file_path in self.file_dependencies:
            path_lower = file_path.lower()
            if any(keyword in path_lower for keyword in ['ui', 'view', 'controller', 'handler']):
                layers["presentation"].append(file_path)
            elif any(keyword in path_lower for keyword in ['service', 'logic', 'business']):
                layers["business"].append(file_path)
            elif any(keyword in path_lower for keyword in ['dao', 'repository', 'model', 'entity']):
                layers["data"].append(file_path)

        return {
            "detected": len(layers["presentation"]) > 0 and len(layers["business"]) > 0,
            "layers": layers,
            "layer_dependencies": self._analyze_layer_dependencies(layers)
        }

    def _detect_microservices_pattern(self) -> Dict:
        """Detect microservices architectural patterns."""
        # Look for service boundaries and independent deployments
        services = []
        service_indicators = ['service', 'api', 'microservice', 'lambda', 'function']

        for file_path in self.file_dependencies:
            if any(indicator in file_path.lower() for indicator in service_indicators):
                services.append(file_path)

        return {
            "detected": len(services) > 1,
            "potential_services": services,
            "service_isolation": self._analyze_service_isolation(services)
        }

    def _detect_shared_libraries(self) -> Dict:
        """Detect shared library usage patterns."""
        shared_files = []

        for file_path, dependents in self.reverse_dependencies.items():
            if len(dependents) > 3:  # Used by more than 3 files
                shared_files.append({
                    "file": file_path,
                    "usage_count": len(dependents),
                    "dependents": list(dependents)
                })

        return {
            "shared_components": shared_files,
            "shared_library_ratio": len(shared_files) / max(1, len(self.file_dependencies))
        }

    def _detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies between files."""
        # Simple cycle detection using DFS
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.file_dependencies.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in self.file_dependencies:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _detect_high_coupling_files(self) -> List[Dict]:
        """Detect files with high coupling (many dependencies)."""
        high_coupling = []

        for file_path, deps in self.file_dependencies.items():
            if len(deps) > 10:  # Arbitrary threshold
                high_coupling.append({
                    "file": file_path,
                    "dependency_count": len(deps),
                    "dependencies": list(deps)
                })

        return sorted(high_coupling, key=lambda x: x["dependency_count"], reverse=True)

    def _analyze_layer_dependencies(self, layers: Dict) -> Dict:
        """Analyze dependencies between architectural layers."""
        layer_deps = {
            "presentation_to_business": 0,
            "business_to_data": 0,
            "presentation_to_data": 0,  # Should be minimal in layered architecture
            "data_to_presentation": 0,  # Should be zero in layered architecture
            "data_to_business": 0       # Should be zero in layered architecture
        }

        # Count dependencies between layers
        for from_file in self.file_dependencies:
            from_layer = self._get_file_layer(from_file, layers)
            if not from_layer:
                continue

            for to_file in self.file_dependencies[from_file]:
                to_layer = self._get_file_layer(to_file, layers)
                if to_layer:
                    dep_key = f"{from_layer}_to_{to_layer}"
                    if dep_key in layer_deps:
                        layer_deps[dep_key] += 1

        return layer_deps

    def _get_file_layer(self, file_path: str, layers: Dict) -> Optional[str]:
        """Get the architectural layer of a file."""
        for layer_name, files in layers.items():
            if file_path in files:
                return layer_name
        return None

    def _analyze_service_isolation(self, services: List[str]) -> Dict:
        """Analyze how well services are isolated."""
        cross_service_deps = 0
        total_deps = 0

        for service in services:
            service_deps = self.file_dependencies.get(service, set())
            total_deps += len(service_deps)

            # Count dependencies to other services
            for dep in service_deps:
                if dep in services and dep != service:
                    cross_service_deps += 1

        return {
            "cross_service_dependencies": cross_service_deps,
            "total_dependencies": total_deps,
            "isolation_ratio": 1 - (cross_service_deps / max(1, total_deps))
        }

    def _calculate_dependency_metrics(self) -> Dict:
        """Calculate various dependency metrics."""
        total_files = len(self.file_dependencies)
        total_dependencies = sum(len(deps) for deps in self.file_dependencies.values())

        # Calculate average dependencies per file
        avg_deps = total_dependencies / max(1, total_files)

        # Find most depended upon files
        most_depended = sorted(
            [(file, len(dependents)) for file, dependents in self.reverse_dependencies.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "total_files": total_files,
            "total_dependencies": total_dependencies,
            "average_dependencies_per_file": avg_deps,
            "most_depended_upon_files": most_depended,
            "dependency_density": total_dependencies / max(1, total_files * (total_files - 1))
        }


def analyze_inter_file_dependencies(file_list: List[str], semantic_analysis: Dict) -> Dict:
    """Main entry point for inter-file dependency analysis."""
    analyzer = InterFileDependencyAnalyzer()
    return analyzer.analyze_inter_file_dependencies(file_list, semantic_analysis)