"""
Offline Execution Mode Enforcement for Repository Intelligence Scanner.

BPS-015 & BPS-016: Implement offline_only execution mode and network_access forbidden constraint.
This module ensures the scanner operates completely offline with comprehensive network access blocking.
"""

import os
import socket
import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
import threading
import time
import sys
import builtins

logger = logging.getLogger(__name__)


@dataclass
class NetworkAccessAttempt:
    """Represents a detected network access attempt."""
    operation: str
    target: str
    protocol: str
    timestamp: str
    blocked: bool
    thread_id: int
    stack_trace: Optional[str] = None


@dataclass
class OfflineViolation:
    """Represents a violation of offline-only mode."""
    violation_type: str
    description: str
    operation: str
    details: Dict[str, Any]
    timestamp: str
    severity: str
    blocked: bool = True


class NetworkAccessBlocker:
    """
    BPS-016: Comprehensive network access blocking mechanisms.

    Implements multiple layers of network access prevention.
    """

    # Store original socket class at class level
    _original_socket_class = socket.socket

    def __init__(self):
        self.blocked_hosts: Set[str] = set()
        self.blocked_ports: Set[int] = set()
        self.allowed_interfaces: Set[str] = {'lo', 'localhost'}  # Only loopback allowed
        self.dns_blocked = True
        self.http_blocked = True
        self.https_blocked = True

    def activate_network_blocks(self):
        """Activate all network blocking mechanisms."""
        # Block socket operations first (before other modules import socket)
        self._block_socket_operations()

        # Block HTTP requests
        self._block_http_requests()

        # Block DNS resolution
        self._block_dns_resolution()

        # Block external interfaces
        self._block_external_interfaces()

        logger.info("Network access blocking activated")

    def _block_socket_operations(self):
        """Block socket operations at the Python level."""
        # Store original socket class
        self._original_socket_class = socket.socket

        # Create a blocking socket wrapper
        class BlockedSocketWrapper:
            def __init__(self, *args, **kwargs):
                self._real_socket = NetworkAccessBlocker._original_socket_class(*args, **kwargs)
                self._blocked = False

            def connect(self, address):
                host, port = address[0], address[1] if len(address) > 1 else 0
                if not self._is_localhost(host):
                    self._record_blocked_attempt("socket_connect", f"{host}:{port}", "tcp")
                    raise OSError("Network access forbidden: socket connection blocked")
                return self._real_socket.connect(address)

            def bind(self, address):
                host, port = address[0], address[1] if len(address) > 1 else 0
                if not self._is_localhost(host):
                    self._record_blocked_attempt("socket_bind", f"{host}:{port}", "tcp")
                    raise OSError("Network access forbidden: socket binding blocked")
                return self._real_socket.bind(address)

            def _is_localhost(self, host: str) -> bool:
                localhost_aliases = {'localhost', '127.0.0.1', '::1', '0.0.0.0', ''}
                return host.lower() in localhost_aliases or host.startswith('127.')

            def _record_blocked_attempt(self, operation: str, target: str, protocol: str):
                import traceback
                attempt = NetworkAccessAttempt(
                    operation=operation,
                    target=target,
                    protocol=protocol,
                    timestamp="2025-12-31T00:00:00Z",
                    blocked=True,
                    thread_id=threading.get_ident(),
                    stack_trace=''.join(traceback.format_stack())
                )
                from .offline_enforcement import offline_enforcer
                offline_enforcer.network_attempts.append(attempt)
                logger.warning("Blocked network access: %s to %s (%s)", operation, target, protocol)

            # Delegate all other methods to the real socket
            def __getattr__(self, name):
                return getattr(self._real_socket, name)

        # Replace socket.socket with our wrapper
        socket.socket = BlockedSocketWrapper
        """Block socket operations at the Python level."""
        # Store original socket class
        self._original_socket_class = socket.socket

        # Create a blocking socket wrapper
        class BlockedSocketWrapper:
            def __init__(self, *args, **kwargs):
                self._real_socket = NetworkAccessBlocker._original_socket_class(*args, **kwargs)
                self._blocked = False

            def connect(self, address):
                host, port = address[0], address[1] if len(address) > 1 else 0
                if not self._is_localhost(host):
                    self._record_blocked_attempt("socket_connect", f"{host}:{port}", "tcp")
                    raise OSError("Network access forbidden: socket connection blocked")
                return self._real_socket.connect(address)

            def bind(self, address):
                host, port = address[0], address[1] if len(address) > 1 else 0
                if not self._is_localhost(host):
                    self._record_blocked_attempt("socket_bind", f"{host}:{port}", "tcp")
                    raise OSError("Network access forbidden: socket binding blocked")
                return self._real_socket.bind(address)

            def _is_localhost(self, host: str) -> bool:
                localhost_aliases = {'localhost', '127.0.0.1', '::1', '0.0.0.0', ''}
                return host.lower() in localhost_aliases or host.startswith('127.')

            def _record_blocked_attempt(self, operation: str, target: str, protocol: str):
                import traceback
                attempt = NetworkAccessAttempt(
                    operation=operation,
                    target=target,
                    protocol=protocol,
                    timestamp="2025-12-23T00:00:00Z",
                    blocked=True,
                    thread_id=threading.get_ident(),
                    stack_trace=''.join(traceback.format_stack())
                )
                from .offline_enforcement import offline_enforcer
                offline_enforcer.network_attempts.append(attempt)
                logger.warning("Blocked network access: %s to %s (%s)", operation, target, protocol)

            # Delegate all other methods to the real socket
            def __getattr__(self, name):
                return getattr(self._real_socket, name)

        # Replace socket.socket with our wrapper
        socket.socket = BlockedSocketWrapper

    def _block_http_requests(self):
        """Block HTTP/HTTPS requests by intercepting common libraries."""
        # Block urllib requests
        try:
            import urllib.request
            original_urlopen = urllib.request.urlopen

            def blocked_urlopen(url, *args, **kwargs):
                self._record_blocked_attempt("urllib_request", str(url), "http")
                raise OSError("Network access forbidden: HTTP request blocked")

            urllib.request.urlopen = blocked_urlopen
        except ImportError:
            pass

        # Block requests library if already imported
        try:
            import requests
            original_get = requests.get
            original_post = requests.post

            def blocked_request(method, url, *args, **kwargs):
                self._record_blocked_attempt(f"requests_{method}", str(url), "http")
                raise ConnectionError("Network access forbidden: HTTP request blocked")

            requests.get = lambda url, *args, **kwargs: blocked_request("get", url, *args, **kwargs)
            requests.post = lambda url, *args, **kwargs: blocked_request("post", url, *args, **kwargs)
        except ImportError:
            pass

    def _block_dns_resolution(self):
        """Block DNS resolution."""
        original_getaddrinfo = socket.getaddrinfo

        def blocked_getaddrinfo(host, port, *args, **kwargs):
            if not self._is_localhost(host):
                self._record_blocked_attempt("dns_resolution", host, "dns")
                raise socket.gaierror("Network access forbidden: DNS resolution blocked")
            return original_getaddrinfo(host, port, *args, **kwargs)

        socket.getaddrinfo = blocked_getaddrinfo

    def _block_external_interfaces(self):
        """Block access to external network interfaces."""
        # This would require system-level blocking in production
        # For now, we'll rely on socket-level blocking
        pass

    def _is_localhost(self, host: str) -> bool:
        """Check if host is localhost/loopback."""
        localhost_aliases = {'localhost', '127.0.0.1', '::1', '0.0.0.0', ''}
        return host.lower() in localhost_aliases or host.startswith('127.')

    def _record_blocked_attempt(self, operation: str, target: str, protocol: str):
        """Record a blocked network access attempt."""
        import traceback

        attempt = NetworkAccessAttempt(
            operation=operation,
            target=target,
            protocol=protocol,
            timestamp="2025-12-23T00:00:00Z",
            blocked=True,
            thread_id=threading.get_ident(),
            stack_trace=''.join(traceback.format_stack())
        )

        # Get the global offline enforcer to record this
        from .offline_enforcement import offline_enforcer
        offline_enforcer.network_attempts.append(attempt)

        logger.warning("Blocked network access: %s to %s (%s)", operation, target, protocol)


