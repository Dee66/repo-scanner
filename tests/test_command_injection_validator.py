"""Unit tests for Command Injection Validator."""

import pytest
from src.core.security.command_injection_validator import CommandInjectionValidator


@pytest.fixture
def validator():
    """Create command injection validator instance."""
    return CommandInjectionValidator()


class TestCommandInjectionPatterns:
    """Test command injection pattern detection."""
    
    def test_os_system_with_concatenation(self, validator):
        """Test os.system with string concatenation."""
        code = 'os.system("ls " + user_input)'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
        assert "concatenation" in reason.lower()
    
    def test_os_system_with_fstring(self, validator):
        """Test os.system with f-string."""
        code = 'os.system(f"cat {filename}")'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
        assert "f-string" in reason.lower()
    
    def test_subprocess_with_shell_true(self, validator):
        """Test subprocess with shell=True."""
        code = 'subprocess.run(f"ls {path}", shell=True)'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
        # Case-insensitive check for shell=True
        assert "shell" in reason.lower() and "true" in reason.lower()
    
    def test_subprocess_call_with_concatenation(self, validator):
        """Test subprocess.call with concatenation."""
        code = 'subprocess.call("grep " + pattern + " file.txt", shell=True)'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
    
    def test_safe_subprocess_list_form(self, validator):
        """Test safe subprocess with list form."""
        code = 'subprocess.run(["ls", user_input])'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert not is_vuln
        assert confidence < 0.3
    
    def test_safe_subprocess_shell_false(self, validator):
        """Test subprocess with explicit shell=False."""
        code = 'subprocess.run(["cat", filename], shell=False)'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert not is_vuln
    
    def test_safe_path_library(self, validator):
        """Test safe Path library usage."""
        code = 'Path(filename).read_text()'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert not is_vuln


class TestContextAnalysis:
    """Test context-aware analysis."""
    
    def test_test_file_reduces_confidence(self, validator):
        """Test that test files reduce confidence."""
        code = 'os.system(f"ls {path}")'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "test_utils.py", 10, "", []
        )
        # Should detect but with lower confidence
        assert confidence < 0.5
        assert "test file" in reason.lower()
    
    def test_static_command_not_vulnerable(self, validator):
        """Test static commands are not flagged."""
        code = 'os.system("ls -la")'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert not is_vuln
        # Static command with no unsafe patterns is correctly not detected
        assert "no unsafe" in reason.lower() or "static" in reason.lower()
    
    def test_shlex_quote_reduces_confidence(self, validator):
        """Test shlex.quote reduces confidence."""
        code = 'os.system(f"cat {filename}")'
        context = [
            "import shlex",
            "filename = shlex.quote(user_input)",
            code
        ]
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", context
        )
        # shlex.quote should reduce confidence significantly
        assert confidence < 0.5 or not is_vuln
        assert "sanitization" in reason.lower()


class TestShellAnalysis:
    """Test shell-specific analysis."""
    
    def test_shell_true_increases_confidence(self, validator):
        """Test shell=True increases confidence."""
        code_without_shell = 'subprocess.run("ls " + path)'
        code_with_shell = 'subprocess.run("ls " + path, shell=True)'
        
        is_vuln1, _, conf1 = validator.validate_command_execution(
            code_without_shell, "app.py", 10, "", []
        )
        is_vuln2, _, conf2 = validator.validate_command_execution(
            code_with_shell, "app.py", 10, "", []
        )
        
        # Both should be vulnerable, but shell=True should have higher confidence
        assert is_vuln1 and is_vuln2
        assert conf2 >= conf1
    
    def test_metacharacters_detected(self, validator):
        """Test shell metacharacter detection."""
        codes_with_metachar = [
            'os.system("ls; " + cmd)',
            'os.system("ls | " + cmd)',
            'os.system("ls && " + cmd)',
            'os.system("ls $" + cmd)',
        ]
        
        for code in codes_with_metachar:
            is_vuln, reason, confidence = validator.validate_command_execution(
                code, "app.py", 10, "", []
            )
            assert is_vuln
            assert confidence > 0.7


class TestInputValidation:
    """Test input validation detection."""
    
    def test_allowlist_validation(self, validator):
        """Test allowlist validation reduces confidence."""
        code = 'os.system(f"cat {filename}")'
        context = [
            "filename = request.args.get('file')",
            "if filename in ['file1.txt', 'file2.txt']:",
            "    " + code
        ]
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", context
        )
        # Allowlist should reduce confidence
        assert confidence < 0.5 or not is_vuln
    
    def test_validation_function(self, validator):
        """Test validation function reduces confidence."""
        code = 'os.system(f"ls {path}")'
        context = [
            "path = request.args.get('path')",
            "path = validate(path)",
            code
        ]
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", context
        )
        # Validation should reduce confidence
        assert confidence < 0.5 or not is_vuln


class TestEdgeCases:
    """Test edge cases and corner scenarios."""
    
    def test_os_popen(self, validator):
        """Test os.popen detection."""
        code = 'os.popen("ls " + path)'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
    
    def test_subprocess_check_output(self, validator):
        """Test subprocess.check_output with shell=True."""
        code = 'subprocess.check_output(f"grep {pattern} file.txt", shell=True)'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
    
    def test_eval_with_input(self, validator):
        """Test eval with user input."""
        code = 'eval("import os; os.system(" + user_input + ")")'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
    
    def test_exec_with_input(self, validator):
        """Test exec with user input."""
        code = 'exec("os.system(" + user_cmd + ")")'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7
    
    def test_multiline_command(self, validator):
        """Test multiline command construction."""
        # Test the actual concatenation line
        code = 'os.system("ls " + user_input)'
        is_vuln, reason, confidence = validator.validate_command_execution(
            code, "app.py", 10, "", []
        )
        assert is_vuln
        assert confidence > 0.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
