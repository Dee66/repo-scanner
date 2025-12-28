"""Enterprise API Server for Repository Intelligence Scanner."""

import asyncio
import json
import logging
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import uvicorn
import git
import shutil

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import aiofiles

# Import scanner components
try:
    from src.core.pipeline.analysis import execute_pipeline
    from src.core.quality.output_contract import generate_primary_report, generate_machine_output, generate_executive_verdict
    from src.core.exceptions import ScannerError, RepositoryDiscoveryError, AnalysisError, OutputGenerationError, ValidationError
    from src.core.monitoring import get_metrics_collector, get_health_checker, get_performance_monitor, get_alert_manager
    from src.core.system_config import DATA_USAGE_CONFIG
except ImportError as e:
    logging.error(f"Failed to import scanner components: {e}")
    raise

# Helper functions for remote repository scanning
def validate_git_url(url: str) -> bool:
    """Validate Git URL for security and format."""
    import re
    from urllib.parse import urlparse

    # Basic URL validation
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False
    except Exception:
        return False

    # Only allow HTTPS for security
    if parsed.scheme.lower() != 'https':
        return False

    # Block localhost and private IPs
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Repository Intelligence Scanner API",
    description="Enterprise-grade repository analysis API",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

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
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "1.1.0",
        "uptime": "operational"
    }

@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with system metrics."""
    health_checker = get_health_checker()
    return await health_checker.check_system_health()

@app.get("/metrics")
async def get_metrics():
    """Get system metrics."""
    metrics_collector = get_metrics_collector()
    return await metrics_collector.collect_metrics()

@app.get("/performance")
async def get_performance_stats():
    """Get performance monitoring statistics."""
    performance_monitor = get_performance_monitor()
    return await performance_monitor.get_performance_stats()

@app.get("/alerts")
async def get_alerts():
    """Get active alerts."""
    alert_manager = get_alert_manager()
    return {"active_alerts": [alert.__dict__ for alert in alert_manager.get_active_alerts()]}

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
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Start a repository scan job."""
    job_id = str(uuid.uuid4())

    # Create job record
    job = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0.0,
        "message": "Job queued for processing",
        "created_at": datetime.utcnow(),
        "request": request.dict()
    }
    jobs[job_id] = job

    # Add background task
    background_tasks.add_task(process_scan_job, job_id)

    return ScanResponse(
        job_id=job_id,
        status="accepted",
        message="Scan job accepted and queued",
        created_at=job["created_at"],
        estimated_completion=None
    )

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
    """Process a scan job in the background."""
    performance_monitor = get_performance_monitor()
    metrics_collector = get_metrics_collector()

    # Start job performance tracking
    performance_monitor.start_operation("scan_job", {"job_id": job_id})

    job = jobs[job_id]
    job["status"] = "running"
    job["started_at"] = datetime.utcnow()
    job["message"] = "Starting repository analysis"

    try:
        request = job["request"]

        # Determine repository path
        temp_dir = None
        if request.get("repository_path"):
            repo_path = Path(request["repository_path"])
        elif request.get("repository_url"):
            # Validate Git URL
            if not validate_git_url(request["repository_url"]):
                raise ValidationError("Invalid or unsafe Git URL")

            # Clone repository
            temp_dir = tempfile.mkdtemp()
            try:
                repo = git.Repo.clone_from(request["repository_url"], temp_dir, depth=1)
                repo_path = Path(temp_dir)
            except Exception as e:
                if temp_dir:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                raise ValidationError(f"Failed to clone repository: {e}")
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

        # Execute pipeline
        analysis_result = await asyncio.get_event_loop().run_in_executor(
            None, execute_pipeline, str(repo_path)
        )

        # Update progress
        job["progress"] = 75.0
        job["message"] = "Analysis complete, generating reports"

        # Create output directory
        output_dir = Path(f"/tmp/scanner-{job_id}")
        output_dir.mkdir(exist_ok=True)
        job["output_dir"] = str(output_dir)

        # Generate outputs
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
        logger.error(f"Job {job_id} failed: {e}")
        job["status"] = "failed"
        job["message"] = f"Scan failed: {str(e)}"
        job["error"] = str(e)
        job["completed_at"] = datetime.utcnow()

        # Track failed operation
        performance_monitor.complete_operation("scan_job", {
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        })

        # Update metrics for failed scan
        await metrics_collector.record_scan_failure({"error": str(e)})

    finally:
        # Cleanup temp directory if used
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("Repository Intelligence Scanner API starting up")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("Repository Intelligence Scanner API shutting down")

if __name__ == "__main__":
    port = int(os.getenv("REPO_SCANNER_API_PORT", "8080"))
    host = os.getenv("REPO_SCANNER_API_HOST", "127.0.0.1")

    uvicorn.run(
        "src.api_server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
