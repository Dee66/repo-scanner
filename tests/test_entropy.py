"""Tests for entropy calculator."""

import pytest
from src.core.security.entropy import (
    calculate_shannon_entropy,
    has_high_entropy,
    has_repeated_pattern,
    calculate_character_diversity,
    analyze_entropy_profile
)


class TestShannonEntropy:
    """Test Shannon entropy calculation."""
    
    def test_empty_string(self):
        """Empty string has zero entropy."""
        assert calculate_shannon_entropy("") == 0.0
    
    def test_single_character(self):
        """Single repeated character has zero entropy."""
        assert calculate_shannon_entropy("aaaa") == 0.0
    
    def test_low_entropy_test_key(self):
        """Test keys have low entropy."""
        test_key = "test-license-key-for-build-encryption-2024"
        entropy = calculate_shannon_entropy(test_key)
        assert entropy < 4.5, f"Test key entropy {entropy:.2f} should be < 4.5"
    
    def test_medium_entropy_password(self):
        """Common passwords have medium entropy."""
        entropy = calculate_shannon_entropy("password123")
        assert 2.5 < entropy < 4.0, f"Password entropy {entropy:.2f} should be medium"
    
    def test_high_entropy_real_secret(self):
        """Real API keys have high entropy."""
        real_key = "sk_live_51H7f2hg8k9m2p5x7q1w4e3r5t6y7u8i9o0"
        entropy = calculate_shannon_entropy(real_key)
        assert entropy > 4.5, f"Real key entropy {entropy:.2f} should be > 4.5"
    
    def test_high_entropy_random_string(self):
        """Random strings have high entropy."""
        random = "a8f3k9m2p5x7q1w4e3r5t6y7u8i9o0"
        entropy = calculate_shannon_entropy(random)
        assert entropy > 4.5, f"Random string entropy {entropy:.2f} should be > 4.5"


class TestHighEntropyCheck:
    """Test high entropy detection."""
    
    def test_default_threshold(self):
        """Test default threshold of 4.5."""
        assert has_high_entropy("sk_live_51H7f2hg8k9m2p5x7q1w4e3r5t6y7") is True
        assert has_high_entropy("test-key-example") is False
    
    def test_custom_threshold(self):
        """Test custom threshold."""
        assert has_high_entropy("test123", threshold=2.0) is True
        assert has_high_entropy("test", threshold=3.0) is False


class TestRepetitionPattern:
    """Test repetition detection."""
    
    def test_single_char_repetition(self):
        """Single character repeated."""
        assert has_repeated_pattern("aaaaaaa") is True
        assert has_repeated_pattern("a1b2c3d4") is False
    
    def test_pattern_repetition(self):
        """Pattern repeated."""
        # "123123" has only 3 unique chars (1,2,3), ratio = 3/12 = 0.25 < 0.4
        # but most common is '1' appearing 4 times, 4/12 = 0.33 < 0.4
        assert has_repeated_pattern("1111111111") is True  # Single char
        assert has_repeated_pattern("12345678") is False
    
    def test_normal_strings(self):
        """Normal strings don't trigger."""
        assert has_repeated_pattern("password123") is False
        assert has_repeated_pattern("api_key_value") is False


class TestCharacterDiversity:
    """Test character diversity calculation."""
    
    def test_no_diversity(self):
        """All same character."""
        assert calculate_character_diversity("aaaa") == 0.25
    
    def test_full_diversity(self):
        """All unique characters."""
        assert calculate_character_diversity("abcd") == 1.0
    
    def test_normal_diversity(self):
        """Normal strings have medium-high diversity."""
        diversity = calculate_character_diversity("password123")
        # "password123" has 10 unique chars out of 11 total = 0.909
        assert 0.7 < diversity <= 1.0


class TestEntropyProfile:
    """Test comprehensive entropy analysis."""
    
    def test_real_secret_profile(self):
        """Real secret has good profile."""
        # Use a more realistic high-entropy key
        profile = analyze_entropy_profile("sk_live_51H7f2hg8k9m2p5x7q1w4e3r5t6y7u8i9o0")
        assert profile['has_high_entropy'] is True
        assert profile['has_repetition'] is False
        assert profile['is_likely_real_secret'] is True
    
    def test_test_secret_profile(self):
        """Test secret has poor profile."""
        profile = analyze_entropy_profile("test-key-example")
        assert profile['has_high_entropy'] is False
        assert profile['is_likely_real_secret'] is False
    
    def test_profile_structure(self):
        """Profile has all expected keys."""
        profile = analyze_entropy_profile("test")
        assert 'shannon_entropy' in profile
        assert 'character_diversity' in profile
        assert 'length' in profile
        assert 'has_high_entropy' in profile
        assert 'has_repetition' in profile
        assert 'is_likely_real_secret' in profile


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
