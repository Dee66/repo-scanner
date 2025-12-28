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
        cached_files = _file_list_cache[repository_root]
        # Validate cache integrity
        if not all(isinstance(f, str) for f in cached_files):
            print(f"DEBUG: Cache corruption detected for {repository_root}, rebuilding...")
            _file_list_cache.pop(repository_root, None)
        else:
            return cached_files.copy()
    
    if not isinstance(repository_root, str):
        return []
    
    root_path = Path(repository_root)
    files = []
    # Directories to always skip
    _EXCLUDE_DIRS = {
        'node_modules',
        '__pycache__',
        'build',
        'dist',
        'venv',
        '.venv',
        '.env',
        '.pytest_cache',
        'target',
        'out',
        '.idea',
        '.vscode',
        '.egg-info',
        '.mypy_cache',
        'site-packages',
        'vendor',
        'third_party',
        'deps',
        '.scanner_cache',
        'analysis',
        'tmp_scan_output',
        'scan_output',
        'reports',
        'outputs',
        '.cache',
        '.export',
        'dist-info',
        '__generated__',
    }

    try:
        # Use os.walk for better performance than rglob
        for dirpath, dirnames, filenames in os.walk(root_path):
            if not isinstance(dirpath, str):
                print(f"DEBUG: Non-string dirpath: {dirpath} (type: {type(dirpath)})")
                continue
            if not all(isinstance(d, str) for d in dirnames):
                non_strings = [d for d in dirnames if not isinstance(d, str)]
                print(f"DEBUG: Non-string dirnames: {non_strings[:5]} (types: {[type(d) for d in non_strings[:5]]})")
                dirnames[:] = [d for d in dirnames if isinstance(d, str)]
            if not all(isinstance(f, str) for f in filenames):
                non_strings = [f for f in filenames if not isinstance(f, str)]
                print(f"DEBUG: Non-string filenames: {non_strings[:5]} (types: {[type(f) for f in non_strings[:5]]})")
                filenames[:] = [f for f in filenames if isinstance(f, str)]
            
            # Filter dirnames in-place to control traversal. Keep '.git' only.
            filtered = []
            for d in dirnames:
                if not isinstance(d, str):
                    print(f"DEBUG: Non-string dirname: {d} (type: {type(d)})")
                    continue
                if d == '.git':
                    filtered.append(d)
                    continue
                # Skip any dot-folder except .git
                if d.startswith('.'):
                    continue
                if d in _EXCLUDE_DIRS:
                    continue
                filtered.append(d)
            dirnames[:] = filtered

            for filename in filenames:
                if not isinstance(filename, str):
                    print(f"DEBUG: Non-string filename: {filename} (type: {type(filename)})")
                    continue
                # Skip compiled and temporary files
                if filename.endswith(('.pyc', '.pyo', '.class', '.so')):
                    continue
                if filename in ('.coverage', 'coverage.xml'):
                    continue
                # Skip typical generated bundle artifacts
                if filename.endswith(('.min.js', '.bundle.js', '.map')):
                    continue
                file_path = Path(dirpath) / filename
                # Get absolute path for consistent file access
                try:
                    resolved_path = str(file_path.resolve())
                    if not isinstance(resolved_path, str):
                        print(f"DEBUG: Non-string resolved path: {resolved_path} (type: {type(resolved_path)})")
                        continue
                    files.append(resolved_path)
                except (OSError, RuntimeError):
                    # Skip problematic files
                    continue
    except (OSError, ValueError):
        pass
    
    # Sort bytewise for determinism
    files.sort()
    _file_list_cache[repository_root] = files.copy()
    return files