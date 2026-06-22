from sqlalchemy import Column, String, Integer, Float, DateTime, JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from src.core.database import Base

class Job(Base):
    """
    Job model to track the status, metadata, and final execution summaries
    of the CSV upload runs.
    """
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, nullable=False, default="pending")  # pending, processing, completed, failed
    
    # Layer E metrics (persisted in database fields)
    total_spend_inr = Column(Float, nullable=True)
    total_spend_usd = Column(Float, nullable=True)
    top_merchants = Column(JSON, nullable=True)  # Stored as serialized JSON list of strings
    anomaly_count = Column(Integer, nullable=True)
    narrative = Column(String, nullable=True)
    risk_level = Column(String, nullable=True)  # low, medium, high

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relational link to children transactions
    transactions = relationship("Transaction", back_populates="job", cascade="all, delete-orphan")
