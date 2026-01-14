"""Enterprise API Server for Repository Intelligence Scanner."""

import asyncio
import json
import logging
import os
import tempfile
import uuid
import time
import re
import html
import ipaddress
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import uvicorn
import git
import shutil

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Response
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import aiofiles

# Optional input sanitization imports
try:
    from .input_sanitization import get_input_sanitizer, sanitize_input
    INPUT_SANITIZATION_AVAILABLE = True
except ImportError:
    INPUT_SANITIZATION_AVAILABLE = False

def sanitize_string(input_str: str, max_length: int = 1000) -> str:
    """Sanitize string input to prevent injection attacks."""
    if INPUT_SANITIZATION_AVAILABLE:
        return sanitize_input(input_str, 'text', max_length=max_length)
    else:
        # Fallback implementation
        if not isinstance(input_str, str):
            raise ValueError("Input must be a string")
        sanitized = input_str.replace('\x00', '').replace('\r', '').replace('\n', ' ')
        sanitized = html.escape(sanitized)
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        return sanitized

def validate_url(url: str) -> bool:
    """Validate URL for security."""
    if INPUT_SANITIZATION_AVAILABLE:
        try:
            sanitize_input(url, 'url')
            return True
        except ValueError:
            return False
    else:
        # Fallback implementation
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ['http', 'https']:
                return False
            if not parsed.netloc:
                return False
            if os.getenv("REPO_SCANNER_ENV") == "production":
                hostname = parsed.hostname.lower()
                if hostname in ['localhost', '127.0.0.1', '::1']:
                    return False
                try:
                    ip = ipaddress.ip_address(hostname)
                    if ip.is_private or ip.is_loopback:
                        return False
                except ValueError:
                    pass
            return True
        except Exception:
            return False

def validate_filename(filename: str) -> str:
    """Validate and sanitize filename."""
    if INPUT_SANITIZATION_AVAILABLE:
        return sanitize_input(filename, 'filename')
    else:
        # Fallback implementation
        if not filename or len(filename) > 255:
            raise ValueError("Invalid filename length")
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
        sanitized = re.sub(r'[^\w\.-]', '', sanitized)
        if '..' in sanitized or '/' in sanitized or '\\' in sanitized:
            raise ValueError("Invalid filename: directory traversal detected")
        return sanitized

def validate_repository_name(name: str) -> str:
    """Validate repository name."""
    if INPUT_SANITIZATION_AVAILABLE:
        return sanitize_input(name, 'text', max_length=100)
    else:
        # Fallback implementation
        if not name or len(name) > 100:
            raise ValueError("Invalid repository name length")
        if not re.match(r'^[a-zA-Z0-9._-]+$', name):
            raise ValueError("Invalid repository name format")
        return name

# Optional tracing imports
try:
    from .tracing import setup_distributed_tracing, get_tracer, instrument_fastapi_app
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False

# Optional alerting imports
try:
    from .alerting import get_alert_manager
    ALERTING_AVAILABLE = True
except ImportError:
    ALERTING_AVAILABLE = False

# Optional dashboard imports
try:
    from .dashboard import create_dashboard_routes
    DASHBOARD_AVAILABLE = True
except ImportError:
    DASHBOARD_AVAILABLE = False

# Optional logging aggregation imports
try:
    from .logging_aggregation import (
        setup_structured_logging, create_correlation_middleware,
        get_log_aggregator, correlation_context
    )
    LOGGING_AGGREGATION_AVAILABLE = True
except ImportError:
    LOGGING_AGGREGATION_AVAILABLE = False

# Import timeout and resource limits
from src.core.timeouts_and_limits import api_timeout, api_limits, health_check_timeout, TimeoutError, ResourceLimitError

# Import scanner components
try:
    from src.core.pipeline.analysis import execute_pipeline
    from src.core.quality.output_contract import generate_primary_report, generate_machine_output, generate_executive_verdict
    from src.core.exceptions import ScannerError, RepositoryDiscoveryError, AnalysisError, OutputGenerationError, ValidationError
    from src.optional.monitoring import get_metrics_collector, get_health_checker, get_performance_monitor, get_alert_manager
    from src.core.system_config import DATA_USAGE_CONFIG
    from src.optional.circuit_breaker import circuit_breaker, GIT_OPERATIONS_CONFIG, get_circuit_breaker_registry
    from src.optional.error_handling import with_error_handling, async_with_error_handling, FILESYSTEM_RETRY_CONFIG
    from src.optional.recovery_strategies import register_all_recovery_strategies

    # Initialize recovery strategies
    register_all_recovery_strategies()
except ImportError as e:
    logging.error(f"Failed to import scanner components: {e}")
    raise

# Helper functions for remote repository scanning
def validate_git_url(url: str) -> bool:
    """Validate Git URL for security and format."""
    # First sanitize the input
    url = sanitize_string(url, 2000)

    # Use the new validation function
    if not validate_url(url):
        return False

    parsed = urlparse(url)

    # Only allow secure schemes
    if parsed.scheme not in ["https", "ssh", "git"]:
        return False

    # Block localhost and private IPs (additional check beyond validate_url)
    hostname = parsed.hostname.lower()
    if hostname in ['localhost', '127.0.0.1', '::1'] or hostname.startswith('192.168.') or hostname.startswith('10.') or hostname.startswith('172.'):
        return False

    # Allow common Git hosting services
    allowed_domains = [
        'github.com', 'gitlab.com', 'bitbucket.org',
        'codeberg.org', 'sourceforge.net', 'git.kernel.org'
    ]

    if hostname not in allowed_domains:
        return False

    # Block command injection attempts - reject URLs with shell metacharacters
    dangerous_chars = [';', '|', '`', '$', '(', ')', '<', '>', '&', '!', '{', '}', '[', ']', '*', '?', '~']
    if any(char in url for char in dangerous_chars):
        return False

    return True

def validate_repository_path(path: str) -> bool:
    """Validate repository path for security - prevent path traversal attacks."""
    from pathlib import Path

    # Sanitize input first
    path = sanitize_string(path, 1000)

    # Normalize path separators (handle both / and \)
    normalized_path = path.replace('\\', '/')

    # Convert to Path object for validation
    path_obj = Path(normalized_path)

    # Reject paths that contain .. (parent directory traversal)
    if '..' in path_obj.parts:
        return False

    # Reject absolute paths that point to system directories
    system_paths = ['/etc', '/bin', '/sbin', '/usr', '/var', '/root', '/home/root', '/proc', '/sys', '/dev']
    if path.startswith('/') and any(path.startswith(sys_path) for sys_path in system_paths):
        return False

    # Reject Windows system paths (normalized)
    windows_system_paths = ['C:/Windows', 'C:/System32', 'C:/Program Files']
    normalized_upper = normalized_path.upper()
    if any(normalized_upper.startswith(sys_path.upper()) for sys_path in windows_system_paths):
        return False

    # Reject paths with suspicious characters that could be used for traversal
    suspicious_chars = ['~', '$', '`']
    if any(char in path for char in suspicious_chars):
        return False

    return True

