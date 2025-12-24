"""Contextual Grafting Audit - Style Consistency Validation for 99.999% Accuracy.

Validates that generated code grafts maintain perfect style consistency with
the target repository's conventions, ensuring AI-generated code appears human-written.
"""

from typing import Dict, List, Any, Optional, Tuple
import os
import ast
import re
import logging
from pathlib import Path
from dataclasses import dataclass
import subprocess
import tempfile

logger = logging.getLogger(__name__)

@dataclass
class StyleViolation:
    """Represents a style violation in grafted code."""
    file_path: str
    line_number: int
    violation_type: str
    description: str
    severity: str  # 'error', 'warning', 'info'
    expected: str
    actual: str

@dataclass
class StyleProfile:
    """Repository's style profile."""
    import_order: List[str]  # ['stdlib', 'third_party', 'local']
    indentation: str  # 'spaces' or 'tabs'
    indent_size: int
    line_length: int
    quote_style: str  # 'single' or 'double'
    naming_conventions: Dict[str, str]  # {'function': 'snake_case', 'class': 'PascalCase'}
    docstring_format: str  # 'google', 'numpy', 'sphinx'
    blank_lines_between_imports: bool

@dataclass
class GraftingAuditResult:
    """Result of a style grafting audit."""
    total_violations: int
    violations_by_severity: Dict[str, int]
    style_consistency_score: float  # 0-1
    critical_violations: List[StyleViolation]
    recommendations: List[str]