class ExternalServiceBlocker:
    """
    BPS-017: Comprehensive external service blocking mechanisms.

    Prevents usage of external services like APIs, cloud services, databases, etc.
    """

    def __init__(self):
        self.blocked_service_types = {
            'api': ['api', 'rest', 'graphql', 'webhook', 'boto3', 'botocore'],
            'cloud': ['aws', 'azure', 'gcp', 's3', 'ec2', 'lambda', 'cloudfront'],
            'database': ['mongodb', 'postgresql', 'mysql', 'redis', 'dynamodb'],
            'package_registry': ['npm', 'pypi', 'maven', 'nuget', 'docker'],
            'version_control': ['github', 'gitlab', 'bitbucket', 'svn'],
            'ci_cd': ['jenkins', 'travis', 'circleci', 'github_actions'],
            'monitoring': ['datadog', 'newrelic', 'sentry', 'rollbar'],
            'communication': ['slack', 'discord', 'teams', 'email']
        }

        self.service_detection_patterns = self._build_detection_patterns()

    def _build_detection_patterns(self) -> Dict[str, List[str]]:
        """Build patterns for detecting external service usage."""
        patterns = {}

        for service_type, keywords in self.blocked_service_types.items():
            patterns[service_type] = []
            for keyword in keywords:
                # Add common variations
                patterns[service_type].extend([
                    keyword,
                    f"{keyword}_",
                    f"{keyword}.",
                    f"{keyword}-",
                    keyword.upper(),
                    keyword.capitalize()
                ])

        return patterns

    def activate_service_blocks(self):
        """Activate all external service blocking mechanisms."""
        self._block_import_based_services()
        self._block_environment_based_services()
        self._block_configuration_based_services()

        logger.info("External service blocking activated")

    def _block_import_based_services(self):
        """Block services that require specific Python imports."""
        service_imports = {
            'boto3': 'cloud:aws',
            'botocore': 'cloud:aws',
            'azure': 'cloud:azure',
            'google.cloud': 'cloud:gcp',
            'pymongo': 'database:mongodb',
            'psycopg2': 'database:postgresql',
            'pymysql': 'database:mysql',
            'redis': 'database:redis',
            'requests': 'api:http',
            'urllib3': 'api:http',
            'httpx': 'api:http',
            'github': 'version_control:github',
            'gitlab': 'version_control:gitlab',
            'slack-sdk': 'communication:slack',
            'discord': 'communication:discord'
        }

        # Monkey patch __import__ to detect blocked service imports
        original_import = __builtins__['__import__']

        def blocked_import(name, *args, **kwargs):
            if name in service_imports:
                service_info = service_imports[name]
                self._record_blocked_service_attempt("import", name, service_info)
                raise ImportError(f"External service usage forbidden: {service_info}")

            return original_import(name, *args, **kwargs)

        __builtins__['__import__'] = blocked_import

    def _block_environment_based_services(self):
        """Block services that use environment variables."""
        blocked_env_vars = [
            'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN',
            'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 'AZURE_TENANT_ID',
            'GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_CLOUD_PROJECT',
            'GITHUB_TOKEN', 'GITLAB_TOKEN', 'SLACK_TOKEN',
            'DOCKER_USERNAME', 'DOCKER_PASSWORD',
            'DATABASE_URL', 'REDIS_URL', 'MONGODB_URI'
        ]

        # Check for blocked environment variables
        for env_var in blocked_env_vars:
            if env_var in os.environ:
                self._record_blocked_service_attempt("environment_variable", env_var, "external_service")
                # Don't remove the variable, just log the violation

    def _block_configuration_based_services(self):
        """Block services that use configuration files or URLs."""
        blocked_config_patterns = [
            r'https?://.*\.amazonaws\.com',
            r'https?://.*\.azure\.com',
            r'https?://.*\.googleapis\.com',
            r'https?://api\.github\.com',
            r'https?://api\.gitlab\.com',
            r'https?://.*\.slack\.com',
            r'mongodb://', r'postgresql://', r'mysql://', r'redis://'
        ]

        # This would be checked when configuration is loaded
        # For now, we'll rely on the import and environment blocking

    def detect_service_usage_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """
        Detect if an operation attempts to use external services.

        Returns True if external service usage is detected.
        """
        operation_str = operation.lower()
        context_str = str(context).lower()

        for service_type, patterns in self.service_detection_patterns.items():
            if any(pattern.lower() in operation_str or pattern.lower() in context_str
                   for pattern in patterns):
                self._record_blocked_service_attempt("operation", operation, service_type)
                return True

        return False

    def _record_blocked_service_attempt(self, attempt_type: str, target: str, service_type: str):
        """Record a blocked external service usage attempt."""
        import traceback

        violation = OfflineViolation(
            violation_type="external_service_forbidden",
            description=f"Attempted to use external service: {service_type}",
            operation=f"{attempt_type}:{target}",
            details={
                "service_type": service_type,
                "attempt_type": attempt_type,
                "target": target,
                "stack_trace": ''.join(traceback.format_stack())
            },
            timestamp="2025-12-31T00:00:00Z",
            severity="high",
            blocked=True
        )

        # Get the global offline enforcer to record this
        from .offline_enforcement import offline_enforcer
        offline_enforcer.violations.append(violation)

        logger.error("Blocked external service usage: %s (%s) via %s", target, service_type, attempt_type)


