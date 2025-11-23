from pydantic import BaseModel, EmailStr,field_validator
from typing import Optional

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    phone_number: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        extra = "ignore"
    # @field_validator('password', mode='before')
    # @classmethod
    # def prevent_password_update_in_general_update(cls, v):
    #     if v is not None:
    #         # This line raises an error if a password is included in the request body
    #         raise ValueError(
    #             "Password cannot be updated via this general endpoint. Please use the dedicated /password/change endpoint."
    #         )
    #     return v