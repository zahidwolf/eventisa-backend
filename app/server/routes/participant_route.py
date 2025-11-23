from fastapi import (
    APIRouter, Request, Response, status,
    Form, File, UploadFile, Depends, Body
)
import re, os, shutil
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from server.database import get_db
from server.models.participant_model import ParticipantCreate
from server.controller.participent_controller import *
from server.schema.participatn_schema import ParticipantUpdate
from server.controller.ws_manager import participant_manager
from server.response_model import ResponseModel, ErrorResponseModel
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


router = APIRouter()

# ----------------------- Guest Booking Schema -----------------------
class GuestBooking(BaseModel):
    name: Optional[str] = ""
    email: str
    phone: Optional[str] = ""
    host_id: int
    event_id: int
    total_booked: Optional[int] = 1

# ----------------------- Add Participant -----------------------
@router.post("/add", response_description="Add Participant")
async def add_participant(participant: ParticipantCreate, db: Session = Depends(get_db)):
    participant_data = participant.dict()
    try:
        new_participant = await add_participant_controller(db, participant_data)
        return ResponseModel(new_participant.__dict__, "Participant added successfully")
    except Exception as e:
        db.rollback()
        return ErrorResponseModel(str(e), 500, "Failed to add participant")

# ----------------------- Guest Booking (No Login Required) -----------------------
@router.post("/guest-booking", response_description="Guest booking without login")
async def guest_booking(booking: GuestBooking, db: Session = Depends(get_db)):
    try:
        booking_data = booking.dict()
        new_participant = await add_participant_guest_controller(db, booking_data)
        return ResponseModel(new_participant.__dict__, "Booking successful! An account has been created for you.")
    except Exception as e:
        db.rollback()
        return ErrorResponseModel(str(e), 500, f"Failed to process booking: {str(e)}")
    

# ----------------------- Get Participants -----------------------
@router.get("/all", response_description="Get Participants")
async def get_participants(response: Response, db: Session = Depends(get_db)):
    
    participants = await retrieve_all_participant_controller(db)
    return ResponseModel(participants, "Participant data retrieved successfully")


# ----------------------- Get Participant by field -----------------------
@router.get("/get_participants/{field}/{value}", response_description="Get Participant")
async def get_participants(response: Response,field:str, value:int, db: Session = Depends(get_db)):
    participants = await retrieve_participant_controller(db,field,value)
    return ResponseModel(participants, "Participant data retrieved successfully")


#------------------------- analysis part-------------------

#------------------------ get daily sales for event --------

@router.get("/analysis/daily_sale_event/{event_id}", response_description="Get Participant")
async def get_daily_sales_for_event_info(response: Response,event_id:int, db: Session = Depends(get_db)):
    sales_data_event=await get_daily_sales_for_event(db,event_id)
    return ResponseModel(sales_data_event,"Daily event sale retrieved successfully")

#------------------------ get daily sales for category --------

@router.get("/analysis/daily_sale_category/{category}", response_description="Get Participant")
async def get_daily_sales_category_wise_info(response: Response,category:str, db: Session = Depends(get_db)):
    sales_data_category=await get_daily_sales_for_category(db,category)
    return ResponseModel(sales_data_category,"Daily Category wise sale retrieved successfully")



#------------------------ get daily total sales --------

@router.get("/analysis/daily_sale_total", response_description="Get Participant")
async def get_daily_total_sale_info(response: Response, db: Session = Depends(get_db)):
    sales_data_total=await get_daily_total_sales(db)
    return ResponseModel(sales_data_total,"Daily total sale retrieved successfully")


#------------------------ get daily participants event wise --------

@router.get("/analysis/daily_participant_event/{event_id}", response_description="Get Participant")
async def get_daily_participant_for_event_info(response: Response,event_id:int, db: Session = Depends(get_db)):
    sales_data_participant=await get_daily_participants_for_event(db,event_id)
    return ResponseModel(sales_data_participant,"Daily participant data retrieved successfully")



#------------------------ get total sale category wise --------

@router.get("/analysis/total_sale_category/{category}", response_description="Get Participant")
async def get_total_sale_for_category(response: Response,category:str, db: Session = Depends(get_db)):
    sales_data_category=await get_total_sale_category_wise(db,category)
    return ResponseModel(sales_data_category,"Total sale category wise retrieved successfully")




#------------------------ get total sale Event-wise --------

@router.get("/analysis/total_sale_event/{event_id}", response_description="Get Participant")
async def get_total_sale_for_event(response: Response,event_id:int, db: Session = Depends(get_db)):
    sales_data_event=await get_total_sale_event_wise(db,event_id)
    return ResponseModel(sales_data_event,"Total sale event wise retrieved successfully")



#------------------------ get total monthly sale --------

@router.get("/analysis/total_monthly_sale", response_description="Get Participant")
async def get_monthly_total_sale_info(response: Response, db: Session = Depends(get_db)):
    sales_data_monthly_total=await get_monthly_total_sale(db)
    return ResponseModel(sales_data_monthly_total,"Monthly total sale retrieved successfully")



#------------------------ get total monthly sale category wise --------

@router.get("/analysis/total_monthly_sale_category/{category}", response_description="Get Participant")
async def get_monthly_sale_for_category_info(response: Response,category:str, db: Session = Depends(get_db)):
    sales_data_monthly_category=await get_monthly_category_sale(db,category)
    return ResponseModel(sales_data_monthly_category,"Monthly total sale for category retrieved successfully")



#------------------------ get total monthly sale event wise --------

@router.get("/analysis/total_monthly_sale_event/{event_id}", response_description="Get Participant")
async def get_monthly_sale_for_event_info(response: Response,event_id:int, db: Session = Depends(get_db)):
    sales_data_monthly_event=await get_monthly_event_sale(db,event_id)
    return ResponseModel(sales_data_monthly_event,"Monthly total sale for event retrieved successfully")



