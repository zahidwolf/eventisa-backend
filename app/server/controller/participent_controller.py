from typing import Any, Dict
from sqlalchemy.orm import Session
from server.models.user_model import User
from server.controller.qr_code_sender import send_qr_ticket_email
from server.controller.qrcode_event_controller import add_qrcode_data
from server.models.participant_model import * 
from server.controller.ws_manager import participant_manager
from datetime import datetime, timedelta
from server.response_model import ResponseModel, ErrorResponseModel
from server.controller.event_controller import update_event_seat_controller
from server.controller.user_controller import retrieve_user_by_email, add_user
from server.cryptography import encrypt_password
from sqlalchemy import func
from server.models.event_model import *
import secrets


# ------------------ Add New Participant ------------------


async def add_participant_controller(db: Session, participant_data: Dict[str, Any]):
    

    # Normalize / compute payment date & time before creating the Participant
    payment = float(participant_data.get("payment", 0.0) or 0.0)
    if payment > 0:
        payment_date = datetime.utcnow()
        payment_time = payment_date.strftime("%H:%M:%S")
    else:

        payment_date = None
        payment_time = None


    participant_payload = participant_data.copy()
    participant_payload["payment"] = payment
    participant_payload["payment_date"] = payment_date
    participant_payload["payment_time"] = payment_time

    

    # Create participant
    new_participant = Participant(**participant_payload)
    user = db.query(User).filter(User.id == new_participant.user_id).first()
    event = db.query(Event).filter(Event.id == new_participant.event_id).first()

    new_participant.payment=event.event_price*new_participant.total_booked
    print(new_participant.payment)

    db.add(new_participant)
    db.commit()
    db.refresh(new_participant)

    # Broadcast participant info (uses committed values)
    await participant_manager.broadcast({
        "event": "new_participant",
        "data": {
            "id": new_participant.id,
            "host_id": new_participant.host_id,
            "event_id": new_participant.event_id,
            "user_id": new_participant.user_id,
            "total_booked": new_participant.total_booked,
            "payment": new_participant.payment,
            "due": new_participant.due,
            "payment_date": new_participant.payment_date,
            "payment_time": new_participant.payment_time,
        }
    })

    # Update event seats (expects {"booked": n})
    await update_event_seat_controller(
        db,
        new_participant.event_id,
        {"booked": new_participant.total_booked}
    )

    # Fetch related user & event objects for QR/email generation
    

    # Ensure event and user were found (optional; raise or handle as needed)
    if not user or not event:
        # If you prefer raising exceptions, replace the return with raise
        return new_participant

    # Generate QR codes and send emails (function handles multiple tickets)
    await add_qrcode_data(db, new_participant, user, event)

    return new_participant


# ------------------ Retrieve ALL participants ------------------
async def retrieve_all_participant_controller(db:Session):
    from sqlalchemy.orm import joinedload
    return db.query(Participant).options(joinedload(Participant.user)).all()


# ------------------ Retrieve participant by host/event/participant id ------------------
async def retrieve_participant_controller(db:Session,field:str,value:str):
    try:
        from sqlalchemy.orm import joinedload
        
        if field=="host_id":
            return db.query(Participant).options(joinedload(Participant.user)).filter(Participant.host_id==int(value)).all()
        
        if field=="event_id":
            return db.query(Participant).options(joinedload(Participant.user)).filter(Participant.event_id==int(value)).all()
        
        if field=="user_id":
            return db.query(Participant).options(joinedload(Participant.user)).filter(Participant.user_id==int(value)).all()
        
    except Exception as e:
        return e.str()


# ----------------------- Analysis part ---------------------

# ------------------ Analysis daily sales for event ------------------
async def get_daily_sales_for_event(db: Session, event_id: int):
    results = (
        db.query(
            func.date(Participant.payment_date).label("date"),
            func.sum(Participant.payment).label("total_payment")
        )
        .filter(
            Participant.event_id == event_id,
            Participant.payment_date.isnot(None)
        )
        .group_by(func.date(Participant.payment_date))
        .order_by(func.date(Participant.payment_date))
        .all()
    )

    if not results:
        return []

    # Convert to dictionary
    sales_by_date = {
        r.date: float(r.total_payment or 0.0)
        for r in results
    }

    # Get full date range
    start_date = min(sales_by_date.keys())
    end_date = max(sales_by_date.keys())

    # Fill missing days
    daily_sales = []
    current_date = start_date
    while current_date <= end_date:
        total_payment = sales_by_date.get(current_date, 0.0)
        daily_sales.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "total_payment": total_payment
        })
        current_date += timedelta(days=1)

    return daily_sales


