"""Unit tests for XSS Validator."""

import pytest
from src.core.security.xss_validator import XSSValidator


class TestXSSPatterns:
    """Test XSS pattern detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = XSSValidator()
    
    def test_detect_jinja2_safe_filter(self):
        """Should detect Jinja2 |safe filter with user input."""
        code = '<div>{{ user_content|safe }}</div>'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/templates/page.html', 10, code, []
        )
        assert is_vulnerable
        assert 'safe' in reason.lower()
        assert confidence > 0.7
    
    def test_detect_django_mark_safe(self):
        """Should detect Django mark_safe."""
        code = 'return mark_safe(user_html)'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/views.py', 15, code, []
        )
        assert is_vulnerable
        assert 'mark_safe' in reason.lower()
    
    def test_detect_dangerouslySetInnerHTML(self):
        """Should detect React dangerouslySetInnerHTML."""
        code = '<div dangerouslySetInnerHTML={{__html: userInput}} />'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/component.jsx', 20, code, []
        )
        assert is_vulnerable
        # Check case-insensitive
        assert 'dangerously' in reason.lower() or 'innerhtml' in reason.lower()
    
    def test_detect_innerHTML_assignment(self):
        """Should detect innerHTML assignment with concatenation."""
        code = 'element.innerHTML = "<div>" + user_data + "</div>";'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/script.js', 25, code, []
        )
        assert is_vulnerable
        assert 'innerHTML' in reason.lower()
    
    def test_detect_document_write(self):
        """Should detect document.write with user input."""
        code = 'document.write("<h1>" + userContent + "</h1>");'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/legacy.js', 30, code, []
        )
        assert is_vulnerable
        assert 'document.write' in reason.lower()
    
    def test_detect_vue_v_html(self):
        """Should detect Vue v-html directive."""
        code = '<div v-html="message"></div>'
        context = ['data() { return { message: userInput } }']
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/component.vue', 15, code, context
        )
        assert is_vulnerable
        assert 'v-html' in reason.lower()
    
    def test_safe_jinja2_escape(self):
        """Should accept Jinja2 escape filter."""
        code = '<div>{{ user_content|e }}</div>'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/templates/safe_page.html', 10, code, []
        )
        # Escape filter makes it safe
        assert not is_vulnerable or confidence < 0.5
    
    def test_safe_textContent(self):
        """Should accept textContent (safe)."""
        code = 'element.textContent = user_data;'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/safe_script.js', 15, code, []
        )
        assert not is_vulnerable


class TestContextDetection:
    """Test context detection (HTML, JS, CSS)."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = XSSValidator()
    
    def test_javascript_context_higher_risk(self):
        """Should increase risk for JavaScript context."""
        code = '<script>var data = {{ user_data|safe }};</script>'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/templates/page.html', 20, code, []
        )
        assert is_vulnerable
        assert 'javascript' in reason.lower()
        # Should have high confidence due to JS context
        assert confidence > 0.8
    
    def test_html_context_detection(self):
        """Should detect HTML context."""
        code = '<div>{{ content|safe }}</div>'
        file_content = '<html><body>' + code + '</body></html>'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/templates/page.html', 10, file_content, []
        )
        assert is_vulnerable


class TestOutputEncoding:
    """Test output encoding detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = XSSValidator()
    
    def test_detect_html_escape(self):
        """Should detect html.escape() usage."""
        code = 'output = html.escape(user_input)'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/handler.py', 15, code, []
        )
        assert not is_vulnerable
    
    def test_encoding_in_context(self):
        """Should detect encoding in surrounding context."""
        code = 'return mark_safe(content)'
        context = [
            'content = html.escape(user_input)',
            'content = bleach.clean(content)'
        ]
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/views.py', 20, code, context
        )
        # Should have lower confidence due to prior encoding
        if is_vulnerable:
            assert confidence < 0.7


class TestTemplateEngines:
    """Test template engine safety."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = XSSValidator()
    
    def test_auto_escape_enabled(self):
        """Should detect auto-escape configuration."""
        code = '{{ user_content|safe }}'
        file_content = '''
from jinja2 import Environment
env = Environment(autoescape=True)
template = env.get_template("page.html")
''' + code
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/templates/page.html', 30, file_content, []
        )
        # Should have lower confidence due to auto-escape
        if is_vulnerable:
            assert confidence < 0.7


class TestStaticContent:
    """Test static content detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = XSSValidator()
    
    def test_static_html_safe(self):
        """Should accept static HTML without variables."""
        code = '<div>Welcome to our site</div>'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/templates/static.html', 10, code, []
        )
        assert not is_vulnerable
    
    def test_no_user_input_safe(self):
        """Should accept output without variables."""
        code = 'element.innerHTML = "<p>Welcome</p>";'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/script.js', 15, code, []
        )
        assert not is_vulnerable


class TestEdgeCases:
    """Test edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = XSSValidator()
    
    def test_no_unsafe_pattern(self):
        """Should return false for safe operations."""
        code = 'return render_template("page.html", data=data)'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/app/views.py', 10, code, []
        )
        assert not is_vulnerable
        assert 'no unsafe' in reason.lower()
    
    def test_test_file_lower_confidence(self):
        """Should lower confidence for test files."""
        code = '<div>{{ test_data|safe }}</div>'
        is_vulnerable, reason, confidence = self.validator.validate_output_rendering(
            code, '/tests/test_templates.py', 15, code, []
        )
        # May or may not be vulnerable depending on confidence threshold
        if is_vulnerable:
            assert confidence < 0.7
