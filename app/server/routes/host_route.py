from fastapi import (
    APIRouter, Request, Response, status,
    Form, File, UploadFile, Depends, Body
)
import re, os, shutil
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from server.database import get_db
from server.controller.host_controller import *
from server.schema.host_schema import HostUpdate
from server.controller.ws_manager import user_manager
from server.response_model import ResponseModel, ErrorResponseModel
from datetime import datetime

router = APIRouter()
# Use absolute path for uploads directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "hosts")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ----------------------- ADD USER -----------------------
@router.post("/add",response_description="Add Host")
async def add_host_data(
    request:Request,
    response:Response,
    name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    password: str = Form(...),
    division: str = Form(...),
    district: str = Form(...),
    upzilla_thana: str = Form(...),
    address: str = Form(...),
    file: UploadFile = File(None),
    db:Session=Depends(get_db)
):
    try:
        if re.match(r"[^@]+@[^@]+\.[^@]+", name):
            return ErrorResponseModel(f"Invalid name: {name}", 400, "Full name should not be an email")
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            return ErrorResponseModel(f"Invalid email: {email}", 400, "Email format invalid")
        if not re.match(r"^01[1-9]\d{8}$", phone_number):
            return ErrorResponseModel("Invalid phone number format", 400, "Phone number must be 11 digits starting with 01")
        
        existing =await retrieve_host(db,"email",email)
        if existing:
            return ErrorResponseModel(f"Host with email {email} exists!", 400, "Email already exists")
        
        image_url = None
        if file:
            path = os.path.join(UPLOAD_DIR, file.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            # Use relative path from app directory for URL
            BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            relative_path = os.path.relpath(path, BASE_DIR)
            image_url = f"/{relative_path.replace(os.sep, '/')}"

        host_data = jsonable_encoder({
            "name": name,
            "email": email,
            "phone_number": phone_number,
            "password": password,
            "division": division,
            "district": district,
            "upzilla_thana": upzilla_thana,
            "address": address,
            "image_url": image_url, 
        })

        new_host=await add_host(db,host_data)
        return ResponseModel(new_host, "An OTP sent to email for verification.")

    except Exception as e:
        return ErrorResponseModel("An error occurred", 500, str(e))
    




# ----------------------- verification of otp -----------------------
@router.get("/verify/email/{email}/otp/{otp}", response_description="Verify OTP")
async def get_host_verfied(response: Response,email:str,otp:str, db: Session = Depends(get_db)):
    hosts = await verification_of_host(db,email,otp)
    return ResponseModel(hosts, "Host email verified successfully")


# ----------------------- Resending otp -----------------------
@router.get("/resend/otp/{email}", response_description="Resent otp")
async def resend_otp(response: Response,email:str, db: Session = Depends(get_db)):
    hosts = await resedning_otp_for_verification(db,email)
    return ResponseModel(hosts, "OTP sent to your email")

# ----------------------- GET Host Login Message-----------------------
@router.get("/login/email/{email}/password/{password}", response_description="Retrieve all hosts")
async def get_host_login_msg(response: Response,email:str,password:str, db: Session = Depends(get_db)):
    hosts = await host_login(db,email,password)

    if (hosts["status"]=="failed"):
        ErrorResponseModel(hosts["status"],400,hosts["msg"])

    return ResponseModel(hosts["status"], hosts["msg"])


# ----------------------- GET ALL Host -----------------------
@router.get("/all", response_description="Retrieve all hosts")
async def get_hosts(response: Response, db: Session = Depends(get_db)):
    hosts = await retrieve_hosts(db)
    return ResponseModel(hosts, "Users retrieved successfully")



# ----------------------- SEARCH Hosts -----------------------
@router.get("/search/{host_id}")
async def search_host(response: Response, host_id: str, db: Session = Depends(get_db)):
    try:
        host = None
        # Try to search by ID first
        try:
            host_id_int = int(host_id)
            host = await retrieve_host(db, "id", host_id_int)
        except ValueError:
            pass

        # Try by email
        if not host:
            host = await retrieve_host(db, "email", host_id)

        # Try by name
        if not host:
            host = await retrieve_host(db, "name", host_id)

        # Try by phone number
        if not host:
            host = await retrieve_host(db, "phone_number", host_id)

        if host:
            # Convert SQLAlchemy model to dict
            host_dict = {
                "id": host.id,
                "name": host.name,
                "email": host.email,
                "phone_number": host.phone_number,
                "division": host.division,
                "district": host.district,
                "upzilla_thana": host.upzilla_thana,
                "address": host.address,
                "image_url": host.image_url,
                "verification": host.verification
            }
            return ResponseModel(host_dict, "Host found")

        return ErrorResponseModel("Not found", 404, "Host not found")
    except Exception as e:
        return ErrorResponseModel("An error occurred", 400, str(e))
    

# ----------------------- UPDATE Host -----------------------
@router.put("/update/{email}", response_description="Update host details")
async def update_host_data(
    response: Response,
    email: str,
    update_data: HostUpdate = Body(...),
    db: Session = Depends(get_db)
):
    try:
        existing_host = await retrieve_host(db,"email", email)
        if not existing_host:
            return ErrorResponseModel("Host not found", 404, f"Host with email {email} does not exist.")

        update_dict = update_data.model_dump(exclude_none=True)
        if not update_dict:
            return ErrorResponseModel("No data provided", 400, "Request body cannot be empty.")
        
        updated_host = await update_host(db, existing_host.id, update_dict)
        return ResponseModel(updated_host, "Host updated successfully")

    except Exception as e:
        return ErrorResponseModel("An unexpected error occurred", 500, str(e))
    

# ----------------------- DELETE USER -----------------------
@router.delete("/delete/{email}")
async def delete_user_data(response: Response, email: str, db: Session = Depends(get_db)):
    deleted_host = await delete_host(db, email)
    if deleted_host:
        return ResponseModel(f"Host with email: {email} removed", "Host deleted successfully")
    return ErrorResponseModel("Not found", 404, f"Host with email {email} doesn't exist")



# ----------------------- UPDATE PASSWORD -----------------------
@router.put("/update/password/{host_id}", response_description="Update host password")
async def update_password(
    response: Response,
    host_id: int,
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        host = await retrieve_host(db, "id", host_id)
        if not host:
            return ErrorResponseModel("Host Not Found", 404, f"Host with ID {host_id} does not exist.")

        if not verify_password(current_password, host.password):
            return ErrorResponseModel("Authentication Failed", 401, "Incorrect current password.")

        hashed_new_password = encrypt_password(new_password)
        await update_host(db, host_id, {"password": hashed_new_password})
        return ResponseModel(None, "Password updated successfully.")

    except Exception as e:
        return ErrorResponseModel("An unexpected error occurred", 500, str(e))


# ----------------------- FORGOT PASSWORD (SEND OTP) -----------------------
@router.post("/forgot_password/send_otp", response_description="Send OTP for password reset")
async def forgot_password(response: Response, email: str = Form(...), db: Session = Depends(get_db)):
    try:
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            return ErrorResponseModel(f"Invalid email: {email}", 400, "Email format invalid")

        result = await send_otp(db, email,"reset","host")
        return ResponseModel(
            {"email": email},
            "If this email is registered, an OTP has been sent for password reset."
        )
    except Exception as e:
        return ErrorResponseModel("An error occurred", 500, str(e))
    

# ----------------------- VERIFY OTP -----------------------
@router.post("/forgot_password/verify_otp/", response_description="Verify OTP for password reset")
async def verify_reset_otp(response: Response, email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    try:
        print("got it ")
        result = await verify_reset_otp_controller(db, email, otp,"host")
        print("got it ")
        response.status_code = result.get("code", status.HTTP_200_OK)
        return result
    except Exception as e:
        return ErrorResponseModel("An error occurred",500,str(e))

# ----------------------- RESET PASSWORD -----------------------

@router.post("/forgot_password/reset/", response_description="Handle OTP verification and password reset")
async def password_reset_host(
    response: Response,
    email: str = Form(...),
    new_password: str = Form(None),
    db: Session = Depends(get_db)
):
    result = await password_reset(db, email, new_password)
    response.status_code = result["code"] if "code" in result else status.HTTP_200_OK
    return result

# ----------------------- WEBSOCKET -----------------------
@router.websocket("/ws/hosts")
async def websocket_users(websocket):
    await host_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        host_manager.disconnect(websocket)


__all__ = ["router"]