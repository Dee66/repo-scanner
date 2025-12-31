"""
Repository Intelligence Scanner - Repository Interfaces

This module defines the core interfaces and protocols for repository operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol
from enum import Enum


class RepositoryType(Enum):
    """Supported repository types."""
    GIT = "git"
    SVN = "svn"
    MERCURIAL = "mercurial"
    LOCAL = "local"
    CLOUD = "cloud"


class AuthenticationMethod(Enum):
    """Supported authentication methods."""
    NONE = "none"
    BASIC = "basic"
    TOKEN = "token"
    SSH = "ssh"
    OAUTH = "oauth"


@dataclass
class FileInfo:
    """Information about a file in the repository."""
    path: Path
    size: int
    modified_time: float
    is_binary: bool
    hash: Optional[str] = None


@dataclass
class RepositoryInfo:
    """Comprehensive repository information."""
    url: str
    type: RepositoryType
    name: str
    owner: Optional[str]
    description: Optional[str]
    default_branch: str
    branches: List[str]
    tags: List[str]
    commit_count: int
    contributor_count: int
    size_bytes: int
    file_count: int
    language_stats: Dict[str, int]
    last_commit: Optional[Dict[str, Any]]
    created_at: Optional[str]
    updated_at: Optional[str]


class RepositoryOperations(Protocol):
    """Protocol for repository operations."""

    async def initialize(self, url: str, **kwargs) -> 'RepositoryHandle':
        """Initialize repository access."""
        ...

    async def clone(self, handle: 'RepositoryHandle', local_path: Path) -> Path:
        """Clone repository to local path."""
        ...

    async def pull(self, handle: 'RepositoryHandle', local_path: Path) -> None:
        """Pull latest changes."""
        ...

    async def get_info(self, handle: 'RepositoryHandle') -> RepositoryInfo:
        """Get comprehensive repository information."""
        ...

    async def list_files(self, local_path: Path, pattern: Optional[str] = None) -> List[FileInfo]:
        """List files with optional pattern matching."""
        ...

    async def read_file(self, local_path: Path, file_path: str) -> str:
        """Read file content."""
        ...

    async def get_history(self, local_path: Path, file_path: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """Get commit history."""
        ...

    async def cleanup(self, local_path: Path) -> None:
        """Clean up local repository copy."""
        ...


class RepositoryHandle:
    """Handle for repository operations."""

    def __init__(self, url: str, type: RepositoryType, metadata: Dict[str, Any]):
        self.url = url
        self.type = type
        self.metadata = metadata
        self.credentials: Optional[Dict[str, Any]] = None

    def set_credentials(self, method: AuthenticationMethod, **credentials):
        """Set authentication credentials."""
        self.credentials = {
            'method': method,
            **credentials
        }


class RepositoryProvider(ABC):
    """Abstract base class for repository providers."""

    @property
    @abstractmethod
    def supported_types(self) -> List[RepositoryType]:
        """Return list of supported repository types."""
        pass

    @abstractmethod
    async def can_handle(self, url: str) -> bool:
        """Check if provider can handle the given URL."""
        pass

    @abstractmethod
    async def create_handle(self, url: str, **kwargs) -> RepositoryHandle:
        """Create repository handle."""
        pass

    @abstractmethod
    async def validate_credentials(self, handle: RepositoryHandle) -> bool:
        """Validate repository credentials."""
        pass


class CachingStrategy(ABC):
    """Abstract base class for caching strategies."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get cached item."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached item with optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete cached item."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached items."""
        pass


class RedisCachingStrategy(CachingStrategy):
    """Redis-based caching strategy."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[Any]:
        """Get cached item from Redis."""
        import json
        data = self.redis.get(key)
        return json.loads(data) if data else None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached item in Redis."""
        import json
        data = json.dumps(value)
        if ttl:
            self.redis.setex(key, ttl, data)
        else:
            self.redis.set(key, data)

    async def delete(self, key: str) -> None:
        """Delete cached item from Redis."""
        self.redis.delete(key)

    async def clear(self) -> None:
        """Clear all cached items."""
        self.redis.flushdb()


class FileSystemCachingStrategy(CachingStrategy):
    """File system-based caching strategy."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    async def get(self, key: str) -> Optional[Any]:
        """Get cached item from file system."""
        import json
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            async with aiofiles.open(cache_file, 'r') as f:
                return json.loads(await f.read())
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached item in file system."""
        import json
        cache_file = self.cache_dir / f"{key}.json"
        async with aiofiles.open(cache_file, 'w') as f:
            await f.write(json.dumps(value))

    async def delete(self, key: str) -> None:
        """Delete cached item from file system."""
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            cache_file.unlink()

    async def clear(self) -> None:
        """Clear all cached items."""
        import shutil
        shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(exist_ok=True)