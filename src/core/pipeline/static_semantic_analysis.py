"""Static semantic analysis stage for Repository Intelligence Scanner."""

import ast
import os
import re
from pathlib import Path
from typing import Dict, List, Set


def analyze_semantic_structure(file_list: List[str], structure: Dict) -> Dict:
    """Analyze the semantic structure of code files in the repository."""
    semantic = {
        "python_analysis": analyze_python_files(file_list),
        "javascript_analysis": analyze_javascript_files(file_list),
        "typescript_analysis": analyze_typescript_files(file_list),
        "java_analysis": analyze_java_files(file_list),
        "imports": {},
        "exports": {},
        "dependencies": {},
        "code_quality_signals": []
    }

    # Analyze files by language
    python_files = [f for f in file_list if f.endswith('.py')]
    if python_files:
        semantic["python_analysis"] = analyze_python_codebase(python_files)

    js_files = [f for f in file_list if f.endswith(('.js', '.jsx'))]
    if js_files:
        semantic["javascript_analysis"] = analyze_javascript_codebase(js_files)

    ts_files = [f for f in file_list if f.endswith(('.ts', '.tsx'))]
    if ts_files:
        semantic["typescript_analysis"] = analyze_typescript_codebase(ts_files)

    java_files = [f for f in file_list if f.endswith('.java')]
    if java_files:
        semantic["java_analysis"] = analyze_java_codebase(java_files)

    return semantic


def analyze_python_files(file_list: List[str]) -> Dict:
    """Basic analysis of Python files."""
    python_files = [f for f in file_list if f.endswith('.py')]
    return {
        "python_files_count": len(python_files),
        "has_main_files": any('__main__' in f or f.endswith('main.py') for f in python_files),
        "has_init_files": any('__init__.py' in f for f in python_files),
        "has_tests": any('test' in f.lower() for f in python_files)
    }


def analyze_python_codebase(python_files: List[str]) -> Dict:
    """Perform semantic analysis on Python codebase."""
    analysis = {
        "modules": [],
        "classes": [],
        "functions": [],
        "imports": [],
        "exports": [],
        "complexity_signals": [],
        "test_coverage_signals": []
    }
    
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=file_path)
            file_analysis = analyze_python_file(tree, file_path)
            
            analysis["modules"].append(file_path)
            analysis["classes"].extend(file_analysis["classes"])
            analysis["functions"].extend(file_analysis["functions"])
            analysis["imports"].extend(file_analysis["imports"])
            
        except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
            # Skip files that can't be parsed
            continue
    
    # Deduplicate and summarize
    analysis["imports"] = sorted(list(set(analysis["imports"])))
    analysis["classes"] = sorted(analysis["classes"], key=lambda x: (x["name"], x["file"], x["line"]))
    analysis["functions"] = sorted(analysis["functions"], key=lambda x: (x["name"], x["file"], x["line"]))
    analysis["modules"] = sorted(list(set(analysis["modules"])))
    analysis["total_classes"] = len(analysis["classes"])
    analysis["total_functions"] = len(analysis["functions"])
    analysis["total_modules"] = len(analysis["modules"])
    
    return analysis


def analyze_python_file(tree: ast.AST, file_path: str) -> Dict:
    """Analyze a single Python file's AST."""
    analysis = {
        "classes": [],
        "functions": [],
        "imports": []
    }
    
    class Visitor(ast.NodeVisitor):
        def visit_ClassDef(self, node):
            analysis["classes"].append({
                "name": node.name,
                "file": file_path,
                "line": node.lineno
            })
        
        def visit_FunctionDef(self, node):
            analysis["functions"].append({
                "name": node.name,
                "file": file_path,
                "line": node.lineno,
                "is_method": isinstance(node.parent, ast.ClassDef) if hasattr(node, 'parent') else False
            })
        
        def visit_Import(self, node):
            for alias in node.names:
                analysis["imports"].append(alias.name)
        
        def visit_ImportFrom(self, node):
            module = node.module or ""
            for alias in node.names:
                full_name = f"{module}.{alias.name}" if module else alias.name
                analysis["imports"].append(full_name)
    
    # Add parent references for method detection
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node
    
    visitor = Visitor()
    visitor.visit(tree)
    
    return analysis


# JavaScript/TypeScript Analysis Functions

