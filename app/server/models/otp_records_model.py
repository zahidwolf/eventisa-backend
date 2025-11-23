from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from server.database import Base
from datetime import datetime

class OTPRecord(Base):
    __tablename__ = "otp_records"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, nullable=False)       # ID of the entity (user, host, admin, etc.)
    owner_type = Column(String(50), nullable=False)  # Type of the entity
    
    otp = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
