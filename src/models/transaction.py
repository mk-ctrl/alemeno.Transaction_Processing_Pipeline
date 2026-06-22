from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.core.database import Base

class Transaction(Base):
    """
    Transaction model representing individual transaction records parsed
    from raw uploads.
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    txn_id = Column(String, nullable=True)  # Raw CSV transaction ID (can be null or duplicate before cleaning)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    
    date = Column(String, nullable=True)        # Format converted to strict ISO 8601 string
    merchant = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String, nullable=True)    # Normalized uppercase
    status = Column(String, nullable=True)      # Forced uppercase SUCCESS/FAILED/PENDING
    category = Column(String, nullable=True)    # Nulls mapped to 'Uncategorised', refined by LLM
    account_id = Column(String, nullable=True)
    notes = Column(String, nullable=True)

    # Outlier / Anomaly logic results
    is_anomaly = Column(Boolean, default=False, nullable=False)
    anomaly_reason = Column(String, nullable=True)

    # LLM Categorization failure flag
    llm_failed = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relational link back to the parent Job
    job = relationship("Job", back_populates="transactions")

# Establish bi-directional relationship in Job model by adding:
# Job.transactions = relationship("Transaction", back_populates="job", cascade="all, delete-orphan")
# (We will import this/register this in models/__init__.py or directly in the Job model if needed)
