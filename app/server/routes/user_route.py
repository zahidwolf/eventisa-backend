from fastapi import (
    APIRouter, Request, Response, status,
    Form, File, UploadFile, Depends, Body
)
import re, os, shutil
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from server.database import get_db
from server.controller.user_controller import *
from server.schema.user_schema import UserUpdate
from server.controller.ws_manager import user_manager
from server.response_model import ResponseModel, ErrorResponseModel
from datetime import datetime

router = APIRouter()
# Use absolute path for uploads directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "users")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------------- ADD USER -----------------------
@router.post("/add", response_description="Add user")
async def add_user_data(
    request: Request,
    response: Response,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    file: UploadFile = File(None),
    phone_number: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        if re.match(r"[^@]+@[^@]+\.[^@]+", name):
            return ErrorResponseModel(f"Invalid name: {name}", 400, "Full name should not be an email")
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            return ErrorResponseModel(f"Invalid email: {email}", 400, "Email format invalid")
        if not re.match(r"^01[1-9]\d{8}$", phone_number):
            return ErrorResponseModel("Invalid phone number format", 400, "Phone number must be 11 digits starting with 01")

        # Check if user exists
        existing = await retrieve_user_by_email(db, email)
        if existing:
            return ErrorResponseModel(f"User with email {email} exists!", 400, "Email already exists")

        # Handle image upload
        image_url = None
        if file:
            path = os.path.join(UPLOAD_DIR, file.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            # Use relative path from app directory for URL
            relative_path = os.path.relpath(path, BASE_DIR)
            image_url = f"/{relative_path.replace(os.sep, '/')}"

        # Add user
        user_data = jsonable_encoder({
            "name": name,
            "email": email,
            "password": password,
            "image_url": image_url,
            "phone_number": phone_number
        })
        new_user = await add_user(db, user_data)
        return ResponseModel(new_user, "User added successfully")

    except Exception as e:
        return ErrorResponseModel("An error occurred", 500, str(e))


# ----------------------- GET ALL USERS -----------------------
@router.get("/all", response_description="Retrieve all users")
async def get_users(response: Response, db: Session = Depends(get_db)):
    users = await retrieve_users(db)
    return ResponseModel(users, "Users retrieved successfully")


# ----------------------- SEARCH USER -----------------------
@router.get("/search/{user_id}")
async def search_user(response: Response, user_id: str, db: Session = Depends(get_db)):
    try:
        user = await retrieve_searched_users(db, "name", user_id)
        if user:
            return ResponseModel(user, "Name found")

        user =await retrieve_searched_users(db, "phone_number", user_id)
        if user:
            return ResponseModel(user, "Phone number found")
        
        user =await retrieve_searched_users(db, "email", user_id)
        if user:
            return ResponseModel(user, "Email not found")

        return ErrorResponseModel("Not found", 404, "User not found")
    except Exception as e:
        return ErrorResponseModel("An error occurred", 400, str(e))


# ----------------------- UPDATE USER -----------------------
@router.put("/update/{email}", response_description="Update user details")
async def update_user_data(
    response: Response,
    email: str,
    update_data: UserUpdate = Body(...),
    db: Session = Depends(get_db)
):
    try:
        existing_user = await retrieve_user_by_email(db, email)
        if not existing_user:
            return ErrorResponseModel("User not found", 404, f"User with email {email} does not exist.")

        update_dict = update_data.model_dump(exclude_none=True)
        if not update_dict:
            return ErrorResponseModel("No data provided", 400, "Request body cannot be empty.")

        updated_user = await update_user(db, existing_user.id, update_dict)
        return ResponseModel(updated_user, "User updated successfully")

    except Exception as e:
        return ErrorResponseModel("An unexpected error occurred", 500, str(e))


# ----------------------- DELETE USER -----------------------
@router.delete("/delete/{email}")
async def delete_user_data(response: Response, email: str, db: Session = Depends(get_db)):
    deleted_user = await delete_user(db, email)
    if deleted_user:
        return ResponseModel(f"User with email: {email} removed", "User deleted successfully")
    return ErrorResponseModel("Not found", 404, f"User with email {email} doesn't exist")


# ----------------------- USER LOGIN -----------------------
@router.get("/login/email/{email}/password/{password}", response_description="User login")
async def get_user_login_msg(response: Response, email: str, password: str, db: Session = Depends(get_db)):
    result = await user_login(db, email, password)
    if result["status"] == "failed":
        response.status_code = status.HTTP_400_BAD_REQUEST
        return ErrorResponseModel(result["status"], 400, result["msg"])
    return ResponseModel(result["status"], result["msg"])

# ----------------------- UPDATE PASSWORD -----------------------
@router.put("/update/password/{user_id}", response_description="Update user password")
async def update_password(
    response: Response,
    user_id: int,
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = await retrieve_user(db, "id", user_id)
        if not user:
            return ErrorResponseModel("User Not Found", 404, f"User with ID {user_id} does not exist.")

        if not verify_password(current_password, user.password):
            return ErrorResponseModel("Authentication Failed", 401, "Incorrect current password.")

        hashed_new_password = encrypt_password(new_password)
        await update_user(db, user_id, {"password": hashed_new_password})
        return ResponseModel(None, "Password updated successfully.")

    except Exception as e:
        return ErrorResponseModel("An unexpected error occurred", 500, str(e))


# ----------------------- FORGOT PASSWORD (SEND OTP) -----------------------
@router.post("/password/forgot", response_description="Send OTP for password reset")
async def forgot_password(response: Response, email: str = Form(...), db: Session = Depends(get_db)):
    try:
        if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
            return ErrorResponseModel(f"Invalid email: {email}", 400, "Email format invalid")

        result = await initiate_password_reset_otp(db, email,"user")
        return ResponseModel(
            {"email": email},
            "If this email is registered, an OTP has been sent for password reset."
        )
    except Exception as e:
        return ErrorResponseModel("An error occurred", 500, str(e))


# ----------------------- VERIFY OTP -----------------------
@router.post("/password/verify", response_description="Verify OTP for password reset")
async def verify_reset_otp(response: Response, email: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    result = await verify_reset_otp_controller(db, email, otp,"user")
    response.status_code = result.get("code", status.HTTP_200_OK)
    return result

# ----------------------- RESET PASSWORD -----------------------

@router.post("/password/reset", response_description="Handle OTP verification and password reset")
async def handle_password_reset(
    response: Response,
    email: str = Form(...),
    new_password: str = Form(None),
    db: Session = Depends(get_db)
):
    result = await password_reset_controller(db, email, new_password)
    response.status_code = result["code"] if "code" in result else status.HTTP_200_OK
    return result

# ----------------------- WEBSOCKET -----------------------
@router.websocket("/ws/users")
async def websocket_users(websocket):
    await user_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        user_manager.disconnect(websocket)


__all__ = ["router"]
