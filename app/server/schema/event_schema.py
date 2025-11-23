from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EventUpdate(BaseModel):
    event_title: Optional[str] = None
    event_banner_img: Optional[str] = None
    event_location: Optional[str] = None
    event_description: Optional[str] = None
    event_date: Optional[datetime] = None
    event_time: Optional[str] = None
    event_price: Optional[float] = None
    total_seat: Optional[int] = None
    filled_seat: Optional[int] = None
    event_category:Optional[str]=None

    class Config:
        extra = "ignore"
