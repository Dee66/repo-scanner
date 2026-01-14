"""Test indicator database for false positive reduction."""

from typing import List, Set, Tuple
import re


# Words that indicate test/example values
TEST_INDICATORS = {
    # Common test words
    'test', 'tests', 'testing', 'tester',
    'example', 'examples', 'sample', 'samples',
    'dummy', 'dummies', 'mock', 'mocks', 'mocking',
    'fake', 'fakes', 'fixture', 'fixtures',
    'placeholder', 'placeholders', 'stub', 'stubs',
    'demo', 'demos', 'development', 'dev',
    'local', 'localhost', 'prototype',
    
    # Build/CI related
    'build', 'ci', 'pipeline', 'temporary', 'temp',
    
    # Common weak/test passwords
    'password', 'changeme', 'admin', 'root',
    '123456', '654321', 'qwerty', 'letmein',
    
    # Descriptive/documentation
    'your', 'insert', 'enter', 'replace',
    'here', 'value', 'put',
}


# Prefixes that indicate test API keys
TEST_API_KEY_PREFIXES = {
    'sk_test_',      # Stripe test
    'pk_test_',      # Stripe test public
    'rk_test_',      # Stripe test restricted
    'test_',         # Generic test
    'dev_',          # Development
    'local_',        # Local
    'demo_',         # Demo
    'sample_',       # Sample
    'example_',      # Example
    'dummy_',        # Dummy
}


# Context phrases indicating test/build context
TEST_CONTEXT_PHRASES = {
    'for testing',
    'test only',
    'test purposes',
    'example only',
    'sample only',
    'build-time',
    'build time',
    'compile-time',
    'compile time',
    'development only',
    'not production',
    'non-production',
    'placeholder',
    'replace with',
    'change this',
    'dummy value',
    'example value',
    'test value',
    'do not use in production',
    'not for production',
}


# Common weak secrets that are never real
WEAK_SECRETS = {
    'password', 'password1', 'password123',
    'changeme', 'change_me',
    'admin', 'admin123',
    'secret', 'secret123',
    '123456', '12345678',
    'qwerty', 'qwerty123',
    'letmein',
    'welcome', 'welcome123',
    'root', 'toor',
    'guest',
}


def contains_test_indicator(text: str) -> Tuple[bool, str]:
    """
    Check if text contains test indicators.
    
    Args:
        text: String to check (case-insensitive)
        
    Returns:
        (has_indicator, reason)
    """
    text_lower = text.lower()
    
    for indicator in TEST_INDICATORS:
        if indicator in text_lower:
            return True, f"Contains test indicator: '{indicator}'"
    
    return False, ""


def has_test_prefix(text: str) -> Tuple[bool, str]:
    """
    Check if text starts with test API key prefix.
    
    Args:
        text: String to check
        
    Returns:
        (has_prefix, reason)
    """
    for prefix in TEST_API_KEY_PREFIXES:
        if text.startswith(prefix):
            return True, f"Test API key prefix: '{prefix}'"
    
    return False, ""


def is_weak_secret(text: str) -> Tuple[bool, str]:
    """
    Check if text is a common weak/placeholder secret.
    
    Args:
        text: String to check (case-insensitive)
        
    Returns:
        (is_weak, reason)
    """
    text_lower = text.lower()
    
    if text_lower in WEAK_SECRETS:
        return True, f"Common weak/placeholder password"
    
    # Check for weak patterns like "password1", "password2"
    if re.match(r'password\d+', text_lower):
        return True, "Password + number pattern"
    
    if re.match(r'test\d+', text_lower):
        return True, "Test + number pattern"
    
    return False, ""


def has_test_context(context_lines: List[str]) -> Tuple[bool, str]:
    """
    Check if context lines indicate test/build environment.
    
    Args:
        context_lines: List of strings (surrounding code lines)
        
    Returns:
        (has_context, reason)
    """
    context_text = ' '.join(context_lines).lower()
    
    for phrase in TEST_CONTEXT_PHRASES:
        if phrase in context_text:
            return True, f"Test context phrase: '{phrase}'"
    
    return False, ""


def get_context_lines(file_content: str, line_num: int, window: int = 5) -> List[str]:
    """
    Extract lines around a specific line number.
    
    Args:
        file_content: Full file content
        line_num: Target line number (1-based)
        window: Number of lines before/after (default 5)
        
    Returns:
        List of context lines
    """
    lines = file_content.splitlines()
    start = max(0, line_num - window - 1)
    end = min(len(lines), line_num + window)
    
    return lines[start:end]


def is_test_file_path(file_path: str) -> Tuple[bool, str]:
    """
    Check if file path indicates test/build file.
    
    Args:
        file_path: Path to check
        
    Returns:
        (is_test, reason)
    """
    path_lower = file_path.lower()
    
    # Test directories - check both with and without leading slash
    test_dirs = [
        'test/', 'tests/', '__tests__/',
        'spec/', 'specs/',
        'fixture/', 'fixtures/',
        'mock/', 'mocks/',
        'example/', 'examples/',
        'sample/', 'samples/',
        'demo/', 'demos/',
    ]
    
    for test_dir in test_dirs:
        # Check if path starts with or contains the test directory
        if path_lower.startswith(test_dir) or f'/{test_dir}' in path_lower:
            return True, f"Test directory: {test_dir}"
    
    # Test file patterns
    if '_test.' in path_lower or '.test.' in path_lower:
        return True, "Test file name pattern"
    
    if '_spec.' in path_lower or '.spec.' in path_lower:
        return True, "Spec file name pattern"
    
    if path_lower.startswith('test_') or path_lower.startswith('test/'):
        return True, "Starts with 'test'"
    
    # Build files
    build_files = [
        'build.rs', 'build.py', 'build.gradle',
        'makefile', 'cmake', 'setup.py', 'setup.cfg',
        'gulpfile.js', 'gruntfile.js',
    ]
    
    for build_file in build_files:
        if build_file in path_lower:
            return True, f"Build file: {build_file}"
    
    # Config files (often contain test values)
    if any(x in path_lower for x in ['.config.', '.test.', '.dev.', '.local.']):
        return True, "Config file with test/dev/local suffix"
    
    return False, ""
