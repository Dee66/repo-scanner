"""Context-aware secret validation with zero false positive goal."""

import re
from typing import Tuple, Dict, Any
from .entropy import (
    calculate_shannon_entropy,
    has_high_entropy,
    has_repeated_pattern,
    calculate_character_diversity
)
from .test_indicators import (
    contains_test_indicator,
    has_test_prefix,
    is_weak_secret,
    has_test_context,
    get_context_lines,
    is_test_file_path
)


class SecretValidator:
    """Multi-layer validation for secret detection with 0 FP goal."""
    
    def __init__(self, min_entropy: float = 4.5, min_length: int = 8):
        """
        Initialize validator.
        
        Args:
            min_entropy: Minimum Shannon entropy for real secrets
            min_length: Minimum secret length
        """
        self.min_entropy = min_entropy
        self.min_length = min_length
    
    def validate_secret(
        self,
        secret: str,
        file_path: str,
        line_num: int,
        file_content: str
    ) -> Tuple[bool, str, float]:
        """
        Comprehensive secret validation with 7 layers.
        
        Args:
            secret: The potential secret string
            file_path: Path to the file
            line_num: Line number (1-based)
            file_content: Full file content for context
            
        Returns:
            (is_valid, reason, confidence)
            - is_valid: True if likely a real secret
            - reason: Explanation for the decision
            - confidence: 0.0-1.0 confidence score
        """
        confidence = 1.0
        reasons = []
        
        # Layer 1: Length check
        if len(secret) < self.min_length:
            return False, f"Too short: {len(secret)} < {self.min_length} chars", 0.0
        
        # Layer 2: Test prefixes (check BEFORE entropy)
        has_prefix, prefix_reason = has_test_prefix(secret)
        if has_prefix:
            return False, prefix_reason, 0.1
        
        # Layer 3: Test indicators in value
        has_indicator, indicator_reason = contains_test_indicator(secret)
        if has_indicator:
            return False, indicator_reason, 0.1
        
        # Layer 3.5: Config key / enum constant exclusion
        # Dotted identifiers (e.g., "api_server.enabled") are config paths, not secrets
        if re.match(r'^[\w]+(?:\.[\w]+)+$', secret):
            return False, f"Looks like a config path: {secret}", 0.1
        # Simple lowercase single words are typically enum values or constants
        if re.match(r'^[a-z_]+$', secret) and len(secret) < 30:
            return False, f"Looks like an enum/constant value: {secret}", 0.1
        # Check surrounding context for config/schema indicators
        config_indicators = ('key=', 'key =', 'default=', 'default =',
                             'ConfigurationSchema', 'choices=', 'choices =')
        # Get the line containing the secret for context check
        for line in file_content.splitlines():
            if secret in line:
                if any(indicator in line for indicator in config_indicators):
                    return False, "Appears in config/schema definition context", 0.15
                break
        
        # Layer 4: Entropy check - lower threshold for format-specific keys
        # AWS keys, JWTs have unique formats but may have lower entropy
        entropy = calculate_shannon_entropy(secret)
        
        # Special handling for known formats
        is_aws_key = secret.startswith('AKIA') or secret.startswith('ASIA')
        is_jwt = secret.count('.') == 2 and len(secret) > 50
        
        # AWS keys often have lower entropy due to fixed prefix
        min_entropy_threshold = 3.5 if is_aws_key else (3.8 if is_jwt else self.min_entropy)
        
        if entropy < min_entropy_threshold:
            return False, f"Low entropy: {entropy:.2f} < {min_entropy_threshold}", 0.1
        reasons.append(f"High entropy: {entropy:.2f}")
        
        # Layer 5: Weak/common secrets
        is_weak, weak_reason = is_weak_secret(secret)
        if is_weak:
            return False, weak_reason, 0.1
        
        # Layer 6: Repetition patterns
        if has_repeated_pattern(secret):
            return False, "High repetition pattern", 0.2
        
        # Layer 7: File path check
        is_test_file, test_reason = is_test_file_path(file_path)
        if is_test_file:
            # Reject outright if in test file
            return False, f"In test file: {test_reason}", 0.2
        
        # Layer 8: Context check (surrounding lines)
        context_lines = get_context_lines(file_content, line_num, window=5)
        has_context, context_reason = has_test_context(context_lines)
        if has_context:
            confidence *= 0.4  # Heavy penalty for test context
            reasons.append(f"Test context: {context_reason}")
        
        # Layer 9: Character diversity
        # JWTs and base64-encoded secrets naturally have lower diversity
        diversity = calculate_character_diversity(secret)
        
        # Relax diversity check for base64/JWT formats
        is_base64_format = is_jwt or all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=._-' for c in secret)
        min_diversity = 0.35 if is_base64_format else 0.5
        
        if diversity < min_diversity:
            confidence *= 0.7
            reasons.append(f"Low diversity: {diversity:.2f}")
        else:
            reasons.append(f"Good diversity: {diversity:.2f}")
        
        # Decision threshold
        if confidence < 0.85:
            return False, f"Confidence too low: {confidence:.2f}. " + "; ".join(reasons), confidence
        
        return True, f"High confidence real secret. {'; '.join(reasons)}", confidence
    
    def get_detailed_analysis(
        self,
        secret: str,
        file_path: str,
        line_num: int,
        file_content: str
    ) -> Dict[str, Any]:
        """
        Get detailed analysis for debugging/reporting.
        
        Returns:
            Dictionary with all validation layers
        """
        entropy = calculate_shannon_entropy(secret)
        diversity = calculate_character_diversity(secret)
        context_lines = get_context_lines(file_content, line_num)
        
        return {
            'secret_length': len(secret),
            'entropy': {
                'value': entropy,
                'high': entropy >= self.min_entropy,
                'threshold': self.min_entropy
            },
            'diversity': {
                'value': diversity,
                'good': diversity > 0.5
            },
            'repetition': {
                'detected': has_repeated_pattern(secret),
            },
            'test_indicators': {
                'in_value': contains_test_indicator(secret)[0],
                'test_prefix': has_test_prefix(secret)[0],
                'weak_secret': is_weak_secret(secret)[0],
            },
            'file_analysis': {
                'is_test_file': is_test_file_path(file_path)[0],
                'path': file_path,
            },
            'context': {
                'has_test_phrases': has_test_context(context_lines)[0],
                'lines': context_lines,
            }
        }
