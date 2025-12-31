"""
Repository Intelligence Scanner - Repository Abstraction Layer

This module provides a unified interface for accessing repositories regardless of type
(Git, SVN, Mercurial, local directories, cloud-hosted repositories).

Key Features:
- Unified repository access API
- Incremental cloning/pulling with caching
- Authentication support (SSH, tokens, certificates)
- Multi-protocol support (Git, SVN, Mercurial, REST APIs)
- Performance optimizations for large repositories
"""

import asyncio
import hashlib
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Protocol, Union
from urllib.parse import urlparse

import aiofiles
import aiohttp
import redis
from fsspec import filesystem
from pygit2 import Repository as GitRepository, clone_repository, init_repository
from ray import remote
import kubernetes as k8s

logger = logging.getLogger(__name__)


@dataclass
class RepositoryMetadata:
    """Metadata for a repository."""
    url: str
    type: str  # 'git', 'svn', 'mercurial', 'local', 'cloud'
    name: str
    owner: Optional[str] = None
    branch: str = 'main'
    commit_hash: Optional[str] = None
    size_bytes: Optional[int] = None
    file_count: Optional[int] = None
    last_modified: Optional[str] = None


@dataclass
class RepositoryCredentials:
    """Credentials for repository access."""
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    ssh_key_path: Optional[str] = None
    ssh_key_passphrase: Optional[str] = None


class RepositoryProvider(ABC):
    """Abstract base class for repository providers."""

    @abstractmethod
    async def clone_or_pull(self, metadata: RepositoryMetadata,
                           credentials: Optional[RepositoryCredentials],
                           local_path: Path) -> Path:
        """Clone or pull repository to local path."""
        pass

    @abstractmethod
    async def get_metadata(self, url: str,
                          credentials: Optional[RepositoryCredentials]) -> RepositoryMetadata:
        """Get repository metadata without cloning."""
        pass

    @abstractmethod
    async def list_files(self, local_path: Path) -> List[Path]:
        """List all files in the repository."""
        pass

    @abstractmethod
    async def get_file_content(self, local_path: Path, file_path: str) -> str:
        """Get content of a specific file."""
        pass


