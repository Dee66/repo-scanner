"""
Repository Intelligence Scanner - Git Repository Provider

Specialized provider for Git repositories using pygit2 for high-performance operations.
"""

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiofiles
from pygit2 import Repository as GitRepository, clone_repository, init_repository, GitError
from pygit2 import Remote, RemoteCallbacks, Username, UserPass, Keypair, Object

from .interfaces import (
    RepositoryProvider, RepositoryHandle, RepositoryInfo, FileInfo,
    RepositoryType, AuthenticationMethod
)

logger = logging.getLogger(__name__)


class GitRemoteCallbacks(RemoteCallbacks):
    """Custom remote callbacks for Git operations."""

    def __init__(self, credentials: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.credentials = credentials or {}

    def credentials(self, url, username_from_url, allowed_types):
        """Provide credentials for Git operations."""
        method = self.credentials.get('method', AuthenticationMethod.NONE)

        if method == AuthenticationMethod.SSH:
            ssh_key = self.credentials.get('ssh_key_path')
            ssh_passphrase = self.credentials.get('ssh_key_passphrase')
            if ssh_key:
                return Keypair(username_from_url or 'git', ssh_key, None, ssh_passphrase)

        elif method == AuthenticationMethod.TOKEN:
            token = self.credentials.get('token')
            if token:
                return UserPass(username_from_url or 'token', token)

        elif method == AuthenticationMethod.BASIC:
            username = self.credentials.get('username')
            password = self.credentials.get('password')
            if username and password:
                return UserPass(username, password)

        return None


class GitRepositoryProvider(RepositoryProvider):
    """Git repository provider implementation."""

    def __init__(self, cache_dir: Optional[Path] = None,
                 redis_client: Optional[Any] = None):
        self.cache_dir = cache_dir or Path.home() / '.cache' / 'repo_scanner' / 'git'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.redis = redis_client

    @property
    def supported_types(self) -> List[RepositoryType]:
        """Return supported repository types."""
        return [RepositoryType.GIT]

    async def can_handle(self, url: str) -> bool:
        """Check if URL is a Git repository."""
        parsed = urlparse(url)

        # Check for Git-specific indicators
        if parsed.scheme in ('git', 'ssh', 'http', 'https'):
            if url.endswith('.git'):
                return True
            if any(domain in parsed.netloc for domain in ['github.com', 'gitlab.com', 'bitbucket.org']):
                return True

        # Check for local Git repository
        if os.path.isdir(url):
            return os.path.exists(os.path.join(url, '.git'))

        return False

    async def create_handle(self, url: str, **kwargs) -> RepositoryHandle:
        """Create Git repository handle."""
        # Extract metadata from URL
        metadata = await self._extract_metadata(url)

        handle = RepositoryHandle(url, RepositoryType.GIT, metadata)

        # Set credentials if provided
        if 'credentials' in kwargs:
            creds = kwargs['credentials']
            method = creds.get('method', AuthenticationMethod.NONE)
            handle.set_credentials(method, **creds)

        return handle

    async def validate_credentials(self, handle: RepositoryHandle) -> bool:
        """Validate Git repository credentials."""
        try:
            # Attempt to fetch repository info
            callbacks = GitRemoteCallbacks(handle.credentials)
            remote = Remote(handle.url, callbacks=callbacks)
            remote.connect()
            remote.disconnect()
            return True
        except GitError:
            return False

    async def clone(self, handle: RepositoryHandle, local_path: Path) -> Path:
        """Clone Git repository."""
        repo_path = local_path / handle.metadata['name']
        repo_path.mkdir(parents=True, exist_ok=True)

        callbacks = GitRemoteCallbacks(handle.credentials)

        try:
            # Perform clone
            clone_repository(
                handle.url,
                str(repo_path),
                callbacks=callbacks,
                checkout_branch=handle.metadata.get('default_branch', 'main')
            )

            logger.info(f"Successfully cloned {handle.url} to {repo_path}")
            return repo_path

        except GitError as e:
            logger.error(f"Failed to clone repository: {e}")
            raise

    async def pull(self, handle: RepositoryHandle, local_path: Path) -> None:
        """Pull latest changes for Git repository."""
        if not local_path.exists():
            await self.clone(handle, local_path.parent)
            return

        repo = GitRepository(str(local_path))

        # Get default remote
        remote_name = 'origin'
        remote = repo.remotes[remote_name]

        callbacks = GitRemoteCallbacks(handle.credentials)

        try:
            # Fetch and merge
            remote.fetch(callbacks=callbacks)

            # Get remote head
            remote_head = repo.references[f'refs/remotes/{remote_name}/HEAD']
            local_head = repo.head

            # Merge if needed
            if remote_head.target != local_head.target:
                repo.merge(remote_head.target)
                logger.info(f"Successfully pulled changes for {handle.url}")

        except GitError as e:
            logger.error(f"Failed to pull repository: {e}")
            raise

    async def get_info(self, handle: RepositoryHandle) -> RepositoryInfo:
        """Get comprehensive Git repository information."""
        # This would require cloning or using GitHub/GitLab APIs
        # For now, return basic info
        metadata = handle.metadata

        return RepositoryInfo(
            url=handle.url,
            type=RepositoryType.GIT,
            name=metadata['name'],
            owner=metadata.get('owner'),
            description=metadata.get('description'),
            default_branch=metadata.get('default_branch', 'main'),
            branches=[],  # Would need to fetch
            tags=[],     # Would need to fetch
            commit_count=0,  # Would need to count
            contributor_count=0,  # Would need to analyze
            size_bytes=metadata.get('size_bytes', 0),
            file_count=0,  # Would need to count
            language_stats={},  # Would need to analyze
            last_commit=None,
            created_at=metadata.get('created_at'),
            updated_at=metadata.get('updated_at')
        )

    async def list_files(self, local_path: Path, pattern: Optional[str] = None) -> List[FileInfo]:
        """List files in Git repository."""
        files = []

        for root, dirs, filenames in os.walk(local_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')

            for filename in filenames:
                file_path = Path(root) / filename
                rel_path = file_path.relative_to(local_path)

                # Apply pattern filter if specified
                if pattern and not self._matches_pattern(str(rel_path), pattern):
                    continue

                try:
                    stat = file_path.stat()
                    is_binary = self._is_binary_file(file_path)

                    files.append(FileInfo(
                        path=rel_path,
                        size=stat.st_size,
                        modified_time=stat.st_mtime,
                        is_binary=is_binary,
                        hash=self._calculate_hash(file_path) if not is_binary else None
                    ))
                except OSError:
                    # Skip files that can't be accessed
                    continue

        return files

    async def read_file(self, local_path: Path, file_path: str) -> str:
        """Read file content from Git repository."""
        full_path = local_path / file_path

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            return await f.read()

    async def get_history(self, local_path: Path, file_path: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """Get commit history for repository or specific file."""
        repo = GitRepository(str(local_path))

        history = []
        walker = repo.walk(repo.head.target, GitRepository.Sort.TOPOLOGICAL)

        for commit in walker:
            if len(history) >= limit:
                break

            commit_info = {
                'hash': commit.id.hex,
                'message': commit.message,
                'author': {
                    'name': commit.author.name,
                    'email': commit.author.email
                },
                'committer': {
                    'name': commit.committer.name,
                    'email': commit.committer.email
                },
                'timestamp': commit.commit_time,
                'parents': [p.hex for p in commit.parents]
            }

            # If file_path specified, check if commit affects that file
            if file_path:
                if self._commit_affects_file(repo, commit, file_path):
                    history.append(commit_info)
            else:
                history.append(commit_info)

        return history

    async def cleanup(self, local_path: Path) -> None:
        """Clean up local Git repository copy."""
        import shutil
        if local_path.exists():
            shutil.rmtree(local_path)

    async def _extract_metadata(self, url: str) -> Dict[str, Any]:
        """Extract metadata from Git URL."""
        parsed = urlparse(url)

        metadata = {
            'url': url,
            'type': 'git'
        }

        if parsed.scheme in ('http', 'https'):
            # Extract from URL path
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                metadata['owner'] = path_parts[-2]
                repo_name = path_parts[-1]
                if repo_name.endswith('.git'):
                    repo_name = repo_name[:-4]
                metadata['name'] = repo_name

        elif os.path.isdir(url):
            # Local repository
            metadata['name'] = Path(url).name
            metadata['local_path'] = url

        else:
            # SSH or other format
            metadata['name'] = Path(url).name
            if metadata['name'].endswith('.git'):
                metadata['name'] = metadata['name'][:-4]

        # Set defaults
        metadata.setdefault('default_branch', 'main')
        metadata.setdefault('description', None)
        metadata.setdefault('size_bytes', 0)

        return metadata

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

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        hash_obj = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def _commit_affects_file(self, repo: GitRepository, commit: Object, file_path: str) -> bool:
        """Check if commit affects specific file."""
        try:
            # Get diff for commit
            if len(commit.parents) > 0:
                diff = repo.diff(commit.parents[0], commit)
            else:
                # Initial commit
                diff = commit.tree.diff_to_tree()

            for patch in diff:
                if patch.delta.new_file.path == file_path or patch.delta.old_file.path == file_path:
                    return True

            return False
        except:
            return False