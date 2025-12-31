"""
Repository Intelligence Scanner - Repository Manager

Main orchestration class for repository operations across all supported types.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import redis
from ray import init as ray_init, remote

from .interfaces import (
    RepositoryProvider, RepositoryHandle, RepositoryInfo, FileInfo,
    RepositoryType, CachingStrategy, RedisCachingStrategy, FileSystemCachingStrategy
)
from .git_provider import GitRepositoryProvider
from .cloud_provider import CloudRepositoryProvider

logger = logging.getLogger(__name__)


class RepositoryManager:
    """
    Main repository management class providing unified access to repositories
    of all supported types with caching, authentication, and distributed processing.
    """

    def __init__(self,
                 cache_dir: Optional[Path] = None,
                 redis_url: Optional[str] = None,
                 enable_ray: bool = False,
                 providers: Optional[List[Type[RepositoryProvider]]] = None):
        """
        Initialize repository manager.

        Args:
            cache_dir: Directory for file system caching
            redis_url: Redis URL for distributed caching
            enable_ray: Enable Ray for distributed processing
            providers: Custom repository providers
        """
        self.cache_dir = cache_dir or Path.home() / '.cache' / 'repo_scanner'
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize caching
        if redis_url:
            import redis
            self.cache = RedisCachingStrategy(redis.from_url(redis_url))
        else:
            self.cache = FileSystemCachingStrategy(self.cache_dir / 'repositories')

        # Initialize providers
        self.providers: Dict[RepositoryType, RepositoryProvider] = {}

        # Default providers
        default_providers = [
            GitRepositoryProvider,
            CloudRepositoryProvider
        ]

        if providers:
            default_providers.extend(providers)

        for provider_class in default_providers:
            provider = provider_class(cache_dir=self.cache_dir, redis_client=self.cache)
            for repo_type in provider.supported_types:
                self.providers[repo_type] = provider

        # Initialize Ray if enabled
        self.ray_enabled = enable_ray
        if enable_ray:
            ray_init(ignore_reinit_error=True)

        logger.info(f"RepositoryManager initialized with {len(self.providers)} providers")

    async def get_repository(self, url: str,
                           credentials: Optional[Dict[str, Any]] = None,
                           local_path: Optional[Path] = None,
                           force_refresh: bool = False) -> Path:
        """
        Get repository at specified location, using cache when possible.

        Args:
            url: Repository URL
            credentials: Authentication credentials
            local_path: Local path for repository
            force_refresh: Force re-download/clone

        Returns:
            Path to local repository
        """
        # Detect repository type
        repo_type = await self._detect_repository_type(url)

        # Get appropriate provider
        provider = self.providers.get(repo_type)
        if not provider:
            raise ValueError(f"No provider available for repository type: {repo_type}")

        # Create repository handle
        handle = await provider.create_handle(url, credentials=credentials)

        # Set local path
        if not local_path:
            local_path = self._get_cache_path(handle)

        # Check cache unless force refresh
        cache_key = f"repo:{handle.url}:{handle.metadata.get('default_branch', 'main')}"
        if not force_refresh:
            cached_path = await self._get_cached_repository(cache_key)
            if cached_path and cached_path.exists():
                logger.info(f"Using cached repository: {cached_path}")
                return cached_path

        # Clone or download repository
        try:
            local_repo_path = await provider.clone(handle, local_path)

            # Cache the result
            await self._cache_repository(cache_key, local_repo_path)

            logger.info(f"Successfully retrieved repository: {url} -> {local_repo_path}")
            return local_repo_path

        except Exception as e:
            logger.error(f"Failed to retrieve repository {url}: {e}")
            raise

    async def get_repository_info(self, url: str,
                                credentials: Optional[Dict[str, Any]] = None) -> RepositoryInfo:
        """
        Get comprehensive repository information without cloning.

        Args:
            url: Repository URL
            credentials: Authentication credentials

        Returns:
            RepositoryInfo object
        """
        repo_type = await self._detect_repository_type(url)
        provider = self.providers.get(repo_type)

        if not provider:
            raise ValueError(f"No provider for type: {repo_type}")

        handle = await provider.create_handle(url, credentials=credentials)
        return await provider.get_info(handle)

    async def list_repository_files(self, url: str,
                                  credentials: Optional[Dict[str, Any]] = None,
                                  pattern: Optional[str] = None) -> List[FileInfo]:
        """
        List files in repository.

        Args:
            url: Repository URL
            credentials: Authentication credentials
            pattern: File pattern filter

        Returns:
            List of FileInfo objects
        """
        local_path = await self.get_repository(url, credentials)
        repo_type = await self._detect_repository_type(url)
        provider = self.providers.get(repo_type)

        return await provider.list_files(local_path, pattern)

    async def read_repository_file(self, url: str, file_path: str,
                                 credentials: Optional[Dict[str, Any]] = None) -> str:
        """
        Read file content from repository.

        Args:
            url: Repository URL
            file_path: Path to file within repository
            credentials: Authentication credentials

        Returns:
            File content as string
        """
        local_path = await self.get_repository(url, credentials)
        repo_type = await self._detect_repository_type(url)
        provider = self.providers.get(repo_type)

        return await provider.read_file(local_path, file_path)

    async def validate_credentials(self, url: str,
                                 credentials: Dict[str, Any]) -> bool:
        """
        Validate repository credentials.

        Args:
            url: Repository URL
            credentials: Credentials to validate

        Returns:
            True if credentials are valid
        """
        repo_type = await self._detect_repository_type(url)
        provider = self.providers.get(repo_type)

        if not provider:
            return False

        handle = await provider.create_handle(url, credentials=credentials)
        return await provider.validate_credentials(handle)

    async def cleanup_repository(self, url: str,
                               credentials: Optional[Dict[str, Any]] = None) -> None:
        """
        Clean up local repository copy.

        Args:
            url: Repository URL
            credentials: Authentication credentials
        """
        try:
            local_path = await self.get_repository(url, credentials)
            repo_type = await self._detect_repository_type(url)
            provider = self.providers.get(repo_type)

            await provider.cleanup(local_path)

            # Remove from cache
            cache_key = f"repo:{url}"
            await self.cache.delete(cache_key)

            logger.info(f"Cleaned up repository: {url}")

        except Exception as e:
            logger.warning(f"Failed to cleanup repository {url}: {e}")

    async def _detect_repository_type(self, url: str) -> RepositoryType:
        """Detect repository type from URL."""
        for repo_type, provider in self.providers.items():
            if await provider.can_handle(url):
                return repo_type

        # Check for local directory
        if Path(url).is_dir():
            return RepositoryType.LOCAL

        raise ValueError(f"Unsupported repository URL: {url}")

    def _get_cache_path(self, handle: RepositoryHandle) -> Path:
        """Generate cache path for repository."""
        import hashlib

        # Create deterministic cache key
        key_components = [
            handle.url,
            handle.metadata.get('default_branch', 'main'),
            str(handle.metadata.get('commit_hash', ''))
        ]
        cache_key = '|'.join(key_components)
        hash_key = hashlib.sha256(cache_key.encode()).hexdigest()[:16]

        return self.cache_dir / 'repos' / hash_key / handle.metadata['name']

    async def _get_cached_repository(self, cache_key: str) -> Optional[Path]:
        """Get cached repository path."""
        cached_data = await self.cache.get(cache_key)
        if cached_data and isinstance(cached_data, dict):
            path = Path(cached_data.get('path', ''))
            if path.exists():
                return path
        return None

    async def _cache_repository(self, cache_key: str, repo_path: Path) -> None:
        """Cache repository information."""
        cache_data = {
            'path': str(repo_path),
            'timestamp': asyncio.get_event_loop().time()
        }
        await self.cache.set(cache_key, cache_data, ttl=3600)  # 1 hour TTL

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        # This would depend on cache implementation
        return {
            'cache_type': type(self.cache).__name__,
            'cache_dir': str(self.cache_dir)
        }

    async def clear_cache(self) -> None:
        """Clear all cached repositories."""
        await self.cache.clear()
        logger.info("Repository cache cleared")

    async def close(self) -> None:
        """Clean up resources."""
        # Close any open connections
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                await provider.close()

        if hasattr(self.cache, 'close'):
            await self.cache.close()

        logger.info("RepositoryManager closed")


# Distributed processing functions for Ray
@remote
def clone_repository_distributed(url: str, credentials: dict, local_path: str) -> str:
    """Distributed repository cloning."""
    import asyncio
    manager = RepositoryManager()
    try:
        repo_path = asyncio.run(manager.get_repository(url, credentials, Path(local_path)))
        return str(repo_path)
    finally:
        asyncio.run(manager.close())


@remote
def analyze_repository_distributed(repo_path: str, analysis_config: dict) -> dict:
    """Distributed repository analysis."""
    # This would integrate with the analysis engine
    # For now, return placeholder
    return {
        'repo_path': repo_path,
        'config': analysis_config,
        'status': 'completed'
    }