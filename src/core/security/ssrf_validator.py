"""Server-Side Request Forgery (SSRF) deep validation with context-aware analysis.

This module provides a 5-layer validation system for SSRF detection:
1. Pattern Analysis - Detect unsafe HTTP requests
2. URL Validation - Check for user-controlled URLs
3. Allowlist Analysis - Check for URL allowlisting
4. Internal Network Detection - Check for internal IP access
5. Confidence Scoring - Calculate detection confidence
"""

from typing import Tuple, List
import re


class SSRFValidator:
    """Multi-layer validation for SSRF detection."""
    
    # Unsafe request patterns
    UNSAFE_PATTERNS = [
        # HTTP libraries with user input
        (r'requests\.get\([^)]*\+', 'requests.get with concatenation'),
        (r'requests\.get\(f["\']', 'requests.get with f-string'),
        (r'requests\.get\([a-zA-Z_]', 'requests.get with variable'),
        (r'requests\.post\([^)]*\+', 'requests.post with concatenation'),
        (r'requests\.post\(f["\']', 'requests.post with f-string'),
        (r'requests\.post\([a-zA-Z_]', 'requests.post with variable'),
        (r'urllib\.request\.urlopen\([^)]*\+', 'urllib.urlopen with concatenation'),
        (r'urllib\.request\.urlopen\(f["\']', 'urllib.urlopen with f-string'),
        (r'http\.client\.HTTPConnection\([^)]*\+', 'HTTPConnection with concatenation'),
        (r'httpx\.(get|post)\([^)]*\+', 'httpx with concatenation'),
        (r'fetch\([^)]*\+', 'fetch() with concatenation'),
        (r'axios\.(get|post)\([^)]*\+', 'axios with concatenation'),
    ]
    
    # Safe patterns
    SAFE_PATTERNS = [
        r'requests\.get\(["\']http',  # Hardcoded URL
        r'ALLOWED_HOSTS',              # Allowlist check
        r'ALLOWED_DOMAINS',            # Domain allowlist
        r'whitelist',                  # Whitelist mention
    ]
    
    # URL validation patterns
    URL_VALIDATION_PATTERNS = [
        r'urlparse\(',
        r'urllib\.parse',
        r'URL\([^)]*\)\.host',
        r'\.startswith\(["\']https?://',
        r'if.*in\s+allowed_',
    ]
    
    # Internal IP patterns
    INTERNAL_IP_PATTERNS = [
        r'127\.0\.0\.',      # Localhost
        r'localhost',        # Localhost
        r'0\.0\.0\.0',       # All interfaces
        r'10\.\d+\.\d+\.',   # Private 10.x
        r'172\.(1[6-9]|2\d|3[01])\.',  # Private 172.16-31
        r'192\.168\.',       # Private 192.168
        r'169\.254\.',       # Link-local
        r'::1',              # IPv6 localhost
        r'metadata\.google\.internal',  # Cloud metadata
        r'169\.254\.169\.254',  # AWS metadata
    ]
    
    def __init__(self):
        """Initialize SSRF validator."""
        self.unsafe_patterns = [(re.compile(p, re.IGNORECASE), desc) 
                                for p, desc in self.UNSAFE_PATTERNS]
        self.safe_patterns = [re.compile(p, re.IGNORECASE) for p in self.SAFE_PATTERNS]
        self.url_validation_patterns = [re.compile(p) for p in self.URL_VALIDATION_PATTERNS]
        self.internal_ip_patterns = [re.compile(p, re.IGNORECASE) for p in self.INTERNAL_IP_PATTERNS]
    
    def validate_http_request(
        self,
        code_line: str,
        file_path: str,
        line_num: int,
        file_content: str,
        context_lines: List[str]
    ) -> Tuple[bool, str, float]:
        """
        Validate HTTP request for SSRF vulnerabilities.
        
        Args:
            code_line: The line of code with HTTP request
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
                confidence = 0.9
                reasons.append(desc)
                break
        
        if not unsafe_pattern_found:
            return False, "No unsafe HTTP request detected", 0.0
        
        # Layer 2: URL Validation Check
        has_url_validation = self._check_url_validation(context_lines)
        if has_url_validation:
            confidence *= 0.5
            reasons.append("URL validation detected")
        
        # Layer 3: Safe Pattern Check
        for safe_pattern in self.safe_patterns:
            if safe_pattern.search(code_line):
                return False, "Safe URL pattern detected", 0.2
        
        # Layer 4: Internal Network Detection
        has_internal_ip = self._check_internal_ip(code_line, context_lines)
        if has_internal_ip:
            confidence = min(confidence * 1.2, 1.0)
            reasons.append("Internal IP/hostname detected")
        
        # Check if URL is static
        if self._is_static_url(code_line):
            return False, "Static URL with no user input", 0.1
        
        # Test file check
        is_test = self._is_test_file(file_path)
        if is_test:
            confidence *= 0.3
            reasons.append("In test file")
        
        # Layer 5: Allowlist Check
        has_allowlist = self._check_allowlist(context_lines)
        if has_allowlist:
            confidence *= 0.4
            reasons.append("URL allowlist detected")
        
        # Final decision
        if confidence > 0.7:
            reason = f"SSRF risk: {unsafe_description}. " + "; ".join(reasons)
            return True, reason, confidence
        else:
            reason = f"Low risk: {'; '.join(reasons)}"
            return False, reason, confidence
    
    def _check_url_validation(self, context_lines: List[str]) -> bool:
        """Check if URL validation is present."""
        context = '\n'.join(context_lines)
        
        for pattern in self.url_validation_patterns:
            if pattern.search(context):
                return True
        
        return False
    
    def _check_internal_ip(self, code_line: str, context_lines: List[str]) -> bool:
        """Check for internal IP addresses or hostnames."""
        all_code = code_line + '\n' + '\n'.join(context_lines)
        
        for pattern in self.internal_ip_patterns:
            if pattern.search(all_code):
                return True
        
        return False
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        test_indicators = ['test_', '_test.', '/test/', '/tests/', 'spec.', 'mock', 'fixture']
        path_lower = file_path.lower()
        return any(indicator in path_lower for indicator in test_indicators)
    
    def _is_static_url(self, code_line: str) -> bool:
        """Check if URL is static (no variables)."""
        # Check for hardcoded URLs
        if re.search(r'["\']https?://[a-zA-Z0-9\.\-]+["\']', code_line):
            # Has full hardcoded URL in quotes
            return True
        
        # Check for f-string with variable
        if re.search(r'\{[a-zA-Z_]', code_line):
            return False
        
        # Check for concatenation with variable
        if re.search(r'\+\s*[a-zA-Z_]', code_line):
            return False
        
        # Check for function calls with variable-like arguments (lowercase identifiers)
        if re.search(r'\([a-z_][a-z0-9_]*\)', code_line):
            return False
        
        return True
    
    def _check_allowlist(self, context_lines: List[str]) -> bool:
        """Check for URL allowlisting."""
        context = '\n'.join(context_lines)
        
        allowlist_patterns = [
            r'ALLOWED_HOSTS',
            r'ALLOWED_DOMAINS',
            r'allowed_urls',
            r'whitelist',
            r'if.*\.host\s+in\s+\[',
            r'if.*domain\s+in\s+\[',
        ]
        
        for pattern in allowlist_patterns:
            if re.search(pattern, context, re.IGNORECASE):
                return True
        
        return False