def check_repo_limits(repo_path: Path, max_files: int = None, max_size_mb: int = None) -> None:
    """Check repository size limits to prevent abuse."""
    # Use config values if not specified
    if max_files is None or max_size_mb is None:
        is_ci = os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'
        limits = DATA_USAGE_CONFIG["limits"]["automated_scans" if is_ci else "manual_scans"]
        max_files = max_files or limits["max_files"]
        max_size_mb = max_size_mb or limits["max_size_mb"]
    
    total_files = 0
    total_size = 0
    large_files = []
    
    for root, dirs, files in os.walk(repo_path):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')

        for file in files:
            total_files += 1
            if total_files > max_files:
                raise ValidationError(f"Repository exceeds maximum file limit of {max_files}")

            file_path = Path(root) / file
            try:
                file_size = file_path.stat().st_size
                total_size += file_size
                
                # Track files over threshold
                threshold = DATA_USAGE_CONFIG["monitoring"]["track_large_files_threshold_mb"] * 1024 * 1024
                if file_size > threshold:
                    large_files.append((str(file_path.relative_to(repo_path)), file_size / (1024*1024)))
                
                if total_size > max_size_mb * 1024 * 1024:
                    raise ValidationError(f"Repository exceeds maximum size limit of {max_size_mb}MB")
            except OSError:
                # Skip files we can't stat
                continue
    
    # Log data usage for monitoring
    size_mb = total_size / (1024 * 1024)
    logger.info(f"Repository size: {size_mb:.2f}MB, {total_files} files")
    if large_files:
        logger.warning(f"Large files detected: {large_files}")
    
    # Additional check for automated processes
    if DATA_USAGE_CONFIG["monitoring"]["ci_stricter_limits"]:
        is_ci = os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true'
        if is_ci:
            ci_limits = DATA_USAGE_CONFIG["limits"]["automated_scans"]
            if size_mb > ci_limits["max_size_mb"]:
                raise ValidationError(f"Repository too large for automated scanning: {size_mb:.2f}MB (limit: {ci_limits['max_size_mb']}MB)")
            if total_files > ci_limits["max_files"]:
                raise ValidationError(f"Repository has too many files for automated scanning: {total_files} (limit: {ci_limits['max_files']})")

@circuit_breaker("git_clone", GIT_OPERATIONS_CONFIG)
@with_error_handling("clone_repository", "api_server", FILESYSTEM_RETRY_CONFIG)
def clone_git_repository(url: str, target_dir: str, **kwargs) -> git.Repo:
    """Clone Git repository with circuit breaker and comprehensive error handling protection."""
    return git.Repo.clone_from(url, target_dir, **kwargs)

# Configure structured logging
if LOGGING_AGGREGATION_AVAILABLE:
    logger = setup_structured_logging("api_server")
    logger.info("Structured logging with aggregation enabled")
else:
    # Fallback to basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.info("Basic logging enabled (structured logging not available)")

app = FastAPI(
    title="Repository Intelligence Scanner API",
    description="Enterprise-grade repository analysis API",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure distributed tracing (optional)
if TRACING_AVAILABLE:
    tracing_enabled = setup_distributed_tracing("repo-scanner-api")
    if tracing_enabled:
        instrument_fastapi_app(app)
else:
    logger.info("Distributed tracing disabled (tracing module not available)")

# Add correlation middleware for request tracing
if LOGGING_AGGREGATION_AVAILABLE:
    app.middleware("http")(create_correlation_middleware())
    logger.info("Correlation middleware added for request tracing")
else:
    logger.info("Correlation middleware not available")

# Add security middleware with advanced rate limiting and abuse prevention
@app.middleware("http")
async def security_middleware(request, call_next):
    """Security middleware with advanced rate limiting and abuse prevention."""
    from fastapi.responses import JSONResponse
    from .rate_limiting import get_abuse_prevention_engine, get_progressive_delay
    import asyncio

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent", "")
    path = request.url.path
    method = request.method

    # Get abuse prevention engine
    abuse_engine = get_abuse_prevention_engine()
    progressive_delay = get_progressive_delay()

    # Analyze request for suspicious activity
    try:
        body = await request.body()
        body_str = body.decode('utf-8', errors='ignore') if body else ""
    except:
        body_str = ""

    analysis = abuse_engine.analyze_request(client_ip, user_agent, path, body_str)

    # Apply progressive delay for suspicious requests
    if analysis['suspicious']:
        delay = progressive_delay.get_delay(client_ip)
        if delay > 0:
            await asyncio.sleep(delay)
            progressive_delay.record_violation(client_ip)

    # Check concurrent request limits
    if not abuse_engine.check_concurrent_requests(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Too many concurrent requests. Please try again later."}
        )

    try:
        # Check rate limits based on endpoint
        rule_name = 'api_general'
        if path.startswith('/api/scan'):
            rule_name = 'api_scan'
        elif path.startswith('/health'):
            rule_name = 'api_health'
        elif path.startswith('/dashboard'):
            rule_name = 'dashboard'

        allowed, retry_after = abuse_engine.check_rate_limit(client_ip, rule_name)

        if not allowed:
            if retry_after:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded. Try again later.",
                        "retry_after": int(retry_after)
                    },
                    headers={"Retry-After": str(int(retry_after))}
                )
            else:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Access denied."}
                )

        # Check request size if body is present
        if hasattr(request, '_body') and request._body:
            if not abuse_engine.check_request_size(len(request._body)):
                abuse_engine.record_failed_attempt(client_ip)
                return JSONResponse(
                    status_code=413,
                    content={"error": "Request too large."}
                )

        # Process request
        response = await call_next(request)

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Add HSTS in production
        if os.getenv("REPO_SCANNER_ENV") == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

    finally:
        # Always release concurrent request slot
        abuse_engine.release_concurrent_request(client_ip)

