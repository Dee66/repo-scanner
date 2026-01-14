"""Unit tests for SSRF Validator."""

import pytest
from src.core.security.ssrf_validator import SSRFValidator


class TestSSRFPatterns:
    """Test SSRF pattern detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SSRFValidator()
    
    def test_detect_requests_get_concatenation(self):
        """Should detect requests.get with URL concatenation."""
        code = 'response = requests.get(base_url + user_path)'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/api_client.py', 10, code, []
        )
        assert is_vulnerable
        assert 'concatenation' in reason.lower()
        assert confidence > 0.7
    
    def test_detect_requests_get_fstring(self):
        """Should detect requests.get with f-string."""
        code = 'response = requests.get(f"http://api.example.com/{user_input}")'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/api_client.py', 15, code, []
        )
        assert is_vulnerable
        assert 'f-string' in reason.lower()
    
    def test_detect_requests_post_concatenation(self):
        """Should detect requests.post with concatenation."""
        code = 'response = requests.post(url_prefix + endpoint)'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/webhook.py', 20, code, []
        )
        assert is_vulnerable
        assert confidence > 0.7
    
    def test_detect_urllib_urlopen(self):
        """Should detect urllib.request.urlopen with concatenation."""
        code = 'response = urllib.request.urlopen(base + path)'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/fetcher.py', 25, code, []
        )
        assert is_vulnerable
    
    def test_detect_httpx_get(self):
        """Should detect httpx with concatenation."""
        code = 'response = httpx.get(api_base + user_endpoint)'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/async_client.py', 30, code, []
        )
        assert is_vulnerable
    
    def test_safe_hardcoded_url(self):
        """Should accept hardcoded URL."""
        code = 'response = requests.get("https://api.example.com/data")'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/safe_client.py', 10, code, []
        )
        assert not is_vulnerable


class TestURLValidation:
    """Test URL validation detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SSRFValidator()
    
    def test_detect_urlparse_validation(self):
        """Should detect URL parsing/validation."""
        code = 'response = requests.get(target_url)'
        context = [
            'from urllib.parse import urlparse',
            'parsed = urlparse(target_url)',
            'if parsed.scheme not in ["http", "https"]:',
            '    raise ValueError("Invalid URL")'
        ]
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/validated_client.py', 20, code, context
        )
        # Should have lower confidence due to validation
        if is_vulnerable:
            assert confidence < 0.7
    
    def test_detect_host_check(self):
        """Should detect host/domain checking."""
        code = 'requests.get(url_from_user)'
        context = [
            'parsed = URL(url_from_user)',
            'if parsed.host not in ALLOWED_HOSTS:',
            '    raise ValueError("Unauthorized host")'
        ]
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/restricted_client.py', 25, code, context
        )
        # Should have lower confidence due to host check
        if is_vulnerable:
            assert confidence < 0.7


class TestInternalIPDetection:
    """Test internal IP/hostname detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SSRFValidator()
    
    def test_detect_localhost(self):
        """Should detect localhost access."""
        code = 'response = requests.get(f"http://localhost:{port}/api")'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/local_client.py', 10, code, []
        )
        assert is_vulnerable
        assert 'internal' in reason.lower()
    
    def test_detect_127_0_0_1(self):
        """Should detect 127.0.0.1 access."""
        code = 'response = requests.get(f"http://127.0.0.1:{port}/api")'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/client.py', 15, code, []
        )
        # Should detect f-string with localhost
        assert is_vulnerable
    
    def test_detect_private_ip_10(self):
        """Should detect private 10.x IP."""
        code = 'requests.get(f"http://10.0.0.{host}/data")'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/internal_api.py', 20, code, []
        )
        assert is_vulnerable
    
    def test_detect_private_ip_192_168(self):
        """Should detect private 192.168.x IP."""
        code = 'response = requests.get(target_url)'
        context = ['target_url = "http://192.168.1.1/admin"']
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/router_client.py', 25, code, context
        )
        # Variable usage - should be detected
        assert is_vulnerable
    
    def test_detect_metadata_service(self):
        """Should detect cloud metadata service access."""
        code = 'data = requests.get(f"http://169.254.169.254/latest/{path}").json()'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/cloud_client.py', 30, code, []
        )
        assert is_vulnerable
        assert 'internal' in reason.lower()


class TestAllowlistDetection:
    """Test allowlist detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SSRFValidator()
    
    def test_detect_allowed_hosts(self):
        """Should detect ALLOWED_HOSTS check."""
        code = 'response = requests.get(url)'
        context = [
            'ALLOWED_HOSTS = ["api.example.com", "data.example.com"]',
            'parsed = urlparse(url)',
            'if parsed.netloc not in ALLOWED_HOSTS:',
            '    raise ValueError("Host not allowed")'
        ]
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/restricted_client.py', 30, code, context
        )
        # Should have lower confidence due to allowlist
        if is_vulnerable:
            assert confidence < 0.7
    
    def test_detect_domain_whitelist(self):
        """Should detect domain whitelist."""
        code = 'requests.post(target_url, data=payload)'
        context = [
            'if domain not in allowed_urls:',
            '    return None'
        ]
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/webhook_client.py', 35, code, context
        )
        # Should have lower confidence due to whitelist
        if is_vulnerable:
            assert confidence < 0.7


class TestStaticURLs:
    """Test static URL detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SSRFValidator()
    
    def test_static_url_safe(self):
        """Should accept fully static URLs."""
        code = 'response = requests.get("https://api.example.com/v1/data")'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/client.py', 10, code, []
        )
        assert not is_vulnerable
        # Message can be either "static" or "no unsafe" - both are correct
        assert 'static' in reason.lower() or 'no unsafe' in reason.lower()
    
    def test_config_url_safe(self):
        """Should accept configuration-based URLs."""
        code = 'response = requests.get(API_ENDPOINT)'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/client.py', 15, code, []
        )
        assert not is_vulnerable


class TestEdgeCases:
    """Test edge cases."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SSRFValidator()
    
    def test_no_unsafe_pattern(self):
        """Should return false for non-HTTP operations."""
        code = 'data = json.loads(response.text)'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/parser.py', 10, code, []
        )
        assert not is_vulnerable
        assert 'no unsafe' in reason.lower()
    
    def test_test_file_lower_confidence(self):
        """Should lower confidence for test files."""
        code = 'response = requests.get(base_url + endpoint)'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/tests/test_api_client.py', 20, code, []
        )
        # May or may not be vulnerable depending on confidence threshold
        if is_vulnerable:
            assert confidence < 0.7
    
    def test_fetch_api_detection(self):
        """Should detect JavaScript fetch() API."""
        code = 'fetch(apiUrl + userPath).then(r => r.json())'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/frontend.js', 25, code, []
        )
        assert is_vulnerable
    
    def test_axios_detection(self):
        """Should detect axios library."""
        code = 'axios.get(baseURL + endpoint)'
        is_vulnerable, reason, confidence = self.validator.validate_http_request(
            code, '/app/api.js', 30, code, []
        )
        assert is_vulnerable
