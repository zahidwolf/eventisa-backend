from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from server.database import Base

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)


    event_title = Column(String, nullable=False)
    event_banner_img = Column(String, nullable=True)
    event_location = Column(String, nullable=False)
    event_description = Column(Text, nullable=True)
    event_date = Column(DateTime, nullable=False)
    event_time = Column(String, nullable=False)
    event_price = Column(Float, nullable=False)
    total_seat = Column(Integer, nullable=False)
    filled_seat = Column(Integer, default=0)
    event_category=Column(String,nullable=False)
    approval_status = Column(String, default="pending", nullable=False)  # pending, approved, rejected

    # Relationships
    host = relationship("Host", back_populates="events")
    participants = relationship("Participant", back_populates="event", cascade="all, delete-orphan")
    qrcodes = relationship("QRCode", back_populates="event", cascade="all, delete-orphan")
