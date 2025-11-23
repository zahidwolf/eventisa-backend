from sqlalchemy import Column, Integer, Float, DateTime, String, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from server.database import Base
from pydantic import BaseModel, Field
from typing import Optional

class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    total_booked = Column(Integer, nullable=False, default=1)
    payment = Column(Float, nullable=False, default=0.0)
    due = Column(Float, nullable=False, default=0.0)
    payment_date = Column(DateTime, nullable=True)
    payment_time = Column(String, nullable=True)

    # Relationships
    host = relationship("Host", back_populates="participants")
    event = relationship("Event", back_populates="participants")
    user = relationship("User", back_populates="participants")

    # QR Codes linked to this participant
    qrcodes = relationship("QRCode", back_populates="participant", cascade="all, delete-orphan")


class ParticipantCreate(BaseModel):
    host_id: int
    event_id: int
    user_id: int
    total_booked: Optional[int] = 1
    payment: Optional[float] = 0.0
    due: Optional[float] = 0.0