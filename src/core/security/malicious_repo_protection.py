"""
Malicious Repository Protection Module

Protects the scanner from malicious repository content including:
- Symlink attacks
- Path traversal
- Resource bombs (large files, deep nesting)
- Malformed content
"""

import logging
from pathlib import Path
from typing import Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SecurityLimits:
    """Security limits for repository scanning."""
    max_file_size_bytes: int = 10 * 1024 * 1024  # 10MB
    max_line_count: int = 100_000
    max_directory_depth: int = 20
    max_files_total: int = 50_000
    max_filename_length: int = 255
    forbid_symlinks: bool = True
    forbid_device_files: bool = True
    forbid_special_files: bool = True


class SecurityViolation(Exception):
    """Raised when a security policy is violated."""
    pass


class MaliciousRepoProtection:
    """
    Comprehensive protection against malicious repository content.
    
    This class validates files and directories before analysis to prevent:
    - Symlink attacks pointing to sensitive system files
    - Path traversal attacks escaping the repository directory
    - Resource exhaustion from large files or deep nesting
    - Special files (devices, sockets, etc.) that could compromise the host
    """
    
    def __init__(self, repo_root: Path, limits: Optional[SecurityLimits] = None):
        """
        Initialize protection for a repository.
        
        Args:
            repo_root: Root directory of the repository being analyzed
            limits: Security limits to enforce (uses defaults if None)
        """
        self.repo_root = repo_root.resolve()
        self.limits = limits or SecurityLimits()
        self.files_checked = 0
        self.violations_found: Set[str] = set()
        
    def validate_file_safe(self, file_path: Path) -> bool:
        """
        Validate that a file is safe to analyze.
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            True if file is safe
            
        Raises:
            SecurityViolation: If file violates security policies
        """
        self.files_checked += 1
        
        # Check total file count
        if self.files_checked > self.limits.max_files_total:
            raise SecurityViolation(
                f"Repository exceeds maximum file count: {self.limits.max_files_total}"
            )
        
        # Check filename length
        if len(file_path.name) > self.limits.max_filename_length:
            raise SecurityViolation(
                f"Filename too long: {file_path.name[:50]}... "
                f"(>{self.limits.max_filename_length} chars)"
            )
        
        # Check for symlinks
        if file_path.is_symlink() and self.limits.forbid_symlinks:
            violation = f"Symlink forbidden: {file_path}"
            self.violations_found.add(violation)
            raise SecurityViolation(violation)
        
        # Check for special files
        if self.limits.forbid_special_files:
            if file_path.is_socket():
                raise SecurityViolation(f"Socket file forbidden: {file_path}")
            if file_path.is_fifo():
                raise SecurityViolation(f"FIFO file forbidden: {file_path}")
        
        # Check for device files
        if self.limits.forbid_device_files:
            if file_path.is_block_device():
                raise SecurityViolation(f"Block device forbidden: {file_path}")
            if file_path.is_char_device():
                raise SecurityViolation(f"Character device forbidden: {file_path}")
        
        # Check path traversal - ensure file is within repo root
        try:
            resolved_path = file_path.resolve()
            if not str(resolved_path).startswith(str(self.repo_root)):
                raise SecurityViolation(
                    f"Path traversal detected: {file_path} resolves outside repository"
                )
        except (OSError, RuntimeError) as e:
            raise SecurityViolation(f"Cannot resolve path: {file_path}: {e}")
        
        # Check directory depth
        try:
            relative_path = file_path.relative_to(self.repo_root)
            depth = len(relative_path.parts)
            if depth > self.limits.max_directory_depth:
                raise SecurityViolation(
                    f"Directory nesting too deep: {depth} > {self.limits.max_directory_depth}"
                )
        except ValueError:
            raise SecurityViolation(f"File not in repository: {file_path}")
        
        # Check file size (only for regular files)
        if file_path.is_file():
            try:
                file_size = file_path.stat().st_size
                if file_size > self.limits.max_file_size_bytes:
                    raise SecurityViolation(
                        f"File too large: {file_path} "
                        f"({file_size / 1024 / 1024:.1f}MB > "
                        f"{self.limits.max_file_size_bytes / 1024 / 1024:.1f}MB)"
                    )
            except OSError as e:
                raise SecurityViolation(f"Cannot stat file: {file_path}: {e}")
        
        return True
    
    def validate_file_content_safe(self, file_path: Path, content: str) -> bool:
        """
        Validate that file content is safe to process.
        
        Args:
            file_path: Path to file
            content: File content as string
            
        Returns:
            True if content is safe
            
        Raises:
            SecurityViolation: If content violates security policies
        """
        # Check line count
        line_count = content.count('\n')
        if line_count > self.limits.max_line_count:
            raise SecurityViolation(
                f"File has too many lines: {file_path} "
                f"({line_count:,} > {self.limits.max_line_count:,})"
            )
        
        # Check for suspiciously long lines (could be obfuscation)
        max_line_length = 10_000
        for i, line in enumerate(content.split('\n')[:100], 1):  # Check first 100 lines
            if len(line) > max_line_length:
                raise SecurityViolation(
                    f"Suspiciously long line in {file_path}:{i} "
                    f"({len(line):,} > {max_line_length:,} chars)"
                )
        
        return True
    
    def validate_directory_safe(self, dir_path: Path) -> bool:
        """
        Validate that a directory is safe to traverse.
        
        Args:
            dir_path: Path to directory
            
        Returns:
            True if directory is safe
            
        Raises:
            SecurityViolation: If directory violates security policies
        """
        # Check if symlink
        if dir_path.is_symlink() and self.limits.forbid_symlinks:
            raise SecurityViolation(f"Symlink directory forbidden: {dir_path}")
        
        # Check path traversal
        resolved_path = dir_path.resolve()
        if not str(resolved_path).startswith(str(self.repo_root)):
            raise SecurityViolation(
                f"Path traversal detected: {dir_path} resolves outside repository"
            )
        
        return True
    
    def get_violation_summary(self) -> dict:
        """
        Get summary of violations found during scanning.
        
        Returns:
            Dictionary with violation statistics
        """
        return {
            "files_checked": self.files_checked,
            "violations_found": len(self.violations_found),
            "violations": list(self.violations_found)
        }


def get_malicious_protection(repo_root: Path, 
                            limits: Optional[SecurityLimits] = None) -> MaliciousRepoProtection:
    """
    Get malicious repository protection instance.
    
    Args:
        repo_root: Root directory of repository
        limits: Optional custom security limits
        
    Returns:
        MaliciousRepoProtection instance
    """
    return MaliciousRepoProtection(repo_root, limits)
