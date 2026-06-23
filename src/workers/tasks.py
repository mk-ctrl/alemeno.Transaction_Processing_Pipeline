import logging
from src.workers.celery_app import celery_app
from src.core.database import SessionLocal
from src.models.job import Job
from src.models.transaction import Transaction
from src.services.cleaning import parse_and_clean_csv
from src.services.anomaly import detect_anomalies
from src.services.llm import classify_uncategorised_batch, generate_executive_summary

logger = logging.getLogger("alemeno.workers.tasks")

@celery_app.task(name="alemeno.workers.tasks.process_transaction_job")
def process_transaction_job(job_id: str, csv_content: str):
    """
    Asynchronous Celery task mapping to the execution pipeline (Layer A - E).
    Safely reads, cleans, processes outliers, categorizes via LLM, and aggregates.
    """
    logger.info(f"Task process_transaction_job started for Job ID: {job_id}")
    db = SessionLocal()
    
    try:
        # 1. Fetch parent Job and transition state to processing (Layer A)
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job with ID {job_id} not found in database. Aborting.")
            return False
            
        job.status = "processing"
        db.commit()
        
        # 2. Ingest and Clean the input data (Layer B)
        cleaned_records = parse_and_clean_csv(csv_content)
        
        # 3. Process Statistical Outliers and Logical Anomalies (Layer C)
        cleaned_records = detect_anomalies(cleaned_records)
        
        # 4. Perform Batched LLM Classification on Uncategorised rows (Layer D)
        cleaned_records = classify_uncategorised_batch(cleaned_records)
        
        # 5. Build individual Transaction database records (Layer A)
        transaction_objects = []
        for row in cleaned_records:
            txn_obj = Transaction(
                txn_id=row.get("txn_id"),
                job_id=job_id,
                date=row.get("date"),
                merchant=row.get("merchant"),
                amount=row.get("amount"),
                currency=row.get("currency"),
                status=row.get("status"),
                category=row.get("category"),
                account_id=row.get("account_id"),
                notes=row.get("notes"),
                is_anomaly=row.get("is_anomaly", False),
                anomaly_reason=row.get("anomaly_reason"),
                llm_failed=row.get("llm_failed", False)
            )
            transaction_objects.append(txn_obj)
            
        db.add_all(transaction_objects)
        db.flush()  # Push records to db to count or reference before commit
        
        # 6. Generate Narrative Summary and Metrics (Layer E)
        summary = generate_executive_summary(cleaned_records)
        
        # 7. Persist metrics and complete Job
        job.total_spend_inr = summary.get("total_spend_inr")
        job.total_spend_usd = summary.get("total_spend_usd")
        job.top_merchants = summary.get("top_merchants")
        job.anomaly_count = summary.get("anomaly_count")
        job.narrative = summary.get("narrative")
        job.risk_level = summary.get("risk_level")
        job.status = "completed"
        
        db.commit()
        logger.info(f"Task process_transaction_job successfully finished for Job ID: {job_id}")
        return True
        
    except Exception as e:
        logger.exception(f"Error during execution pipeline for Job ID: {job_id}")
        # Rollback and mark job as failed on unhandled errors
        db.rollback()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = "failed"
                db.commit()
        except Exception as db_err:
            logger.error(f"Failed to set status to FAILED for Job ID: {job_id}: {db_err}")
        return False
        
    finally:
        db.close()
