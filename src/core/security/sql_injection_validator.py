"""SQL Injection deep validation with context-aware analysis.

This module provides a 5-layer validation system for SQL injection detection:
1. Pattern Analysis - Detect unsafe SQL construction
2. Context Analysis - Check file type and usage context
3. Dataflow Analysis - Trace input sources and sanitization
4. Framework-Specific Validation - Check ORM/framework usage
5. Confidence Scoring - Calculate detection confidence
"""

from typing import Tuple, List, Optional
import re


class SQLInjectionValidator:
    """Multi-layer validation for SQL injection detection."""
    
    # Unsafe SQL patterns (string concatenation, format strings)
    # Require SQL structural context (FROM, SET, INTO, VALUES, WHERE) alongside keywords
    # to avoid matching English words (e.g., "Updated" matching UPDATE)
    UNSAFE_PATTERNS = [
        # Python string formatting with concatenation
        (r'\b(SELECT\b.+?\bFROM\b|INSERT\s+INTO\b|UPDATE\b.+?\bSET\b|DELETE\s+FROM\b).*?["\'].*?\+', 'String concatenation in SQL'),
        (r'\+.*?\b(SELECT\b.+?\bFROM\b|INSERT\s+INTO\b|UPDATE\b.+?\bSET\b|DELETE\s+FROM\b)', 'String concatenation in SQL'),
        # F-strings with actual SQL structure
        (r'f["\'].*?\b(SELECT\b.+?\bFROM\b|INSERT\s+INTO\b|UPDATE\b.+?\bSET\b|DELETE\s+FROM\b).*?\{', 'F-string in SQL'),
        # .format() method with actual SQL structure
        (r'["\'].*?\b(SELECT\b.+?\bFROM\b|INSERT\s+INTO\b|UPDATE\b.+?\bSET\b|DELETE\s+FROM\b).*?["\']\s*\.format\(', '.format() in SQL'),
        # % formatting with actual SQL structure
        (r'["\'].*?\b(SELECT\b.+?\bFROM\b|INSERT\s+INTO\b|UPDATE\b.+?\bSET\b|DELETE\s+FROM\b).*?["\']\s*%', '% formatting in SQL'),
    ]
    
    # Safe patterns (parameterized queries, ORM)
    SAFE_PATTERNS = [
        # Parameterized queries
        r'\.execute\(["\'][^"\']*\?',  # cursor.execute("SELECT * FROM users WHERE id = ?", ...)
        r'\.execute\(["\'][^"\']*%s',  # cursor.execute("SELECT * FROM users WHERE id = %s", ...)
        r'\.execute\(["\'][^"\']*:\w+',  # .execute("SELECT * FROM users WHERE id = :id", ...)
        # ORM patterns
        r'\.filter\(',  # Django/SQLAlchemy .filter()
        r'\.filter_by\(',  # SQLAlchemy .filter_by()
        r'\.get\(',  # ORM .get()
        r'\.all\(',  # ORM .all()
        r'\.first\(',  # ORM .first()
        r'Q\(',  # Django Q objects
        # Query builders
        r'\.select\(',  # Query builder .select()
        r'\.where\(',  # Query builder .where()
        r'\.join\(',  # Query builder .join()
    ]
    
    # Framework-specific safe methods
    FRAMEWORK_SAFE = {
        'django': [
            'objects.filter', 'objects.get', 'objects.all', 'objects.create',
            'objects.update', 'objects.delete', 'Q(', 'F('
        ],
        'sqlalchemy': [
            'query.filter', 'query.filter_by', 'query.get', 'session.query',
            'select(', 'insert(', 'update(', 'delete('
        ],
        'flask_sqlalchemy': [
            'query.filter', 'query.filter_by', 'query.get', 'db.session.query'
        ]
    }
    
    # Input sanitization indicators
    SANITIZATION_PATTERNS = [
        r'int\(',  # Type coercion to int
        r'float\(',  # Type coercion to float
        r'str\(',  # Explicit string conversion
        r'escape\(',  # Escape function
        r'sanitize\(',  # Sanitization function
        r'validate\(',  # Validation function
        r'clean\(',  # Cleaning function
        r'if.*in\s*\[',  # Allowlist check
    ]
    
    def __init__(self):
        """Initialize SQL injection validator."""
        self.unsafe_patterns = [(re.compile(p, re.IGNORECASE | re.DOTALL), desc) 
                                for p, desc in self.UNSAFE_PATTERNS]
        self.safe_patterns = [re.compile(p, re.IGNORECASE) for p in self.SAFE_PATTERNS]
        self.sanitization_patterns = [re.compile(p) for p in self.SANITIZATION_PATTERNS]
    
    def validate_sql_operation(
        self,
        code_line: str,
        file_path: str,
        line_num: int,
        file_content: str,
        context_lines: List[str]
    ) -> Tuple[bool, str, float]:
        """
        Validate SQL operation for injection vulnerabilities.
        
        Args:
            code_line: The line of code with SQL operation
            file_path: Path to the file
            line_num: Line number (1-based)
            file_content: Full file content
            context_lines: Lines before and after for context
            
        Returns:
            (is_vulnerable, reason, confidence)
            - is_vulnerable: True if likely vulnerable
            - reason: Explanation
            - confidence: 0.0-1.0 confidence score
        """
        confidence = 0.0
        reasons = []
        
        # Layer 1: Pattern Analysis
        unsafe_pattern_found = False
        unsafe_description = ""
        
        for pattern, desc in self.unsafe_patterns:
            if pattern.search(code_line):
                unsafe_pattern_found = True
                unsafe_description = desc
                confidence = 0.8
                reasons.append(desc)
                break
        
        if not unsafe_pattern_found:
            # No unsafe pattern detected
            return False, "No unsafe SQL pattern detected", 0.0
        
        # Layer 2: Check for safe patterns (parameterization)
        for safe_pattern in self.safe_patterns:
            if safe_pattern.search(code_line):
                # Parameterized query detected - reduce confidence
                return False, "Parameterized query detected", 0.2
        
        # Layer 3: Context Analysis
        is_test = self._is_test_file(file_path)
        if is_test:
            confidence *= 0.3
            reasons.append("In test file")
        
        # Check if it's a static query (no variables)
        if self._is_static_query(code_line):
            return False, "Static query with no user input", 0.1
        
        # Layer 4: Dataflow Analysis
        has_sanitization = self._check_sanitization(context_lines)
        if has_sanitization:
            confidence *= 0.5
            reasons.append("Input sanitization detected")
        
        # Layer 5: Framework-Specific Validation
        framework_safe = self._check_framework_safety(code_line, file_content)
        if framework_safe:
            confidence *= 0.4
            reasons.append("Framework-safe pattern detected")
        
        # Final confidence adjustment
        if confidence > 0.7:
            reason = f"SQL injection risk: {unsafe_description}. " + "; ".join(reasons)
            return True, reason, confidence
        else:
            reason = f"Low risk: {'; '.join(reasons)}"
            return False, reason, confidence
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        test_indicators = ['test_', '_test.', '/test/', '/tests/', 'spec.', 'mock', 'fixture']
        path_lower = file_path.lower()
        return any(indicator in path_lower for indicator in test_indicators)
    
    def _is_static_query(self, code_line: str) -> bool:
        """Check if query uses only static values (no variables)."""
        # Look for variable usage indicators
        variable_indicators = [
            r'\{[a-zA-Z_]',  # f-string with variable
            r'\+\s*[a-zA-Z_]',  # concatenation with variable
            r'%\s*[a-zA-Z_]',  # % formatting with variable
            r'\.format\([a-zA-Z_]',  # .format() with variable
        ]
        
        for pattern in variable_indicators:
            if re.search(pattern, code_line):
                return False
        
        return True
    
    def _check_sanitization(self, context_lines: List[str]) -> bool:
        """Check if input sanitization is present in context."""
        context = '\n'.join(context_lines)
        
        for pattern in self.sanitization_patterns:
            if pattern.search(context):
                return True
        
        return False
    
    def _check_framework_safety(self, code_line: str, file_content: str) -> bool:
        """Check if code uses framework-safe patterns."""
        # Check for ORM imports
        orm_imports = [
            'from django.db import models',
            'from sqlalchemy import',
            'from flask_sqlalchemy import',
            'import peewee',
        ]
        
        for import_stmt in orm_imports:
            if import_stmt in file_content:
                # Check if line uses safe framework methods
                for framework, safe_methods in self.FRAMEWORK_SAFE.items():
                    for method in safe_methods:
                        if method in code_line:
                            return True
        
        return False
