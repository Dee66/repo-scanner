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
except ImportError as e:
    logging.error(f"Failed to import scanner components: {e}")
    raise

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

@app.get("/alerts/history")
async def get_alert_history(hours: int = 24):
    """Get alert history for the last N hours."""
    alert_manager = get_alert_manager()
    return {"alert_history": [alert.__dict__ for alert in alert_manager.get_alert_history(hours)]}

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
        if request.get("repository_path"):
            repo_path = Path(request["repository_path"])
        elif request.get("repository_url"):
            # Clone repository
            with tempfile.TemporaryDirectory() as temp_dir:
                repo_path = Path(temp_dir) / "repo"
                # TODO: Implement git clone
                raise NotImplementedError("Git URL scanning not yet implemented")
        else:
            raise ValueError("Either repository_path or repository_url must be provided")

        # Validate repository
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path {repo_path} does not exist")

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
