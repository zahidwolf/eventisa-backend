from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from sqlalchemy.orm import Session
from server.models.user_model import * 
from server.controller.ws_manager import user_manager
from server.cryptography import *
from server.constant_file import (eventisa_email,
                                  password_reset_subject,
                                  eventisa_email_password)
from server.models.otp_records_model import *
from datetime import datetime, timedelta
from server.response_model import ResponseModel, ErrorResponseModel
from server.controller.otp_handler import *


import os
import asyncio

# ------------------ Add New User ------------------
async def add_user(db: Session, user_data: dict):
    new_user = User(**user_data)
    new_user.password=encrypt_password(new_user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Broadcast new user
    await user_manager.broadcast({
        "event": "new_user",
        "data": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "phone_number":new_user.phone_number,
            "image_url": new_user.image_url,
        }
    })
    return new_user.__dict__

async def retrieve_users(db: Session):
    return db.query(User).all()



async def retrieve_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()



async def retrieve_user(db: Session, field: str, value: str):
    if field == "id":
        return db.query(User).filter(User.id == value).first()
    elif field == "email":
        return db.query(User).filter(User.email == value).first()
    elif field == "name":
        return db.query(User).filter(User.name == value).first()
    elif field =="phone_number":
        return db.query(User).filter(User.phone_number==value).first()
    return None

async def retrieve_searched_users(db: Session, field: str, value: str):
    if field == "name":
        return db.query(User).filter(User.name == value).all()
    if field == "phone_number":
        return db.query(User).filter(User.phone_number == value).all()
    if field == "email":
        return db.query(User).filter(User.email == value).all()



async def update_user(db: Session, user_id: int, update_data: dict):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    if user.email!=update_data["email"]:
        return "Invalid to change email"
    for key, val in update_data.items():
        setattr(user, key, val)
    db.commit()
    db.refresh(user)
    return user.__dict__

async def delete_user(db: Session, email: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    
    db.delete(user)
    db.commit()
    return user.__dict__




async def initiate_password_reset_otp(db: Session, email: str, owner_type="user"):
#------------------Generate or update OTP -------------------
    owner = db.query(User).filter(User.email == email).first()
    if not owner:
        return False

    new_otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    otp_record = db.query(OTPRecord).filter(
        OTPRecord.owner_id == owner.id,
        OTPRecord.owner_type == owner_type
    ).first()

    if otp_record:
        if otp_record.expires_at > datetime.utcnow():
            otp_to_send = otp_record.otp
        else:
            otp_record.otp = new_otp
            otp_record.expires_at = expires_at
            db.commit()
            otp_to_send = new_otp
    else:
        otp_record = OTPRecord(
            owner_id=owner.id,
            owner_type=owner_type,
            otp=new_otp,
            expires_at=expires_at
        )
        db.add(otp_record)
        db.commit()
        otp_to_send = new_otp

    email_sent = await send_email(owner.email, otp_to_send)
    if email_sent:
        return {"message": f"OTP sent to {owner.email}"}
    return False

async def password_reset_controller(db: Session, email: str, new_password: str=None):
    
    try:
        #  Retrieve user
        user = await retrieve_user_by_email(db, email)
        if not user:
            return ErrorResponseModel("User not found", 404, f"No user with email {email}")

        if not new_password:
            return ErrorResponseModel("Missing Password", 400, "New password is required for reset")

        # Update password
        user.password = encrypt_password(new_password)
        db.commit()

        return ResponseModel({"email": email}, "Password reset successfully. You can now log in.")

    except Exception as e:
        return ErrorResponseModel("Unexpected server error", 500, str(e))

#---------------Verify OTP for password reset--------------
async def verify_reset_otp_controller(db: Session, email: str, otp: str, owner_type="user"):
    
    owner = db.query(User).filter(User.email == email).first()
    if not owner:
        return ErrorResponseModel("Owner not found", 404, f"No {owner_type} with this email.")

    otp_record = db.query(OTPRecord).filter(
        OTPRecord.owner_id == owner.id,
        OTPRecord.owner_type == owner_type
    ).first()

    if not otp_record:
        return ErrorResponseModel("OTP not found", 404, "No OTP record found.")

    if otp_record.otp != otp:
        return ErrorResponseModel("Invalid OTP", 400, "Incorrect OTP.")

    if otp_record.expires_at < datetime.utcnow():
        db.delete(otp_record)
        db.commit()
        return ErrorResponseModel("Expired OTP", 400, "OTP has expired.")

    # OTP is valid — delete it and allow password reset
    db.delete(otp_record)
    db.commit()
    return ResponseModel({"email": owner.email}, "OTP verified successfully. Proceed to reset password.")

# -------------------- Login user -----------------
async def user_login(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"status": "failed", "msg": "Email not found"}
    if not verify_password(password, user.password):
        return {"status": "failed", "msg": "Wrong password"}
    return {"status": "success", "msg": "Successfully Log in"}