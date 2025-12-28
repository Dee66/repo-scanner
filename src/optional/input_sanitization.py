"""Comprehensive input sanitization and validation system."""

import re
import html
import json
import os
import sys
from typing import Any, Dict, List, Optional, Union, Callable
from pathlib import Path
from urllib.parse import urlparse, quote, unquote
import ipaddress
import base64
import hashlib
from datetime import datetime
import logging

# Optional imports
try:
    from .logging_aggregation import setup_structured_logging
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False

class InputSanitizer:
    """Comprehensive input sanitization and validation system."""

    def __init__(self):
        if LOGGING_AVAILABLE:
            self.logger = setup_structured_logging("input_sanitizer")
        else:
            self.logger = logging.getLogger(__name__)

        # Define validation patterns
        self._init_validation_patterns()

    def _init_validation_patterns(self):
        """Initialize validation patterns and rules."""
        # Dangerous character patterns
        self.dangerous_chars = {
            'null_bytes': '\x00',
            'newlines': '\r\n',
            'carriage_returns': '\r',
            'tabs': '\t',
            'shell_metas': [';', '|', '`', '$', '(', ')', '<', '>', '&', '!', '{', '}', '[', ']', '*', '?', '~'],
            'path_traversal': ['../', '..\\', '.\\', './'],
            'sql_injection': ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'UNION', 'EXEC', 'EXECUTE'],
            'script_injection': ['<script', 'javascript:', 'vbscript:', 'data:', 'onload=', 'onerror='],
        }

        # Content type validators
        self.content_validators = {
            'text': self._validate_text,
            'url': self._validate_url,
            'email': self._validate_email,
            'filename': self._validate_filename,
            'filepath': self._validate_filepath,
            'json': self._validate_json,
            'base64': self._validate_base64,
            'number': self._validate_number,
            'boolean': self._validate_boolean,
            'repository_url': self._validate_repository_url,
            'branch_name': self._validate_branch_name,
            'commit_hash': self._validate_commit_hash,
        }

        # Size limits
        self.size_limits = {
            'text': 10000,  # 10KB
            'url': 2000,    # 2KB
            'email': 254,   # RFC 5321
            'filename': 255, # Common filesystem limit
            'filepath': 4096, # Common PATH_MAX
            'json': 100000, # 100KB
            'base64': 100000, # 100KB
        }

    def sanitize_input(self, input_data: Any, input_type: str = 'text',
                      strict: bool = True, max_length: Optional[int] = None) -> Any:
        """
        Sanitize input based on type.

        Args:
            input_data: The input data to sanitize
            input_type: Type of input ('text', 'url', 'email', etc.)
            strict: If True, reject invalid inputs; if False, attempt to clean them
            max_length: Maximum allowed length (overrides defaults)

        Returns:
            Sanitized input data

        Raises:
            ValueError: If input is invalid and strict=True
        """
        if input_data is None:
            return None

        # Convert to string for initial processing
        if not isinstance(input_data, str):
            input_data = str(input_data)

        # Apply length limits
        limit = max_length or self.size_limits.get(input_type, 1000)
        if len(input_data) > limit:
            if strict:
                raise ValueError(f"Input exceeds maximum length of {limit} characters")
            else:
                input_data = input_data[:limit]
                self.logger.warning(f"Input truncated to {limit} characters")

        # Apply type-specific validation and sanitization
        validator = self.content_validators.get(input_type, self._validate_text)
        return validator(input_data, strict)

    def _validate_text(self, text: str, strict: bool = True) -> str:
        """Validate and sanitize text input."""
        # Remove null bytes
        sanitized = text.replace(self.dangerous_chars['null_bytes'], '')

        # Handle newlines based on strictness
        if strict:
            # Replace newlines with spaces
            sanitized = sanitized.replace(self.dangerous_chars['carriage_returns'], ' ')
            sanitized = sanitized.replace(self.dangerous_chars['newlines'], ' ')
        else:
            # Allow controlled newlines but limit consecutive ones
            sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)
            sanitized = re.sub(r'\r{3,}', '\r\r', sanitized)

        # HTML escape
        sanitized = html.escape(sanitized)

        # Check for dangerous patterns (only the most critical ones for text)
        critical_patterns = ['script_injection']
        for pattern_name in critical_patterns:
            patterns = self.dangerous_chars.get(pattern_name, [])
            if isinstance(patterns, list):
                for pattern in patterns:
                    if pattern.lower() in sanitized.lower():
                        if strict:
                            raise ValueError(f"Dangerous pattern detected: {pattern_name}")
                        else:
                            # Remove the pattern
                            sanitized = sanitized.replace(pattern, '')
                            self.logger.warning(f"Removed dangerous pattern: {pattern_name}")

        return sanitized.strip()

    def _validate_url(self, url: str, strict: bool = True) -> str:
        """Validate and sanitize URL."""
        try:
            # Parse URL
            parsed = urlparse(url.strip())

            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")

            # Only allow HTTP/HTTPS
            if parsed.scheme.lower() not in ['http', 'https']:
                raise ValueError("Only HTTP and HTTPS URLs are allowed")

            # Check for dangerous characters in path/query
            dangerous_in_url = ['<', '>', '"', "'", '{', '}', '|', '`']
            url_string = url.lower()
            for char in dangerous_in_url:
                if char in url_string:
                    raise ValueError(f"Dangerous character in URL: {char}")

            # Block localhost/private IPs in production
            if os.getenv("REPO_SCANNER_ENV") == "production":
                hostname = parsed.hostname.lower()
                blocked_hosts = ['localhost', '127.0.0.1', '::1', '0.0.0.0']
                if hostname in blocked_hosts:
                    raise ValueError("Localhost URLs not allowed in production")

                try:
                    ip = ipaddress.ip_address(hostname)
                    if ip.is_private or ip.is_loopback or ip.is_link_local:
                        raise ValueError("Private IP addresses not allowed in production")
                except ValueError:
                    pass  # Not an IP, continue

            # Reconstruct clean URL
            clean_url = f"{parsed.scheme}://{parsed.netloc}{quote(unquote(parsed.path))}"
            if parsed.query:
                clean_url += f"?{quote(unquote(parsed.query), safe='=&')}"
            if parsed.fragment:
                clean_url += f"#{quote(unquote(parsed.fragment))}"

            return clean_url

        except Exception as e:
            if strict:
                raise ValueError(f"Invalid URL: {e}")
            else:
                # Fallback: basic sanitization
                return re.sub(r'[^\w\.\-\:\/\?\&\=\#]', '', url)

    def _validate_email(self, email: str, strict: bool = True) -> str:
        """Validate and sanitize email address."""
        email = email.strip().lower()

        # Basic email pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(pattern, email):
            raise ValueError("Invalid email format")

        # Length checks
        local_part, domain = email.split('@')
        if len(local_part) > 64 or len(domain) > 253:
            raise ValueError("Email address too long")

        # Check for dangerous characters
        dangerous = ['<', '>', '"', "'", ';', '|', '&', '`']
        for char in dangerous:
            if char in email:
                raise ValueError(f"Dangerous character in email: {char}")

        return email

    def _validate_filename(self, filename: str, strict: bool = True) -> str:
        """Validate and sanitize filename."""
        filename = filename.strip()

        # Remove path separators and dangerous characters
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in dangerous_chars:
            if char in filename:
                if strict:
                    raise ValueError(f"Invalid character in filename: {char}")
                else:
                    filename = filename.replace(char, '_')

        # Prevent path traversal
        if '..' in filename or filename.startswith('.'):
            raise ValueError("Path traversal detected in filename")

        # Remove control characters
        filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)

        # Ensure not empty and not too long
        if not filename or len(filename) > 255:
            raise ValueError("Invalid filename length")

        return filename

    def _validate_filepath(self, filepath: str, strict: bool = True) -> str:
        """Validate and sanitize file path."""
        from pathlib import Path

        # Convert to Path for normalization
        path = Path(filepath)

        # Resolve to prevent traversal
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError):
            raise ValueError("Invalid file path")

        # Check for path traversal
        if '..' in path.parts:
            raise ValueError("Path traversal detected")

        # Prevent access to system directories
        system_paths = ['/etc', '/bin', '/sbin', '/usr', '/var', '/root', '/proc', '/sys', '/dev',
                       'C:\\Windows', 'C:\\System32', 'C:\\Program Files']
        resolved_str = str(resolved)
        for sys_path in system_paths:
            if resolved_str.startswith(sys_path):
                raise ValueError("Access to system directories not allowed")

        return str(path)

    def _validate_json(self, json_str: str, strict: bool = True) -> str:
        """Validate and sanitize JSON input."""
        try:
            # Parse to validate
            parsed = json.loads(json_str)

            # Check for dangerous content in strings
            def sanitize_json_obj(obj):
                if isinstance(obj, str):
                    return self._validate_text(obj, strict)
                elif isinstance(obj, dict):
                    return {k: sanitize_json_obj(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [sanitize_json_obj(item) for item in obj]
                else:
                    return obj

            sanitized = sanitize_json_obj(parsed)

            # Re-serialize
            return json.dumps(sanitized, separators=(',', ':'))

        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid JSON: {e}")

    def _validate_base64(self, b64_str: str, strict: bool = True) -> str:
        """Validate and sanitize base64 input."""
        # Remove whitespace
        b64_str = re.sub(r'\s+', '', b64_str)

        # Check basic base64 pattern
        if not re.match(r'^[A-Za-z0-9+/]*={0,2}$', b64_str):
            raise ValueError("Invalid base64 format")

        try:
            # Decode to validate
            decoded = base64.b64decode(b64_str, validate=True)

            # Check decoded content for dangerous patterns
            decoded_str = decoded.decode('utf-8', errors='ignore')
            if any(pattern in decoded_str for pattern in self.dangerous_chars['script_injection']):
                raise ValueError("Dangerous content detected in base64")

            return b64_str

        except Exception as e:
            raise ValueError(f"Invalid base64: {e}")

    def _validate_number(self, num_str: str, strict: bool = True) -> Union[int, float]:
        """Validate and convert number input."""
        num_str = num_str.strip()

        try:
            # Try integer first
            if '.' not in num_str and 'e' not in num_str.lower():
                num = int(num_str)
            else:
                num = float(num_str)

            # Reasonable bounds check
            if abs(num) > 1e10:  # 10 billion
                raise ValueError("Number too large")

            return num

        except (ValueError, OverflowError):
            raise ValueError("Invalid number format")

    def _validate_boolean(self, bool_str: str, strict: bool = True) -> bool:
        """Validate and convert boolean input."""
        bool_str = bool_str.strip().lower()

        true_values = ['true', '1', 'yes', 'on', 'enabled']
        false_values = ['false', '0', 'no', 'off', 'disabled']

        if bool_str in true_values:
            return True
        elif bool_str in false_values:
            return False
        else:
            raise ValueError("Invalid boolean value")

    def _validate_repository_url(self, url: str, strict: bool = True) -> str:
        """Validate repository URL with additional Git-specific checks."""
        # First validate as regular URL
        url = self._validate_url(url, strict)

        parsed = urlparse(url)

        # Allow common Git hosting services
        allowed_domains = [
            'github.com', 'gitlab.com', 'bitbucket.org',
            'codeberg.org', 'sourceforge.net', 'git.kernel.org',
            'gitee.com', 'gittea.com'
        ]

        if parsed.hostname not in allowed_domains:
            # In non-strict mode, allow but log warning
            if strict:
                raise ValueError(f"Repository host not in allowed list: {parsed.hostname}")
            else:
                self.logger.warning(f"Non-standard repository host: {parsed.hostname}")

        # Check for .git extension (common for Git repos)
        if not parsed.path.endswith('.git') and not parsed.path.endswith('/'):
            if strict:
                url += '.git'
            else:
                self.logger.info("Added .git extension to repository URL")

        return url

    def _validate_branch_name(self, branch: str, strict: bool = True) -> str:
        """Validate Git branch name."""
        branch = branch.strip()

        # Git branch name rules
        if not re.match(r'^[a-zA-Z0-9._/-]+$', branch):
            raise ValueError("Invalid branch name format")

        # Prevent dangerous names
        dangerous_names = ['HEAD', 'ORIG_HEAD', 'FETCH_HEAD', 'refs/heads/', 'refs/tags/']
        if branch.upper() in dangerous_names:
            raise ValueError(f"Dangerous branch name: {branch}")

        # Length check
        if len(branch) > 255:
            raise ValueError("Branch name too long")

        return branch

    def _validate_commit_hash(self, commit_hash: str, strict: bool = True) -> str:
        """Validate Git commit hash."""
        commit_hash = commit_hash.strip().lower()

        # Git commit hash is typically 40 characters (SHA-1) or 64 (SHA-256)
        if not re.match(r'^[0-9a-f]{4,64}$', commit_hash):
            raise ValueError("Invalid commit hash format")

        return commit_hash

    def sanitize_environment_variables(self) -> Dict[str, str]:
        """Sanitize environment variables."""
        sanitized = {}

        # List of environment variables to sanitize
        env_vars_to_check = [
            'REPO_SCANNER_API_PORT', 'REPO_SCANNER_API_HOST',
            'REPO_SCANNER_ENV', 'REPO_SCANNER_LOG_LEVEL',
            'REPO_SCANNER_DATA_DIR', 'REPO_SCANNER_CACHE_DIR'
        ]

        for var_name in env_vars_to_check:
            value = os.getenv(var_name)
            if value is not None:
                try:
                    if var_name.endswith('_PORT'):
                        sanitized[var_name] = str(self.sanitize_input(value, 'number'))
                    elif var_name.endswith('_HOST'):
                        sanitized[var_name] = self.sanitize_input(value, 'text')
                    elif var_name == 'REPO_SCANNER_ENV':
                        if value.lower() in ['development', 'production', 'testing']:
                            sanitized[var_name] = value.lower()
                        else:
                            sanitized[var_name] = 'development'
                    else:
                        sanitized[var_name] = self.sanitize_input(value, 'text')
                except ValueError:
                    self.logger.warning(f"Invalid environment variable {var_name}, using default")
                    sanitized[var_name] = None

        return sanitized

    def sanitize_command_line_args(self, args: List[str]) -> List[str]:
        """Sanitize command line arguments."""
        sanitized = []

        for arg in args:
            try:
                # Basic text sanitization for arguments
                sanitized_arg = self.sanitize_input(arg, 'text', strict=False)
                sanitized.append(sanitized_arg)
            except ValueError:
                self.logger.warning(f"Skipping invalid command line argument: {arg[:50]}...")
                continue

        return sanitized

    def create_input_validator(self, input_type: str, **kwargs) -> Callable:
        """Create a reusable input validator function."""
        def validator(input_data: Any) -> Any:
            return self.sanitize_input(input_data, input_type, **kwargs)
        return validator

# Global sanitizer instance
_sanitizer = None

def get_input_sanitizer() -> InputSanitizer:
    """Get the global input sanitizer instance."""
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = InputSanitizer()
    return _sanitizer

def sanitize_input(input_data: Any, input_type: str = 'text', **kwargs) -> Any:
    """Convenience function for input sanitization."""
    return get_input_sanitizer().sanitize_input(input_data, input_type, **kwargs)