class GitRepositoryProvider(RepositoryProvider):
    """Git repository provider using pygit2."""

    def __init__(self, cache_dir: Optional[Path] = None, redis_client: Optional[redis.Redis] = None):
        self.cache_dir = cache_dir or Path(tempfile.gettempdir()) / 'repo_cache'
        self.cache_dir.mkdir(exist_ok=True)
        self.redis = redis_client

    async def clone_or_pull(self, metadata: RepositoryMetadata,
                           credentials: Optional[RepositoryCredentials],
                           local_path: Path) -> Path:
        """Clone or pull Git repository."""
        cache_key = f"git:{metadata.url}:{metadata.branch}"
        cached_path = self._get_cache_path(cache_key)

        if self._is_cache_valid(cached_path, metadata):
            logger.info(f"Using cached repository: {cached_path}")
            return cached_path

        # Perform clone/pull
        try:
            if credentials and credentials.ssh_key_path:
                # SSH clone
                repo_path = await self._clone_ssh(metadata, credentials, local_path)
            else:
                # HTTPS clone
                repo_path = await self._clone_https(metadata, credentials, local_path)

            # Cache the result
            self._update_cache(cache_key, repo_path)
            return repo_path

        except Exception as e:
            logger.error(f"Failed to clone/pull repository: {e}")
            raise

    async def _clone_ssh(self, metadata: RepositoryMetadata,
                        credentials: RepositoryCredentials, local_path: Path) -> Path:
        """Clone via SSH."""
        # Implementation for SSH cloning with pygit2
        # This would use pygit2's SSH callbacks
        raise NotImplementedError("SSH cloning not yet implemented")

    async def _clone_https(self, metadata: RepositoryMetadata,
                          credentials: Optional[RepositoryCredentials], local_path: Path) -> Path:
        """Clone via HTTPS."""
        # Use pygit2 for cloning
        callbacks = None
        if credentials and credentials.token:
            # Set up credentials callback
            pass

        repo_path = local_path / metadata.name
        clone_repository(metadata.url, str(repo_path), callbacks=callbacks)
        return repo_path

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache path for repository."""
        key_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
        return self.cache_dir / key_hash

    def _is_cache_valid(self, cache_path: Path, metadata: RepositoryMetadata) -> bool:
        """Check if cached repository is still valid."""
        if not cache_path.exists():
            return False

        try:
            repo = GitRepository(str(cache_path))
            # Check if commit hash matches
            if metadata.commit_hash:
                head_commit = repo.head.peel().id.hex
                return head_commit == metadata.commit_hash
            return True
        except:
            return False

    def _update_cache(self, cache_key: str, repo_path: Path):
        """Update cache with new repository."""
        if self.redis:
            self.redis.setex(cache_key, 3600, str(repo_path))  # 1 hour TTL

    async def get_metadata(self, url: str,
                          credentials: Optional[RepositoryCredentials]) -> RepositoryMetadata:
        """Get Git repository metadata."""
        # Parse URL to extract owner/repo
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 2:
            owner, repo = path_parts[-2], path_parts[-1]
            if repo.endswith('.git'):
                repo = repo[:-4]
        else:
            owner, repo = None, Path(url).name

        return RepositoryMetadata(
            url=url,
            type='git',
            name=repo,
            owner=owner,
            branch='main'  # Default, would be detected from remote
        )

    async def list_files(self, local_path: Path) -> List[Path]:
        """List all files in Git repository."""
        files = []
        for root, dirs, filenames in os.walk(local_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')

            for filename in filenames:
                files.append(Path(root) / filename)
        return files

    async def get_file_content(self, local_path: Path, file_path: str) -> str:
        """Get content of a file in Git repository."""
        full_path = local_path / file_path
        async with aiofiles.open(full_path, 'r', encoding='utf-8') as f:
            return await f.read()


class CloudRepositoryProvider(RepositoryProvider):
    """Cloud-hosted repository provider (GitHub, GitLab, Bitbucket)."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def clone_or_pull(self, metadata: RepositoryMetadata,
                           credentials: Optional[RepositoryCredentials],
                           local_path: Path) -> Path:
        """Download repository archive from cloud provider."""
        # Implementation for downloading zip/tar archives via REST APIs
        raise NotImplementedError("Cloud repository cloning not yet implemented")

    async def get_metadata(self, url: str,
                          credentials: Optional[RepositoryCredentials]) -> RepositoryMetadata:
        """Get metadata from cloud provider API."""
        # Parse platform from URL
        parsed = urlparse(url)
        if 'github.com' in parsed.netloc:
            return await self._get_github_metadata(url, credentials)
        elif 'gitlab.com' in parsed.netloc:
            return await self._get_gitlab_metadata(url, credentials)
        else:
            raise ValueError(f"Unsupported cloud provider: {parsed.netloc}")

    async def _get_github_metadata(self, url: str,
                                  credentials: Optional[RepositoryCredentials]) -> RepositoryMetadata:
        """Get metadata from GitHub API."""
        # Extract owner/repo from URL
        path_parts = urlparse(url).path.strip('/').split('/')
        owner, repo = path_parts[0], path_parts[1]

        headers = {}
        if credentials and credentials.token:
            headers['Authorization'] = f'token {credentials.token}'

        async with self.session.get(f'https://api.github.com/repos/{owner}/{repo}',
                                   headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return RepositoryMetadata(
                    url=url,
                    type='cloud',
                    name=repo,
                    owner=owner,
                    branch=data.get('default_branch', 'main'),
                    size_bytes=data.get('size', 0) * 1024,  # GitHub size is in KB
                    last_modified=data.get('updated_at')
                )
            else:
                raise ValueError(f"Failed to fetch GitHub metadata: {response.status}")

    async def _get_gitlab_metadata(self, url: str,
                                  credentials: Optional[RepositoryCredentials]) -> RepositoryMetadata:
        """Get metadata from GitLab API."""
        # Similar implementation for GitLab
        raise NotImplementedError("GitLab metadata not yet implemented")

    async def list_files(self, local_path: Path) -> List[Path]:
        """List files in downloaded repository."""
        return await GitRepositoryProvider().list_files(local_path)

    async def get_file_content(self, local_path: Path, file_path: str) -> str:
        """Get file content from downloaded repository."""
        return await GitRepositoryProvider().get_file_content(local_path, file_path)


from .manager import RepositoryManager


# Ray remote functions for distributed processing
@remote
def clone_repository_distributed(url: str, credentials: dict, local_path: str) -> str:
    """Distributed repository cloning."""
    # Implementation for Ray distributed cloning
    pass


@remote
def analyze_repository_distributed(repo_path: str, analysis_config: dict) -> dict:
    """Distributed repository analysis."""
    # Implementation for Ray distributed analysis
    pass