# Add middleware for HTTP request metrics collection
@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Middleware to collect HTTP request metrics."""
    from .metrics_collector import get_metrics_collector
    import time

    metrics_collector = get_metrics_collector()
    start_time = time.time()

    # Record request start
    method = request.method
    path = request.url.path
    metrics_collector.increment_counter("http_requests_total", labels={"method": method, "endpoint": path})

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        # Record successful response
        status_code = response.status_code
        metrics_collector.observe_histogram("http_request_duration_seconds",
                                          duration,
                                          labels={"method": method, "endpoint": path, "status": str(status_code)})
        metrics_collector.increment_counter("http_responses_total",
                                          labels={"method": method, "endpoint": path, "status": str(status_code)})

        return response

    except Exception as e:
        duration = time.time() - start_time

        # Record error response
        metrics_collector.observe_histogram("http_request_duration_seconds",
                                          duration,
                                          labels={"method": method, "endpoint": path, "status": "500"})
        metrics_collector.increment_counter("http_responses_total",
                                          labels={"method": method, "endpoint": path, "status": "500"})

        # Re-raise the exception
        raise

# Add dashboard routes (optional)
if DASHBOARD_AVAILABLE:
    create_dashboard_routes(app)
    logger.info("Dashboard routes added")
else:
    logger.info("Dashboard not available (dashboard module not loaded)")

# In-memory job storage (use Redis/external storage for production)
jobs: Dict[str, Dict[str, Any]] = {}

class ScanRequest(BaseModel):
    """Scan request model."""
    repository_url: Optional[str] = Field(None, description="Git repository URL")
    repository_path: Optional[str] = Field(None, description="Local repository path")
    branch: str = Field("main", description="Git branch to scan")
    include_submodules: bool = Field(False, description="Include git submodules")
    output_format: str = Field("both", choices=["markdown", "json", "both"], description="Output format")
    report_type: str = Field("comprehensive", choices=["comprehensive", "verdict", "both"], description="Report type")

class ScanResponse(BaseModel):
    """Scan response model."""
    job_id: str
    status: str
    message: str
    created_at: datetime
    estimated_completion: Optional[datetime] = None

class JobStatus(BaseModel):
    """Job status model."""
    job_id: str
    status: str
    progress: float
    message: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/health")
@health_check_timeout
async def health_check():
    """Health check endpoint with comprehensive 99.999% uptime monitoring."""
    health_checker = get_health_checker()
    health_data = await health_checker.check_system_health()
    
    # Return simplified response for basic health check
    return {
        "status": health_data.get("status", "unknown"),
        "overall_healthy": health_data.get("overall_healthy", False),
        "timestamp": health_data.get("timestamp"),
        "uptime": health_data.get("uptime", {}).get("uptime_percentage", 0),
        "sla_compliant": health_data.get("sla_compliance", {}).get("compliant", False),
        "version": health_data.get("version", "1.1.0"),
        "checks_count": len(health_data.get("checks", {}))
    }

@app.get("/health/detailed")
@health_check_timeout
async def detailed_health_check():
    """Detailed health check with system metrics."""
    health_checker = get_health_checker()
    health_data = await health_checker.check_system_health()
    
    # Add circuit breaker metrics
    circuit_breaker_registry = get_circuit_breaker_registry()
    circuit_breaker_metrics = circuit_breaker_registry.get_all_metrics()
    
    # Add error handling metrics
    from .error_handling import get_error_handler
    error_handler = get_error_handler()
    error_metrics = error_handler.get_error_metrics()
    
    health_data["circuit_breakers"] = circuit_breaker_metrics
    health_data["error_handling"] = error_metrics
    
    return health_data

@app.get("/metrics")
async def get_metrics():
    """Get application and system metrics in JSON format."""
    metrics_collector = get_metrics_collector()
    metrics = await metrics_collector.collect_metrics()

    return {
        "application": metrics.get("application", {}),
        "system": metrics.get("system", {}),
        "timestamp": metrics.get("timestamp", datetime.utcnow().isoformat())
    }

@app.get("/performance")
async def get_performance_stats():
    """Get performance monitoring statistics."""
    performance_monitor = get_performance_monitor()
    return performance_monitor.get_performance_stats()

@app.get("/alerts")
async def get_alerts():
    """Get active alerts."""
    alert_manager = get_alert_manager()
    return {"active_alerts": [alert.__dict__ for alert in alert_manager.get_active_alerts()]}

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a scan job and its results."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Clean up job data
    if "output_dir" in job:
        output_dir = Path(job["output_dir"])
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)

    # Remove from jobs dict
    del jobs[job_id]

    return {"message": f"Job {job_id} deleted successfully"}

@app.get("/data-usage")
async def get_data_usage():
    """Get data usage statistics and limits for monitoring."""
    return {
        "current_limits": DATA_USAGE_CONFIG["limits"],
        "recommendations": {
            "typical_repo_size": "1-50MB",
            "large_repo_threshold": f"{DATA_USAGE_CONFIG['monitoring']['track_large_files_threshold_mb']}MB+ files",
            "automated_scan_limit": f"{DATA_USAGE_CONFIG['limits']['automated_scans']['max_size_mb']}MB",
            "manual_scan_limit": f"{DATA_USAGE_CONFIG['limits']['manual_scans']['max_size_mb']}MB"
        },
        "monitoring": DATA_USAGE_CONFIG["monitoring"],
        "environment": {
            "is_ci": os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true',
            "applied_limits": "automated_scans" if (os.getenv('CI') == 'true' or os.getenv('GITHUB_ACTIONS') == 'true') else "manual_scans"
        }
    }

@app.post("/scan", response_model=ScanResponse)
@api_timeout
@api_limits
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Start a repository scan job."""
    # Sanitize inputs first
    if INPUT_SANITIZATION_AVAILABLE:
        sanitizer = get_input_sanitizer()
        try:
            # Sanitize repository URL if provided
            if request.repository_url:
                request.repository_url = sanitizer.sanitize_input(request.repository_url, 'repository_url')

            # Sanitize repository path if provided
            if request.repository_path:
                request.repository_path = sanitizer.sanitize_input(request.repository_path, 'filepath')

            # Sanitize branch name
            request.branch = sanitizer.sanitize_input(request.branch, 'branch_name')

            # Sanitize output format
            if hasattr(request, 'output_format'):
                request.output_format = sanitizer.sanitize_input(request.output_format, 'text', max_length=20)

            # Sanitize report type
            if hasattr(request, 'report_type'):
                request.report_type = sanitizer.sanitize_input(request.report_type, 'text', max_length=20)
        except ValueError as e:
            message = str(e)
            if "maximum length" in message.lower():
                raise HTTPException(status_code=413, detail=message)
            raise HTTPException(status_code=400, detail=message)

    # Validate request before accepting
    if not request.repository_path and not request.repository_url:
        raise HTTPException(status_code=422, detail="Either repository_path or repository_url must be provided")

    if request.repository_path:
        # Check for oversized payload (path too long)
        if len(request.repository_path) > 4096:  # Reasonable path length limit
            raise HTTPException(status_code=413, detail="Repository path too long (max 4096 characters)")
        
        # Validate for path traversal attacks
        if not validate_repository_path(request.repository_path):
            raise HTTPException(status_code=400, detail="Invalid repository path - path traversal detected")
        
        repo_path = Path(request.repository_path)
        if not repo_path.exists():
            raise HTTPException(status_code=400, detail=f"Repository path {repo_path} does not exist")

    if request.repository_url:
        # Check for oversized URL
        if len(request.repository_url) > 2048:  # Reasonable URL length limit
            raise HTTPException(status_code=413, detail="Repository URL too long (max 2048 characters)")
        
        if not validate_git_url(request.repository_url):
            raise HTTPException(status_code=400, detail="Invalid or unsafe Git URL")

    # Validate output format
    if hasattr(request, 'output_format') and request.output_format not in ["json", "markdown", "html", "both"]:
        raise HTTPException(status_code=400, detail="Invalid output format. Must be one of: json, markdown, html, both")

    job_id = str(uuid.uuid4())

    # Create job record
    job = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0.0,
        "message": "Job queued for processing",
        "created_at": datetime.utcnow(),
        "request": request.model_dump()
    }
    jobs[job_id] = job

    # Add background task
    background_tasks.add_task(process_scan_job, job_id)

    response_data = ScanResponse(
        job_id=job_id,
        status="accepted",
        message="Scan job accepted and queued",
        created_at=job["created_at"],
        estimated_completion=None
    )
    
    # Convert to dict and handle datetime serialization
    response_dict = response_data.model_dump()
    response_dict["created_at"] = response_dict["created_at"].isoformat()
    
    return JSONResponse(status_code=202, content=response_dict)