def analyze_javascript_files(file_list: List[str]) -> Dict:
    """Basic analysis of JavaScript files."""
    js_files = [f for f in file_list if f.endswith(('.js', '.jsx'))]
    return {
        "javascript_files_count": len(js_files),
        "has_react_components": any('react' in f.lower() or f.endswith('.jsx') for f in js_files),
        "has_node_modules": any('node_modules' in f for f in js_files),
        "has_tests": any('test' in f.lower() or 'spec' in f.lower() for f in js_files)
    }


def analyze_typescript_files(file_list: List[str]) -> Dict:
    """Basic analysis of TypeScript files."""
    ts_files = [f for f in file_list if f.endswith(('.ts', '.tsx'))]
    return {
        "typescript_files_count": len(ts_files),
        "has_react_components": any('react' in f.lower() or f.endswith('.tsx') for f in ts_files),
        "has_tests": any('test' in f.lower() or 'spec' in f.lower() for f in ts_files),
        "has_config": any('tsconfig' in f.lower() for f in ts_files)
    }


def analyze_java_files(file_list: List[str]) -> Dict:
    """Basic analysis of Java files."""
    java_files = [f for f in file_list if f.endswith('.java')]
    return {
        "java_files_count": len(java_files),
        "has_maven": any('pom.xml' in f for f in file_list),
        "has_gradle": any('build.gradle' in f for f in file_list),
        "has_tests": any('test' in f.lower() for f in java_files)
    }


def analyze_javascript_codebase(js_files: List[str]) -> Dict:
    """Perform semantic analysis on JavaScript codebase."""
    analysis = {
        "modules": [],
        "classes": [],
        "functions": [],
        "imports": [],
        "exports": [],
        "react_components": [],
        "complexity_signals": [],
        "test_coverage_signals": []
    }

    for file_path in js_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            file_analysis = analyze_javascript_file(content, file_path)
            analysis["modules"].append(file_path)
            analysis["classes"].extend(file_analysis["classes"])
            analysis["functions"].extend(file_analysis["functions"])
            analysis["imports"].extend(file_analysis["imports"])
            analysis["exports"].extend(file_analysis["exports"])
            analysis["react_components"].extend(file_analysis["react_components"])

        except (UnicodeDecodeError, FileNotFoundError):
            continue

    # Deduplicate and summarize
    analysis["imports"] = sorted(list(set(analysis["imports"])))
    analysis["exports"] = sorted(list(set(analysis["exports"])))
    analysis["react_components"] = sorted(list(set(analysis["react_components"])))
    analysis["total_classes"] = len(analysis["classes"])
    analysis["total_functions"] = len(analysis["functions"])
    analysis["total_modules"] = len(analysis["modules"])
    analysis["total_react_components"] = len(analysis["react_components"])

    return analysis


def analyze_typescript_codebase(ts_files: List[str]) -> Dict:
    """Perform semantic analysis on TypeScript codebase."""
    # TypeScript is similar to JavaScript but with types
    analysis = analyze_javascript_codebase(ts_files)
    analysis["language"] = "typescript"

    # Add TypeScript-specific analysis
    analysis["interfaces"] = []
    analysis["types"] = []

    for file_path in ts_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple regex-based interface and type detection
            interfaces = re.findall(r'interface\s+(\w+)', content)
            types = re.findall(r'type\s+(\w+)', content)

            analysis["interfaces"].extend(interfaces)
            analysis["types"].extend(types)

        except (UnicodeDecodeError, FileNotFoundError):
            continue

    analysis["interfaces"] = sorted(list(set(analysis["interfaces"])))
    analysis["types"] = sorted(list(set(analysis["types"])))
    analysis["total_interfaces"] = len(analysis["interfaces"])
    analysis["total_types"] = len(analysis["types"])

    return analysis


