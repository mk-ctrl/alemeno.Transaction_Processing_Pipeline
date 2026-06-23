import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.models.job import Job
from src.schemas.job import JobResponse, JobStatusResponse, JobResultsResponse
from src.workers.tasks import process_transaction_job

logger = logging.getLogger("alemeno.api.routes")
router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/upload", response_model=JobResponse, status_code=201)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts a raw CSV upload, initializes a database Job record with status 'pending',
    triggers the out-of-band processing Celery worker, and instantly responds with the Job metadata.
    """
    logger.info(f"Received file upload request: filename={file.filename}")
    
    # 1. Validate file format extension
    if not file.filename.endswith(".csv"):
        logger.error(f"Invalid file extension uploaded: {file.filename}")
        raise HTTPException(status_code=400, detail="Only CSV file uploads are supported.")
        
    try:
        # 2. Read content from upload stream
        content_bytes = await file.read()
        csv_content = content_bytes.decode("utf-8")
    except Exception as e:
        logger.exception("Failed to parse CSV file content string encoding.")
        raise HTTPException(status_code=400, detail="Malformed file contents or encoding.")
        
    # 3. Create a parent Job tracking record (Layer A)
    new_job = Job(status="pending")
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    logger.info(f"Initialized job record in DB. Job ID: {new_job.id}")
    
    # 4. Trigger asynchronous Celery queue task
    try:
        process_transaction_job.delay(new_job.id, csv_content)
        logger.info(f"Successfully pushed Job ID {new_job.id} to Celery task runner queue.")
    except Exception as queue_err:
        logger.exception(f"Failed to queue task for Job ID {new_job.id}.")
        # Update status to failed as task queueing failed
        new_job.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail="Broker connection failed. Unable to queue processing task.")
        
    return new_job

@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Polls the tracking status and anomaly count metrics of a specific processing Job.
    """
    logger.debug(f"Polling status for Job ID: {job_id}")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job record not found.")
        
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        anomaly_count=job.anomaly_count,
        created_at=job.created_at
    )

@router.get("/{job_id}/results", response_model=JobResultsResponse)
def get_job_results(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the complete processed dataset and LLM summaries for a completed Job.
    """
    logger.info(f"Retrieving results for Job ID: {job_id}")
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job record not found.")
        
    if job.status in ["pending", "processing"]:
        logger.warning(f"Requested results before execution finished. Job ID: {job_id}, Status: {job.status}")
        # Return partial status but empty list to prevent crash
        return JobResultsResponse(
            id=job.id,
            status=job.status,
            created_at=job.created_at,
            updated_at=job.updated_at,
            transactions=[]
        )
        
    return job

@router.get("", response_model=List[JobResponse])
def list_jobs(
    status: Optional[str] = Query(None, description="Filter historic runs by execution status"),
    db: Session = Depends(get_db)
):
    """
    Lists all historical pipeline runs, with optional filtering by status (completed, failed, etc.).
    """
    logger.debug(f"Listing jobs. Status filter: {status}")
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status.strip().lower())
        
    # Order by newest run first
    jobs = query.order_by(Job.created_at.desc()).all()
    return jobs
