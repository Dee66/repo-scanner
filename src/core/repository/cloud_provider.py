"""
Repository Intelligence Scanner - Cloud Repository Provider

Provider for cloud-hosted repositories (GitHub, GitLab, Bitbucket) using REST APIs.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp

from .interfaces import (
    RepositoryProvider, RepositoryHandle, RepositoryInfo, FileInfo,
    RepositoryType, AuthenticationMethod
)

logger = logging.getLogger(__name__)


class CloudRepositoryProvider(RepositoryProvider):
    """Cloud-hosted repository provider."""

    def __init__(self, session: Optional[aiohttp.ClientSession] = None,
                 cache_dir: Optional[Path] = None,
                 redis_client: Optional[Any] = None):
        self._session = session
        self.cache_dir = cache_dir
        self.redis = redis_client

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    @property
    def supported_types(self) -> List[RepositoryType]:
        """Return supported repository types."""
        return [RepositoryType.CLOUD]

    async def can_handle(self, url: str) -> bool:
        """Check if URL is a cloud-hosted repository."""
        parsed = urlparse(url)

        if parsed.scheme not in ('http', 'https'):
            return False

        # Check for known cloud providers
        cloud_domains = [
            'github.com', 'gitlab.com', 'bitbucket.org',
            'codeberg.org', 'sourceforge.net', 'launchpad.net'
        ]

        return any(domain in parsed.netloc for domain in cloud_domains)

    async def create_handle(self, url: str, **kwargs) -> RepositoryHandle:
        """Create cloud repository handle."""
        platform = self._detect_platform(url)
        metadata = await self._extract_metadata(url, platform, kwargs.get('credentials'))

        handle = RepositoryHandle(url, RepositoryType.CLOUD, metadata)
        handle.metadata['platform'] = platform

        if 'credentials' in kwargs:
            creds = kwargs['credentials']
            method = creds.get('method', AuthenticationMethod.TOKEN)
            handle.set_credentials(method, **creds)

        return handle

    async def validate_credentials(self, handle: RepositoryHandle) -> bool:
        """Validate cloud repository credentials."""
        platform = handle.metadata.get('platform')
        if not platform:
            return False

        try:
            # Make a simple API call to validate credentials
            if platform == 'github':
                return await self._validate_github_credentials(handle)
            elif platform == 'gitlab':
                return await self._validate_gitlab_credentials(handle)
            elif platform == 'bitbucket':
                return await self._validate_bitbucket_credentials(handle)
            return False
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return False

    async def clone(self, handle: RepositoryHandle, local_path: Path) -> Path:
        """Clone cloud repository by downloading archive."""
        platform = handle.metadata.get('platform')
        repo_path = local_path / handle.metadata['name']
        repo_path.mkdir(parents=True, exist_ok=True)

        try:
            if platform == 'github':
                await self._download_github_archive(handle, repo_path)
            elif platform == 'gitlab':
                await self._download_gitlab_archive(handle, repo_path)
            elif platform == 'bitbucket':
                await self._download_bitbucket_archive(handle, repo_path)
            else:
                raise ValueError(f"Unsupported platform: {platform}")

            logger.info(f"Successfully downloaded {handle.url} to {repo_path}")
            return repo_path

        except Exception as e:
            logger.error(f"Failed to download repository: {e}")
            raise

    async def pull(self, handle: RepositoryHandle, local_path: Path) -> None:
        """Pull latest changes (re-download archive for cloud repos)."""
        # For cloud repos, we re-download since we don't have git history
        await self.clone(handle, local_path.parent)

    async def get_info(self, handle: RepositoryHandle) -> RepositoryInfo:
        """Get comprehensive repository information from cloud API."""
        platform = handle.metadata.get('platform')

        if platform == 'github':
            return await self._get_github_info(handle)
        elif platform == 'gitlab':
            return await self._get_gitlab_info(handle)
        elif platform == 'bitbucket':
            return await self._get_bitbucket_info(handle)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    async def list_files(self, local_path: Path, pattern: Optional[str] = None) -> List[FileInfo]:
        """List files in downloaded repository."""
        import os
        import stat

        files = []

        for root, dirs, filenames in os.walk(local_path):
            for filename in filenames:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(local_path)

                # Apply pattern filter
                if pattern and not self._matches_pattern(str(rel_path), pattern):
                    continue

                try:
                    file_stat = file_path.stat()
                    is_binary = self._is_binary_file(file_path)

                    files.append(FileInfo(
                        path=rel_path,
                        size=file_stat.st_size,
                        modified_time=file_stat.st_mtime,
                        is_binary=is_binary
                    ))
                except OSError:
                    continue

        return files

    async def read_file(self, local_path: Path, file_path: str) -> str:
        """Read file content."""
        import aiofiles

        full_path = local_path / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            return await f.read()

    async def get_history(self, local_path: Path, file_path: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """Get commit history from cloud API."""
        # Cloud providers don't maintain local git history
        # This would need to be implemented via API calls
        raise NotImplementedError("Cloud repository history not yet implemented")

    async def cleanup(self, local_path: Path) -> None:
        """Clean up downloaded repository."""
        import shutil
        if local_path.exists():
            shutil.rmtree(local_path)

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _detect_platform(self, url: str) -> str:
        """Detect cloud platform from URL."""
        parsed = urlparse(url)

        if 'github.com' in parsed.netloc:
            return 'github'
        elif 'gitlab.com' in parsed.netloc:
            return 'gitlab'
        elif 'bitbucket.org' in parsed.netloc:
            return 'bitbucket'
        else:
            raise ValueError(f"Unsupported cloud platform: {parsed.netloc}")

    async def _extract_metadata(self, url: str, platform: str,
                               credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract metadata from cloud repository URL."""
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')

        metadata = {
            'url': url,
            'platform': platform,
            'owner': path_parts[0] if len(path_parts) > 0 else None,
            'name': path_parts[1] if len(path_parts) > 1 else Path(url).name,
            'default_branch': 'main'  # Will be updated from API
        }

        # Try to get additional metadata from API
        try:
            if platform == 'github':
                api_metadata = await self._get_github_repo_info(url, credentials)
                metadata.update(api_metadata)
        except Exception as e:
            logger.warning(f"Could not fetch API metadata: {e}")

        return metadata

    async def _get_github_repo_info(self, url: str,
                                   credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get repository info from GitHub API."""
        path_parts = urlparse(url).path.strip('/').split('/')
        owner, repo = path_parts[0], path_parts[1]

        headers = {'Accept': 'application/vnd.github.v3+json'}
        if credentials and credentials.get('token'):
            headers['Authorization'] = f'token {credentials["token"]}'

        async with self.session.get(f'https://api.github.com/repos/{owner}/{repo}',
                                   headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    'description': data.get('description'),
                    'default_branch': data.get('default_branch', 'main'),
                    'size_bytes': data.get('size', 0) * 1024,  # Size in KB
                    'stars': data.get('stargazers_count', 0),
                    'forks': data.get('forks_count', 0),
                    'language': data.get('language'),
                    'created_at': data.get('created_at'),
                    'updated_at': data.get('updated_at'),
                    'archived': data.get('archived', False)
                }
            else:
                logger.warning(f"GitHub API error: {response.status}")
                return {}

    async def _validate_github_credentials(self, handle: RepositoryHandle) -> bool:
        """Validate GitHub credentials."""
        owner = handle.metadata.get('owner')
        repo = handle.metadata.get('name')

        headers = {'Accept': 'application/vnd.github.v3+json'}
        if handle.credentials and handle.credentials.get('token'):
            headers['Authorization'] = f'token {handle.credentials["token"]}'

        async with self.session.get(f'https://api.github.com/repos/{owner}/{repo}',
                                   headers=headers) as response:
            return response.status == 200

    async def _validate_gitlab_credentials(self, handle: RepositoryHandle) -> bool:
        """Validate GitLab credentials."""
        # Implementation for GitLab
        return False  # Placeholder

    async def _validate_bitbucket_credentials(self, handle: RepositoryHandle) -> bool:
        """Validate Bitbucket credentials."""
        # Implementation for Bitbucket
        return False  # Placeholder

    async def _download_github_archive(self, handle: RepositoryHandle, repo_path: Path) -> None:
        """Download GitHub repository archive."""
        owner = handle.metadata.get('owner')
        repo = handle.metadata.get('name')
        branch = handle.metadata.get('default_branch', 'main')

        headers = {}
        if handle.credentials and handle.credentials.get('token'):
            headers['Authorization'] = f'token {handle.credentials["token"]}'

        archive_url = f'https://api.github.com/repos/{owner}/{repo}/zipball/{branch}'

        async with self.session.get(archive_url, headers=headers) as response:
            if response.status == 200:
                import zipfile
                import io

                # Download and extract zip
                zip_data = await response.read()
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_file:
                    # Extract to repo_path, stripping the top-level directory
                    for member in zip_file.namelist():
                        # Skip the root directory
                        if '/' in member:
                            parts = member.split('/', 1)
                            if len(parts) > 1:
                                target_path = repo_path / parts[1]
                                if not target_path.parent.exists():
                                    target_path.parent.mkdir(parents=True)
                                with open(target_path, 'wb') as f:
                                    f.write(zip_file.read(member))
            else:
                raise ValueError(f"Failed to download archive: {response.status}")

    async def _download_gitlab_archive(self, handle: RepositoryHandle, repo_path: Path) -> None:
        """Download GitLab repository archive."""
        # Implementation for GitLab archive download
        raise NotImplementedError("GitLab archive download not implemented")

    async def _download_bitbucket_archive(self, handle: RepositoryHandle, repo_path: Path) -> None:
        """Download Bitbucket repository archive."""
        # Implementation for Bitbucket archive download
        raise NotImplementedError("Bitbucket archive download not implemented")

    async def _get_github_info(self, handle: RepositoryHandle) -> RepositoryInfo:
        """Get comprehensive GitHub repository info."""
        metadata = handle.metadata

        # Get branches and tags
        branches = await self._get_github_branches(handle)
        tags = await self._get_github_tags(handle)

        return RepositoryInfo(
            url=handle.url,
            type=RepositoryType.CLOUD,
            name=metadata['name'],
            owner=metadata.get('owner'),
            description=metadata.get('description'),
            default_branch=metadata.get('default_branch', 'main'),
            branches=branches,
            tags=tags,
            commit_count=0,  # Would need separate API call
            contributor_count=0,  # Would need separate API call
            size_bytes=metadata.get('size_bytes', 0),
            file_count=0,  # Would need to count after download
            language_stats={},  # Would need languages API
            last_commit=None,  # Would need commits API
            created_at=metadata.get('created_at'),
            updated_at=metadata.get('updated_at')
        )

    async def _get_github_branches(self, handle: RepositoryHandle) -> List[str]:
        """Get GitHub repository branches."""
        owner = handle.metadata.get('owner')
        repo = handle.metadata.get('name')

        headers = {'Accept': 'application/vnd.github.v3+json'}
        if handle.credentials and handle.credentials.get('token'):
            headers['Authorization'] = f'token {handle.credentials["token"]}'

        async with self.session.get(f'https://api.github.com/repos/{owner}/{repo}/branches',
                                   headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return [branch['name'] for branch in data]
            return []

    async def _get_github_tags(self, handle: RepositoryHandle) -> List[str]:
        """Get GitHub repository tags."""
        owner = handle.metadata.get('owner')
        repo = handle.metadata.get('name')

        headers = {'Accept': 'application/vnd.github.v3+json'}
        if handle.credentials and handle.credentials.get('token'):
            headers['Authorization'] = f'token {handle.credentials["token"]}'

        async with self.session.get(f'https://api.github.com/repos/{owner}/{repo}/tags',
                                   headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return [tag['name'] for tag in data]
            return []

    async def _get_gitlab_info(self, handle: RepositoryHandle) -> RepositoryInfo:
        """Get GitLab repository info."""
        raise NotImplementedError("GitLab info not implemented")

    async def _get_bitbucket_info(self, handle: RepositoryHandle) -> RepositoryInfo:
        """Get Bitbucket repository info."""
        raise NotImplementedError("Bitbucket info not implemented")

    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """Check if path matches glob pattern."""
        import fnmatch
        return fnmatch.fnmatch(path, pattern)

    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except:
            return True