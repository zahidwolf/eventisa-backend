from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from server.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    password = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    image_url = Column(String, nullable=True)

    # Relationships
    participants = relationship("Participant", back_populates="user", cascade="all, delete-orphan")
    qrcodes = relationship("QRCode", back_populates="user", cascade="all, delete-orphan")
