from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from server.database import Base

class QRCode(Base):
    __tablename__ = "qrcodes"

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, ForeignKey("hosts.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    participant_id = Column(Integer, ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)

    user_email = Column(String, nullable=False)
    user_name = Column(String, nullable=False)
    qr_data = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    status = Column(String, nullable=True)
    verified = Column(String, default="unverified")  
    scanned_at = Column(DateTime, nullable=True)

    # Relationships
    host = relationship("Host", back_populates="qrcodes")
    event = relationship("Event", back_populates="qrcodes")
    user = relationship("User", back_populates="qrcodes")
    participant = relationship("Participant", back_populates="qrcodes")