def analyze_java_codebase(java_files: List[str]) -> Dict:
    """Perform semantic analysis on Java codebase."""
    analysis = {
        "modules": [],
        "classes": [],
        "interfaces": [],
        "enums": [],
        "methods": [],
        "imports": [],
        "packages": [],
        "annotations": [],
        "complexity_signals": [],
        "test_coverage_signals": []
    }

    for file_path in java_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            file_analysis = analyze_java_file(content, file_path)
            analysis["modules"].append(file_path)
            analysis["classes"].extend(file_analysis["classes"])
            analysis["interfaces"].extend(file_analysis["interfaces"])
            analysis["enums"].extend(file_analysis["enums"])
            analysis["methods"].extend(file_analysis["methods"])
            analysis["imports"].extend(file_analysis["imports"])
            analysis["packages"].extend(file_analysis["packages"])
            analysis["annotations"].extend(file_analysis["annotations"])

        except (UnicodeDecodeError, FileNotFoundError):
            continue

    # Deduplicate and summarize
    analysis["imports"] = sorted(list(set(analysis["imports"])))
    analysis["packages"] = sorted(list(set(analysis["packages"])))
    analysis["annotations"] = sorted(list(set(analysis["annotations"])))
    analysis["total_classes"] = len(analysis["classes"])
    analysis["total_interfaces"] = len(analysis["interfaces"])
    analysis["total_enums"] = len(analysis["enums"])
    analysis["total_methods"] = len(analysis["methods"])
    analysis["total_modules"] = len(analysis["modules"])

    return analysis


def analyze_javascript_file(content: str, file_path: str) -> Dict:
    """Analyze a single JavaScript file using regex patterns."""
    analysis = {
        "classes": [],
        "functions": [],
        "imports": [],
        "exports": [],
        "react_components": []
    }

    lines = content.split('\n')

    # Function detection (including arrow functions)
    function_patterns = [
        r'function\s+(\w+)\s*\(',
        r'const\s+(\w+)\s*=\s*\(',
        r'const\s+(\w+)\s*=\s*(\w+)\s*=>\s*{',
        r'(\w+)\s*\([^)]*\)\s*{'
    ]

    for pattern in function_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            if match and not match.startswith(('if', 'for', 'while', 'catch')):
                analysis["functions"].append({
                    "name": match,
                    "file": file_path,
                    "line": 0  # Would need more complex line tracking
                })

    # Class detection
    class_matches = re.findall(r'class\s+(\w+)', content)
    for match in class_matches:
        analysis["classes"].append({
            "name": match,
            "file": file_path,
            "line": 0
        })

    # Import detection
    import_matches = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', content)
    analysis["imports"].extend(import_matches)

    # Export detection
    export_matches = re.findall(r'export\s+(?:const|function|class)?\s*(\w+)', content)
    analysis["exports"].extend(export_matches)

    # React component detection
    react_patterns = [
        r'function\s+(\w+)\s*\([^)]*\)\s*{[^}]*return\s*\(',
        r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\('
    ]

    for pattern in react_patterns:
        matches = re.findall(pattern, content)
        analysis["react_components"].extend(matches)

    return analysis


def analyze_java_file(content: str, file_path: str) -> Dict:
    """Analyze a single Java file using regex patterns."""
    analysis = {
        "classes": [],
        "interfaces": [],
        "enums": [],
        "methods": [],
        "imports": [],
        "packages": [],
        "annotations": []
    }

    # Package detection
    package_match = re.search(r'package\s+([^;]+);', content)
    if package_match:
        analysis["packages"].append(package_match.group(1))

    # Import detection
    import_matches = re.findall(r'import\s+([^;]+);', content)
    analysis["imports"].extend(import_matches)

    # Class detection
    class_matches = re.findall(r'(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?class\s+(\w+)', content)
    for match in class_matches:
        analysis["classes"].append({
            "name": match,
            "file": file_path,
            "line": 0
        })

    # Interface detection
    interface_matches = re.findall(r'(?:public\s+)?interface\s+(\w+)', content)
    for match in interface_matches:
        analysis["interfaces"].append({
            "name": match,
            "file": file_path,
            "line": 0
        })

    # Enum detection
    enum_matches = re.findall(r'(?:public\s+)?enum\s+(\w+)', content)
    for match in enum_matches:
        analysis["enums"].append({
            "name": match,
            "file": file_path,
            "line": 0
        })

    # Method detection
    method_matches = re.findall(r'(?:public\s+|private\s+|protected\s+)?(?:static\s+|final\s+|abstract\s+)?(?:\w+\s+)+\s+(\w+)\s*\([^)]*\)', content)
    for match in method_matches:
        if not match.startswith(('if', 'for', 'while')) and match not in ['class', 'interface', 'enum']:
            analysis["methods"].append({
                "name": match,
                "file": file_path,
                "line": 0
            })

    # Annotation detection
    annotation_matches = re.findall(r'@\w+', content)
    analysis["annotations"].extend(annotation_matches)

    return analysis