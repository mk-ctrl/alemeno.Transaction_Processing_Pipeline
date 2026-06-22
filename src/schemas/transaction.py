from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class TransactionResponse(BaseModel):
    """
    Response schema for serializing transaction records.
    Provides strict typing for all parsed and normalized columns.
    """
    id: int
    txn_id: Optional[str] = None
    job_id: str
    
    date: Optional[str] = None
    merchant: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    account_id: Optional[str] = None
    notes: Optional[str] = None

    # Anomaly tracking fields
    is_anomaly: bool = False
    anomaly_reason: Optional[str] = None

    # LLM status indicator
    llm_failed: bool = False

    created_at: datetime

    # Configure Pydantic v2 to load data from SQLAlchemy ORM objects
    model_config = ConfigDict(from_attributes=True)
