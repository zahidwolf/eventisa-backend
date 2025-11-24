from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from server.routes.user_route import router as UserRouter
from server.routes.host_route import router as HostRouter
from server.routes.event_route import router as EventRouter
from server.routes.participant_route import router as ParticipantRouter
from server.routes.qr_code_route import router as QRcodeRouter

from server.database import Base, engine
from server.models.user_model import User
from server.models.otp_records_model import OTPRecord
from server.models.qrcode_model import QRCode
from server.models.event_model import Event
from server.models.participant_model import Participant
from server.models.host_model import Host

app = FastAPI()

# Mount static files directory for serving uploaded images
# The uploads directory is relative to the app directory
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
uploads_dir = os.path.join(base_dir, "uploads")
if os.path.exists(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

app.include_router(UserRouter, tags=["User"], prefix="/user")
app.include_router(HostRouter, tags=["Host"], prefix="/host")
app.include_router(EventRouter, tags=["Event"], prefix="/event")
app.include_router(ParticipantRouter, tags=["Participant"], prefix="/participant")
app.include_router(QRcodeRouter, tags=["QRcode"], prefix="/scan_qr")

# Create all tables (must be after importing all models)
# Wrap in try-except to allow server to start even if database is not available
try:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")
except Exception as e:
    print(f"Warning: Could not create database tables: {e}")
    print("Server will start, but database operations will fail until database is configured.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000", "http://localhost:3001"],  
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS", "DELETE", "PUT"],
    allow_headers=["*"],
)

