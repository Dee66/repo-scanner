"""Path Traversal deep validation with context-aware analysis.

This module provides a 5-layer validation system for path traversal detection:
1. Pattern Analysis - Detect unsafe path operations
2. Path Normalization - Check for traversal sequences
3. Input Validation - Check for sanitization
4. Boundary Analysis - Verify path stays within allowed directories
5. Confidence Scoring - Calculate detection confidence
"""

from typing import Tuple, List
import re
from pathlib import Path


class PathTraversalValidator:
    """Multi-layer validation for path traversal detection."""
    
    # Dangerous path patterns
    TRAVERSAL_PATTERNS = [
        r'\.\.[/\\]',  # ../
        r'\.\.\\',     # ..\
        r'%2e%2e',     # URL encoded ..
        r'%252e',      # Double encoded .
        r'\.\.%2f',    # Mixed encoding
        r'\.\.%5c',    # Mixed encoding backslash
    ]
    
    # Unsafe file operations
    UNSAFE_OPERATIONS = [
        (r'open\([^)]*\+', 'open() with user input concatenation'),
        (r'open\(f["\']', 'open() with f-string'),
        (r'Path\([^)]*\+', 'Path() with concatenation'),
        (r'Path\(f["\']', 'Path() with f-string'),
        (r'=\s*\w+\s*\+.*?request', 'Variable assignment with request concatenation'),
        (r'os\.path\.join\([^)]*\+', 'os.path.join with concatenation'),
        (r'shutil\.(copy|move|rmtree)\([^)]*\+', 'shutil operations with concatenation'),
    ]
    
    # Safe patterns
    SAFE_PATTERNS = [
        r'os\.path\.abspath\(',     # Absolute path normalization
        r'os\.path\.realpath\(',    # Real path resolution
        r'Path\([^)]*\)\.resolve\(',  # Path.resolve()
        r'secure_filename\(',       # Flask secure_filename
        r'sanitize_filename\(',     # Sanitization function
    ]
    
    # Sanitization patterns
    SANITIZATION_PATTERNS = [
        r'\.replace\(["\']\.\.["\']\s*,\s*["\']["\']',  # Remove ..
        r'if\s+["\']\.\.["\']\s+in',  # Check for ..
        r'os\.path\.normpath\(',      # Path normalization
        r'Path\([^)]*\)\.resolve\(',  # Path resolution
        r'os\.path\.commonpath\(',    # Common path check
        r'\.startswith\(["\'][^"\']+["\']\)',  # Boundary check
    ]
    
    def __init__(self):
        """Initialize path traversal validator."""
        self.traversal_patterns = [re.compile(p, re.IGNORECASE) for p in self.TRAVERSAL_PATTERNS]
        self.unsafe_operations = [(re.compile(p, re.IGNORECASE), desc) 
                                  for p, desc in self.UNSAFE_OPERATIONS]
        self.safe_patterns = [re.compile(p) for p in self.SAFE_PATTERNS]
        self.sanitization_patterns = [re.compile(p) for p in self.SANITIZATION_PATTERNS]
    
    def validate_path_operation(
        self,
        code_line: str,
        file_path: str,
        line_num: int,
        file_content: str,
        context_lines: List[str]
    ) -> Tuple[bool, str, float]:
        """
        Validate path operation for traversal vulnerabilities.
        
        Args:
            code_line: The line of code with path operation
            file_path: Path to the file
            line_num: Line number (1-based)
            file_content: Full file content
            context_lines: Lines before and after for context
            
        Returns:
            (is_vulnerable, reason, confidence)
        """
        confidence = 0.0
        reasons = []
        
        # Layer 1: Pattern Analysis
        unsafe_pattern_found = False
        unsafe_description = ""
        
        for pattern, desc in self.unsafe_operations:
            if pattern.search(code_line):
                unsafe_pattern_found = True
                unsafe_description = desc
                confidence = 0.8
                reasons.append(desc)
                break
        
        if not unsafe_pattern_found:
            return False, "No unsafe path operation detected", 0.0
        
        # Layer 2: Path Normalization Check
        has_traversal = self._check_traversal_sequences(code_line, context_lines)
        if has_traversal:
            confidence = min(confidence * 1.2, 1.0)
            reasons.append("Path traversal sequences detected")
        
        # Layer 3: Safe Pattern Check
        for safe_pattern in self.safe_patterns:
            if safe_pattern.search(code_line):
                return False, "Safe path operation detected", 0.2
        
        # Layer 4: Context Analysis
        is_test = self._is_test_file(file_path)
        if is_test:
            confidence *= 0.3
            reasons.append("In test file")
        
        # Check if path is static
        if self._is_static_path(code_line):
            return False, "Static path with no user input", 0.1
        
        # Layer 5: Input Validation Analysis
        has_sanitization = self._check_sanitization(context_lines)
        if has_sanitization:
            confidence *= 0.5
            reasons.append("Path sanitization detected")
        
        # Boundary check detection
        has_boundary_check = self._check_boundary(context_lines)
        if has_boundary_check:
            confidence *= 0.6
            reasons.append("Boundary check detected")
        
        # Final decision
        if confidence > 0.7:
            reason = f"Path traversal risk: {unsafe_description}. " + "; ".join(reasons)
            return True, reason, confidence
        else:
            reason = f"Low risk: {'; '.join(reasons)}"
            return False, reason, confidence
    
    def _check_traversal_sequences(self, code_line: str, context_lines: List[str]) -> bool:
        """Check for path traversal sequences."""
        all_code = code_line + '\n' + '\n'.join(context_lines)
        
        for pattern in self.traversal_patterns:
            if pattern.search(all_code):
                return True
        
        return False
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        test_indicators = ['test_', '_test.', '/test/', '/tests/', 'spec.', 'mock', 'fixture']
        path_lower = file_path.lower()
        return any(indicator in path_lower for indicator in test_indicators)
    
    def _is_static_path(self, code_line: str) -> bool:
        """Check if path is static (no variables)."""
        variable_indicators = [
            r'\{[a-zA-Z_]',  # f-string with variable
            r'\+\s*[a-zA-Z_]',  # concatenation with variable
        ]
        
        for pattern in variable_indicators:
            if re.search(pattern, code_line):
                return False
        
        return True
    
    def _check_sanitization(self, context_lines: List[str]) -> bool:
        """Check if path sanitization is present."""
        context = '\n'.join(context_lines)
        
        for pattern in self.sanitization_patterns:
            if pattern.search(context):
                return True
        
        return False
    
    def _check_boundary(self, context_lines: List[str]) -> bool:
        """Check for boundary validation."""
        context = '\n'.join(context_lines)
        
        boundary_patterns = [
            r'\.startswith\(',
            r'os\.path\.commonpath\(',
            r'if.*in\s+allowed_',
            r'ALLOWED_DIR',
            r'BASE_DIR',
        ]
        
        for pattern in boundary_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True
        
        return False
