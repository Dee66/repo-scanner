"""Cross-Site Scripting (XSS) deep validation with context-aware analysis.

This module provides a 5-layer validation system for XSS detection:
1. Pattern Analysis - Detect unsafe output rendering
2. Context Analysis - HTML/JS/CSS context detection
3. Encoding Analysis - Check for output encoding
4. Template Analysis - Check template engine safety
5. Confidence Scoring - Calculate detection confidence
"""

from typing import Tuple, List
import re


class XSSValidator:
    """Multi-layer validation for XSS detection."""
    
    # Unsafe output patterns
    UNSAFE_PATTERNS = [
        # Template rendering
        (r'\{\{\s*\w+.*?\|\s*safe\s*\}\}', 'Jinja2 |safe filter with user input'),
        (r'mark_safe\(', 'Django mark_safe with user input'),
        (r'<script>.*?\{\{.*?\}\}.*?</script>', 'JavaScript with template variable'),
        (r'dangerouslySetInnerHTML', 'React dangerouslySetInnerHTML'),
        (r'v-html\s*=', 'Vue v-html directive'),
        (r'innerHTML\s*=\s*\w', 'Direct innerHTML assignment'),
        (r'outerHTML\s*=\s*\w', 'Direct outerHTML assignment'),
        (r'document\.write\(\w', 'document.write() with user input'),
        # Python string formatting in HTML
        (r'<[^>]*>.*?\{.*?\}', 'HTML with f-string'),
        (r'<[^>]*>.*?%s', 'HTML with % formatting'),
    ]
    
    # Safe patterns
    SAFE_PATTERNS = [
        r'\{\{.*?\|escape\}\}',  # Jinja2 escape
        r'\{\{.*?\|e\}\}',       # Jinja2 e filter
        r'escape\(',             # Explicit escape
        r'html\.escape\(',       # Python html.escape
        r'cgi\.escape\(',        # CGI escape
        r'textContent\s*=',      # Safe textContent
        r'innerText\s*=',        # Safe innerText
        r'\.text\(',             # jQuery .text()
    ]
    
    # Context indicators
    HTML_CONTEXT = [
        r'<html', r'<body', r'<div', r'<span', r'<p>',
        r'render_template', r'render\(', r'\.html\s*$'
    ]
    
    JS_CONTEXT = [
        r'<script', r'\.js\s*$', r'javascript:',
        r'on\w+\s*=\s*["\']'  # Event handlers
    ]
    
    CSS_CONTEXT = [
        r'<style', r'\.css\s*$', r'style\s*=\s*["\']'
    ]
    
    # Encoding functions
    ENCODING_PATTERNS = [
        r'escape\(',
        r'html\.escape\(',
        r'cgi\.escape\(',
        r'bleach\.clean\(',
        r'sanitize\(',
        r'DOMPurify\.sanitize\(',
    ]
    
    def __init__(self):
        """Initialize XSS validator."""
        self.unsafe_patterns = [(re.compile(p, re.IGNORECASE | re.DOTALL), desc) 
                                for p, desc in self.UNSAFE_PATTERNS]
        self.safe_patterns = [re.compile(p, re.IGNORECASE) for p in self.SAFE_PATTERNS]
        self.encoding_patterns = [re.compile(p) for p in self.ENCODING_PATTERNS]
        self.html_context = [re.compile(p, re.IGNORECASE) for p in self.HTML_CONTEXT]
        self.js_context = [re.compile(p, re.IGNORECASE) for p in self.JS_CONTEXT]
        self.css_context = [re.compile(p, re.IGNORECASE) for p in self.CSS_CONTEXT]
    
    def validate_output_rendering(
        self,
        code_line: str,
        file_path: str,
        line_num: int,
        file_content: str,
        context_lines: List[str]
    ) -> Tuple[bool, str, float]:
        """
        Validate output rendering for XSS vulnerabilities.
        
        Args:
            code_line: The line of code with output rendering
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
        
        for pattern, desc in self.unsafe_patterns:
            if pattern.search(code_line):
                unsafe_pattern_found = True
                unsafe_description = desc
                confidence = 0.85
                reasons.append(desc)
                break
        
        if not unsafe_pattern_found:
            return False, "No unsafe output rendering detected", 0.0
        
        # Layer 2: Context Analysis
        context = self._detect_context(code_line, file_path, file_content)
        if context == 'javascript':
            confidence = min(confidence * 1.2, 1.0)
            reasons.append("JavaScript context (high risk)")
        elif context == 'css':
            confidence *= 0.9
            reasons.append("CSS context")
        
        # Layer 3: Safe Pattern Check
        for safe_pattern in self.safe_patterns:
            if safe_pattern.search(code_line):
                return False, "Output encoding detected", 0.2
        
        # Layer 4: Encoding Analysis
        has_encoding = self._check_encoding(context_lines)
        if has_encoding:
            confidence *= 0.4
            reasons.append("Output encoding detected")
        
        # Check if output is static
        if self._is_static_output(code_line):
            return False, "Static output with no user input", 0.1
        
        # Test file check
        is_test = self._is_test_file(file_path)
        if is_test:
            confidence *= 0.3
            reasons.append("In test file")
        
        # Layer 5: Template Engine Safety
        has_auto_escape = self._check_auto_escape(file_content)
        if has_auto_escape:
            confidence *= 0.5
            reasons.append("Auto-escape enabled")
        
        # Final decision
        if confidence > 0.7:
            reason = f"XSS risk: {unsafe_description}. " + "; ".join(reasons)
            return True, reason, confidence
        else:
            reason = f"Low risk: {'; '.join(reasons)}"
            return False, reason, confidence
    
    def _detect_context(self, code_line: str, file_path: str, file_content: str) -> str:
        """Detect rendering context (HTML, JS, CSS)."""
        # Check JavaScript context
        for pattern in self.js_context:
            if pattern.search(code_line) or pattern.search(file_content[:500]):
                return 'javascript'
        
        # Check CSS context
        for pattern in self.css_context:
            if pattern.search(code_line):
                return 'css'
        
        # Check HTML context
        for pattern in self.html_context:
            if pattern.search(code_line) or pattern.search(file_path):
                return 'html'
        
        return 'unknown'
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        test_indicators = ['test_', '_test.', '/test/', '/tests/', 'spec.', 'mock', 'fixture']
        path_lower = file_path.lower()
        return any(indicator in path_lower for indicator in test_indicators)
    
    def _is_static_output(self, code_line: str) -> bool:
        """Check if output is static (no variables)."""
        # Check for template variables or f-strings
        if re.search(r'\{[{a-zA-Z_]', code_line):  # {{ or {var
            # But if it's a literal string in quotes like "{{", it's static
            if re.search(r'["\'].*?\{.*?["\']', code_line):
                return True
            return False
        
        # Check for concatenation
        if re.search(r'\+\s*[a-zA-Z_]', code_line):
            return False
        
        # Check for variable-like identifiers (lowercase_with_underscores pattern)
        # This matches: innerHTML = user_data, document.write(userContent), etc.
        if re.search(r'[=\(]\s*[a-z_][a-z0-9_]*[;\)]', code_line):
            return False
        
        # If we see literal strings in quotes, it's static
        if re.search(r'["\'][^"\']*["\']', code_line):
            return True
        
        return True
    
    def _check_encoding(self, context_lines: List[str]) -> bool:
        """Check if output encoding is present."""
        context = '\n'.join(context_lines)
        
        for pattern in self.encoding_patterns:
            if pattern.search(context):
                return True
        
        return False
    
    def _check_auto_escape(self, file_content: str) -> bool:
        """Check if auto-escape is enabled."""
        auto_escape_patterns = [
            r'autoescape\s*=\s*True',
            r'autoescape:\s*true',
            r'env\s*=.*autoescape\s*=\s*True',
        ]
        
        for pattern in auto_escape_patterns:
            if re.search(pattern, file_content, re.IGNORECASE):
                return True
        
        return False