@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get the status of a scan job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatus(**job)

@app.get("/results/{job_id}/{filename}")
async def get_job_result(job_id: str, filename: str):
    """Download scan results."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")

    # Construct file path
    output_dir = Path(job.get("output_dir", f"/tmp/scanner-{job_id}"))
    file_path = output_dir / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )

@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Job already finished")

    job["status"] = "cancelled"
    job["message"] = "Job cancelled by user"
    job["completed_at"] = datetime.utcnow()

    return {"message": "Job cancelled successfully"}

async def process_scan_job(job_id: str):
    """Process a scan job in the background with comprehensive error handling."""
    from .error_handling import async_with_error_handling, ErrorContext, get_error_handler
    
    performance_monitor = get_performance_monitor()
    metrics_collector = get_metrics_collector()
    error_handler = get_error_handler()

    # Start distributed tracing span if enabled
    span = None
    if TRACING_AVAILABLE:
        tracer = get_tracer(__name__)
        if tracer:
            span = tracer.start_as_span("process_scan_job", attributes={"job_id": job_id})
            span.set_attribute("component", "api_server")

    context = ErrorContext(
        operation="process_scan_job",
        component="api_server",
        metadata={"job_id": job_id}
    )

    job = jobs.get(job_id)
    if not job:
        logger.error(f"Job {job_id} not found when attempting processing")
        return

    temp_dir = None
    job.setdefault("started_at", datetime.utcnow())

    try:
        request = job.get("request", {})

        output_format = request.get("output_format", "both")
        report_type = request.get("report_type", "comprehensive")

        # Determine repository path
        if request.get("repository_path"):
            repo_path = Path(request["repository_path"])
        elif request.get("repository_url"):
            # Start repository cloning span
            clone_span = None
            if span:
                clone_span = tracer.start_as_span("clone_repository", parent=span, attributes={"repository_url": request["repository_url"]})
            
            # Validate Git URL
            if not validate_git_url(request["repository_url"]):
                raise ValidationError("Invalid or unsafe Git URL")

            # Clone repository
            temp_dir = tempfile.mkdtemp()
            try:
                clone_kwargs = {"depth": 1}
                if request.get("branch") and request["branch"] != "main":
                    clone_kwargs["branch"] = request["branch"]
                if request.get("include_submodules"):
                    clone_kwargs["recursive"] = True
                repo = clone_git_repository(request["repository_url"], temp_dir, **clone_kwargs)
                repo_path = Path(temp_dir)
            except Exception as e:
                if temp_dir:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                raise ValidationError(f"Failed to clone repository: {e}")
            finally:
                if clone_span:
                    clone_span.end()
        else:
            raise ValueError("Either repository_path or repository_url must be provided")

        # Validate repository
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path {repo_path} does not exist")

        # Check repo limits if cloned
        if temp_dir:
            check_repo_limits(repo_path)

        # Update progress
        job["progress"] = 25.0
        job["message"] = "Repository validated, starting analysis"

        # Execute pipeline with tracing
        analysis_span = None
        if span:
            analysis_span = tracer.start_as_span("execute_pipeline", parent=span, attributes={"repo_path": str(repo_path)})
        
        analysis_result = await asyncio.get_event_loop().run_in_executor(
            None, execute_pipeline, str(repo_path)
        )
        
        if analysis_span:
            analysis_span.set_attribute("files_analyzed", len(analysis_result.get("files", [])))
            analysis_span.end()

        # Update progress
        job["progress"] = 75.0
        job["message"] = "Analysis complete, generating reports"

        # Create output directory
        output_dir = Path(f"/tmp/scanner-{job_id}")
        output_dir.mkdir(exist_ok=True)
        job["output_dir"] = str(output_dir)

        # Generate outputs with tracing
        report_span = None
        if span:
            report_span = tracer.start_as_span("generate_reports", parent=span, attributes={"output_format": output_format, "report_type": report_type})
        
        output_format = request.get("output_format", "both")
        report_type = request.get("report_type", "comprehensive")

        if report_type in ["comprehensive", "both"]:
            report_content = generate_primary_report(analysis_result, str(repo_path))
            report_path = output_dir / "scan_report.md"
            report_path.write_text(report_content)

        if report_type in ["verdict", "both"]:
            verdict_content = generate_executive_verdict(analysis_result, str(repo_path))
            verdict_path = output_dir / "verdict_report.md"
            verdict_path.write_text(verdict_content)

        if output_format in ["json", "both"]:
            json_data = generate_machine_output(analysis_result, str(repo_path))
            json_path = output_dir / "scan_report.json"
            with open(json_path, 'w') as f:
                json.dump(json_data, f, indent=2, sort_keys=True)
        
        if report_span:
            report_span.end()

        # Complete job
        job["status"] = "completed"
        job["progress"] = 100.0
        job["message"] = "Scan completed successfully"
        job["completed_at"] = datetime.utcnow()
        job["result"] = {
            "files_analyzed": len(analysis_result.get("files", [])),
            "risk_level": analysis_result.get("risk_assessment", {}).get("overall_risk", "unknown"),
            "execution_time": (job["completed_at"] - job["started_at"]).total_seconds()
        }

        # Complete performance tracking
        performance_monitor.complete_operation("scan_job", {
            "job_id": job_id,
            "status": "success",
            "files_analyzed": len(analysis_result.get("files", [])),
            "execution_time": job["result"]["execution_time"]
        })

        # Update metrics
        await metrics_collector.record_scan_completion(job["result"])

        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        # Classify and handle the error
        context = error_handler.classify_error(e, context)
        error_handler.log_error(e, context)

        # Update job status
        job["status"] = "failed"
        job["message"] = f"Scan failed: {str(e)}"
        job["error"] = str(e)
        job["error_category"] = context.category.value
        job["error_severity"] = context.severity.value
        job["completed_at"] = datetime.utcnow()

        # Attempt recovery if possible
        try:
            recovery_result = error_handler.attempt_recovery(e, context)
            if recovery_result is not None:
                # Recovery succeeded, update job with recovery result
                job["status"] = "recovered"
                job["message"] = "Scan recovered from error"
                job["recovery_result"] = str(recovery_result)
                logger.info(f"Job {job_id} recovered from error")
            else:
                logger.warning(f"Job {job_id} failed with no recovery possible")
        except Exception as recovery_error:
            logger.error(f"Recovery failed for job {job_id}: {recovery_error}")

        # Track failed operation
        performance_monitor.complete_operation("scan_job", {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
            "error_category": context.category.value,
            "error_severity": context.severity.value
        })

        # Update metrics for failed scan
        await metrics_collector.record_scan_failure({
            "error": str(e),
            "category": context.category.value,
            "severity": context.severity.value
        })

        # Set span error if tracing enabled
        if span:
            span.set_attribute("error", True)
            span.set_attribute("error_message", str(e))
            span.set_attribute("error_category", context.category.value)

    finally:
        # Close main tracing span
        if span:
            span.end()
        
        # Cleanup temp directory if used
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

# Log aggregation endpoints
if LOGGING_AGGREGATION_AVAILABLE:
    @app.get("/api/logs/recent")
    async def get_recent_logs(limit: int = 100):
        """Get recent logs."""
        aggregator = get_log_aggregator()
        logs = aggregator.get_recent_logs(limit)
        return {"logs": logs, "count": len(logs)}

    @app.get("/api/logs/correlation/{correlation_id}")
    async def get_logs_by_correlation(correlation_id: str):
        """Get logs for a specific correlation ID."""
        aggregator = get_log_aggregator()
        logs = aggregator.get_logs_by_correlation(correlation_id)
        return {"correlation_id": correlation_id, "logs": logs, "count": len(logs)}

    @app.get("/api/logs/component/{component}")
    async def get_logs_by_component(component: str, limit: int = 100):
        """Get logs for a specific component."""
        aggregator = get_log_aggregator()
        logs = aggregator.get_logs_by_component(component, limit)
        return {"component": component, "logs": logs, "count": len(logs)}

    @app.get("/api/logs/level/{level}")
    async def get_logs_by_level(level: str, limit: int = 100):
        """Get logs for a specific level."""
        aggregator = get_log_aggregator()
        logs = aggregator.get_logs_by_level(level.upper(), limit)
        return {"level": level.upper(), "logs": logs, "count": len(logs)}

    @app.get("/api/logs/search")
    async def search_logs(query: str, limit: int = 100):
        """Search logs containing the query string."""
        aggregator = get_log_aggregator()
        logs = aggregator.search_logs(query, limit)
        return {"query": query, "logs": logs, "count": len(logs)}

    @app.get("/api/logs/stats")
    async def get_log_stats():
        """Get log aggregation statistics."""
        aggregator = get_log_aggregator()
        with aggregator.lock:
            total_logs = len(aggregator.logs)
            correlation_count = len(aggregator.correlation_index)
            component_counts = {}
            level_counts = {}

            for log in aggregator.logs:
                component = log.get('component', 'unknown')
                level = log.get('level', 'UNKNOWN')

                component_counts[component] = component_counts.get(component, 0) + 1
                level_counts[level] = level_counts.get(level, 0) + 1

        return {
            "total_logs": total_logs,
            "correlation_ids": correlation_count,
            "component_breakdown": component_counts,
            "level_breakdown": level_counts
        }

    logger.info("Log aggregation endpoints added")
else:
    logger.info("Log aggregation endpoints not available")

# Security audit endpoints
try:
    from .security_audit import run_security_audit, generate_security_report, SecurityFinding
    SECURITY_AUDIT_AVAILABLE = True
except ImportError:
    SECURITY_AUDIT_AVAILABLE = False

if SECURITY_AUDIT_AVAILABLE:
    @app.post("/api/security/audit")
    async def run_security_audit_endpoint():
        """Run comprehensive security audit."""
        try:
            findings = run_security_audit()
            return {
                "status": "completed",
                "findings_count": len(findings),
                "findings": [asdict(finding) for finding in findings]
            }
        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            return {"error": str(e)}

    @app.get("/api/security/audit/report")
    async def get_security_report():
        """Get security audit report."""
        try:
            findings = run_security_audit()
            report = generate_security_report(findings)
            return {
                "report": report,
                "findings_count": len(findings)
            }
        except Exception as e:
            logger.error(f"Security report generation failed: {e}")
            return {"error": str(e)}

    logger.info("Security audit endpoints added")
else:
    logger.info("Security audit not available")

# Input sanitization endpoints
if INPUT_SANITIZATION_AVAILABLE:
    @app.post("/api/sanitize")
    async def sanitize_input_endpoint(data: Dict[str, Any]):
        """Sanitize input data."""
        try:
            input_type = data.get('type', 'text')
            input_data = data.get('data')
            strict = data.get('strict', True)
            max_length = data.get('max_length')

            if input_data is None:
                return {"error": "No input data provided"}

            sanitizer = get_input_sanitizer()
            sanitized = sanitizer.sanitize_input(
                input_data,
                input_type,
                strict=strict,
                max_length=max_length
            )

            return {
                "original": str(input_data)[:100] + "..." if len(str(input_data)) > 100 else str(input_data),
                "sanitized": sanitized,
                "type": input_type,
                "changed": str(input_data) != str(sanitized)
            }
        except ValueError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Input sanitization failed: {e}")
            return {"error": "Internal sanitization error"}

    @app.get("/api/sanitize/types")
    async def get_sanitization_types():
        """Get available sanitization types."""
        sanitizer = get_input_sanitizer()
        return {
            "types": list(sanitizer.content_validators.keys()),
            "description": "Available input sanitization types"
        }

    @app.post("/api/validate")
    async def validate_input_endpoint(data: Dict[str, Any]):
        """Validate input data without sanitizing."""
        try:
            input_type = data.get('type', 'text')
            input_data = data.get('data')

            if input_data is None:
                return {"valid": False, "error": "No input data provided"}

            sanitizer = get_input_sanitizer()
            # Try to sanitize - if it succeeds, input is valid
            try:
                sanitizer.sanitize_input(input_data, input_type, strict=True)
                return {"valid": True}
            except ValueError as e:
                return {"valid": False, "error": str(e)}

        except Exception as e:
            logger.error(f"Input validation failed: {e}")
            return {"error": "Internal validation error"}

    # Rate Limiting and Abuse Prevention Endpoints
    @app.get("/api/rate-limit/stats")
    async def get_rate_limit_stats():
        """Get rate limiting and abuse prevention statistics."""
        try:
            from .rate_limiting import get_abuse_prevention_engine
            engine = get_abuse_prevention_engine()
            stats = engine.get_stats()

            # Add additional metadata
            stats.update({
                "description": "Rate limiting and abuse prevention statistics",
                "rules": {
                    rule_name: {
                        "max_requests": rule.max_requests,
                        "window_seconds": rule.window_seconds,
                        "block_duration_seconds": rule.block_duration_seconds,
                        "description": rule.description
                    }
                    for rule_name, rule in engine.rate_limit_rules.items()
                }
            })

            return stats
        except Exception as e:
            logger.error(f"Failed to get rate limit stats: {e}")
            return {"error": "Internal error"}

    @app.get("/api/rate-limit/client/{client_ip}")
    async def get_client_rate_limit_info(client_ip: str):
        """Get rate limiting information for a specific client."""
        try:
            from .rate_limiting import get_abuse_prevention_engine
            engine = get_abuse_prevention_engine()

            # Get request history
            request_times = list(engine.request_history.get(client_ip, []))
            now = time.time()

            # Calculate stats
            requests_last_minute = len([t for t in request_times if now - t < 60])
            requests_last_hour = len([t for t in request_times if now - t < 3600])

            # Check if blocked
            blocked = client_ip in engine.blocked_ips
            blocked_until = engine.blocked_ips.get(client_ip) if blocked else None

            return {
                "client_ip": client_ip,
                "requests_last_minute": requests_last_minute,
                "requests_last_hour": requests_last_hour,
                "total_requests": len(request_times),
                "blocked": blocked,
                "blocked_until": blocked_until,
                "suspicious": engine.is_ip_suspicious(client_ip),
                "whitelisted": client_ip in engine.ip_whitelist,
                "blacklisted": client_ip in engine.ip_blacklist,
                "active_requests": engine.active_requests.get(client_ip, 0),
                "failed_attempts": len(engine.failed_attempts.get(client_ip, []))
            }
        except Exception as e:
            logger.error(f"Failed to get client info: {e}")
            return {"error": "Internal error"}

    @app.post("/api/rate-limit/blacklist/{client_ip}")
    async def add_to_blacklist(client_ip: str, reason: str = "api_request"):
        """Add client IP to blacklist."""
        try:
            from .rate_limiting import get_abuse_prevention_engine
            engine = get_abuse_prevention_engine()
            engine.add_to_blacklist(client_ip, reason)
            return {"status": "success", "message": f"IP {client_ip} added to blacklist"}
        except Exception as e:
            logger.error(f"Failed to blacklist IP: {e}")
            return {"error": "Internal error"}

    @app.delete("/api/rate-limit/blacklist/{client_ip}")
    async def remove_from_blacklist(client_ip: str):
        """Remove client IP from blacklist."""
        try:
            from .rate_limiting import get_abuse_prevention_engine
            engine = get_abuse_prevention_engine()
            engine.remove_from_blacklist(client_ip)
            return {"status": "success", "message": f"IP {client_ip} removed from blacklist"}
        except Exception as e:
            logger.error(f"Failed to remove from blacklist: {e}")
            return {"error": "Internal error"}

    @app.post("/api/rate-limit/whitelist/{client_ip}")
    async def add_to_whitelist(client_ip: str, reason: str = "api_request"):
        """Add client IP to whitelist."""
        try:
            from .rate_limiting import get_abuse_prevention_engine
            engine = get_abuse_prevention_engine()
            engine.add_to_whitelist(client_ip, reason)
            return {"status": "success", "message": f"IP {client_ip} added to whitelist"}
        except Exception as e:
            logger.error(f"Failed to whitelist IP: {e}")
            return {"error": "Internal error"}

    @app.delete("/api/rate-limit/whitelist/{client_ip}")
    async def remove_from_whitelist(client_ip: str):
        """Remove client IP from whitelist."""
        try:
            from .rate_limiting import get_abuse_prevention_engine
            engine = get_abuse_prevention_engine()
            engine.ip_whitelist.discard(client_ip)
            return {"status": "success", "message": f"IP {client_ip} removed from whitelist"}
        except Exception as e:
            logger.error(f"Failed to remove from whitelist: {e}")
            return {"error": "Internal error"}

    @app.post("/api/rate-limit/reset/{client_ip}")
    async def reset_client_state(client_ip: str):
        """Reset rate limiting state for a client."""
        try:
            from .rate_limiting import get_abuse_prevention_engine, get_progressive_delay
            engine = get_abuse_prevention_engine()
            delay_manager = get_progressive_delay()

            # Reset various states
            if client_ip in engine.request_history:
                del engine.request_history[client_ip]
            if client_ip in engine.blocked_ips:
                del engine.blocked_ips[client_ip]
            if client_ip in engine.failed_attempts:
                del engine.failed_attempts[client_ip]
            engine.suspicious_ips.discard(client_ip)
            engine.active_requests[client_ip] = 0
            delay_manager.reset_violations(client_ip)

            return {"status": "success", "message": f"Client {client_ip} state reset"}
        except Exception as e:
            logger.error(f"Failed to reset client state: {e}")
            return {"error": "Internal error"}

    @app.post("/api/rate-limit/cleanup")
    async def cleanup_expired_blocks():
        """Manually trigger cleanup of expired blocks."""
        try:
            from .rate_limiting import get_abuse_prevention_engine
            engine = get_abuse_prevention_engine()
            engine.cleanup_expired_blocks()
            return {"status": "success", "message": "Expired blocks cleaned up"}
        except Exception as e:
            logger.error(f"Failed to cleanup blocks: {e}")
            return {"error": "Internal error"}

    logger.info("Input sanitization endpoints added")
else:
    logger.info("Input sanitization not available")

@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("Repository Intelligence Scanner API starting up")

    # Start alerting monitoring if available
    if ALERTING_AVAILABLE and os.getenv('REPO_SCANNER_ENABLE_ALERTING', 'false').lower() == 'true':
        try:
            alert_manager = get_alert_manager()
            metrics_collector = get_metrics_collector()
            alert_manager.start_monitoring(metrics_collector)
            logger.info("Alert monitoring started")
        except Exception as e:
            logger.error(f"Failed to start alert monitoring: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("Repository Intelligence Scanner API shutting down")

    # Stop alerting monitoring
    if ALERTING_AVAILABLE:
        try:
            alert_manager = get_alert_manager()
            alert_manager.stop_monitoring()
            logger.info("Alert monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping alert monitoring: {e}")

# Security Incident Response Endpoints
@app.get("/api/incidents")
async def get_incidents(status: str = None, severity: str = None, limit: int = 50):
    """Get security incidents with optional filtering."""
    try:
        from .security_incident_response import get_incident_response
        incident_response = get_incident_response()

        incidents = incident_response.incidents

        # Apply filters
        if status:
            incidents = {k: v for k, v in incidents.items() if v.status.value == status}
        if severity:
            incidents = {k: v for k, v in incidents.items() if v.severity.value == severity}

        # Convert to dict and limit results
        result = {}
        for incident_id, incident in list(incidents.items())[-limit:]:
            result[incident_id] = {
                "incident_id": incident.incident_id,
                "title": incident.title,
                "description": incident.description,
                "severity": incident.severity.value,
                "status": incident.status.value,
                "incident_type": incident.incident_type.value,
                "created_at": incident.created_at,
                "updated_at": incident.updated_at,
                "source_ip": incident.source_ip,
                "affected_endpoints": list(incident.affected_endpoints),
                "event_count": len(incident.events),
                "automated_actions_taken": incident.automated_actions_taken,
                "manual_actions_required": incident.manual_actions_required,
                "tags": list(incident.tags)
            }

        return {"incidents": result, "total": len(result)}
    except Exception as e:
        logger.error(f"Failed to get incidents: {e}")
        return {"error": "Internal error"}

@app.get("/api/incidents/{incident_id}")
async def get_incident_details(incident_id: str):
    """Get detailed information about a specific incident."""
    try:
        from .security_incident_response import get_incident_response
        incident_response = get_incident_response()

        incident = incident_response.get_incident(incident_id)
        if not incident:
            return {"error": "Incident not found"}

        # Convert events to dict
        events = []
        for event in incident.events:
            events.append({
                "event_id": event.event_id,
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "severity": event.severity.value,
                "source_ip": event.source_ip,
                "user_agent": event.user_agent,
                "endpoint": event.endpoint,
                "description": event.description,
                "correlation_id": event.correlation_id
            })

        return {
            "incident_id": incident.incident_id,
            "title": incident.title,
            "description": incident.description,
            "severity": incident.severity.value,
            "status": incident.status.value,
            "incident_type": incident.incident_type.value,
            "created_at": incident.created_at,
            "updated_at": incident.updated_at,
            "source_ip": incident.source_ip,
            "affected_endpoints": list(incident.affected_endpoints),
            "events": events,
            "assigned_to": incident.assigned_to,
            "resolution_notes": incident.resolution_notes,
            "automated_actions_taken": incident.automated_actions_taken,
            "manual_actions_required": incident.manual_actions_required,
            "tags": list(incident.tags)
        }
    except Exception as e:
        logger.error(f"Failed to get incident details: {e}")
        return {"error": "Internal error"}

@app.put("/api/incidents/{incident_id}/status")
async def update_incident_status(incident_id: str, data: Dict[str, Any]):
    """Update incident status and add notes."""
    try:
        from .security_incident_response import get_incident_response, IncidentStatus
        incident_response = get_incident_response()

        status_str = data.get("status")
        notes = data.get("notes", "")
        assigned_to = data.get("assigned_to")

        if not status_str:
            return {"error": "Status is required"}

        try:
            status = IncidentStatus(status_str)
        except ValueError:
            return {"error": f"Invalid status: {status_str}"}

        success = incident_response.update_incident_status(
            incident_id, status, notes, assigned_to
        )

        if success:
            return {"status": "success", "message": f"Incident {incident_id} updated"}
        else:
            return {"error": "Incident not found"}
    except Exception as e:
        logger.error(f"Failed to update incident status: {e}")
        return {"error": "Internal error"}

@app.get("/api/incidents/stats")
async def get_incident_stats():
    """Get incident statistics."""
    try:
        from .security_incident_response import get_incident_response
        incident_response = get_incident_response()
        stats = incident_response.get_incident_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get incident stats: {e}")
        return {"error": "Internal error"}

@app.post("/api/incidents/{incident_id}/escalate")
async def escalate_incident(incident_id: str, reason: str = "Manual escalation"):
    """Manually escalate an incident."""
    try:
        from .security_incident_response import get_incident_response, IncidentStatus
        incident_response = get_incident_response()

        incident = incident_response.get_incident(incident_id)
        if not incident:
            return {"error": "Incident not found"}

        incident.tags.add("escalated")
        incident.manual_actions_required.append(f"Escalated: {reason}")
        incident.status = IncidentStatus.INVESTIGATING

        return {"status": "success", "message": f"Incident {incident_id} escalated"}
    except Exception as e:
        logger.error(f"Failed to escalate incident: {e}")
        return {"error": "Internal error"}

@app.post("/api/security-events/report")
async def report_security_event_endpoint(data: Dict[str, Any]):
    """Manually report a security event."""
    try:
        from .security_incident_response import report_security_event, IncidentSeverity

        event_type = data.get("event_type")
        severity_str = data.get("severity", "medium")
        source_ip = data.get("source_ip")
        description = data.get("description", "")

        if not event_type or not source_ip:
            return {"error": "event_type and source_ip are required"}

        # Convert severity string to enum
        severity_mapping = {
            "low": IncidentSeverity.LOW,
            "medium": IncidentSeverity.MEDIUM,
            "high": IncidentSeverity.HIGH,
            "critical": IncidentSeverity.CRITICAL
        }
        severity = severity_mapping.get(severity_str.lower(), IncidentSeverity.MEDIUM)

        event_id = report_security_event(
            event_type=event_type,
            severity=severity,
            source_ip=source_ip,
            user_agent=data.get("user_agent", ""),
            endpoint=data.get("endpoint", ""),
            description=description,
            raw_data=data.get("raw_data", {})
        )

        return {"status": "success", "event_id": event_id, "message": "Security event reported"}
    except Exception as e:
        logger.error(f"Failed to report security event: {e}")
        return {"error": "Internal error"}

# Secure Configuration Management Endpoints
@app.get("/api/config")
async def get_configuration(include_sensitive: bool = False):
    """Get current configuration (sensitive values masked by default)."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()
        config = config_manager.get_all(include_sensitive=include_sensitive)

        return {
            "configuration": config,
            "last_modified": config_manager.current_config.last_modified.isoformat(),
            "version": config_manager.current_config.version,
            "encrypted_keys": list(config_manager.current_config.encrypted_keys)
        }
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        return {"error": "Internal error"}

