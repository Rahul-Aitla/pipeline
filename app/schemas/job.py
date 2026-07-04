from datetime import date, datetime
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel


class JobUploadResponse(BaseModel):
    job_id: UUID
    status: str


class JobStatusResponse(BaseModel):
    job_id: UUID
    filename: str
    status: str
    row_count_raw: int | None = None
    row_count_clean: int | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class JobListItem(BaseModel):
    id: UUID
    filename: str
    status: str
    row_count_raw: int | None = None
    row_count_clean: int | None = None
    created_at: datetime | None = None


class TransactionResult(BaseModel):
    txn_id: str | None = None
    date: date
    merchant: str
    amount: Decimal
    currency: str
    status: str
    category: str
    account_id: str
    is_anomaly: bool
    anomaly_reason: str | None = None
    llm_category: str | None = None
    llm_failed: bool | None = None


class JobSummaryResult(BaseModel):
    total_spend_inr: Decimal | None = None
    total_spend_usd: Decimal | None = None
    top_merchants: list | None = None
    anomaly_count: int | None = None
    narrative: str | None = None
    risk_level: str | None = None


class JobResultsResponse(BaseModel):
    job_id: UUID
    cleaned_transactions: list[TransactionResult]
    anomalies: list[TransactionResult]
    category_spend_breakdown: dict[str, Decimal]
    summary: JobSummaryResult | None = None