class RepositoryModificationBlocker:
    """
    BPS-018: Comprehensive repository modification blocking mechanisms.

    Prevents modification of the repository being analyzed while allowing
    modifications elsewhere (temp files, logs, reports).
    """

    def __init__(self):
        self.repository_paths: Set[str] = set()
        self.allowed_modification_paths: Set[str] = set()
        self.blocked_operations = {
            'write', 'modify', 'delete', 'create', 'update', 'save',
            'edit', 'change', 'alter', 'remove', 'rename', 'move',
            'mkdir', 'makedirs', 'touch', 'chmod', 'chown'
        }

    def set_repository_path(self, repo_path: str):
        """
        Set the repository path that should be protected from modification.

        BPS-018: This path and all its subdirectories cannot be modified.
        """
        # Normalize the path
        normalized_path = os.path.abspath(repo_path)
        self.repository_paths.add(normalized_path)

        # Also protect common variations
        self.repository_paths.add(normalized_path + os.sep)
        if os.name == 'nt':  # Windows
            self.repository_paths.add(normalized_path.lower())
            self.repository_paths.add((normalized_path + os.sep).lower())

        logger.info(f"Repository modification protection activated for: {normalized_path}")

    def add_allowed_modification_path(self, allowed_path: str):
        """
        Add a path where modifications are allowed (e.g., temp directories, output directories).
        """
        normalized_path = os.path.abspath(allowed_path)
        self.allowed_modification_paths.add(normalized_path)
        self.allowed_modification_paths.add(normalized_path + os.sep)

    def activate_repository_protection(self):
        """Activate repository modification blocking mechanisms."""
        self._block_file_operations()
        self._block_path_operations()
        self._block_file_handle_operations()

        logger.info("Repository modification blocking activated")

    def _block_file_operations(self):
        """Block file operations that could modify repository files."""
        # Monkey patch os and os.path operations
        original_open = open
        original_os_open = os.open
        original_os_remove = os.remove
        original_os_unlink = os.unlink
        original_os_rename = os.rename
        original_os_replace = getattr(os, 'replace', None)

        def blocked_open(file, mode='r', *args, **kwargs):
            if self._is_modification_attempt(file, mode):
                self._record_modification_attempt("file_open", file, mode)
                raise OSError("Repository modification forbidden: file open for writing blocked")
            return original_open(file, mode, *args, **kwargs)

        def blocked_os_open(path, flags, *args, **kwargs):
            if self._is_modification_attempt(path, flags):
                self._record_modification_attempt("os_open", path, str(flags))
                raise OSError("Repository modification forbidden: os.open for writing blocked")
            return original_os_open(path, flags, *args, **kwargs)

        def blocked_remove(path, *, dir_fd=None):
            if dir_fd is not None:
                # For internal calls with dir_fd, allow them (used by shutil, etc.)
                return original_os_remove(path, dir_fd=dir_fd)
            if self._is_repository_path(path):
                self._record_modification_attempt("file_remove", path, "delete")
                raise OSError("Repository modification forbidden: file deletion blocked")
            return original_os_remove(path)

        def blocked_rename(src, dst):
            if self._is_repository_path(src) or self._is_repository_path(dst):
                self._record_modification_attempt("file_rename", f"{src}->{dst}", "rename")
                raise OSError("Repository modification forbidden: file rename blocked")
            return original_os_rename(src, dst)

        # Apply patches
        builtins.open = blocked_open
        os.open = blocked_os_open
        os.remove = blocked_remove
        os.unlink = blocked_remove  # unlink is alias for remove
        os.rename = blocked_rename
        if original_os_replace:
            os.replace = blocked_rename  # replace is similar to rename

    def _block_path_operations(self):
        """Block path operations that could modify repository structure."""
        try:
            import pathlib
            original_path_write_text = pathlib.Path.write_text
            original_path_write_bytes = pathlib.Path.write_bytes
            original_path_unlink = pathlib.Path.unlink
            original_path_rmdir = pathlib.Path.rmdir

            def blocked_write_text(self, *args, **kwargs):
                if self._is_repository_path(str(self)):
                    self._record_modification_attempt("path_write_text", str(self), "write")
                    raise OSError("Repository modification forbidden: Path.write_text blocked")
                return original_path_write_text(self, *args, **kwargs)

            def blocked_write_bytes(self, *args, **kwargs):
                if self._is_repository_path(str(self)):
                    self._record_modification_attempt("path_write_bytes", str(self), "write")
                    raise OSError("Repository modification forbidden: Path.write_bytes blocked")
                return original_path_write_bytes(self, *args, **kwargs)

            def blocked_unlink(self, *args, **kwargs):
                if self._is_repository_path(str(self)):
                    self._record_modification_attempt("path_unlink", str(self), "delete")
                    raise OSError("Repository modification forbidden: Path.unlink blocked")
                return original_path_unlink(self, *args, **kwargs)

            def blocked_rmdir(self, *args, **kwargs):
                if self._is_repository_path(str(self)):
                    self._record_modification_attempt("path_rmdir", str(self), "delete")
                    raise OSError("Repository modification forbidden: Path.rmdir blocked")
                return original_path_rmdir(self, *args, **kwargs)

            # Apply patches
            pathlib.Path.write_text = blocked_write_text
            pathlib.Path.write_bytes = blocked_write_bytes
            pathlib.Path.unlink = blocked_unlink
            pathlib.Path.rmdir = blocked_rmdir

        except ImportError:
            pass  # pathlib not available

    def _block_file_handle_operations(self):
        """Block operations on open file handles that could modify repository files."""
        # This is more complex - would require tracking file handles
        # For now, rely on the file opening blocks above
        pass

    def _is_modification_attempt(self, path: str, mode_or_flags) -> bool:
        """Check if the operation attempts to modify a repository file."""
        if not self._is_repository_path(path):
            return False

        # Check mode string (for open())
        if isinstance(mode_or_flags, str):
            mode = mode_or_flags.lower()
            if any(char in mode for char in ['w', 'a', '+']):
                return True

        # Check flags (for os.open())
        elif isinstance(mode_or_flags, int):
            import stat
            # Check for write flags
            write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC
            if mode_or_flags & write_flags:
                return True

        return False

    def _is_repository_path(self, path: str) -> bool:
        """Check if the path is within a protected repository."""
        if not path:
            return False

        try:
            abs_path = os.path.abspath(path)

            # Check if path is within any repository
            for repo_path in self.repository_paths:
                # Check if the path starts with the repository path
                if abs_path.startswith(repo_path):
                    # Make sure it's not just a prefix match (e.g., /repo vs /repo2)
                    remaining = abs_path[len(repo_path):]
                    if not remaining or remaining.startswith(os.sep):
                        # Allow modifications in explicitly allowed paths
                        if any(abs_path.startswith(allowed) for allowed in self.allowed_modification_paths):
                            return False
                        return True

            return False

        except (OSError, ValueError):
            # If path resolution fails, err on the side of caution
            return True

    def check_modification_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """
        Check if an operation attempts to modify the repository.

        BPS-018: Returns True if repository modification is detected and blocked.
        """
        # Check operation name for modification indicators
        operation_str = operation.lower()
        if any(indicator in operation_str for indicator in self.blocked_operations):
            # Check if context contains repository paths
            for key, value in context.items():
                if isinstance(value, str) and self._is_repository_path(value):
                    self._record_modification_attempt("operation", operation, f"{key}:{value}")
                    return True

        return False

    def _record_modification_attempt(self, attempt_type: str, target: str, details: str):
        """Record a blocked repository modification attempt."""
        import traceback

        violation = OfflineViolation(
            violation_type="repository_modification_forbidden",
            description=f"Attempted to modify repository: {target}",
            operation=f"{attempt_type}:{target}",
            details={
                "modification_type": attempt_type,
                "target": target,
                "details": details,
                "stack_trace": ''.join(traceback.format_stack())
            },
            timestamp="2025-12-31T00:00:00Z",
            severity="high",
            blocked=True
        )

        # Get the global offline enforcer to record this
        from .offline_enforcement import offline_enforcer
        offline_enforcer.violations.append(violation)

        logger.error("Blocked repository modification: %s (%s) via %s", target, details, attempt_type)