@app.get("/api/config/{key}")
async def get_configuration_key(key: str):
    """Get a specific configuration key."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()

        if key not in config_manager._config_schemas:
            return {"error": f"Unknown configuration key: {key}"}

        schema = config_manager._config_schemas[key]
        value = config_manager.get(key)

        return {
            "key": key,
            "value": value if not schema.sensitive else "***MASKED***",
            "type": schema.type.__name__,
            "required": schema.required,
            "sensitive": schema.sensitive,
            "scope": schema.scope.value,
            "description": schema.description
        }
    except Exception as e:
        logger.error(f"Failed to get configuration key: {e}")
        return {"error": "Internal error"}

@app.put("/api/config/{key}")
async def set_configuration_key(key: str, data: Dict[str, Any]):
    """Set a configuration key value."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()

        value = data.get("value")
        if value is None:
            return {"error": "Value is required"}

        source = data.get("source", "api")
        user = data.get("user")
        reason = data.get("reason")

        success = config_manager.set(key, value, source=source, user=user, reason=reason)

        if success:
            return {"status": "success", "message": f"Configuration {key} updated"}
        else:
            return {"error": "Failed to update configuration"}
    except Exception as e:
        logger.error(f"Failed to set configuration key: {e}")
        return {"error": str(e)}

@app.delete("/api/config/{key}")
async def delete_configuration_key(key: str, data: Dict[str, Any] = None):
    """Delete a configuration key."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()

        source = data.get("source", "api") if data else "api"
        user = data.get("user") if data else None
        reason = data.get("reason") if data else None

        success = config_manager.delete(key, source=source, user=user, reason=reason)

        if success:
            return {"status": "success", "message": f"Configuration {key} deleted"}
        else:
            return {"error": f"Configuration key {key} not found"}
    except Exception as e:
        logger.error(f"Failed to delete configuration key: {e}")
        return {"error": str(e)}

@app.post("/api/config/validate")
async def validate_configuration():
    """Validate current configuration against schema."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()

        errors = config_manager.validate_configuration()

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "total_keys": len(config_manager.current_config.data),
            "validated_keys": len(config_manager._config_schemas)
        }
    except Exception as e:
        logger.error(f"Failed to validate configuration: {e}")
        return {"error": "Internal error"}

