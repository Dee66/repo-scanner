"""Repository discovery stage for Repository Intelligence Scanner."""

import os
from pathlib import Path
from typing import Optional

from src.core.exceptions import RepositoryDiscoveryError, FileAccessError

# Cache for repository root discovery
_repo_root_cache: dict[str, str] = {}


def discover_repository_root(start_path: str) -> str:
    """Discover the repository root using git or filesystem fallback with caching."""
    if not isinstance(start_path, str) or not start_path.strip():
        raise RepositoryDiscoveryError("Invalid start path provided", {"start_path": start_path})
    
    start_path = str(Path(start_path).resolve())
    
    # Check cache first
    if start_path in _repo_root_cache:
        return _repo_root_cache[start_path]
    
    path = Path(start_path)
    
    # Try git root first (but only if path exists and we're in a reasonable directory depth)
    if path.exists():
        try:
            if path.stat().st_dev == Path.home().stat().st_dev:  # Only try git if we're on the same filesystem as home
                import subprocess
                result = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=path,
                    capture_output=True,
                    text=True,
                    timeout=2  # Reduced timeout
                )
                if result.returncode == 0:
                    root = result.stdout.strip()
                    if not root:
                        raise RepositoryDiscoveryError("Git returned empty root path")
                    _repo_root_cache[start_path] = root
                    return root
        except subprocess.TimeoutExpired:
            raise RepositoryDiscoveryError("Git command timed out", {"timeout": 2})
        except subprocess.SubprocessError as e:
            raise RepositoryDiscoveryError(f"Git command failed: {e}", {"error": str(e)})
        except FileNotFoundError:
            # Git not available, continue to fallback
            pass
        except OSError as e:
            raise RepositoryDiscoveryError(f"Filesystem error during git check: {e}", {"error": str(e)})
    
    # Fallback to filesystem: find the deepest directory with .git or similar
    current = path
    max_depth = 10  # Limit search depth
    depth = 0
    
    while current.parent != current and depth < max_depth:
        if (current / ".git").exists():
            root = str(current)
            _repo_root_cache[start_path] = root
            return root
        current = current.parent
        depth += 1
    
    # If no .git found, use the provided path (but validate it exists)
    if not path.exists():
        raise RepositoryDiscoveryError("Start path does not exist", {"start_path": start_path})
    
    _repo_root_cache[start_path] = start_path
    return start_path


# Cache for repository root discovery
_repo_root_cache: dict[str, str] = {}
# Cache for file lists
_file_list_cache: dict[str, list[str]] = {}


def clear_caches():
    """Clear all caches to ensure fresh analysis."""
    _repo_root_cache.clear()
    _file_list_cache.clear()


def get_canonical_file_list(repository_root: str) -> list[str]:
    """Get a canonical, sorted list of all files in the repository with caching."""
    if repository_root in _file_list_cache:
        return _file_list_cache[repository_root].copy()
    
    if not isinstance(repository_root, str):
        return []
    
    root_path = Path(repository_root)
    files = []
    
    try:
        # Use os.walk for better performance than rglob
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Skip common directories that shouldn't be analyzed (but keep .git for tests)
            dirnames[:] = [d for d in dirnames if d not in {'node_modules', '__pycache__', 'build', 'dist'}]
            
            for filename in filenames:
                file_path = Path(dirpath) / filename
                # Get absolute path for consistent file access
                files.append(str(file_path.resolve()))
    except (OSError, ValueError):
        pass
    
    # Sort bytewise for determinism
    files.sort()
    _file_list_cache[repository_root] = files.copy()
    return files