from fastapi import (
    APIRouter, Request, Response, status,
    Form, File, UploadFile, Depends, Body
)
import re, os, shutil
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from server.database import get_db
from server.controller.event_controller import *
from server.schema.event_schema import EventUpdate
from server.controller.ws_manager import event_manager
from server.response_model import ResponseModel, ErrorResponseModel
from server.models.event_model import Event
from datetime import datetime

router = APIRouter()
# Use absolute path for uploads directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "events")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------------- ADD Event -----------------------
@router.post("/add", response_description="Create a new event")
async def add_event_data(
    request: Request,
    response: Response,
    host_id: int = Form(..., description="The ID of the host creating the event."),
    event_title: str = Form(...),
    event_banner_file: UploadFile = File(None, description="Optional banner image for the event."), 
    event_location: str = Form(...),
    event_description: str = Form(...),
    event_date: str = Form(..., description="Date of the event (e.g., 'YYYY-MM-DD')."),
    event_time: str = Form(..., description="Time of the event (e.g., 'HH:MM AM/PM')."),
    event_price: float = Form(...),
    total_seat: int = Form(...),
    event_category: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        
        # 1. Validate and Parse Date String to Python datetime object (Required by Event model)
        try:
            # We still need to parse the date string into a Python datetime object 
            # because the database model uses Column(DateTime).
            # The time component will default to midnight (00:00:00).
            parsed_event_date = datetime.strptime(event_date, '%Y-%m-%d')
        except ValueError:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return ErrorResponseModel("Invalid Date Format", 400, "Event date must be in YYYY-MM-DD format.")

        # Time string ('event_time') is passed directly, as requested.

        event_banner_img_url = None
        if event_banner_file and event_banner_file.filename:
            path = os.path.join(UPLOAD_DIR, event_banner_file.filename)
            with open(path, "wb") as buffer:
                # Ensure the file pointer is at the beginning before copying
                event_banner_file.file.seek(0)
                shutil.copyfileobj(event_banner_file.file, buffer)
            # Use relative path from app directory for URL
            relative_path = os.path.relpath(path, BASE_DIR)
            event_banner_img_url = f"/{relative_path.replace(os.sep, '/')}"

        # 2. Prepare event_data, using the parsed datetime object and the raw time string.
        event_data = jsonable_encoder({
            "host_id": host_id,
            "event_title": event_title,
            "event_banner_img": event_banner_img_url,
            "event_location": event_location,
            "event_description": event_description,
            "event_date": parsed_event_date, # Use the parsed datetime object for the DateTime column
            "event_time": event_time,        # Use the raw string for the String column
            "event_price": event_price,
            "total_seat": total_seat,
            "event_category": event_category,
        })


        new_event = await add_event_controller(db, event_data)
        
        return ResponseModel(new_event, "Event created successfully")

    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        # Log the error (str(e)) for debugging purposes
        return ErrorResponseModel("An unexpected error occurred during event creation", 500, str(e))
    
    
# ----------------------- GET ALL Events -----------------------
@router.get("/all", response_description="Retrieve all events")
async def get_events(response: Response, db: Session = Depends(get_db), approval_status: str = "approved"):
    events = await retrieve_events_controller(db, approval_status)
    return ResponseModel(events, "Events retrieved successfully")

# ----------------------- GET Pending Events -----------------------
@router.get("/pending", response_description="Retrieve pending events for approval")
async def get_pending_events(response: Response, db: Session = Depends(get_db)):
    events = await retrieve_pending_events_controller(db)
    return ResponseModel(events, "Pending events retrieved successfully")

# ----------------------- APPROVE Event -----------------------
@router.put("/approve/{event_id}", response_description="Approve an event")
async def approve_event(event_id: int, db: Session = Depends(get_db)):
    approved_event = await approve_event_controller(db, event_id)
    if not approved_event:
        return ErrorResponseModel("Event not found", 404, "Event not found")
    return ResponseModel(approved_event, "Event approved successfully")

# ----------------------- REJECT Event -----------------------
@router.put("/reject/{event_id}", response_description="Reject an event")
async def reject_event(event_id: int, db: Session = Depends(get_db)):
    rejected_event = await reject_event_controller(db, event_id)
    if not rejected_event:
        return ErrorResponseModel("Event not found", 404, "Event not found")
    return ResponseModel(rejected_event, "Event rejected successfully")


# ----------------------- SEARCH Event -----------------------
@router.get("/search/{value}")
async def search_event(response: Response, value: str, db: Session = Depends(get_db)):
    try:
        
        try:
            event_int_id = int(value)
            
            event = await retrieve_event_controller(db, "id", event_int_id)
            if event:
                return ResponseModel(event, "Event found by ID")
        except ValueError:
            pass
        event = await retrieve_event_controller(db, "event_title", value)
        if event:
            return ResponseModel(event, "Event found")
        event =await retrieve_event_controller(db, "event_location", value)
        if event:
            return ResponseModel(event, "Event Location found")
        event =await retrieve_event_controller(db, "event_date", value)
        if event:
            return ResponseModel(event, "Event Date found")
        event =await retrieve_event_controller(db, "host_id", value)
        if event:
            return ResponseModel(event, "Host's event found")

        return ErrorResponseModel("Not found", 404, "Event not found")
    except Exception as e:
        return ErrorResponseModel("An error occurred", 400, str(e))
    

#------------------ Retrieve Multiple Events by Field ------------------
@router.get("/search/filter/{value}", response_description="retrieved field wise events")
async def get_multiple_events( value: str, db: Session = Depends(get_db)):
    events = await retrieve_multiple_event_controller(db, value)
    if not events:
        ErrorResponseModel("No event found",400,"No event found")
    return ResponseModel(events,f"Events filtered successfully",)

# ------------------ Update Event ------------------
@router.put("/update/{event_id}",response_description="updated event successfully")
async def update_event(event_id: int, update_data: EventUpdate, db: Session = Depends(get_db)):
    updated_event = await update_event_controller(db, event_id, update_data.dict(exclude_unset=True))
    if not updated_event:
        raise ErrorResponseModel("Event not found",404,"Event not found")
    return ResponseModel(
        data=updated_event,
        message="Event updated successfully",
    )

# ------------------ Delete Event ------------------
@router.delete("/{event_id}", response_description="deleted event successfully")
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    deleted_event = await delete_event_controller(db, event_id)
    if not deleted_event:
        raise ErrorResponseModel("Event not found",404,"Event not found or already deleted")
    return ResponseModel(
        data=deleted_event,
        message="Event deleted successfully",)


# ------------------ Retrieve Upcoming Events ------------------
@router.get("/upcoming/", response_description="current events retrieved")
async def get_upcoming_events(db: Session = Depends(get_db)):

    all_events = await retrieve_events_controller(db, approval_status="approved")
    upcoming = [event for event in all_events if event.event_date.date() >= datetime.now().date()]
    return ResponseModel(
        data=upcoming,
        message="Upcoming events retrieved successfully",
    )

# ------------------ Retrieve Upcoming Events ------------------
@router.get("/archive/", response_description="Archived events retrieved successfully")
async def get_archived_events(db: Session = Depends(get_db)):

    all_events = await retrieve_events_controller(db, approval_status="approved")
    archived = [event for event in all_events if event.event_date.date() < datetime.now().date()]
    return ResponseModel(
        data=archived,
        message="Archived events retrieved successfully",
    )



# ------------------ Retrieve Events by Host ID ------------------
@router.get("/host/{host_id}", response_description="Host event retrieved")
async def get_events_by_host(host_id: int, db: Session = Depends(get_db)):
    # Query events directly by host_id
    events = db.query(Event).filter(Event.host_id == host_id).all()
    if not events:
        return ErrorResponseModel("No event found", 404, "No events found for this host")
    return ResponseModel(
        data=events,
        message="Events retrieved successfully for host",
    )



# ------------------ Analysis Part ------------------


# ------------------ Retrieve Seat availability ------------------
@router.get("/analysis/seat/{event_id}", response_description="Archived events retrieved successfully")
async def get_events_seat_info(event_id:int,db: Session = Depends(get_db)):

    event_seats=await retrieve_event_seat_availability(db,event_id)

    return ResponseModel(
        data=event_seats,
        message="Retrieved event seats"
    )

# ------------------ Get target earning ------------------
@router.get("/analysis/target_earning/{event_id}", response_description="Archived events retrieved successfully")
async def get_target_earning_info(event_id:int,db: Session = Depends(get_db)):

    event_target=await get_targeted_earning(db,event_id)

    return ResponseModel(
        data=event_target,
        message="Retrieved event seats"
    )



# ------------------ Get Total sale ------------------
@router.get("/analysis/total_sale/{event_id}", response_description="Archived events retrieved successfully")
async def get_total_sale(event_id:int,db: Session = Depends(get_db)):

    event_sale=await get_total_sale_info(db,event_id)

    return ResponseModel(
        data=event_sale,
        message="Retrieved event seats"
    )




__all__ = ["router"]