@app.post("/api/config/reload")
async def reload_configuration():
    """Reload configuration from disk."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()

        success = config_manager.reload_configuration()

        if success:
            return {"status": "success", "message": "Configuration reloaded"}
        else:
            return {"error": "Failed to reload configuration"}
    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        return {"error": "Internal error"}

@app.post("/api/config/backup")
async def backup_configuration(data: Dict[str, Any] = None):
    """Create a configuration backup."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()

        reason = data.get("reason", "api_request") if data else "api_request"
        backup_file = config_manager.backup_configuration(reason)

        if backup_file:
            return {"status": "success", "backup_file": backup_file}
        else:
            return {"error": "Failed to create backup"}
    except Exception as e:
        logger.error(f"Failed to create configuration backup: {e}")
        return {"error": "Internal error"}

@app.post("/api/config/restore")
async def restore_configuration(data: Dict[str, Any]):
    """Restore configuration from backup."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()

        backup_file = data.get("backup_file")
        if not backup_file:
            return {"error": "backup_file is required"}

        success = config_manager.restore_configuration(backup_file)

        if success:
            return {"status": "success", "message": f"Configuration restored from {backup_file}"}
        else:
            return {"error": "Failed to restore configuration"}
    except Exception as e:
        logger.error(f"Failed to restore configuration: {e}")
        return {"error": str(e)}

@app.get("/api/config/audit")
async def get_configuration_audit(key: str = None, limit: int = 50):
    """Get configuration audit trail."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()

        audit_trail = config_manager.get_audit_trail(key=key, limit=limit)

        return {
            "audit_trail": audit_trail,
            "total_entries": len(config_manager.audit_trail),
            "filtered_key": key
        }
    except Exception as e:
        logger.error(f"Failed to get configuration audit: {e}")
        return {"error": "Internal error"}

