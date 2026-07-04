import uuid
from sqlalchemy import Column, String, Integer, Text, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from app.database import Base


class JobSummary(Base):
    __tablename__ = "job_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    total_spend_inr = Column(Numeric(14, 2), default=0)
    total_spend_usd = Column(Numeric(14, 2), default=0)
    top_merchants = Column(JSON, default=list)
    anomaly_count = Column(Integer, default=0)
    narrative = Column(Text, nullable=True)
    risk_level = Column(String(10), default="low")
