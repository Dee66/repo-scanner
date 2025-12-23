#!/usr/bin/env python3
"""
Advanced Code Analysis Stage

Performs advanced static analysis including control flow analysis,
data flow tracking, complexity analysis, and code quality metrics.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ControlFlowNode:
    """Represents a node in the control flow graph."""
    node_type: str  # 'function', 'if', 'loop', 'return', etc.
    line_number: int
    code: str
    successors: List[int] = None
    predecessors: List[int] = None

    def __post_init__(self):
        if self.successors is None:
            self.successors = []
        if self.predecessors is None:
            self.predecessors = []

@dataclass
class DataFlowVariable:
    """Represents a variable in data flow analysis."""
    name: str
    defined_at: List[int]  # Line numbers where defined
    used_at: List[int]     # Line numbers where used
    var_type: str = "unknown"

class AdvancedCodeAnalyzer:
    """Performs advanced static analysis on code."""

    def __init__(self):
        self.complexity_patterns = {
            'cyclomatic': self._calculate_cyclomatic_complexity,
            'cognitive': self._calculate_cognitive_complexity,
            'halstead': self._calculate_halstead_metrics
        }
        self.repo_root = None

    def analyze_advanced_code(self, file_list: List[str], semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive advanced code analysis.

        Args:
            file_list: List of files to analyze
            semantic_data: Semantic analysis results

        Returns:
            Dict containing advanced analysis results
        """
        logger.info("Starting advanced code analysis")

        analysis_results = {
            "control_flow_analysis": {},
            "data_flow_analysis": {},
            "complexity_analysis": {},
            "code_quality_metrics": {},
            "advanced_insights": [],
            "analysis_summary": {}
        }

        # Analyze each file
        for file_path in file_list:
            if file_path.endswith(('.py', '.js', '.ts', '.java')):
                try:
                    file_results = self._analyze_file(file_path)
                    analysis_results["control_flow_analysis"][file_path] = file_results.get("control_flow", {})
                    analysis_results["data_flow_analysis"][file_path] = file_results.get("data_flow", {})
                    analysis_results["complexity_analysis"][file_path] = file_results.get("complexity", {})
                    analysis_results["code_quality_metrics"][file_path] = file_results.get("quality", {})

                except Exception as e:
                    logger.warning(f"Failed to analyze {file_path}: {e}")

        # Generate summary insights
        analysis_results["advanced_insights"] = self._generate_advanced_insights(analysis_results)
        analysis_results["analysis_summary"] = self._generate_analysis_summary(analysis_results)

        return analysis_results

    def _analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a single file for advanced metrics."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Determine language and analyze accordingly
            if file_path.endswith('.py'):
                return self._analyze_python_file(content, file_path)
            elif file_path.endswith(('.js', '.ts')):
                return self._analyze_javascript_file(content, file_path)
            elif file_path.endswith('.java'):
                return self._analyze_java_file(content, file_path)
            else:
                return {}

        except Exception as e:
            logger.warning(f"Error analyzing file {file_path}: {e}")
            return {}

    def _analyze_python_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze Python file with AST-based analysis."""
        results = {
            "control_flow": {},
            "data_flow": {},
            "complexity": {},
            "quality": {}
        }

        try:
            tree = ast.parse(content)

            # Control flow analysis
            results["control_flow"] = self._analyze_python_control_flow(tree)

            # Data flow analysis
            results["data_flow"] = self._analyze_python_data_flow(tree)

            # Complexity analysis
            results["complexity"] = self._calculate_python_complexity(tree, content)

            # Code quality metrics
            results["quality"] = self._calculate_python_quality_metrics(tree, content)

        except SyntaxError:
            # Fallback to regex-based analysis for files with syntax errors
            results["control_flow"] = self._analyze_python_control_flow_regex(content)
            results["complexity"] = self._calculate_complexity_regex(content, 'python')

        return results

    def _analyze_python_control_flow(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze Python control flow using AST."""
        control_nodes = []
        functions = []

        class ControlFlowVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                functions.append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': len(node.args.args),
                    'complexity': self._calculate_function_complexity(node)
                })
                self.generic_visit(node)

            def visit_If(self, node):
                control_nodes.append(ControlFlowNode('if', node.lineno, f'if {self._get_node_code(node.test)}'))
                self.generic_visit(node)

            def visit_For(self, node):
                control_nodes.append(ControlFlowNode('loop', node.lineno, f'for {self._get_node_code(node.target)}'))
                self.generic_visit(node)

            def visit_While(self, node):
                control_nodes.append(ControlFlowNode('loop', node.lineno, f'while {self._get_node_code(node.test)}'))
                self.generic_visit(node)

            def _get_node_code(self, node):
                return "condition"  # Simplified

            def _calculate_function_complexity(self, node):
                complexity = 1  # Base complexity
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.For, ast.While, ast.And, ast.Or)):
                        complexity += 1
                return complexity

        visitor = ControlFlowVisitor()
        visitor.visit(tree)

        return {
            'functions': functions,
            'control_structures': len(control_nodes),
            'total_functions': len(functions),
            'average_function_complexity': sum(f['complexity'] for f in functions) / len(functions) if functions else 0
        }

    def _analyze_python_data_flow(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze Python data flow."""
        variables = {}

        class DataFlowVisitor(ast.NodeVisitor):
            def visit_Name(self, node):
                if isinstance(node.ctx, ast.Store):
                    # Variable definition
                    if node.id not in variables:
                        variables[node.id] = DataFlowVariable(node.id, [], [])
                    variables[node.id].defined_at.append(node.lineno)
                elif isinstance(node.ctx, ast.Load):
                    # Variable usage
                    if node.id not in variables:
                        variables[node.id] = DataFlowVariable(node.id, [], [])
                    variables[node.id].used_at.append(node.lineno)

        visitor = DataFlowVisitor()
        visitor.visit(tree)

        return {
            'variables': {name: {
                'definitions': var.defined_at,
                'usages': var.used_at,
                'total_definitions': len(var.defined_at),
                'total_usages': len(var.used_at)
            } for name, var in variables.items()},
            'total_variables': len(variables),
            'average_usages_per_variable': sum(len(v.used_at) for v in variables.values()) / len(variables) if variables else 0
        }

    def _calculate_python_complexity(self, tree: ast.AST, content: str) -> Dict[str, Any]:
        """Calculate complexity metrics for Python code."""
        lines = content.split('\n')
        total_lines = len(lines)

        # Cyclomatic complexity
        cyclomatic = self._calculate_cyclomatic_complexity(content, 'python')

        # Cognitive complexity
        cognitive = self._calculate_cognitive_complexity(content, 'python')

        # Halstead metrics
        halstead = self._calculate_halstead_metrics(content, 'python')

        return {
            'cyclomatic_complexity': cyclomatic,
            'cognitive_complexity': cognitive,
            'halstead_metrics': halstead,
            'lines_of_code': total_lines,
            'complexity_score': (cyclomatic + cognitive) / 2
        }

    def _calculate_python_quality_metrics(self, tree: ast.AST, content: str) -> Dict[str, Any]:
        """Calculate code quality metrics for Python."""
        metrics = {
            'maintainability_index': 100,  # Placeholder
            'technical_debt_ratio': 0.0,   # Placeholder
            'duplication_percentage': 0.0, # Would need comparison with other files
            'documentation_coverage': 0.0, # Placeholder
            'test_coverage_estimate': 0.0  # Placeholder
        }

        # Count functions with docstrings
        functions_with_docs = 0
        total_functions = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                total_functions += 1
                if ast.get_docstring(node):
                    functions_with_docs += 1

        if total_functions > 0:
            metrics['documentation_coverage'] = functions_with_docs / total_functions

        return metrics

    def _analyze_javascript_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript file."""
        # Use regex-based analysis for JS/TS
        return {
            "control_flow": self._analyze_javascript_control_flow_regex(content),
            "data_flow": self._analyze_javascript_data_flow_regex(content),
            "complexity": self._calculate_complexity_regex(content, 'javascript'),
            "quality": self._calculate_javascript_quality_metrics(content)
        }

    def _analyze_java_file(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analyze Java file."""
        # Use regex-based analysis for Java
        return {
            "control_flow": self._analyze_java_control_flow_regex(content),
            "data_flow": self._analyze_java_data_flow_regex(content),
            "complexity": self._calculate_complexity_regex(content, 'java'),
            "quality": self._calculate_java_quality_metrics(content)
        }

    # Control flow analysis methods
    def _analyze_python_control_flow_regex(self, content: str) -> Dict[str, Any]:
        """Regex-based control flow analysis for Python."""
        functions = len(re.findall(r'def\s+\w+', content))
        if_statements = len(re.findall(r'\bif\s+', content))
        loops = len(re.findall(r'\b(for|while)\s+', content))

        return {
            'functions': functions,
            'control_structures': if_statements + loops,
            'if_statements': if_statements,
            'loops': loops
        }

    def _analyze_javascript_control_flow_regex(self, content: str) -> Dict[str, Any]:
        """Regex-based control flow analysis for JavaScript."""
        functions = len(re.findall(r'\bfunction\s+\w+|const\s+\w+\s*=\s*\(', content))
        if_statements = len(re.findall(r'\bif\s*\(', content))
        loops = len(re.findall(r'\b(for|while|do)\s+', content))

        return {
            'functions': functions,
            'control_structures': if_statements + loops,
            'if_statements': if_statements,
            'loops': loops
        }

    def _analyze_java_control_flow_regex(self, content: str) -> Dict[str, Any]:
        """Regex-based control flow analysis for Java."""
        methods = len(re.findall(r'\b(public|private|protected)?\s+\w+\s+\w+\s*\(', content))
        if_statements = len(re.findall(r'\bif\s*\(', content))
        loops = len(re.findall(r'\b(for|while|do)\s+', content))

        return {
            'methods': methods,
            'control_structures': if_statements + loops,
            'if_statements': if_statements,
            'loops': loops
        }

    # Data flow analysis methods
    def _analyze_python_data_flow_regex(self, content: str) -> Dict[str, Any]:
        """Regex-based data flow analysis for Python."""
        # Simple variable analysis
        assignments = len(re.findall(r'\w+\s*=\s*[^=]', content))
        usages = len(re.findall(r'\b\w+\b(?!\s*=)', content))

        return {
            'variable_assignments': assignments,
            'variable_usages': usages,
            'data_flow_complexity': assignments + usages
        }

    def _analyze_javascript_data_flow_regex(self, content: str) -> Dict[str, Any]:
        """Regex-based data flow analysis for JavaScript."""
        var_declarations = len(re.findall(r'\b(var|let|const)\s+\w+', content))
        assignments = len(re.findall(r'\w+\s*=\s*[^=]', content))

        return {
            'variable_declarations': var_declarations,
            'assignments': assignments,
            'data_flow_complexity': var_declarations + assignments
        }

    def _analyze_java_data_flow_regex(self, content: str) -> Dict[str, Any]:
        """Regex-based data flow analysis for Java."""
        declarations = len(re.findall(r'\b\w+\s+\w+\s*;', content))
        assignments = len(re.findall(r'\w+\s*=\s*[^=]', content))

        return {
            'variable_declarations': declarations,
            'assignments': assignments,
            'data_flow_complexity': declarations + assignments
        }

    # Complexity calculation methods
    def _calculate_cyclomatic_complexity(self, content: str, language: str) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity

        # Decision points
        if language == 'python':
            complexity += len(re.findall(r'\b(if|elif|for|while|and|or|case)\b', content))
        elif language in ['javascript', 'java']:
            complexity += len(re.findall(r'\b(if|for|while|case|&&|\|\|)\b', content))

        return complexity

    def _calculate_cognitive_complexity(self, content: str, language: str) -> int:
        """Calculate cognitive complexity."""
        # Simplified cognitive complexity
        complexity = self._calculate_cyclomatic_complexity(content, language)

        # Add nesting levels
        lines = content.split('\n')
        nesting_level = 0
        max_nesting = 0

        for line in lines:
            indent = len(line) - len(line.lstrip())
            if language == 'python':
                nesting_level = indent // 4
            else:
                nesting_level = indent // 2
            max_nesting = max(max_nesting, nesting_level)

        return complexity + max_nesting

    def _calculate_halstead_metrics(self, content: str, language: str) -> Dict[str, Any]:
        """Calculate Halstead complexity metrics."""
        # Simplified Halstead metrics
        operators = len(re.findall(r'[+\-*/=<>!&|]', content))
        operands = len(re.findall(r'\b\w+\b', content))

        return {
            'operators': operators,
            'operands': operands,
            'program_length': operators + operands,
            'vocabulary_size': len(set(re.findall(r'\b\w+\b', content))),
            'volume': (operators + operands) * (operators + operands).bit_length() if operators + operands > 0 else 0
        }

    def _calculate_complexity_regex(self, content: str, language: str) -> Dict[str, Any]:
        """Calculate complexity using regex patterns."""
        return {
            'cyclomatic_complexity': self._calculate_cyclomatic_complexity(content, language),
            'cognitive_complexity': self._calculate_cognitive_complexity(content, language),
            'halstead_metrics': self._calculate_halstead_metrics(content, language)
        }

    # Quality metrics methods
    def _calculate_javascript_quality_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate quality metrics for JavaScript."""
        return {
            'maintainability_index': 85.0,  # Placeholder
            'technical_debt_ratio': 0.05,   # Placeholder
            'eslint_violations_estimate': len(re.findall(r'(var\s|==\s|!=\s)', content))
        }

    def _calculate_java_quality_metrics(self, content: str) -> Dict[str, Any]:
        """Calculate quality metrics for Java."""
        return {
            'maintainability_index': 80.0,  # Placeholder
            'technical_debt_ratio': 0.08,   # Placeholder
            'checkstyle_violations_estimate': len(re.findall(r'(public\s+\w+\s*\(|;\s*$)', content))
        }

    def _generate_advanced_insights(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate advanced insights from analysis results."""
        insights = []

        # Analyze control flow complexity
        control_flow = analysis_results.get("control_flow_analysis", {})
        high_complexity_files = []

        for file_path, file_data in control_flow.items():
            if isinstance(file_data, dict):
                avg_complexity = file_data.get("average_function_complexity", 0)
                if avg_complexity > 10:
                    high_complexity_files.append({
                        'file': file_path,
                        'complexity': avg_complexity,
                        'type': 'high_function_complexity'
                    })

        if high_complexity_files:
            insights.append({
                'type': 'complexity_warning',
                'severity': 'medium',
                'description': f'Found {len(high_complexity_files)} files with high function complexity',
                'details': high_complexity_files[:5]  # Top 5
            })

        # Analyze data flow issues
        data_flow = analysis_results.get("data_flow_analysis", {})
        data_flow_issues = []

        for file_path, file_data in data_flow.items():
            if isinstance(file_data, dict):
                variables = file_data.get("variables", {})
                for var_name, var_data in variables.items():
                    if var_data.get("total_definitions", 0) > 5:
                        data_flow_issues.append({
                            'file': file_path,
                            'variable': var_name,
                            'definitions': var_data['total_definitions'],
                            'type': 'frequently_redefined_variable'
                        })

        if data_flow_issues:
            insights.append({
                'type': 'data_flow_warning',
                'severity': 'low',
                'description': f'Found {len(data_flow_issues)} variables redefined frequently',
                'details': data_flow_issues[:3]
            })

        return insights

    def _generate_analysis_summary(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall analysis summary."""
        total_files = len(analysis_results.get("control_flow_analysis", {}))
        total_functions = 0
        total_complexity = 0
        complexity_count = 0

        for file_data in analysis_results.get("control_flow_analysis", {}).values():
            if isinstance(file_data, dict):
                total_functions += file_data.get("total_functions", 0)
                avg_complexity = file_data.get("average_function_complexity", 0)
                if avg_complexity > 0:
                    total_complexity += avg_complexity
                    complexity_count += 1

        return {
            'total_files_analyzed': total_files,
            'total_functions_analyzed': total_functions,
            'average_complexity': total_complexity / complexity_count if complexity_count > 0 else 0,
            'analysis_coverage': f"{total_files} files with advanced analysis"
        }


def analyze_advanced_code(file_list: List[str], semantic_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze code using advanced static analysis techniques.

    Args:
        file_list: List of files to analyze
        semantic_data: Semantic analysis results

    Returns:
        Dict containing advanced analysis results
    """
    analyzer = AdvancedCodeAnalyzer()
    return analyzer.analyze_advanced_code(file_list, semantic_data)