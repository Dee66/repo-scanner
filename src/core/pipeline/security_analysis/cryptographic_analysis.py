"""Cryptographic implementation depth analysis for Repository Intelligence Scanner."""

import re
import os
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from cryptography.hazmat.primitives.kdf import hkdf, pbkdf2
from cryptography.hazmat.backends import default_backend

from ...exceptions import AnalysisError

@dataclass
class CryptoFinding:
    """Represents a cryptographic implementation finding."""
    finding_type: str
    severity: str  # 'critical', 'high', 'medium', 'low', 'info'
    file_path: str
    line_number: int
    description: str
    code_snippet: str
    recommendation: str = ""
    cwe_id: str = ""

class CryptographicAnalyzer:
    """Analyzes cryptographic implementations for security depth."""

    def __init__(self):
        self.findings: List[CryptoFinding] = []

    def analyze_key_management(self, file_list: List[str]) -> List[CryptoFinding]:
        """Analyze key management lifecycle and security."""
        self.findings = []

        for file_path in file_list:
            if not self._is_code_file(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')

                self._analyze_key_generation(content, lines, file_path)
                self._analyze_key_storage(content, lines, file_path)
                self._analyze_key_rotation(content, lines, file_path)
                self._analyze_key_derivation(content, lines, file_path)

            except Exception as e:
                raise AnalysisError(f"Error analyzing {file_path}: {str(e)}")

        return self.findings

    def _analyze_key_generation(self, content: str, lines: List[str], file_path: str):
        """Analyze cryptographic key generation practices."""
        # Check for secure key generation
        secure_patterns = [
            (r'rsa\.generate_private_key\s*\(\s*public_exponent\s*=\s*65537', 'RSA key generation with secure parameters'),
            (r'ec\.generate_private_key\s*\(\s*ec\.SECP256R1', 'ECDSA key generation with secure curve'),
            (r'os\.urandom\s*\(\s*32\s*\)', 'Secure random key generation'),
            (r'secrets\.token_bytes\s*\(\s*32\s*\)', 'Secure token generation'),
        ]

        insecure_patterns = [
            (r'random\.randint\s*\(', 'Insecure random number generation for keys', 'CWE-338'),
            (r'random\.random\s*\(', 'Insecure random generation', 'CWE-338'),
            (r'randint\s*\(\s*0\s*,\s*\d+\s*\)', 'Weak random key generation', 'CWE-338'),
        ]

        for pattern, desc, cwe in insecure_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = self._get_line_number(lines, match.start())
                self.findings.append(CryptoFinding(
                    finding_type='weak_key_generation',
                    severity='high',
                    file_path=file_path,
                    line_number=line_num,
                    description=f'Insecure key generation: {desc}',
                    code_snippet=self._get_code_snippet(lines, line_num),
                    recommendation='Use cryptographically secure random generation (os.urandom, secrets module)',
                    cwe_id=cwe
                ))

    def _analyze_key_storage(self, content: str, lines: List[str], file_path: str):
        """Analyze key storage practices."""
        # Check for proper key storage
        insecure_patterns = [
            (r'key\s*=\s*["\'][^"\']+["\']', 'Hardcoded cryptographic keys', 'CWE-798'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'Hardcoded secrets', 'CWE-798'),
            (r'password\s*=\s*["\'][^"\']+["\']', 'Hardcoded passwords', 'CWE-798'),
        ]

        for pattern, desc, cwe in insecure_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = self._get_line_number(lines, match.start())
                # Skip if in test files or comments
                if self._is_test_file(file_path) or self._is_in_comment(lines[line_num-1] if line_num > 0 else ''):
                    continue
                self.findings.append(CryptoFinding(
                    finding_type='insecure_key_storage',
                    severity='critical',
                    file_path=file_path,
                    line_number=line_num,
                    description=f'Insecure key storage: {desc}',
                    code_snippet=self._get_code_snippet(lines, line_num),
                    recommendation='Use environment variables, key management services, or secure vaults',
                    cwe_id=cwe
                ))

    def _analyze_key_rotation(self, content: str, lines: List[str], file_path: str):
        """Analyze key rotation practices."""
        # Look for key rotation mechanisms
        rotation_indicators = [
            r'rotate.*key',
            r'key.*rotation',
            r'expir.*key',
            r'key.*expir',
        ]

        has_rotation = any(re.search(pattern, content, re.IGNORECASE) for pattern in rotation_indicators)

        if not has_rotation and self._contains_crypto_operations(content):
            self.findings.append(CryptoFinding(
                finding_type='missing_key_rotation',
                severity='medium',
                file_path=file_path,
                line_number=1,
                description='No key rotation mechanism detected',
                code_snippet='',
                recommendation='Implement automated key rotation policies and procedures',
                cwe_id='CWE-320'
            ))

    def _analyze_key_derivation(self, content: str, lines: List[str], file_path: str):
        """Analyze key derivation functions."""
        # Check for secure KDF usage
        secure_kdf = [
            r'hkdf\.HKDF',
            r'pbkdf2\.PBKDF2HMAC',
            r'scrypt',
            r'bcrypt',
            r'argon2',
        ]

        weak_kdf = [
            r'md5\s*\(',
            r'sha1\s*\(',
            r'hashlib\.md5',
            r'hashlib\.sha1',
        ]

        has_secure_kdf = any(re.search(pattern, content, re.IGNORECASE) for pattern in secure_kdf)
        has_weak_kdf = any(re.search(pattern, content, re.IGNORECASE) for pattern in weak_kdf)

        if has_weak_kdf and not has_secure_kdf:
            for pattern in weak_kdf:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = self._get_line_number(lines, match.start())
                    self.findings.append(CryptoFinding(
                        finding_type='weak_key_derivation',
                        severity='high',
                        file_path=file_path,
                        line_number=line_num,
                        description='Weak key derivation function detected',
                        code_snippet=self._get_code_snippet(lines, line_num),
                        recommendation='Use PBKDF2, HKDF, scrypt, bcrypt, or Argon2 for key derivation',
                        cwe_id='CWE-916'
                    ))

    def _contains_crypto_operations(self, content: str) -> bool:
        """Check if file contains cryptographic operations."""
        crypto_indicators = [
            r'encrypt', r'decrypt', r'cipher', r'hash', r'sign', r'verify',
            r'cryptography', r'key', r'secret', r'token'
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in crypto_indicators)

    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file."""
        code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.cs', '.php', '.rb'}
        return Path(file_path).suffix.lower() in code_extensions

    def _is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        path = Path(file_path)
        return 'test' in path.name.lower() or 'spec' in path.name.lower()

    def _is_in_comment(self, line: str) -> bool:
        """Check if line is in a comment."""
        return line.strip().startswith('#') or line.strip().startswith('//')

    def _get_line_number(self, lines: List[str], char_pos: int) -> int:
        """Get line number from character position."""
        current_pos = 0
        for i, line in enumerate(lines):
            current_pos += len(line) + 1  # +1 for newline
            if current_pos > char_pos:
                return i + 1
        return len(lines)

    def _get_code_snippet(self, lines: List[str], line_num: int, context: int = 2) -> str:
        """Get code snippet around line number."""
        start = max(0, line_num - context - 1)
        end = min(len(lines), line_num + context)
        snippet_lines = []
        for i in range(start, end):
            marker = ">>> " if i + 1 == line_num else "    "
            snippet_lines.append(f"{marker}{i+1:4d}: {lines[i]}")
        return '\n'.join(snippet_lines)