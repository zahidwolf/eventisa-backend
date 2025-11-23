from fastapi import (
    APIRouter, Request, Response, status,
    Form, File, UploadFile, Depends, Body
)
import re, os, shutil
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from server.database import get_db
from server.controller.qrcode_event_controller import *
from server.schema.qr_code_schema import QRCodeUpdate
from server.controller.ws_manager import qr_code_manager
from server.response_model import ResponseModel, ErrorResponseModel
from datetime import datetime

router = APIRouter()

@router.get("/verify/{qr_text}", response_description="Verification completed successfully")
async def verification_of_qr_code(qr_text:str,db: Session = Depends(get_db)):
    verification=await verify_qr_code(db,qr_text)
    if (verification["status"]=="valid"):
        return ResponseModel(verification,"Verified")
    return ErrorResponseModel("Failed to verified",400,verification["message"])


__all__ = ["router"]


