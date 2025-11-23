from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ParticipantUpdate(BaseModel):
    total_booked: Optional[int] = None
    payment: Optional[float] = None
    due: Optional[float] = None
    payment_date: Optional[datetime] = None
    payment_time: Optional[str] = None

    class Config:
        extra = "ignore"
