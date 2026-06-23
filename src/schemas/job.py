from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from src.schemas.transaction import TransactionResponse

class JobResponse(BaseModel):
    """
    Standard job summary metadata response contract.
    """
    id: str
    status: str
    filename: Optional[str] = None
    row_count_raw: Optional[int] = None
    row_count_clean: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobStatusResponse(BaseModel):
    """
    Response contract specifically returned for polling status endpoints.
    """
    job_id: str
    status: str
    anomaly_count: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class JobResultsResponse(BaseModel):
    """
    Full detailed report schema containing processing analytics
    and all associated transaction records.
    """
    id: str
    status: str
    
    # Layer E metrics
    total_spend_inr: Optional[float] = None
    total_spend_usd: Optional[float] = None
    top_merchants: Optional[List[str]] = None
    anomaly_count: Optional[int] = None
    narrative: Optional[str] = None
    risk_level: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    # List of nested child transactions
    transactions: List[TransactionResponse] = []

    model_config = ConfigDict(from_attributes=True)
