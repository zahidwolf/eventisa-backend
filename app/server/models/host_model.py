from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from server.database import Base

class Host(Base):
    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    phone_number = Column(String, nullable=False)
    password = Column(String, nullable=False)
    division = Column(String, nullable=False)
    district = Column(String, nullable=False)
    upzilla_thana = Column(String, nullable=False)
    address = Column(String, nullable=False)
    image_url = Column(String, nullable=True)
    verification = Column(String, nullable=True, default="unverified") 

    # Relationships
    events = relationship("Event", back_populates="host", cascade="all, delete-orphan")
    participants = relationship("Participant", back_populates="host", cascade="all, delete-orphan")
    qrcodes = relationship("QRCode", back_populates="host", cascade="all, delete-orphan")
