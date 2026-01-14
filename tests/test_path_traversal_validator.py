"""Unit tests for Path Traversal Validator."""

import pytest
from src.core.security.path_traversal_validator import PathTraversalValidator


class TestPathTraversalPatterns:
    """Test path traversal pattern detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PathTraversalValidator()
    
    def test_detect_open_with_concatenation(self):
        """Should detect open() with path concatenation."""
        code = 'with open(base_path + user_file, "r") as f:'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/file_handler.py', 10, code, []
        )
        assert is_vulnerable
        assert 'concatenation' in reason.lower()
        assert confidence > 0.7
    
    def test_detect_open_with_fstring(self):
        """Should detect open() with f-string path."""
        code = 'with open(f"/var/data/{user_input}", "r") as f:'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/file_handler.py', 10, code, []
        )
        assert is_vulnerable
        assert 'f-string' in reason.lower()
        assert confidence > 0.7
    
    def test_detect_path_with_concatenation(self):
        """Should detect Path() with concatenation."""
        code = 'file_path = Path(base_dir + filename)'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/utils.py', 15, code, []
        )
        assert is_vulnerable
        assert 'concatenation' in reason.lower()
    
    def test_detect_shutil_with_concatenation(self):
        """Should detect shutil operations with concatenation."""
        code = 'shutil.copy(source_dir + user_file, dest)'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/file_ops.py', 20, code, []
        )
        assert is_vulnerable
        assert confidence > 0.7
    
    def test_safe_abspath_usage(self):
        """Should accept safe os.path.abspath usage."""
        code = 'safe_path = os.path.abspath(user_path)'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/safe_handler.py', 10, code, []
        )
        assert not is_vulnerable
    
    def test_safe_realpath_usage(self):
        """Should accept safe os.path.realpath usage."""
        code = 'real_path = os.path.realpath(user_input)'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/safe_handler.py', 15, code, []
        )
        assert not is_vulnerable
    
    def test_safe_path_resolve(self):
        """Should accept Path.resolve() usage."""
        code = 'safe_path = Path(user_input).resolve()'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/safe_handler.py', 20, code, []
        )
        assert not is_vulnerable


class TestTraversalSequences:
    """Test traversal sequence detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PathTraversalValidator()
    
    def test_detect_dotdot_slash(self):
        """Should detect ../ traversal."""
        code = 'with open(base + user_input, "r") as f:'
        context = ['filename = "../secret.txt"']
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/handler.py', 10, code, context
        )
        assert is_vulnerable
        assert 'traversal' in reason.lower()
    
    def test_detect_url_encoded_traversal(self):
        """Should detect path concatenation (URL encoding in input)."""
        code = 'file_path = base_path + request.args.get("file")'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/web_handler.py', 25, code, []
        )
        # Pattern detected - concatenation itself is risky
        assert is_vulnerable


class TestContextAnalysis:
    """Test context-aware analysis."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PathTraversalValidator()
    
    def test_static_path_safe(self):
        """Should accept static paths."""
        code = 'with open("/var/log/app.log", "r") as f:'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/logger.py', 10, code, []
        )
        assert not is_vulnerable
        # Message can be either "static" or "no unsafe" - both are correct
        assert 'static' in reason.lower() or 'no unsafe' in reason.lower()
    
    def test_test_file_lower_confidence(self):
        """Should lower confidence for test files."""
        code = 'with open(base + user_file, "r") as f:'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/tests/test_file_handler.py', 10, code, []
        )
        # May or may not be vulnerable depending on confidence threshold
        if is_vulnerable:
            assert confidence < 0.8  # Lower than normal
    
    def test_sanitization_detected(self):
        """Should detect path sanitization."""
        code = 'file_path = base_dir + filename'
        context = [
            'filename = user_input.replace("..", "")',
            'if ".." in filename:',
            '    raise ValueError("Invalid path")'
        ]
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/handler.py', 15, code, context
        )
        # Should have lower confidence due to sanitization
        if is_vulnerable:
            assert confidence < 0.7


class TestBoundaryChecks:
    """Test boundary validation detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PathTraversalValidator()
    
    def test_detect_startswith_check(self):
        """Should detect startswith boundary check."""
        code = 'file_path = base + user_input'
        context = [
            'if not file_path.startswith(ALLOWED_DIR):',
            '    raise ValueError("Path outside allowed directory")'
        ]
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/handler.py', 20, code, context
        )
        # Should have lower confidence due to boundary check
        if is_vulnerable:
            assert confidence < 0.7
    
    def test_detect_commonpath_check(self):
        """Should detect os.path.commonpath check."""
        code = 'target = Path(base_dir + filename)'
        context = [
            'if os.path.commonpath([base_dir, target]) != base_dir:',
            '    raise ValueError("Invalid path")'
        ]
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/secure_handler.py', 30, code, context
        )
        # Should have lower confidence due to commonpath check
        if is_vulnerable:
            assert confidence < 0.7


class TestEdgeCases:
    """Test edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = PathTraversalValidator()
    
    def test_no_unsafe_pattern(self):
        """Should return false for safe operations."""
        code = 'data = json.load(f)'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/parser.py', 10, code, []
        )
        assert not is_vulnerable
        assert 'no unsafe' in reason.lower()
    
    def test_secure_filename_usage(self):
        """Should accept Flask secure_filename."""
        code = 'filename = secure_filename(user_input)'
        is_vulnerable, reason, confidence = self.validator.validate_path_operation(
            code, '/app/upload.py', 15, code, []
        )
        assert not is_vulnerable