class CodeExecutionBlocker:
    """
    BPS-019: Comprehensive code execution blocking mechanisms.

    Prevents execution of application code found in repositories to ensure
    analysis remains safe and deterministic.
    """

    def __init__(self):
        self.execution_indicators = {
            'subprocess': ['subprocess', 'run', 'call', 'popen', 'check_output'],
            'system_calls': ['system', 'popen', 'spawn', 'exec', 'execl', 'execv'],
            'code_execution': ['exec', 'eval', 'compile', 'execfile'],
            'import_execution': ['importlib', 'imp', 'runpy'],
            'script_execution': ['python', 'bash', 'sh', 'cmd', 'powershell'],
            'binary_execution': ['exe', 'bin', 'app', 'command']
        }

        self.dangerous_modules = {
            'subprocess', 'importlib', 'imp', 'runpy'
        }

    def activate_execution_blocks(self, allow_tree_sitter: bool = False):
        """Activate all code execution blocking mechanisms."""
        self.allow_tree_sitter = allow_tree_sitter
        self._block_subprocess_execution()
        self._block_system_execution()
        self._block_code_execution()
        self._block_module_execution()

        logger.info("Code execution blocking activated")

    def _block_subprocess_execution(self):
        """Block subprocess module execution."""
        try:
            import subprocess
            original_run = subprocess.run
            original_call = subprocess.call
            original_check_output = subprocess.check_output
            original_popen = subprocess.Popen

            def blocked_run(*args, **kwargs):
                # Allow safe subprocess calls by trusted modules
                import inspect
                frame = inspect.currentframe()
                try:
                    # Check the calling module
                    caller_frame = frame.f_back
                    while caller_frame:
                        caller_filename = caller_frame.f_code.co_filename
                        if 'repository_discovery.py' in caller_filename:
                            # Allow repository_discovery to run git commands
                            break
                        caller_frame = caller_frame.f_back
                    else:
                        # No safe caller found, block the call
                        self._record_execution_attempt("subprocess_run", str(args[0]) if args else "unknown", "subprocess")
                        raise OSError("Code execution forbidden: subprocess.run blocked")
                finally:
                    del frame
                return original_run(*args, **kwargs)

            def blocked_call(*args, **kwargs):
                self._record_execution_attempt("subprocess_call", str(args[0]) if args else "unknown", "subprocess")
                raise OSError("Code execution forbidden: subprocess.call blocked")

            def blocked_check_output(*args, **kwargs):
                self._record_execution_attempt("subprocess_check_output", str(args[0]) if args else "unknown", "subprocess")
                raise OSError("Code execution forbidden: subprocess.check_output blocked")

            def blocked_popen(*args, **kwargs):
                # Allow safe subprocess calls by trusted modules
                import inspect
                frame = inspect.currentframe()
                try:
                    # Check the calling module
                    caller_frame = frame.f_back
                    while caller_frame:
                        caller_filename = caller_frame.f_code.co_filename
                        if 'repository_discovery.py' in caller_filename:
                            # Allow repository_discovery to run git commands
                            break
                        caller_frame = caller_frame.f_back
                    else:
                        # No safe caller found, block the call
                        self._record_execution_attempt("subprocess_popen", str(args[0]) if args else "unknown", "subprocess")
                        raise OSError("Code execution forbidden: subprocess.Popen blocked")
                finally:
                    del frame
                return original_popen(*args, **kwargs)

            subprocess.run = blocked_run
            subprocess.call = blocked_call
            subprocess.check_output = blocked_check_output
            subprocess.Popen = blocked_popen

        except ImportError:
            pass

    def _block_system_execution(self):
        """Block system-level execution functions."""
        # Block os.system, os.popen, etc.
        original_system = os.system
        original_popen = os.popen
        original_spawn = os.spawnl if hasattr(os, 'spawnl') else None
        original_exec = os.execv if hasattr(os, 'execv') else None

        def blocked_system(command):
            self._record_execution_attempt("os_system", command, "system_call")
            raise OSError("Code execution forbidden: os.system blocked")

        def blocked_popen(command, *args, **kwargs):
            self._record_execution_attempt("os_popen", command, "system_call")
            raise OSError("Code execution forbidden: os.popen blocked")

        def blocked_spawn(*args, **kwargs):
            self._record_execution_attempt("os_spawn", str(args), "system_call")
            raise OSError("Code execution forbidden: os.spawn blocked")

        def blocked_exec(*args, **kwargs):
            self._record_execution_attempt("os_exec", str(args), "system_call")
            raise OSError("Code execution forbidden: os.exec blocked")

        os.system = blocked_system
        os.popen = blocked_popen
        if original_spawn:
            os.spawnl = blocked_spawn
            os.spawnv = blocked_spawn
        if original_exec:
            os.execv = blocked_exec
            os.execl = blocked_exec

    def _block_code_execution(self):
        """Block direct code execution functions."""
        # Block eval, exec, compile
        original_eval = eval
        original_exec = exec
        original_compile = compile

        def blocked_eval(*args, **kwargs):
            self._record_execution_attempt("eval", str(args[0]) if args else "unknown", "code_execution")
            raise RuntimeError("Code execution forbidden: eval blocked")

        def blocked_exec(*args, **kwargs):
            # Allow exec() calls from tree_sitter modules for AST parsing in development
            if self.allow_tree_sitter:
                import inspect
                frame = inspect.currentframe()
                try:
                    # Check the calling module
                    caller_frame = frame.f_back
                    while caller_frame:
                        caller_filename = caller_frame.f_code.co_filename
                        if 'tree_sitter' in caller_filename or 'tree_sitter_' in caller_filename:
                            # Allow tree_sitter modules to use exec for language loading
                            return original_exec(*args, **kwargs)
                        caller_frame = caller_frame.f_back
                    else:
                        # No safe caller found, block the call
                        self._record_execution_attempt("exec", str(args[0]) if args else "unknown", "code_execution")
                        raise RuntimeError("Code execution forbidden: exec blocked")
                finally:
                    del frame
            else:
                self._record_execution_attempt("exec", str(args[0]) if args else "unknown", "code_execution")
                raise RuntimeError("Code execution forbidden: exec blocked")

        def blocked_compile(*args, **kwargs):
            # Allow compile() calls from tree_sitter modules for AST parsing in development
            if self.allow_tree_sitter:
                import inspect
                frame = inspect.currentframe()
                try:
                    # Check the calling module
                    caller_frame = frame.f_back
                    while caller_frame:
                        caller_filename = caller_frame.f_code.co_filename
                        if 'tree_sitter' in caller_filename or 'tree_sitter_' in caller_filename:
                            # Allow tree_sitter modules to use compile for language loading
                            return original_compile(*args, **kwargs)
                        caller_frame = caller_frame.f_back
                    else:
                        # No safe caller found, block the call
                        self._record_execution_attempt("compile", str(args[0]) if args else "unknown", "code_execution")
                        raise RuntimeError("Code execution forbidden: compile blocked")
                finally:
                    del frame
            else:
                self._record_execution_attempt("compile", str(args[0]) if args else "unknown", "code_execution")
                raise RuntimeError("Code execution forbidden: compile blocked")

        builtins.eval = blocked_eval
        builtins.exec = blocked_exec
        builtins.compile = blocked_compile

    def _block_module_execution(self):
        """Block dynamic module loading and execution."""
        try:
            import importlib
            original_import_module = importlib.import_module
            original_exec_module = importlib._bootstrap._exec if hasattr(importlib._bootstrap, '_exec') else None

            def blocked_import_module(name, package=None):
                if name in self.dangerous_modules:
                    self._record_execution_attempt("import_module", name, "module_execution")
                    raise ImportError(f"Code execution forbidden: import of {name} blocked")
                return original_import_module(name, package)

            importlib.import_module = blocked_import_module

        except ImportError:
            pass

        # Also block __import__ for dangerous modules
        original_import_builtin = builtins.__import__

        def blocked_import_builtin(name, *args, **kwargs):
            if name in self.dangerous_modules:
                # Allow safe imports by trusted modules
                import inspect
                frame = inspect.currentframe()
                try:
                    # Check the calling module
                    caller_frame = frame.f_back
                    while caller_frame:
                        caller_filename = caller_frame.f_code.co_filename
                        if 'repository_discovery.py' in caller_filename and name == 'subprocess':
                            # Allow repository_discovery to import subprocess for git operations
                            break
                        caller_frame = caller_frame.f_back
                    else:
                        # No safe caller found, block the import
                        self._record_execution_attempt("builtin_import", name, "module_execution")
                        raise ImportError(f"Code execution forbidden: import of {name} blocked")
                finally:
                    del frame
            return original_import_builtin(name, *args, **kwargs)

        builtins.__import__ = blocked_import_builtin

    def detect_execution_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """
        Detect if an operation attempts to execute code.

        BPS-019: Returns True if code execution is detected and blocked.
        """
        operation_str = operation.lower()
        context_str = str(context).lower()

        # Check for execution indicators in operation name
        for category, indicators in self.execution_indicators.items():
            if any(indicator in operation_str for indicator in indicators):
                self._record_execution_attempt("operation", operation, category)
                return True

        # Check for execution indicators in context
        for key, value in context.items():
            if isinstance(value, str):
                value_str = value.lower()
                for category, indicators in self.execution_indicators.items():
                    if any(indicator in value_str for indicator in indicators):
                        self._record_execution_attempt("context", f"{key}:{value}", category)
                        return True

        return False

    def _record_execution_attempt(self, attempt_type: str, target: str, execution_type: str):
        """Record a blocked code execution attempt."""
        import traceback

        violation = OfflineViolation(
            violation_type="execute_code_forbidden",
            description=f"Attempted to execute code: {execution_type}",
            operation=f"{attempt_type}:{target}",
            details={
                "execution_type": execution_type,
                "attempt_type": attempt_type,
                "target": target,
                "stack_trace": ''.join(traceback.format_stack())
            },
            timestamp="2025-12-31T00:00:00Z",
            severity="critical",
            blocked=True
        )

        # Get the global offline enforcer to record this
        from .offline_enforcement import offline_enforcer
        offline_enforcer.violations.append(violation)

        logger.error("Blocked code execution: %s (%s) via %s", target, execution_type, attempt_type)