@app.get("/api/config/schema")
async def get_configuration_schema():
    """Get configuration schema definitions."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()

        schema_info = {}
        for key, schema in config_manager._config_schemas.items():
            schema_info[key] = {
                "type": schema.type.__name__,
                "required": schema.required,
                "default": schema.default,
                "sensitive": schema.sensitive,
                "scope": schema.scope.value,
                "description": schema.description
            }

        return {
            "schema": schema_info,
            "total_keys": len(schema_info)
        }
    except Exception as e:
        logger.error(f"Failed to get configuration schema: {e}")
        return {"error": "Internal error"}

@app.post("/api/config/rotate-key")
async def rotate_encryption_key(data: Dict[str, Any]):
    """Rotate the configuration encryption key."""
    try:
        from .secure_config import get_config_manager
        config_manager = get_config_manager()

        new_key = data.get("new_key")
        if not new_key:
            return {"error": "new_key is required"}

        success = config_manager.rotate_encryption_key(new_key)

        if success:
            return {"status": "success", "message": "Encryption key rotated"}
        else:
            return {"error": "Failed to rotate encryption key"}
    except Exception as e:
        logger.error(f"Failed to rotate encryption key: {e}")
        return {"error": "Internal error"}

if __name__ == "__main__":
    port = int(os.getenv("REPO_SCANNER_API_PORT", "8080"))
    host = os.getenv("REPO_SCANNER_API_HOST", "127.0.0.1")

    uvicorn.run(
        "src.optional.api_server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
