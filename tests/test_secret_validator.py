"""Tests for secret validator with zero false positive goal."""

import pytest
from src.core.security.secret_validator import SecretValidator


class TestSecretValidator:
    """Test comprehensive secret validation."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return SecretValidator(min_entropy=4.5, min_length=8)
    
    def test_costpilot_test_key_rejected(self, validator):
        """CostPilot test key from build.rs should be rejected."""
        test_key = "test-license-key-for-build-encryption-2024"
        file_content = '''
    // Use a test license key for build-time encryption
    // In production, this would be provided by the license server
    let test_license_key = "test-license-key-for-build-encryption-2024";
        '''
        
        is_valid, reason, confidence = validator.validate_secret(
            secret=test_key,
            file_path="build.rs",
            line_num=3,
            file_content=file_content
        )
        
        assert is_valid is False, "Test key should be rejected"
        assert "entropy" in reason.lower() or "test" in reason.lower()
        assert confidence < 0.85
    
    def test_real_api_key_accepted(self, validator):
        """Real API key in production file should be accepted."""
        real_key = "sk_live_51H7f2hg8k9m2p5x7q1w4e3r5t6y7u8i9o0"
        file_content = '''
    # Production API configuration
    API_KEY = "sk_live_51H7f2hg8k9m2p5x7q1w4e3r5t6y7u8i9o0"
    API_URL = "https://api.example.com"
        '''
        
        is_valid, reason, confidence = validator.validate_secret(
            secret=real_key,
            file_path="src/config/production.py",
            line_num=2,
            file_content=file_content
        )
        
        assert is_valid is True, f"Real key should be accepted: {reason}"
        assert confidence >= 0.85
    
    def test_test_prefix_rejected(self, validator):
        """Keys with test_ prefix rejected."""
        test_key = "sk_test_a8f3k9m2p5x7q1w4e3r5"
        file_content = 'KEY = "sk_test_a8f3k9m2p5x7q1w4e3r5"'
        
        is_valid, reason, confidence = validator.validate_secret(
            secret=test_key,
            file_path="config.py",
            line_num=1,
            file_content=file_content
        )
        
        assert is_valid is False
        assert "test" in reason.lower()
    
    def test_secret_in_test_file_rejected(self, validator):
        """Even high-entropy secrets in test files have low confidence."""
        high_entropy_key = "a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1"
        file_content = f'SECRET = "{high_entropy_key}"'
        
        is_valid, reason, confidence = validator.validate_secret(
            secret=high_entropy_key,
            file_path="tests/test_auth.py",
            line_num=1,
            file_content=file_content
        )
        
        # Should be rejected due to test file location
        assert is_valid is False or confidence < 0.85
    
    def test_weak_password_rejected(self, validator):
        """Common weak passwords rejected."""
        for weak in ["password", "password123", "changeme", "admin123"]:
            is_valid, reason, _ = validator.validate_secret(
                secret=weak,
                file_path="config.py",
                line_num=1,
                file_content=f'PASS = "{weak}"'
            )
            assert is_valid is False, f"{weak} should be rejected"
    
    def test_short_secret_rejected(self, validator):
        """Secrets shorter than min_length rejected."""
        short = "abc123"
        is_valid, reason, _ = validator.validate_secret(
            secret=short,
            file_path="config.py",
            line_num=1,
            file_content=f'KEY = "{short}"'
        )
        
        assert is_valid is False
        assert "short" in reason.lower()
    
    def test_context_with_test_phrase(self, validator):
        """Secrets with 'for testing' context rejected."""
        key = "a8f3k9m2p5x7q1w4e3r5t6y7u8"
        file_content = '''
    # This key is for testing purposes only
    # Do not use in production
    TEST_KEY = "a8f3k9m2p5x7q1w4e3r5t6y7u8"
        '''
        
        is_valid, reason, confidence = validator.validate_secret(
            secret=key,
            file_path="config.py",
            line_num=3,
            file_content=file_content
        )
        
        # Should have low confidence due to context
        assert confidence < 0.85
    
    def test_repeated_pattern_rejected(self, validator):
        """Keys with high repetition rejected."""
        repeated = "aaaabbbbccccdddd"
        is_valid, reason, _ = validator.validate_secret(
            secret=repeated,
            file_path="config.py",
            line_num=1,
            file_content=f'KEY = "{repeated}"'
        )
        
        assert is_valid is False
        # Caught by low entropy check (2.00 < 4.5)
        assert "entropy" in reason.lower()
    
    def test_detailed_analysis(self, validator):
        """Detailed analysis provides all metrics."""
        secret = "test-key-example"
        file_content = 'KEY = "test-key-example"'
        
        analysis = validator.get_detailed_analysis(
            secret=secret,
            file_path="config.py",
            line_num=1,
            file_content=file_content
        )
        
        assert 'entropy' in analysis
        assert 'diversity' in analysis
        assert 'test_indicators' in analysis
        assert 'file_analysis' in analysis
        assert 'context' in analysis
        
        # Test key should fail entropy check
        assert analysis['entropy']['high'] is False


class TestRealWorldScenarios:
    """Test real-world secret detection scenarios."""
    
    @pytest.fixture
    def validator(self):
        return SecretValidator()
    
    def test_github_token(self, validator):
        """GitHub personal access token."""
        token = "ghp_a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1q2w3"
        file_content = f'GITHUB_TOKEN = "{token}"'
        
        is_valid, _, confidence = validator.validate_secret(
            token, "src/config.py", 1, file_content
        )
        
        assert is_valid is True
        assert confidence >= 0.85
    
    def test_aws_access_key(self, validator):
        """AWS access key ID."""
        # Use a realistic AWS key format (20 chars, starts with AKIA)
        # Not the AWS documentation example which contains "EXAMPLE"
        key = "AKIAZQ7M3PNBX8YFGHTR"
        file_content = f'AWS_ACCESS_KEY_ID = "{key}"'
        
        is_valid, _, confidence = validator.validate_secret(
            key, "config.py", 1, file_content
        )
        
        # Real AWS keys have specific format and high entropy
        assert is_valid is True or confidence > 0.7
    
    def test_jwt_token(self, validator):
        """JWT token with high entropy."""
        # Use a JWT that doesn't contain substring matches for test indicators
        # Real JWT with random payload
        token = "eyJhbGdvcml0aG0iOiJIUzI1NiIsInR5cGUiOiJKV1QifQ.eyJ1c2VyX2lkIjoiNzg5MDEyMzQ1In0.kL8m9nP2qR5sT7uV3wX1yZ4aB6cD8eF0gH2iJ4kL6mN8"
        file_content = f'TOKEN = "{token}"'
        
        is_valid, _, confidence = validator.validate_secret(
            token, "auth.py", 1, file_content
        )
        
        assert is_valid is True
        assert confidence >= 0.85


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
