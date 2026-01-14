"""Repository discovery stage for Repository Intelligence Scanner."""

import os
from pathlib import Path
from typing import Optional
import logging

from src.core.exceptions import RepositoryDiscoveryError, FileAccessError
from src.core.security.malicious_repo_protection import MaliciousRepoProtection, SecurityLimits

logger = logging.getLogger(__name__)

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
            # DEBUG_DISABLED: print(f"DEBUG: Cache corruption detected for {repository_root}, rebuilding...")
            _file_list_cache.pop(repository_root, None)
        else:
            return cached_files.copy()
    
    if not isinstance(repository_root, str):
        return []
    
    root_path = Path(repository_root)
    files = []
    
    # Initialize malicious repo protection
    repo_protection = MaliciousRepoProtection(
        repo_root=root_path,
        limits=SecurityLimits(
            max_file_size_bytes=10 * 1024 * 1024,  # 10 MB
            max_files_total=50000,  # 50k files
            forbid_symlinks=True,
            max_directory_depth=20,
            max_line_count=100000,  # 100k lines
        )
    )
    
    # Validate the root directory
    if not repo_protection.validate_directory_safe(root_path):
        logger.error("Repository root failed safety validation: %s", repository_root)
        return []
    # Directories to always skip
    _EXCLUDE_DIRS = {
        # Python
        '__pycache__',
        '.pytest_cache',
        '.mypy_cache',
        '.tox',
        '.coverage',
        'htmlcov',
        'site-packages',
        'dist-info',
        '.eggs',
        '*.egg-info',
        'pip-wheel-metadata',

        # JavaScript/Node.js
        'node_modules',
        'bower_components',
        '.npm',
        '.yarn',
        'jspm_packages',

        # Java/Maven/Gradle
        'target',
        'build',
        'out',
        '.gradle',
        '.m2',
        '.maven',

        # .NET/C#
        'bin',
        'obj',
        '.nuget',

        # Go
        'vendor',
        'Godeps',

        # Rust
        'target',
        'Cargo.lock.target',

        # IDEs and editors
        '.idea',
        '.vscode',
        '.vs',
        '.eclipse',
        '*.swp',
        '*.swo',
        '*~',

        # OS generated
        '.DS_Store',
        'Thumbs.db',
        '.Trashes',
        '.fseventsd',
        '.DocumentRevisions-V100',
        '.TemporaryItems',
        '.Spotlight-V100',

        # Version control
        '.git',
        '.svn',
        '.hg',
        '.bzr',

        # Virtual environments
        'venv',
        '.venv',
        'env',
        '.env',
        'ENV',

        # Package managers
        '.bundle',
        'vendor/bundle',

        # Build tools
        'dist',
        'build',
        'cmake-build-*',
        '.cmake',

        # Testing and coverage
        'coverage',
        '.nyc_output',
        'test-results',
        'junit-reports',

        # Documentation generation
        'docs/_build',
        'docs/build',
        'site',
        '.doctrees',

        # Logs and temporary files
        'logs',
        '*.log',
        'tmp',
        'temp',
        '.tmp',

        # Cache directories
        '.cache',
        '.pytest_cache',
        '__pycache__',
        'node_modules/.cache',
        '.yarn/cache',

        # Output and generated directories
        'output',
        'outputs',
        'out',
        'dist',
        'build',
        'generated',
        '__generated__',
        '.generated',
        'auto-generated',

        # Scanner-specific
        '.scanner_cache',
        'analysis',
        'tmp_scan_output',
        'scan_output',
        'reports',
        'scan_results',
        'batch_scan_results',
        'scan_results_cc',
        'scan_results_debug',
        'scan_results_pa',
        'scan_results_litmus',
        'outputs',
        'outputs_ci',
        'outputs_determinism',
        'tmp_scan_output_qav011',
        'golden-repos',
        'test_scan_output',
        'test_repositories',
        'test_repo',
        'test_data',
        'validation_data',

        # CI/CD
        '.github/workflows/.cache',
        '.circleci/cache',
        '.travis/cache',

        # Docker
        '.docker',

        # Kubernetes
        '.kube',

        # Terraform
        '.terraform',

        # Ansible
        '.ansible',

        # Database
        '.sqlite',
        '*.db',
        '*.sqlite3',

        # Backup files
        '*.bak',
        '*.backup',
        '*~',
        '*.orig',
        '*.rej',

        # Archives (often contain generated code)
        '*.zip',
        '*.tar.gz',
        '*.tgz',
        '*.rar',
        '*.7z',

        # Lock files (but keep the actual lock files for analysis)
        # Note: We exclude directories containing lock files, not the files themselves
    }

    try:
        # Use os.walk for better performance than rglob
        for dirpath, dirnames, filenames in os.walk(root_path):
            if not isinstance(dirpath, str):
            # DEBUG_DISABLED: print(f"DEBUG: Non-string dirpath: {dirpath} (type: {type(dirpath)})")
                continue
            if not all(isinstance(d, str) for d in dirnames):
                non_strings = [d for d in dirnames if not isinstance(d, str)]
            # DEBUG_DISABLED: print(f"DEBUG: Non-string dirnames: {non_strings[:5]} (types: {[type(d) for d in non_strings[:5]]})")
                dirnames[:] = [d for d in dirnames if isinstance(d, str)]
            if not all(isinstance(f, str) for f in filenames):
                non_strings = [f for f in filenames if not isinstance(f, str)]
            # DEBUG_DISABLED: print(f"DEBUG: Non-string filenames: {non_strings[:5]} (types: {[type(f) for f in non_strings[:5]]})")
                filenames[:] = [f for f in filenames if isinstance(f, str)]
            
            # Filter dirnames in-place to control traversal. Keep '.git' only.
            filtered = []
            for d in dirnames:
                if not isinstance(d, str):
            # DEBUG_DISABLED: print(f"DEBUG: Non-string dirname: {d} (type: {type(d)})")
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
            # DEBUG_DISABLED: print(f"DEBUG: Non-string filename: {filename} (type: {type(filename)})")
                    continue

                # Skip files in version control directories
                dirpath_parts = Path(dirpath).parts
                if any(part in ('.git', '.svn', '.hg', '.bzr') for part in dirpath_parts):
                    continue

                # Skip compiled and temporary files
                if filename.endswith((
                    '.pyc', '.pyo', '.class', '.so', '.dll', '.exe', '.dylib',
                    '.o', '.obj', '.lib', '.a', '.pdb', '.ilk'
                )):
                    continue

                # Skip coverage and test artifacts
                if filename in ('.coverage', 'coverage.xml', '.coverage.*', 'nosetests.xml', 'junit.xml'):
                    continue
                if filename.startswith('coverage') and filename.endswith(('.xml', '.html', '.lcov')):
                    continue

                # Skip typical generated bundle artifacts
                if filename.endswith(('.min.js', '.bundle.js', '.map', '.min.css', '.bundle.css')):
                    continue

                # Skip log files
                if filename.endswith('.log') or '.log.' in filename or filename in ('debug.log', 'error.log'):
                    continue

                # Skip backup and temporary files
                if filename.endswith(('~', '.bak', '.backup', '.orig', '.rej', '.tmp', '.temp')):
                    continue
                if filename.startswith(('#', '.')) and filename.endswith(('#', '~')):
                    continue

                # Skip OS-specific files
                if filename in ('.DS_Store', 'Thumbs.db', 'Desktop.ini', 'ehthumbs.db'):
                    continue

                # Skip generated files by common tools
                if filename.endswith((
                    '.generated.cs', '.generated.vb', '.g.cs', '.g.vb',  # C#/VB generated
                    '.generated.go',  # Go generated
                    '.generated.rs',  # Rust generated
                    '.generated.ts',  # TypeScript generated
                    '_pb2.py',  # Protocol buffers
                    '.spec.ts',  # TypeScript generated
                )):
                    continue

                file_path = Path(dirpath) / filename
                # Get absolute path for consistent file access
                try:
                    resolved_path = str(file_path.resolve())
                    if not isinstance(resolved_path, str):
            # DEBUG_DISABLED: print(f"DEBUG: Non-string resolved path: {resolved_path} (type: {type(resolved_path)})")
                        continue
                    
                    # Validate file safety before adding to list
                    if not repo_protection.validate_file_safe(Path(resolved_path)):
                        logger.warning("Skipping unsafe file: %s", resolved_path)
                        continue
                    
                    # Check file count limit
                    if len(files) >= repo_protection.limits.max_files_total:
                        logger.error("Repository exceeds maximum file count (%d)", 
                                   repo_protection.limits.max_files_total)
                        break
                    
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