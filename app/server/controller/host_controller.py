from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from sqlalchemy.orm import Session
from server.models.host_model import * 
from server.controller.ws_manager import host_manager
from server.cryptography import *
from server.constant_file import (eventisa_email,
                                  password_reset_subject,
                                  eventisa_email_password)
from server.models.otp_records_model import *
from datetime import datetime, timedelta
from server.response_model import ResponseModel, ErrorResponseModel
from server.controller.otp_handler import *


# ------------------ Add Host ------------------
async def add_host(db:Session,host_data:dict):
    new_host= Host(**host_data)
    new_host.password=encrypt_password(new_host.password)
    db.add(new_host)
    db.commit()
    db.refresh(new_host)

    await host_manager.broadcast({
        "event":"new_host",
        "data":{
        "id": new_host.id,
        "name": new_host.name,
        "email": new_host.email,
        "phone_number": new_host.phone_number,
        "division": new_host.division,
        "district": new_host.district,
        "upzilla_thana": new_host.upzilla_thana,
        "address": new_host.address,
        "image_url": new_host.image_url,
        }
    })

    await send_otp(db,new_host.email,"verification","host")

    return new_host.__dict__

#------------------- host verification --------------------------

async def resedning_otp_for_verification(db:Session,email:str,owner_type="host"):
    owner = db.query(Host).filter(Host.email == email).first()
    if not owner:
        return ErrorResponseModel("Owner not found", 404, f"No {owner_type} with this email.")

    otp_record = db.query(OTPRecord).filter(
        OTPRecord.owner_id == owner.id,
        OTPRecord.owner_type == owner_type
    ).first()

    if otp_record and otp_record.expires_at < datetime.utcnow():
        db.delete(otp_record)
        db.commit()
        return ErrorResponseModel("Expired OTP", 400, "OTP has expired.")
    
    await send_otp(db,email,"verification","host")


#------------------- host verification --------------------------

async def verification_of_host(db:Session,email:str,otp:str,owner_type="host"):
    owner = db.query(Host).filter(Host.email == email).first()
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

    owner = db.query(Host).filter(Host.email == email).first()
    setattr(owner,"verification","verified")
    db.commit()
    db.refresh(owner)
    
    return ResponseModel({"email": owner.email}, "Host Verified")



# -------------------- Login host -----------------
async def host_login(db:Session,email:str,password:str):
    host=db.query(Host).filter(Host.email==email).first()
    if not host:
        return {"status":"failed","msg":"Email not found"}
    if (host.verification=="unverified"):
        return {"status":"failed","msg":"Unverified"}
    if not (verify_password(password,host.password)):
        return {"status":"failed","msg":"Wrong password"}
    return {"status":"success","msg":"Successfully Log in"}




# ------------------ Retrieve Hosts ------------------
async def retrieve_hosts(db:Session):
    return db.query(Host).all()

# ------------------ Retrieve Host ------------------
async def retrieve_host(db:Session,field:str,value:str):
    if field=="id":
        return db.query(Host).filter(Host.id==value).first()
    elif field=="email":
        return db.query(Host).filter(Host.email==value).first()
    elif field=="name":
        return db.query(Host).filter(Host.name==value).first()
    elif field=="phone_number":
        return db.query(Host).filter(Host.phone_number==value).first()
    

# ------------------ Retrieve Hosts ------------------
async def retrieve_user(db:Session,field:str,value:str):
    if field=="name":
        return db.query(Host).filter(Host.name==value).all()
    if field=="phone_number":
        return db.query(Host).filter(Host.phone_number==value).all()
    
# ------------------ Update Host ------------------
async def update_host(db:Session,host_id:int,update_data:dict):
    host=db.query(Host).filter(Host.id==host_id).first()
    if not host:
        return None
    # print("got it 1")
    if "email" in update_data and host.email!=update_data["email"]:
        return "Invalid to change email"
    # print("got it 2")
    for key,val in update_data.items():
        setattr(host,key,val)

    db.commit()
    db.refresh(host)
    return host.__dict__


# ------------------ Delete Host ------------------
async def delete_host(db:Session,email:str):
    host=db.query(Host).filter(Host.email==email).first()
    if not host:
        return None
    
    db.delete(host)
    db.commit()

    return host.__dict__


async def send_otp(db:Session,email:str,message:str,owner_type:str="host"):
    owner = db.query(Host).filter(Host.email == email).first()
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

    email_sent = await send_email(owner.email, otp_to_send,message)
    if email_sent:
        return {"message": f"OTP sent to {owner.email}"}
    return False


# ------------------ Password Reset ------------------

async def password_reset(db:Session,email:str,new_password:str=None):
    try:
        host=await retrieve_host(db,"email",email)
        if not host:
            return ErrorResponseModel("Host not found", 404, f"No host with email {email}")

        if not new_password:
            return ErrorResponseModel("Missing Password", 400, "New password is required for reset")
        
        host.password=encrypt_password(new_password)
        db.commit()
        return ResponseModel({"email": email}, "Password reset successfully. You can now log in.")

    except Exception as e:
        return ErrorResponseModel("Unexpected server error", 500, str(e))


#---------------Verify OTP for password reset--------------
async def verify_reset_otp_controller(db:Session,email:str,otp:str,owner_type="host"):
    print("come")
    owner = db.query(Host).filter(Host.email == email).first()
    
    if not owner:
        return ErrorResponseModel("Owner not found", 404, f"No {owner_type} with this email.")
    
    print(owner.id)

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
