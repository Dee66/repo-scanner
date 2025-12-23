"""Custom exceptions for Repository Intelligence Scanner."""

from typing import Optional, Dict, Any


class ScannerError(Exception):
    """Base exception for scanner operations."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class RepositoryDiscoveryError(ScannerError):
    """Raised when repository discovery fails."""
    pass


class AnalysisError(ScannerError):
    """Raised when analysis pipeline fails."""
    pass


class OutputGenerationError(ScannerError):
    """Raised when output generation fails."""
    pass


class ValidationError(ScannerError):
    """Raised when input validation fails."""
    pass


class ConfigurationError(ScannerError):
    """Raised when configuration is invalid."""
    pass


class FileAccessError(ScannerError):
    """Raised when file access operations fail."""
    
    def __init__(self, message: str, file_path: str, operation: str):
        super().__init__(message, {"file_path": file_path, "operation": operation})
        self.file_path = file_path
        self.operation = operation


class GitError(ScannerError):
    """Raised when git operations fail."""
    
    def __init__(self, message: str, command: str, return_code: int):
        super().__init__(message, {"command": command, "return_code": return_code})
        self.command = command
        self.return_code = return_code