# ------------------ Analysis daily sales for category ------------------

async def get_daily_sales_for_category(db: Session, category: str):
    results = (
        db.query(
            func.date(Participant.payment_date).label("date"),
            func.sum(Participant.payment).label("total_payment")
        )
        .join(Event, Participant.event_id == Event.id)
        .filter(
            Event.event_category == category,
            Participant.payment_date.isnot(None)
        )
        .group_by(func.date(Participant.payment_date))
        .order_by(func.date(Participant.payment_date))
        .all()
    )

    if not results:
        return []

    # Convert to dictionary
    sales_by_date = {
        r.date: float(r.total_payment or 0.0)
        for r in results
    }

    # Get full date range
    start_date = min(sales_by_date.keys())
    end_date = max(sales_by_date.keys())

    # Fill missing days
    daily_sales = []
    current_date = start_date
    while current_date <= end_date:
        total_payment = sales_by_date.get(current_date, 0.0)
        daily_sales.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "total_payment": total_payment
        })
        current_date += timedelta(days=1)

    return daily_sales

# ------------------ Analysis daily sales for total sale ------------------


async def get_daily_total_sales(db: Session):
    results = (
        db.query(
            func.date(Participant.payment_date).label("date"),
            func.sum(Participant.payment).label("total_payment")
        )
        .filter(Participant.payment_date.isnot(None))
        .group_by(func.date(Participant.payment_date))
        .order_by(func.date(Participant.payment_date))
        .all()
    )

    print(results)

    if not results:
        return []

    # Convert to dictionary
    sales_by_date = {
        r.date: float(r.total_payment or 0.0)
        for r in results
    }

    # Determine full date range
    start_date = min(sales_by_date.keys())
    end_date = max(sales_by_date.keys())

    # Fill missing days

    print("come")
    daily_sales = []
    current_date = start_date
    while current_date <= end_date:
        total_payment = sales_by_date.get(current_date, 0.0)
        daily_sales.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "total_payment": total_payment
        })
        current_date += timedelta(days=1)

    return daily_sales



#---------- Daily Participant Report (number of participants who paid)----------
async def get_daily_participants_for_event(db: Session, event_id: int):
    results = (
        db.query(
            func.date(Participant.payment_date).label("date"),
            func.sum(Participant.total_booked).label("total_participants")
        )
        .filter(
            Participant.event_id == event_id,
            Participant.payment_date.isnot(None)
        )
        .group_by(func.date(Participant.payment_date))
        .order_by(func.date(Participant.payment_date))
        .all()
    )

    if not results:
        return []

    # Convert to dictionary
    participants_by_date = {
        r.date: r.total_participants
        for r in results
    }

    # Get full date range
    start_date = min(participants_by_date.keys())
    end_date = max(participants_by_date.keys())

    # Fill missing days
    daily_participants = []
    current_date = start_date
    while current_date <= end_date:
        total_participants = participants_by_date.get(current_date, 0)
        daily_participants.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "total_participants": total_participants
        })
        current_date += timedelta(days=1)

    return daily_participants

#--------------- Category wise sale --------------------

async def get_total_sale_category_wise(db: Session, category: str):
    
    results = (
        db.query(
            func.sum(Participant.payment).label("total_sale"),
            func.sum(Participant.total_booked).label("total_participants"),
            func.count(func.distinct(Event.id)).label("total_events")
        )
        .join(Event, Participant.event_id == Event.id)
        .filter(Event.event_category == category)
        .first()
    )

    return {
        "total_sale": float(results.total_sale or 0.0),
        "total_participants": results.total_participants or 0,
    }

#--------------- Total Sale (Event-wise) --------------------
async def get_total_sale_event_wise(db: Session, event_id: int):
    
    results = (
        db.query(
            Event.id.label("event_id"),
            Event.event_title.label("event_title"),
            func.sum(Participant.payment).label("total_sale"),
            func.sum(Participant.total_booked).label("total_participants")
        )
        .join(Participant, Participant.event_id == Event.id)
        .filter(Event.id == event_id)
        .group_by(Event.id, Event.event_title)
        .first()
    )

    if not results:
        return {
            "total_sale": 0.0,
            "total_participants": 0
        }

    return {
        "total_sale": float(results.total_sale or 0.0),
        "total_participants": results.total_participants or 0
    }



#---------------- monthly total sale-------------

