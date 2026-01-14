"""Command Injection deep validation with context-aware analysis.

This module provides a 5-layer validation system for command injection detection:
1. Pattern Analysis - Detect unsafe command execution
2. Context Analysis - Check file type and usage context
3. Input Validation Analysis - Check for input sanitization
4. Shell Analysis - Detect shell=True and metacharacters
5. Confidence Scoring - Calculate detection confidence
"""

from typing import Tuple, List
import re


class CommandInjectionValidator:
    """Multi-layer validation for command injection detection."""
    
    # Unsafe command execution patterns
    UNSAFE_PATTERNS = [
        # Python subprocess with shell=True
        (r'subprocess\.(run|call|Popen|check_output).*?shell\s*=\s*True', 'shell=True with potential injection'),
        # os.system patterns
        (r'os\.system\(.*?\+', 'os.system with string concatenation'),
        (r'os\.system\(f["\']', 'os.system with f-string'),
        (r'os\.system\(.*?\.format', 'os.system with format'),
        # os.popen patterns
        (r'os\.popen\(.*?\+', 'os.popen with string concatenation'),
        (r'os\.popen\(f["\']', 'os.popen with f-string'),
        # subprocess patterns (any string building)
        (r'subprocess\.(run|call|check_output|Popen)\(.*?\+', 'subprocess with string concatenation'),
        (r'subprocess\.(run|call|check_output|Popen)\(f["\']', 'subprocess with f-string'),
        (r'subprocess\.(run|call|check_output|Popen)\(.*?\.format', 'subprocess with format'),
        # eval/exec patterns
        (r'eval\(.*?\+', 'eval with concatenated input'),
        (r'exec\(.*?\+', 'exec with concatenated input'),
    ]
    
    # Safe patterns (list form, no shell)
    SAFE_PATTERNS = [
        r'subprocess\.(run|call|Popen)\(\[',  # List form: subprocess.run(['ls', path])
        r'shell\s*=\s*False',  # Explicit shell=False
        r'Path\([^)]*\)\.(read_text|read_bytes|write_text)',  # Path library usage
        r'shutil\.',  # shutil library (safe alternatives)
    ]
    
    # Shell metacharacters that enable injection
    SHELL_METACHARACTERS = [';', '|', '&', '$', '`', '$(', '>', '<', '\n', '&&', '||']
    
    # Input sanitization indicators
    SANITIZATION_PATTERNS = [
        r'shlex\.quote\(',  # Shell escape
        r'pipes\.quote\(',  # Pipes quote (older Python)
        r'if.*in\s*\[',  # Allowlist check
        r'whitelist',  # Whitelist mention
        r'allowed_commands',  # Allowed commands check
        r'sanitize\(',  # Sanitization function
        r'validate\(',  # Validation function
        r'escape\(',  # Escape function
    ]
    
    def __init__(self):
        """Initialize command injection validator."""
        self.unsafe_patterns = [(re.compile(p, re.IGNORECASE | re.DOTALL), desc) 
                                for p, desc in self.UNSAFE_PATTERNS]
        self.safe_patterns = [re.compile(p, re.IGNORECASE) for p in self.SAFE_PATTERNS]
        self.sanitization_patterns = [re.compile(p, re.IGNORECASE) for p in self.SANITIZATION_PATTERNS]
    
    def validate_command_execution(
        self,
        code_line: str,
        file_path: str,
        line_num: int,
        file_content: str,
        context_lines: List[str]
    ) -> Tuple[bool, str, float]:
        """
        Validate command execution for injection vulnerabilities.
        
        Args:
            code_line: The line of code with command execution
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
                confidence = 0.9
                reasons.append(desc)
                break
        
        if not unsafe_pattern_found:
            # No unsafe pattern detected
            return False, "No unsafe command execution pattern", 0.0
        
        # Layer 2: Check for safe patterns
        for safe_pattern in self.safe_patterns:
            if safe_pattern.search(code_line):
                # Safe pattern detected
                return False, "Safe command execution pattern", 0.1
        
        # Layer 3: Context Analysis
        is_test = self._is_test_file(file_path)
        if is_test:
            confidence *= 0.3
            reasons.append("In test file")
        
        # Check if command is static (no variables)
        if self._is_static_command(code_line):
            return False, "Static command with no user input", 0.2
        
        # Layer 4: Shell Analysis
        uses_shell = self._uses_shell(code_line)
        has_metacharacters = self._check_metacharacters(code_line, context_lines)
        
        if uses_shell:
            confidence = min(confidence * 1.2, 1.0)
            reasons.append("Uses shell=True")
        
        if has_metacharacters:
            confidence = min(confidence * 1.1, 1.0)
            reasons.append("Shell metacharacters detected")
        
        # Layer 5: Input Validation Analysis
        has_sanitization = self._check_sanitization(context_lines)
        if has_sanitization:
            confidence *= 0.4
            reasons.append("Input sanitization detected")
        
        # Final confidence adjustment
        if confidence > 0.7:
            reason = f"Command injection risk: {unsafe_description}. " + "; ".join(reasons)
            return True, reason, confidence
        else:
            reason = f"Low risk: {'; '.join(reasons)}"
            return False, reason, confidence
    
    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        test_indicators = ['test_', '_test.', '/test/', '/tests/', 'spec.', 'mock', 'fixture']
        path_lower = file_path.lower()
        return any(indicator in path_lower for indicator in test_indicators)
    
    def _is_static_command(self, code_line: str) -> bool:
        """Check if command uses only static values (no variables)."""
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
    
    def _uses_shell(self, code_line: str) -> bool:
        """Check if command uses shell=True."""
        return bool(re.search(r'shell\s*=\s*True', code_line, re.IGNORECASE))
    
    def _check_metacharacters(self, code_line: str, context_lines: List[str]) -> bool:
        """Check for shell metacharacters in code or context."""
        all_code = code_line + '\n' + '\n'.join(context_lines)
        
        for metachar in self.SHELL_METACHARACTERS:
            if metachar in all_code:
                return True
        
        return False
    
    def _check_sanitization(self, context_lines: List[str]) -> bool:
        """Check if input sanitization is present in context."""
        context = '\n'.join(context_lines)
        
        for pattern in self.sanitization_patterns:
            if pattern.search(context):
                return True
        
        return False
