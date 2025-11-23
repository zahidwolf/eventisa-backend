from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class QRCodeUpdate(BaseModel):
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    qr_data: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        extra = "ignore"