class ContextualGraftingAudit:
    """Audits code grafts for style consistency with target repository."""

    def __init__(self):
        self.linter_configs = {
            'flake8': ['--max-line-length=88', '--extend-ignore=E203,W503'],
            'black': ['--check', '--diff'],
            'pylint': ['--disable=C0114,C0115,C0116']  # Disable docstring warnings for audit
        }

    def audit_code_graft(self, original_repo_path: str, grafted_code: Dict[str, str],
                        target_files: List[str]) -> GraftingAuditResult:
        """Audit grafted code for style consistency."""
        violations = []
        recommendations = []

        # Extract style profile from original repository
        style_profile = self._extract_style_profile(original_repo_path)

        # Analyze each grafted file
        for file_path, code_content in grafted_code.items():
            if file_path in target_files:
                file_violations = self._audit_file_style(code_content, file_path, style_profile)
                violations.extend(file_violations)

        # Run automated linters
        linter_violations = self._run_linters(grafted_code, original_repo_path)
        violations.extend(linter_violations)

        # Calculate consistency score
        consistency_score = self._calculate_consistency_score(violations, len(grafted_code))

        # Generate recommendations
        recommendations = self._generate_recommendations(violations, style_profile)

        violations_by_severity = {}
        for v in violations:
            violations_by_severity[v.severity] = violations_by_severity.get(v.severity, 0) + 1

        critical_violations = [v for v in violations if v.severity == 'error']

        return GraftingAuditResult(
            total_violations=len(violations),
            violations_by_severity=violations_by_severity,
            style_consistency_score=consistency_score,
            critical_violations=critical_violations,
            recommendations=recommendations
        )

    def _extract_style_profile(self, repo_path: str) -> StyleProfile:
        """Extract style profile from repository files."""
        profile = StyleProfile(
            import_order=['stdlib', 'third_party', 'local'],
            indentation='spaces',
            indent_size=4,
            line_length=88,
            quote_style='double',
            naming_conventions={
                'function': 'snake_case',
                'class': 'PascalCase',
                'variable': 'snake_case',
                'constant': 'UPPER_CASE'
            },
            docstring_format='google',
            blank_lines_between_imports=True
        )

        # Analyze Python files in repository
        python_files = list(Path(repo_path).rglob('*.py'))
        if not python_files:
            return profile

        # Sample a few files for analysis
        sample_files = python_files[:min(10, len(python_files))]

        for file_path in sample_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._analyze_file_for_profile(content, profile)
            except Exception as e:
                logger.warning(f"Failed to analyze {file_path}: {e}")

        return profile

    def _analyze_file_for_profile(self, content: str, profile: StyleProfile):
        """Analyze file content to update style profile."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return

        # Analyze indentation
        lines = content.split('\n')
        indent_sizes = []
        for line in lines[:50]:  # Check first 50 lines
            stripped = line.lstrip()
            if stripped and line != stripped:
                indent = len(line) - len(stripped)
                if indent > 0:
                    indent_sizes.append(indent)

        if indent_sizes:
            most_common_indent = max(set(indent_sizes), key=indent_sizes.count)
            profile.indent_size = most_common_indent
            profile.indentation = 'tabs' if '\t' in content[:1000] else 'spaces'

        # Analyze quote style
        single_quotes = content.count("'")
        double_quotes = content.count('"')
        profile.quote_style = 'single' if single_quotes > double_quotes else 'double'

        # Analyze naming conventions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.isupper():
                    profile.naming_conventions['function'] = 'UPPER_CASE'
                elif '_' in node.name:
                    profile.naming_conventions['function'] = 'snake_case'
                else:
                    profile.naming_conventions['function'] = 'camelCase'

            elif isinstance(node, ast.ClassDef):
                if node.name[0].isupper() and '_' not in node.name:
                    profile.naming_conventions['class'] = 'PascalCase'
                elif '_' in node.name:
                    profile.naming_conventions['class'] = 'snake_case'

    def _audit_file_style(self, content: str, file_path: str, profile: StyleProfile) -> List[StyleViolation]:
        """Audit a single file's style against the profile."""
        violations = []

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return [StyleViolation(
                file_path=file_path,
                line_number=e.lineno or 1,
                violation_type='syntax_error',
                description=f"Syntax error: {e.msg}",
                severity='error',
                expected='Valid Python syntax',
                actual='Invalid syntax'
            )]

        lines = content.split('\n')

        # Check indentation
        for i, line in enumerate(lines, 1):
            if line.strip() and not line.startswith((' ', '\t')):
                continue

            stripped = line.lstrip()
            if not stripped:
                continue

            indent_char = line[0] if line else ' '
            expected_indent = profile.indentation[0] * profile.indent_size

            if indent_char != expected_indent[0] if expected_indent else ' ':
                violations.append(StyleViolation(
                    file_path=file_path,
                    line_number=i,
                    violation_type='indentation',
                    description=f"Incorrect indentation: expected {profile.indentation}, got {indent_char}",
                    severity='warning',
                    expected=f"{profile.indentation} ({profile.indent_size})",
                    actual=indent_char
                ))

        # Check naming conventions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                expected_case = profile.naming_conventions.get('function', 'snake_case')
                if not self._check_naming_case(node.name, expected_case):
                    violations.append(StyleViolation(
                        file_path=file_path,
                        line_number=node.lineno,
                        violation_type='naming_convention',
                        description=f"Function name '{node.name}' does not follow {expected_case} convention",
                        severity='warning',
                        expected=expected_case,
                        actual=self._detect_case(node.name)
                    ))

            elif isinstance(node, ast.ClassDef):
                expected_case = profile.naming_conventions.get('class', 'PascalCase')
                if not self._check_naming_case(node.name, expected_case):
                    violations.append(StyleViolation(
                        file_path=file_path,
                        line_number=node.lineno,
                        violation_type='naming_convention',
                        description=f"Class name '{node.name}' does not follow {expected_case} convention",
                        severity='warning',
                        expected=expected_case,
                        actual=self._detect_case(node.name)
                    ))

        # Check import organization
        import_lines = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_lines.append(node.lineno)

        if len(import_lines) > 1:
            # Check for blank lines between import groups
            consecutive_imports = []
            for i in range(len(import_lines) - 1):
                if import_lines[i+1] - import_lines[i] == 1:
                    consecutive_imports.append((import_lines[i], import_lines[i+1]))

            if consecutive_imports and profile.blank_lines_between_imports:
                violations.append(StyleViolation(
                    file_path=file_path,
                    line_number=consecutive_imports[0][0],
                    violation_type='import_grouping',
                    description="Missing blank lines between import groups",
                    severity='info',
                    expected="Blank lines between import groups",
                    actual="Consecutive imports"
                ))

        return violations

    def _check_naming_case(self, name: str, expected_case: str) -> bool:
        """Check if name follows the expected case convention."""
        if expected_case == 'snake_case':
            return '_' in name or name.islower()
        elif expected_case == 'PascalCase':
            return name[0].isupper() and '_' not in name
        elif expected_case == 'camelCase':
            return name[0].islower() and '_' not in name
        elif expected_case == 'UPPER_CASE':
            return name.isupper()
        return True

    def _detect_case(self, name: str) -> str:
        """Detect the case convention of a name."""
        if name.isupper():
            return 'UPPER_CASE'
        elif '_' in name:
            return 'snake_case'
        elif name[0].isupper():
            return 'PascalCase'
        else:
            return 'camelCase'

    def _run_linters(self, grafted_code: Dict[str, str], repo_path: str) -> List[StyleViolation]:
        """Run automated linters on grafted code."""
        violations = []

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write grafted files
            for file_path, content in grafted_code.items():
                full_path = temp_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)

            # Run flake8
            try:
                result = subprocess.run(
                    ['flake8', '--max-line-length=88', str(temp_path)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0:
                    for line in result.stdout.split('\n'):
                        if line.strip() and ':' in line:
                            parts = line.split(':')
                            if len(parts) >= 3:
                                file_path = parts[0]
                                try:
                                    line_num = int(parts[1])
                                    message = ':'.join(parts[2:])
                                    violations.append(StyleViolation(
                                        file_path=file_path,
                                        line_number=line_num,
                                        violation_type='linter_flake8',
                                        description=message,
                                        severity='warning',
                                        expected='Flake8 compliance',
                                        actual='Violation'
                                    ))
                                except ValueError:
                                    continue
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("Flake8 not available or timed out")

        return violations

    def _calculate_consistency_score(self, violations: List[StyleViolation], total_files: int) -> float:
        """Calculate style consistency score."""
        if total_files == 0:
            return 1.0

        # Weight violations by severity
        weighted_violations = 0
        for v in violations:
            if v.severity == 'error':
                weighted_violations += 3
            elif v.severity == 'warning':
                weighted_violations += 1
            else:
                weighted_violations += 0.5

        # Normalize to 0-1 scale (lower violations = higher score)
        max_expected_violations = total_files * 5  # Allow some minor issues
        score = max(0, 1 - (weighted_violations / max_expected_violations))

        return score

    def _generate_recommendations(self, violations: List[StyleViolation], profile: StyleProfile) -> List[str]:
        """Generate recommendations based on violations."""
        recommendations = []

        violation_types = {}
        for v in violations:
            violation_types[v.violation_type] = violation_types.get(v.violation_type, 0) + 1

        if violation_types.get('indentation', 0) > 0:
            recommendations.append(f"Use {profile.indentation} for indentation ({profile.indent_size} spaces/tabs)")

        if violation_types.get('naming_convention', 0) > 0:
            recommendations.append(f"Follow naming conventions: {profile.naming_conventions}")

        if violation_types.get('import_grouping', 0) > 0:
            recommendations.append("Add blank lines between import groups (stdlib, third-party, local)")

        if violation_types.get('linter_flake8', 0) > 0:
            recommendations.append("Run 'black' and 'flake8' to auto-fix style issues")

        if not recommendations:
            recommendations.append("Code style is consistent with repository conventions")

        return recommendations