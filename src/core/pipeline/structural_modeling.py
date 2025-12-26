"""Structural modeling stage for Repository Intelligence Scanner."""

import os
from pathlib import Path
from typing import Dict, List, Set


def analyze_repository_structure(file_list: List[str]) -> Dict:
    """Analyze the structural composition of the repository."""
    structure = {
        "languages": detect_languages(file_list),
        "frameworks": detect_frameworks(file_list),
        "build_systems": detect_build_systems(file_list),
        "test_frameworks": detect_test_frameworks(file_list),
        "documentation": detect_documentation(file_list),
        "configuration": detect_configuration(file_list),
        "file_counts": get_file_counts(file_list)
    }
    return structure


def detect_languages(file_list: List[str]) -> Dict[str, int]:
    """Detect programming languages based on file extensions."""
    extensions = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.java': 'Java',
        '.rs': 'Rust',
        '.go': 'Go',
        '.cpp': 'C++',
        '.c': 'C',
        '.h': 'C/C++ Header',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.sh': 'Shell',
        '.yml': 'YAML',
        '.yaml': 'YAML',
        '.json': 'JSON',
        '.xml': 'XML',
        '.md': 'Markdown',
        '.txt': 'Text'
    }
    
    languages = {}
    for file_path in file_list:
        _, ext = os.path.splitext(file_path)
        lang = extensions.get(ext.lower(), 'Unknown')
        languages[lang] = languages.get(lang, 0) + 1
    
    return languages


def detect_frameworks(file_list: List[str]) -> List[str]:
    """Detect frameworks based on configuration files."""
    frameworks = []
    
    # Python
    if any('requirements.txt' in f for f in file_list):
        frameworks.append('Python (requirements.txt)')
    if any('pyproject.toml' in f for f in file_list):
        frameworks.append('Python (pyproject.toml)')
    if any('setup.py' in f for f in file_list):
        frameworks.append('Python (setup.py)')
    
    # Node.js
    if any('package.json' in f for f in file_list):
        frameworks.append('Node.js')
    
    # Java
    if any('pom.xml' in f for f in file_list):
        frameworks.append('Maven (Java)')
    if any('build.gradle' in f for f in file_list):
        frameworks.append('Gradle (Java)')
    
    # Rust
    if any('Cargo.toml' in f for f in file_list):
        frameworks.append('Rust (Cargo)')
    
    return frameworks


def detect_build_systems(file_list: List[str]) -> List[str]:
    """Detect build systems."""
    build_systems = []
    
    if any('Makefile' in f for f in file_list):
        build_systems.append('Make')
    if any('CMakeLists.txt' in f for f in file_list):
        build_systems.append('CMake')
    if any('build.gradle' in f for f in file_list):
        build_systems.append('Gradle')
    if any('pom.xml' in f for f in file_list):
        build_systems.append('Maven')
    
    return build_systems


def detect_test_frameworks(file_list: List[str]) -> List[str]:
    """Detect test frameworks."""
    test_frameworks = []
    
    # Python
    if any('pytest' in f.lower() for f in file_list):
        test_frameworks.append('pytest')
    if any('unittest' in f.lower() for f in file_list):
        test_frameworks.append('unittest')
    
    # JavaScript
    if any('jest' in f.lower() for f in file_list):
        test_frameworks.append('Jest')
    if any('mocha' in f.lower() for f in file_list):
        test_frameworks.append('Mocha')
    
    # Look for test directories
    if any('test' in f.lower() and os.path.isdir(f) for f in file_list):
        test_frameworks.append('Test Directory Detected')
    
    return test_frameworks


def detect_documentation(file_list: List[str]) -> List[str]:
    """Detect documentation files."""
    docs = []
    
    if any('README' in f.upper() for f in file_list):
        docs.append('README')
    if any('docs/' in f for f in file_list):
        docs.append('docs/ directory')
    if any('.md' in f for f in file_list):
        docs.append('Markdown files')
    
    return docs


def detect_configuration(file_list: List[str]) -> List[str]:
    """Detect configuration files."""
    config = []
    
    config_files = ['.gitignore', '.gitattributes', '.editorconfig', '.prettierrc', 'eslint.config.js']
    for cf in config_files:
        if any(cf in f for f in file_list):
            config.append(cf)
    
    return config


def get_file_counts(file_list: List[str]) -> Dict[str, int]:
    """Get counts of different file types."""
    # Normalize and deduplicate input paths to avoid variations caused by
    # traversal order or duplicate entries. Use a sorted list so iteration
    # order is deterministic across runs.
    normalized_files = sorted({os.path.normpath(f) for f in file_list})

    counts = {
        'total': len(normalized_files),
        'code': 0,
        'test': 0,
        'config': 0,
        'docs': 0
    }

    code_exts = {'.py', '.js', '.ts', '.java', '.rs', '.go', '.cpp', '.c', '.rb', '.php'}
    config_exts = {'.yml', '.yaml', '.json', '.xml', '.toml', '.ini', '.cfg'}

    for file_path in normalized_files:
        lower = file_path.lower()
        _, ext = os.path.splitext(lower)

        if ext in code_exts:
            counts['code'] += 1
        if 'test' in lower:
            counts['test'] += 1
        if ext in config_exts:
            counts['config'] += 1
        if 'readme' in lower or ext == '.md' or 'docs' in lower:
            counts['docs'] += 1

    return counts