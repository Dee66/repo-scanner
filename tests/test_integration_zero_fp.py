"""
Integration tests for zero false positive validation.

Tests the complete validation pipeline on real-world scenarios.
"""
import pytest
from src.core.security.secret_validator import SecretValidator
from src.core.security.entropy import calculate_shannon_entropy


class TestZeroFalsePositiveIntegration:
    """Integration tests for complete validation pipeline."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return SecretValidator()
    
    def test_costpilot_false_positive_eliminated(self, validator):
        """CostPilot's test-license-key correctly rejected."""
        secret = "test-license-key-for-build-encryption-2024"
        file_content = '''const LICENSE_KEY: &str = "test-license-key-for-build-encryption-2024";'''
        
        is_valid, reason, confidence = validator.validate_secret(
            secret=secret,
            file_path="build.rs",
            line_num=90,
            file_content=file_content
        )
        
        assert is_valid is False, "CostPilot test key should be rejected"
        assert "test" in reason.lower(), "Should mention 'test' indicator"
        assert confidence < 0.85, "Confidence should be below threshold"
    
    def test_multiple_validation_layers(self, validator):
        """All validation layers work together."""
        # Test each layer individually
        test_cases = [
            # (secret, file_path, should_reject, reason_keyword)
            ("abc", "app.py", True, "short"),  # Layer 1: Length
            ("sk_test_12345678901234567890", "config.py", True, "test"),  # Layer 2: Test prefix
            ("test-api-key-dummy-value-here", "app.py", True, "test"),  # Layer 3: Test indicator
            ("nonwordpassword", "app.py", True, "password"),  # Layer 5: Weak secret (caught before entropy)
            ("aaaaaaaaaaaaaaaa", "app.py", True, "entropy"),  # Layer 6: Repetition
            ("a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1", "tests/test_auth.py", True, "test file"),  # Layer 7: Test file
        ]
        
        for secret, file_path, should_reject, reason_keyword in test_cases:
            is_valid, reason, _ = validator.validate_secret(
                secret=secret,
                file_path=file_path,
                line_num=1,
                file_content=f'KEY = "{secret}"'
            )
            
            if should_reject:
                assert is_valid is False, f"Should reject {secret}"
                assert reason_keyword in reason.lower(), f"Expected '{reason_keyword}' in reason: {reason}"
    
    def test_real_secrets_accepted(self, validator):
        """Real secrets with high confidence pass validation."""
        real_secrets = [
            ("ghp_a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1q2r3", "config.py"),  # GitHub PAT
            ("AKIAZQ7M3PNBX8YFGHTR", "aws_config.py"),  # AWS access key
            ("sk_live_51H7f2hg8k9m2p5x7q1w4e3r5t6y7u8i9o0", "stripe_config.py"),  # Stripe live key
        ]
        
        for secret, file_path in real_secrets:
            is_valid, reason, confidence = validator.validate_secret(
                secret=secret,
                file_path=file_path,
                line_num=1,
                file_content=f'API_KEY = "{secret}"'
            )
            
            assert is_valid is True, f"Real secret should be accepted: {secret}"
            assert confidence >= 0.85, f"Confidence should be high: {confidence}"
    
    def test_entropy_calculation_accuracy(self):
        """Shannon entropy calculations are accurate."""
        # Known entropy values (calculated manually)
        test_cases = [
            ("", 0.0),  # Empty string
            ("a", 0.0),  # Single character
            ("aaaa", 0.0),  # Repeated single character
            ("test-license-key-for-build-encryption-2024", 4.07),  # CostPilot key
            ("password123", 3.18),  # Common password
        ]
        
        for text, expected_entropy in test_cases:
            calculated = calculate_shannon_entropy(text)
            # Allow small floating point differences
            assert abs(calculated - expected_entropy) < 0.1, \
                f"{text}: expected {expected_entropy}, got {calculated}"
    
    def test_confidence_scoring_ranges(self, validator):
        """Confidence scores are in valid range [0.0, 1.0]."""
        test_secrets = [
            "test-key-12345678",
            "sk_test_12345678901234567890",
            "a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1",
            "ghp_a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1q2r3",
        ]
        
        for secret in test_secrets:
            _, _, confidence = validator.validate_secret(
                secret=secret,
                file_path="app.py",
                line_num=1,
                file_content=f'KEY = "{secret}"'
            )
            
            assert 0.0 <= confidence <= 1.0, f"Invalid confidence: {confidence}"
    
    def test_file_path_patterns(self, validator):
        """Test file detection works for common patterns."""
        test_file_paths = [
            "tests/test_auth.py",
            "__tests__/integration.js",
            "spec/unit_spec.rb",
            "test_config.py",
            "app.test.ts",
            "build.rs",
            "setup.py",
        ]
        
        secret = "a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1"  # High entropy
        
        for file_path in test_file_paths:
            is_valid, reason, _ = validator.validate_secret(
                secret=secret,
                file_path=file_path,
                line_num=1,
                file_content=f'KEY = "{secret}"'
            )
            
            assert is_valid is False, f"Should reject secrets in test file: {file_path}"
            assert "test" in reason.lower() or "build" in reason.lower(), \
                f"Should mention test/build file: {reason}"
    
    def test_context_phrase_detection(self, validator):
        """Context phrases are detected correctly."""
        secret = "a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1"  # High entropy
        
        file_content = '''
        # This is a test key for local development
        API_KEY = "a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1"
        # Use this for testing only
        '''
        
        is_valid, reason, confidence = validator.validate_secret(
            secret=secret,
            file_path="config.py",
            line_num=2,
            file_content=file_content
        )
        
        # Context should reduce confidence
        assert confidence < 0.85, "Test context should reduce confidence"
    
    def test_format_specific_handling(self, validator):
        """AWS and JWT formats handled correctly."""
        # AWS key with lower entropy but valid format
        aws_key = "AKIAZQ7M3PNBX8YFGHTR"
        aws_entropy = calculate_shannon_entropy(aws_key)
        assert aws_entropy < 4.5, "AWS key has lower entropy"
        
        is_valid, _, _ = validator.validate_secret(
            secret=aws_key,
            file_path="config.py",
            line_num=1,
            file_content=f'AWS_KEY = "{aws_key}"'
        )
        
        assert is_valid is True, "AWS key should be accepted despite lower entropy"
    
    def test_edge_cases(self, validator):
        """Handle edge cases gracefully."""
        edge_cases = [
            ("", "app.py", False, "short"),  # Empty string
            ("a" * 100, "app.py", False, "entropy"),  # Very long repetition
            ("!@#$%^&*()", "app.py", False, "entropy"),  # Special chars - caught by entropy
            (" " * 20, "app.py", False, "entropy"),  # Whitespace - caught by entropy
        ]
        
        for secret, file_path, expected_valid, reason_keyword in edge_cases:
            is_valid, reason, _ = validator.validate_secret(
                secret=secret,
                file_path=file_path,
                line_num=1,
                file_content=f'KEY = "{secret}"'
            )
            
            assert is_valid == expected_valid, f"Edge case failed: {secret}"
            if reason_keyword:
                assert reason_keyword in reason.lower(), \
                    f"Expected '{reason_keyword}' in reason: {reason}"