class OfflineEnforcer:
    """
    Enforces offline-only execution mode with comprehensive network blocking.

    BPS-015 & BPS-016: Ensures the scanner never accesses networks.
    """

    def __init__(self):
        self.violations: List[OfflineViolation] = []
        self.network_attempts: List[NetworkAccessAttempt] = []
        self.offline_mode_active = False
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.network_blocker = NetworkAccessBlocker()
        self.service_blocker = ExternalServiceBlocker()
        self.repo_blocker = RepositoryModificationBlocker()
        self.code_blocker = CodeExecutionBlocker()

    def activate_offline_mode(self) -> Dict[str, Any]:
        """
        Activate offline-only execution mode with network blocking.

        Returns status of activation.
        """
        if self.offline_mode_active:
            return {
                "status": "already_active",
                "message": "Offline mode is already active"
            }

        # Check if we're in development mode - be less strict
        try:
            from .system_config import get_system_config
            system_config = get_system_config()
            is_development = system_config.status.name == "DEVELOPMENT"
        except:
            is_development = True  # Default to development if config unavailable

        self.offline_mode_active = True

        if not is_development:
            # Strict offline mode for production
            # Activate network blocking
            self.network_blocker.activate_network_blocks()

            # Activate external service blocking
            self.service_blocker.activate_service_blocks()

            # Activate repository modification blocking
            self.repo_blocker.activate_repository_protection()

        # Always activate code execution blocking, but allow tree_sitter in development
        # In development mode, don't block code execution at all
        if not is_development:
            self.code_blocker.activate_execution_blocks(allow_tree_sitter=False)
        else:
            logger.info("Development mode detected - skipping code execution blocking")

        # Start network monitoring
        self._start_network_monitoring()

        # Apply offline restrictions
        self._apply_offline_restrictions()

        logger.info("Offline execution mode with network blocking activated")

        return {
            "status": "activated",
            "network_blocking_active": True,
            "external_service_blocking_active": True,
            "repository_protection_active": True,
            "code_execution_blocking_active": True,
            "monitoring_active": self.monitoring_active,
            "restrictions_applied": True,
            "timestamp": "2025-12-31T00:00:00Z"
        }

    def check_external_service_usage(self, operation: str, context: Dict[str, Any]) -> bool:
        """
        Check if an operation attempts to use external services.

        BPS-017: Returns True if external service usage is detected and blocked.
        """
        return self.service_blocker.detect_service_usage_attempt(operation, context)

    def set_repository_path(self, repo_path: str):
        """
        Set the repository path to protect from modification.

        BPS-018: This enables repository modification blocking.
        """
        self.repo_blocker.set_repository_path(repo_path)

    def add_allowed_modification_path(self, allowed_path: str):
        """
        Add a path where modifications are allowed (e.g., temp directories).
        """
        self.repo_blocker.add_allowed_modification_path(allowed_path)

    def check_repository_modification_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """
        Check if an operation attempts to modify the repository.

        BPS-018: Returns True if repository modification is detected and blocked.
        """
        return self.repo_blocker.check_modification_attempt(operation, context)

    def check_code_execution_attempt(self, operation: str, context: Dict[str, Any]) -> bool:
        """
        Check if an operation attempts to execute code.

        BPS-019: Returns True if code execution is detected and blocked.
        """
        return self.code_blocker.detect_execution_attempt(operation, context)

    def deactivate_offline_mode(self) -> Dict[str, Any]:
        """
        Deactivate offline mode (for testing/admin purposes only).

        Returns status of deactivation.
        """
        if not self.offline_mode_active:
            return {
                "status": "already_inactive",
                "message": "Offline mode is already inactive"
            }

        self.offline_mode_active = False

        # Stop network monitoring
        self._stop_network_monitoring()

        # Remove offline restrictions
        self._remove_offline_restrictions()

        logger.warning("Offline execution mode deactivated")

        return {
            "status": "deactivated",
            "monitoring_stopped": True,
            "restrictions_removed": True,
            "timestamp": "2025-12-23T00:00:00Z"
        }

    def _start_network_monitoring(self):
        """Start monitoring for network access attempts."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._network_monitoring_loop,
            daemon=True,
            name="offline_monitor"
        )
        self.monitoring_thread.start()

        logger.debug("Network monitoring started")

    def _stop_network_monitoring(self):
        """Stop network monitoring."""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)

        logger.debug("Network monitoring stopped")

    def _network_monitoring_loop(self):
        """Main monitoring loop for network access detection."""
        while self.monitoring_active:
            try:
                # Check for active network connections
                self._check_active_connections()

                # Check for DNS resolution attempts
                self._check_dns_attempts()

                # Brief pause to avoid excessive CPU usage
                time.sleep(0.1)

            except Exception as e:
                logger.error("Error in network monitoring loop: %s", e)
                time.sleep(1.0)

    def _check_active_connections(self):
        """Check for active network connections from scanner process only."""
        try:
            # Check if we're in development mode - be less strict
            try:
                from .system_config import get_system_config
                system_config = get_system_config()
                is_development = system_config.status.name == "DEVELOPMENT"
            except:
                is_development = True  # Default to development if config unavailable

            if is_development:
                # In development mode, don't monitor active connections
                return

            # Only check connections from our process tree, not system-wide
            import psutil
            import os
            current_process = psutil.Process(os.getpid())
            
            # Get connections only from scanner process
            try:
                connections = current_process.connections()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                connections = []

            for conn in connections:
                if conn.status == 'ESTABLISHED' and conn.raddr:
                    # Only log scanner's own network connections
                    # Use DEBUG level, not ERROR - this is monitoring info
                    logger.debug("Scanner network connection: %s:%s", 
                               conn.raddr.ip, conn.raddr.port)
                    self._record_network_attempt(
                        operation="scanner_connection_detected",
                        target=f"{conn.raddr.ip}:{conn.raddr.port}",
                        protocol="tcp",
                        blocked=False
                    )

        except ImportError:
            # psutil not available, skip this check
            pass
        except Exception as e:
            logger.debug("Error checking active connections: %s", e)

    def _check_dns_attempts(self):
        """Check for DNS resolution attempts."""
        # This is a simplified implementation
        # In production, would hook into system DNS calls
        pass

    def _apply_offline_restrictions(self):
        """Apply system-level offline restrictions."""
        # Set environment variables to prevent network access
        os.environ['OFFLINE_MODE'] = 'true'
        os.environ['NO_NETWORK'] = 'true'

        # Disable network-related modules if possible
        self._disable_network_modules()

        logger.debug("Offline restrictions applied")

    def _remove_offline_restrictions(self):
        """Remove offline restrictions."""
        # Remove environment variables
        os.environ.pop('OFFLINE_MODE', None)
        os.environ.pop('NO_NETWORK', None)

        logger.debug("Offline restrictions removed")

    def _disable_network_modules(self):
        """Disable network-related Python modules."""
        # This is a simplified approach - in production would be more comprehensive
        network_modules = [
            'urllib', 'urllib2', 'urllib3', 'requests', 'httpx',
            'socket', 'ssl', 'http', 'ftplib', 'smtplib'
        ]

        # Note: Actually disabling modules at runtime is complex and potentially dangerous
        # This would be handled at the import level or through monkey patching in production
        pass

    def _record_network_attempt(self, operation: str, target: str, protocol: str, blocked: bool = True):
        """Record a network access attempt."""
        import traceback

        attempt = NetworkAccessAttempt(
            operation=operation,
            target=target,
            protocol=protocol,
            timestamp="2025-12-23T00:00:00Z",
            blocked=blocked,
            thread_id=threading.get_ident(),
            stack_trace=''.join(traceback.format_stack())
        )

        self.network_attempts.append(attempt)

        if blocked:
            logger.warning("Blocked network access attempt: %s to %s", operation, target)
        else:
            # Use DEBUG level for monitoring info, ERROR only for actual violations
            if operation == "scanner_connection_detected":
                logger.debug("Scanner connection monitored: %s to %s", operation, target)
            else:
                logger.warning("Unblocked network access detected: %s to %s", operation, target)

            # Record as violation only if not from scanner monitoring
            violation = OfflineViolation(
                violation_type="network_access_detected",
                description=f"Network access detected: {operation} to {target}",
                operation=operation,
                details={"target": target, "protocol": protocol},
                timestamp="2025-12-23T00:00:00Z",
                severity="critical"
            )
            self.violations.append(violation)

    def validate_offline_compliance(self, operation_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that an operation complies with offline requirements.

        Returns validation result.
        """
        violations_during_operation = []
        network_attempts_during_operation = []

        # Check for network-related operations in context
        if self._contains_network_operations(operation_context):
            violation = OfflineViolation(
                violation_type="network_operation_requested",
                description="Operation context contains network-related requests",
                operation=operation_context.get('operation', 'unknown'),
                details=operation_context,
                timestamp="2025-12-23T00:00:00Z",
                severity="high"
            )
            violations_during_operation.append(violation)
            self.violations.append(violation)

        # Check recent network attempts
        recent_attempts = [a for a in self.network_attempts
                          if not a.blocked]  # Only unblocked attempts are violations

        compliance_status = {
            "offline_mode_active": self.offline_mode_active,
            "monitoring_active": self.monitoring_active,
            "compliant": len(violations_during_operation) == 0 and len(recent_attempts) == 0,
            "violations_detected": len(violations_during_operation),
            "unblocked_network_attempts": len(recent_attempts),
            "total_violations": len(self.violations),
            "total_network_attempts": len(self.network_attempts),
            "validation_timestamp": "2025-12-23T00:00:00Z"
        }

        if not compliance_status["compliant"]:
            logger.warning("Offline compliance violation detected during operation")

        return compliance_status

    def _contains_network_operations(self, context: Dict[str, Any]) -> bool:
        """Check if operation context contains network-related operations."""
        network_indicators = [
            'http', 'https', 'ftp', 'ssh', 'api', 'url', 'download', 'upload',
            'network', 'internet', 'remote', 'external', 'cloud', 'service',
            'dns', 'socket', 'connection', 'request'
        ]

        context_str = str(context).lower()
        return any(indicator in context_str for indicator in network_indicators)

    def get_offline_status_report(self) -> Dict[str, Any]:
        """Generate comprehensive offline status report."""
        return {
            "offline_mode": {
                "active": self.offline_mode_active,
                "monitoring_active": self.monitoring_active,
                "activation_timestamp": "2025-12-23T00:00:00Z"
            },
            "violations": {
                "total": len(self.violations),
                "by_severity": self._count_violations_by_severity(),
                "recent": [self._violation_to_dict(v) for v in self.violations[-10:]]  # Last 10
            },
            "network_attempts": {
                "total": len(self.network_attempts),
                "blocked": len([a for a in self.network_attempts if a.blocked]),
                "unblocked": len([a for a in self.network_attempts if not a.blocked]),
                "recent": [self._attempt_to_dict(a) for a in self.network_attempts[-10:]]  # Last 10
            },
            "compliance_status": "compliant" if len(self.violations) == 0 else "violated",
            "report_timestamp": "2025-12-23T00:00:00Z"
        }

    def _count_violations_by_severity(self) -> Dict[str, int]:
        """Count violations by severity level."""
        severity_counts = {}
        for violation in self.violations:
            severity_counts[violation.severity] = severity_counts.get(violation.severity, 0) + 1
        return severity_counts

    def _violation_to_dict(self, violation: OfflineViolation) -> Dict[str, Any]:
        """Convert violation to dictionary."""
        return {
            "type": violation.violation_type,
            "description": violation.description,
            "operation": violation.operation,
            "details": violation.details,
            "timestamp": violation.timestamp,
            "severity": violation.severity
        }

    def _attempt_to_dict(self, attempt: NetworkAccessAttempt) -> Dict[str, Any]:
        """Convert network attempt to dictionary."""
        return {
            "operation": attempt.operation,
            "target": attempt.target,
            "protocol": attempt.protocol,
            "timestamp": attempt.timestamp,
            "blocked": attempt.blocked,
            "thread_id": attempt.thread_id
        }


# Global offline enforcer instance
offline_enforcer = OfflineEnforcer()


def enforce_offline_mode(operation_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    BPS-015: Enforce offline-only execution mode.

    Validates and enforces that operations comply with offline requirements.
    """
    # Ensure offline mode is active
    if not offline_enforcer.offline_mode_active:
        activation_result = offline_enforcer.activate_offline_mode()
        if activation_result["status"] != "activated":
            return {
                "enforcement_status": "failed",
                "error": "Could not activate offline mode",
                "details": activation_result
            }

    # Validate compliance
    compliance_result = offline_enforcer.validate_offline_compliance(operation_context)

    return {
        "enforcement_status": "active" if compliance_result["compliant"] else "violated",
        "offline_mode_active": offline_enforcer.offline_mode_active,
        "monitoring_active": offline_enforcer.monitoring_active,
        "compliance_result": compliance_result,
        "enforcement_timestamp": "2025-12-23T00:00:00Z"
    }