async def get_monthly_total_sale(db: Session):
    results = (
        db.query(
            func.date_trunc("month", Participant.payment_date).label("month"),
            func.sum(Participant.payment).label("total_payment")
        )
        .filter(Participant.payment_date.isnot(None))
        .group_by(func.date_trunc("month", Participant.payment_date))
        .order_by(func.date_trunc("month", Participant.payment_date))
        .all()
    )

    return [
        {"date": r.month.strftime("%b'%y"), "total_payment": float(r.total_payment or 0.0)}
        for r in results
    ]


#------------------- monthly sale category wise ---------------


async def get_monthly_category_sale(db: Session, category: str):
    results = (
        db.query(
            func.date_trunc("month", Participant.payment_date).label("month"),
            func.sum(Participant.payment).label("total_payment")
        )
        .join(Event, Participant.event_id == Event.id)
        .filter(
            Event.event_category == category,
            Participant.payment_date.isnot(None)
        )
        .group_by(func.date_trunc("month", Participant.payment_date))
        .order_by(func.date_trunc("month", Participant.payment_date))
        .all()
    )

    return [
        {"date": r.month.strftime("%b'%y"), "total_payment": float(r.total_payment or 0.0)}
        for r in results
    ]


#--------------- monthly sale event wise -----------------------

async def get_monthly_event_sale(db: Session, event_id: int):
    results = (
        db.query(
            func.date_trunc("month", Participant.payment_date).label("month"),
            func.sum(Participant.payment).label("total_payment")
        )
        .filter(
            Participant.event_id == event_id,
            Participant.payment_date.isnot(None)
        )
        .group_by(func.date_trunc("month", Participant.payment_date))
        .order_by(func.date_trunc("month", Participant.payment_date))
        .all()
    )

    return [
        {"date": r.month.strftime("%b'%y"), "total_payment": float(r.total_payment or 0.0)}
        for r in results
    ]

# ------------------ Add Participant with Guest Booking (finds or creates user) ------------------
async def add_participant_guest_controller(db: Session, booking_data: Dict[str, Any]):
    """
    Handles guest bookings by finding or creating a user account,
    then creating the participant record.
    """
    try:
        email = booking_data.get("email", "").strip().lower()
        name = booking_data.get("name", "").strip()
        phone = booking_data.get("phone", "").strip()
        host_id = booking_data.get("host_id")
        event_id = booking_data.get("event_id")
        total_booked = booking_data.get("total_booked", 1)
        
        # Validate required fields
        if not email:
            raise ValueError("Email is required")
        if not host_id or not event_id:
            raise ValueError("Host ID and Event ID are required")
        
        # Find or create user
        user = await retrieve_user_by_email(db, email)
        
        if not user:
            # Create new user account with auto-generated password
            # User can reset password later if needed
            auto_password = secrets.token_urlsafe(16)  # Generate secure random password
            
            user_data = {
                "name": name or "Guest User",
                "email": email,
                "password": auto_password,  # Will be encrypted in add_user
                "phone_number": phone or "00000000000",  # Default phone if not provided
                "image_url": None
            }
            
            user = await add_user(db, user_data)
            # add_user returns a dict, so we need to get the actual user object
            user = await retrieve_user_by_email(db, email)
        
        # Update user info if provided (name and phone)
        if name and name != user.name:
            user.name = name
        if phone and phone != user.phone_number:
            user.phone_number = phone
        db.commit()
        db.refresh(user)
        
        # Get event to calculate payment
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise ValueError("Event not found")
        
        # Calculate payment
        payment = event.event_price * total_booked
        payment_date = datetime.utcnow()
        payment_time = payment_date.strftime("%H:%M:%S")
        
        # Create participant
        participant_data = {
            "host_id": host_id,
            "event_id": event_id,
            "user_id": user.id,
            "total_booked": total_booked,
            "payment": payment,
            "due": 0.0,
            "payment_date": payment_date,
            "payment_time": payment_time
        }
        
        new_participant = Participant(**participant_data)
        db.add(new_participant)
        db.commit()
        db.refresh(new_participant)
        
        # Broadcast participant info
        await participant_manager.broadcast({
            "event": "new_participant",
            "data": {
                "id": new_participant.id,
                "host_id": new_participant.host_id,
                "event_id": new_participant.event_id,
                "user_id": new_participant.user_id,
                "total_booked": new_participant.total_booked,
                "payment": new_participant.payment,
                "due": new_participant.due,
                "payment_date": new_participant.payment_date,
                "payment_time": new_participant.payment_time,
            }
        })
        
        # Update event seats
        await update_event_seat_controller(
            db,
            new_participant.event_id,
            {"booked": new_participant.total_booked}
        )
        
        # Generate QR codes and send emails
        await add_qrcode_data(db, new_participant, user, event)
        
        return new_participant
        
    except Exception as e:
        db.rollback()
        raise e