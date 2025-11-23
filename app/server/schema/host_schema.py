from pydantic import BaseModel, EmailStr
from typing import Optional

class HostUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    division: Optional[str] = None
    district: Optional[str] = None
    upzilla_thana: Optional[str] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    verification:Optional[str]=None

    class Config:
        extra = "ignore"