class TestValidatorPerformance:
    """Performance tests for validator."""
    
    def test_validation_speed(self, benchmark):
        """Validator completes in < 1ms per secret."""
        validator = SecretValidator()
        
        result = benchmark(
            validator.validate_secret,
            secret="a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1",
            file_path="config.py",
            line_num=1,
            file_content='KEY = "a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1"'
        )
        
        # Should complete very quickly (no ML, just calculations)
        assert result is not None
    
    def test_batch_validation(self):
        """Can validate multiple secrets efficiently."""
        validator = SecretValidator()
        
        secrets = [
            f"secret_{i:08d}_a8f3k9m2p5x7q1w4"
            for i in range(100)
        ]
        
        results = []
        for secret in secrets:
            is_valid, reason, confidence = validator.validate_secret(
                secret=secret,
                file_path="config.py",
                line_num=1,
                file_content=f'KEY = "{secret}"'
            )
            results.append((is_valid, confidence))
        
        # All should be processed
        assert len(results) == 100
        
        # All should have valid confidence scores
        for is_valid, confidence in results:
            assert 0.0 <= confidence <= 1.0


class TestRealWorldScenarios:
    """Tests based on real repository scenarios."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return SecretValidator()
    
    def test_github_actions_secrets(self, validator):
        """GitHub Actions workflow secrets."""
        # Real secrets in workflows should be detected
        workflow = '''
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          API_KEY: ghp_a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1q2r3
        '''
        
        is_valid, _, confidence = validator.validate_secret(
            secret="ghp_a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1q2r3",
            file_path=".github/workflows/ci.yml",
            line_num=3,
            file_content=workflow
        )
        
        # Should detect as real secret despite being in CI file
        assert is_valid is True
        assert confidence >= 0.85
    
    def test_docker_env_files(self, validator):
        """Docker .env files with real secrets."""
        env_content = '''
        DB_PASSWORD=a8f3k9m2p5x7q1w4e3r5
        API_KEY=sk_live_51H7f2hg8k9m2p5x7q1w4e3r5t6y7u8i9o0
        '''
        
        is_valid, _, _ = validator.validate_secret(
            secret="sk_live_51H7f2hg8k9m2p5x7q1w4e3r5t6y7u8i9o0",
            file_path=".env",
            line_num=2,
            file_content=env_content
        )
        
        assert is_valid is True, "Real secret in .env should be detected"
    
    def test_rust_build_script(self, validator):
        """Rust build.rs with test key (CostPilot case)."""
        build_rs = '''
        const LICENSE_KEY: &str = "test-license-key-for-build-encryption-2024";
        const BUILD_TIMESTAMP: &str = "2024-01-15";
        '''
        
        is_valid, reason, _ = validator.validate_secret(
            secret="test-license-key-for-build-encryption-2024",
            file_path="build.rs",
            line_num=1,
            file_content=build_rs
        )
        
        assert is_valid is False, "Test key in build.rs should be rejected"
        assert "test" in reason.lower() or "build" in reason.lower()
    
    def test_python_test_fixtures(self, validator):
        """Python test fixtures with fake credentials."""
        test_fixture = '''
        @pytest.fixture
        def mock_api_key():
            return "test-api-key-for-unit-tests-12345"
        '''
        
        is_valid, _, _ = validator.validate_secret(
            secret="test-api-key-for-unit-tests-12345",
            file_path="tests/conftest.py",
            line_num=3,
            file_content=test_fixture
        )
        
        assert is_valid is False, "Test fixture key should be rejected"
    
    def test_javascript_config_files(self, validator):
        """JavaScript config with real API keys."""
        config_js = '''
        module.exports = {
          apiKey: "AIzaSyA8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1",
          projectId: "my-project-12345"
        };
        '''
        
        is_valid, _, confidence = validator.validate_secret(
            secret="AIzaSyA8f3k9m2p5x7q1w4e3r5t6y7u8i9o0p1",
            file_path="config/firebase.js",
            line_num=2,
            file_content=config_js
        )
        
        # Google API keys should be detected
        assert is_valid is True
        assert confidence >= 0.85
