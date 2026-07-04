from decimal import Decimal
from fastapi import APIRouter, UploadFile, File, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.job import Job
from app.models.transaction import Transaction
from app.models.job_summary import JobSummary
from app.schemas.job import (
    JobUploadResponse,
    JobStatusResponse,
    JobListItem,
    JobResultsResponse,
    TransactionResult,
    JobSummaryResult,
)
from app.workers.tasks import process_transactions

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/upload", response_model=JobUploadResponse, status_code=201)
def upload_job(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    content = file.file.read().decode("utf-8")

    job = Job(filename=file.filename, raw_csv=content, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    process_transactions.delay(str(job.id))

    return JobUploadResponse(job_id=job.id, status=job.status)


@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id,
        filename=job.filename,
        status=job.status,
        row_count_raw=job.row_count_raw,
        row_count_clean=job.row_count_clean,
        created_at=job.created_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
    )


@router.get("/{job_id}/results", response_model=JobResultsResponse)
def get_job_results(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    txns = db.query(Transaction).filter(Transaction.job_id == job.id).all()

    cleaned = [
        TransactionResult(
            txn_id=t.txn_id,
            date=t.date,
            merchant=t.merchant,
            amount=t.amount,
            currency=t.currency,
            status=t.status,
            category=t.category,
            account_id=t.account_id,
            is_anomaly=t.is_anomaly,
            anomaly_reason=t.anomaly_reason,
            llm_category=t.llm_category,
            llm_failed=t.llm_failed,
        )
        for t in txns
    ]

    anomalies = [t for t in cleaned if t.is_anomaly]

    breakdown: dict[str, Decimal] = {}
    for t in txns:
        if t.status == "SUCCESS":
            cat = t.llm_category if t.llm_category else t.category
            breakdown[cat] = breakdown.get(cat, Decimal("0")) + t.amount

    summary = db.query(JobSummary).filter(JobSummary.job_id == job.id).first()

    return JobResultsResponse(
        job_id=job.id,
        cleaned_transactions=cleaned,
        anomalies=anomalies,
        category_spend_breakdown=breakdown,
        summary=JobSummaryResult(
            total_spend_inr=summary.total_spend_inr if summary else None,
            total_spend_usd=summary.total_spend_usd if summary else None,
            top_merchants=summary.top_merchants if summary else None,
            anomaly_count=summary.anomaly_count if summary else None,
            narrative=summary.narrative if summary else None,
            risk_level=summary.risk_level if summary else None,
        ) if summary else None,
    )


@router.get("", response_model=list[JobListItem])
def list_jobs(status: str | None = Query(None), db: Session = Depends(get_db)):
    query = db.query(Job)
    if status:
        query = query.filter(Job.status == status)
    jobs = query.order_by(Job.created_at.desc()).all()

    return [
        JobListItem(
            id=j.id,
            filename=j.filename,
            status=j.status,
            row_count_raw=j.row_count_raw,
            row_count_clean=j.row_count_clean,
            created_at=j.created_at,
        )
        for j in jobs
    ]
