"""Shannon entropy calculator for secret detection."""

import math
from collections import Counter
from typing import Dict


def calculate_shannon_entropy(text: str) -> float:
    """
    Calculate Shannon entropy of a string.
    
    Higher entropy = more random = more likely to be a real secret.
    Typical values:
    - "password123" = ~3.0 (low, not a real secret)
    - "test-key-example" = ~3.5 (medium, likely test)
    - "a8f3k9m2p5x7q1w4" = ~4.0+ (high, likely real secret)
    
    Args:
        text: String to analyze
        
    Returns:
        Shannon entropy value (typically 0.0 to 5.0+)
    """
    if not text:
        return 0.0
    
    # Count character frequencies
    counter = Counter(text)
    length = len(text)
    
    # Calculate entropy: -sum(p(x) * log2(p(x)))
    entropy = 0.0
    for count in counter.values():
        probability = count / length
        if probability > 0:
            entropy -= probability * math.log2(probability)
    
    return entropy


def has_high_entropy(text: str, threshold: float = 4.5) -> bool:
    """
    Check if text has high entropy (likely real secret).
    
    Args:
        text: String to check
        threshold: Minimum entropy for "high" (default 4.5)
        
    Returns:
        True if entropy >= threshold
    """
    return calculate_shannon_entropy(text) >= threshold


def has_repeated_pattern(text: str, threshold: float = 0.4) -> bool:
    """
    Check if text has high repetition (unlikely real secret).
    
    Examples with high repetition:
    - "aaaaaaaaaa" (single char repeated)
    - "123123123123" (pattern repeated)
    - "testestestest" (sequence repeated)
    
    Args:
        text: String to check
        threshold: Max ratio of most common char (default 0.4)
        
    Returns:
        True if repetition ratio > threshold
    """
    if not text or len(text) < 3:
        return False
    
    counter = Counter(text)
    most_common_count = counter.most_common(1)[0][1]
    ratio = most_common_count / len(text)
    
    return ratio > threshold


def calculate_character_diversity(text: str) -> float:
    """
    Calculate character diversity (unique chars / total chars).
    
    Higher diversity = more likely real secret.
    
    Args:
        text: String to analyze
        
    Returns:
        Diversity ratio (0.0 to 1.0)
    """
    if not text:
        return 0.0
    
    unique_chars = len(set(text))
    total_chars = len(text)
    
    return unique_chars / total_chars


def analyze_entropy_profile(text: str) -> Dict[str, float]:
    """
    Get comprehensive entropy analysis.
    
    Args:
        text: String to analyze
        
    Returns:
        Dictionary with entropy metrics
    """
    return {
        'shannon_entropy': calculate_shannon_entropy(text),
        'character_diversity': calculate_character_diversity(text),
        'length': len(text),
        'has_high_entropy': has_high_entropy(text),
        'has_repetition': has_repeated_pattern(text),
        'is_likely_real_secret': (
            has_high_entropy(text) and 
            not has_repeated_pattern(text) and
            calculate_character_diversity(text) > 0.5
        )
    }


# Pre-computed entropy values for common test strings
COMMON_TEST_ENTROPY = {
    'password': 2.75,
    'test': 2.0,
    '123456': 2.58,
    'changeme': 3.0,
    'admin': 2.32,
    'secret': 2.58,
}
