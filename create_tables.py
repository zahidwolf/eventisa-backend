#!/usr/bin/env python3
"""
Script to create database tables
Run this after the database is created to set up all tables
"""
import sys
import os

# Add the app directory to the path
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_dir)

from server.database import Base, engine
from server.models.user_model import User
from server.models.host_model import Host
from server.models.event_model import Event
from server.models.participant_model import Participant
from server.models.qrcode_model import QRCode
from server.models.otp_records_model import OTPRecord

def create_tables():
    """Create all database tables"""
    try:
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    create_tables()

