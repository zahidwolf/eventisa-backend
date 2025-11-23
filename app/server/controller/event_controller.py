from sqlalchemy import or_
from sqlalchemy.orm import Session
from server.models.event_model import * 
from server.models.host_model import Host
from server.controller.ws_manager import event_manager
from datetime import datetime, timedelta
from server.response_model import ResponseModel, ErrorResponseModel
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from server.constant_file import eventisa_email, eventisa_email_password

# ------------------ Add New User ------------------
async def add_event_controller(db:Session,event_data:dict):
    # Set approval_status to pending by default if not provided
    if "approval_status" not in event_data:
        event_data["approval_status"] = "pending"
    new_event=Event(**event_data)
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    await event_manager.broadcast({
    "event": "new_event",
    "data": {
        "id": new_event.id,
        "host_id": new_event.host_id,
        "event_title": new_event.event_title,
        "event_banner_img": new_event.event_banner_img,
        "event_location": new_event.event_location,
        "event_description": new_event.event_description,
        "event_date": new_event.event_date,
        "event_time": new_event.event_time,
        "event_price": new_event.event_price,
        "total_seat": new_event.total_seat,
        "filled_seat": new_event.filled_seat,
        "event_category": new_event.event_category,
        }
    })

    return new_event.__dict__

# ------------------ Retrieve ALL Event ------------------
async def retrieve_events_controller(db:Session, approval_status: str = "approved"):
    from sqlalchemy.orm import joinedload
    query = db.query(Event).options(joinedload(Event.participants))
    if approval_status:
        query = query.filter(Event.approval_status == approval_status)
    return query.all()

# ------------------ Retrieve Pending Events ------------------
async def retrieve_pending_events_controller(db:Session):
    from sqlalchemy.orm import joinedload
    from server.models.host_model import Host
    return db.query(Event).options(
        joinedload(Event.participants),
        joinedload(Event.host)
    ).filter(Event.approval_status == "pending").all()

# ------------------ Send Approval Email to Host ------------------
async def send_approval_email_to_host(host_email: str, host_name: str, event_title: str):
    """
    Send approval email to host when their event is approved
    """
    def send_blocking_email():
        try:
            message = MIMEMultipart()
            message['From'] = eventisa_email
            message['To'] = host_email
            message['Subject'] = f"Event Approved: {event_title}"
            
            # Create email body using the provided format
            email_body = f"""Dear {host_name},

We are pleased to inform you that your event has been successfully reviewed and approved. It is now live and available for ticket sales on our platform.

You can now share the event link with your audience and begin promoting ticket sales. If you need any assistance with event settings, promotions, or updates, our team is always here to help.

Thank you for choosing our platform to host your event. We look forward to supporting you throughout the journey.

Warm regards,

Zahid Hasan

Founder & CEO

Eventisa"""
            
            message.attach(MIMEText(email_body, 'plain'))
            
            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(eventisa_email, eventisa_email_password)
            text = message.as_string()
            server.sendmail(eventisa_email, host_email, text)
            server.quit()
            return True
            
        except Exception as e:
            print(f"SMTP Error sending approval email: {e}")
            return False
    
    try:
        return await asyncio.to_thread(send_blocking_email)
    except Exception as e:
        print(f"Error sending approval email: {e}")
        return False

# ------------------ Approve Event ------------------
async def approve_event_controller(db:Session, event_id:int):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return None
    event.approval_status = "approved"
    db.commit()
    db.refresh(event)
    
    # Send approval email to host
    host = db.query(Host).filter(Host.id == event.host_id).first()
    if host and host.email:
        # Send email asynchronously (don't wait for it)
        asyncio.create_task(send_approval_email_to_host(
            host_email=host.email,
            host_name=host.name,
            event_title=event.event_title
        ))
    
    return event.__dict__

# ------------------ Reject Event ------------------
async def reject_event_controller(db:Session, event_id:int):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return None
    event.approval_status = "rejected"
    db.commit()
    db.refresh(event)
    return event.__dict__


# ------------------ Retrieve Event by name/location/date/id/host id ------------------
async def retrieve_event_controller(db:Session,field:str,value:str):
    try:
        if field=="id":
            return (db.query(Event).filter(Event.id==value).first())
        elif field=="event_title":
            return db.query(Event).filter(Event.event_title==value).first()
        elif field=="event_location":
            return db.query(Event).filter(Event.event_location==value).first()
        elif field=="event_date":
            return db.query(Event).filter(Event.event_date==value).first()
        elif field=="host_id":
            return db.query(Event).filter(Event.host_id==value).first()
        
    except ValueError as v:
        return None
    except Exception as e:
        return None
    

    

# ------------------ Retrieve Multiple Event by name/location/date/id/host id ------------------
async def retrieve_multiple_event_controller(db: Session, keyword: str):

    search_pattern = f"%{keyword}%"
    query = db.query(Event).filter(
        or_(
            # Match keyword against event_title
            Event.event_title.ilike(search_pattern),
            
            # Match keyword against event_location
            Event.event_location.ilike(search_pattern),
            
            # Match keyword against event_category
            Event.event_category.ilike(search_pattern)
            
            # Add other relevant string fields here if needed (e.g., event_description)
        )
    )
    
    # 3. Execute the query and return results
    return query.all()

# ------------------ Update Event ------------------
async def update_event_controller(db:Session,event_id:int,update_data:dict):
    event=db.query(Event).filter(Event.id==event_id).first()
    if not event:
        return None
    # print("got it 2")
    for key,val in update_data.items():
        setattr(event,key,val)

    db.commit()
    db.refresh(event)
    return event.__dict__



# ------------------ Update Event seat infor ------------------
async def update_event_seat_controller(db: Session, event_id: int, update_data: dict):
    
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return None

    # Increment filled_seat if 'booked' key exists
    booked_increment = update_data.get("booked")
    if booked_increment:
        event.filled_seat = int(event.filled_seat) + int(booked_increment)

    db.commit()
    db.refresh(event)
    return event.__dict__



# ------------------ Delete Event ------------------
async def delete_event_controller(db:Session,id:int):
    event=db.query(Event).filter(Event.id==id).first()
    if not event:
        return None
    
    db.delete(event)
    db.commit()

    return event.__dict__





# ------------------ Analysis Part ------------------
# ------------------ Retrieve Event by name/location/date/id/host id ------------------
async def retrieve_event_seat_availability(db:Session,event_id:int):

    event_detail=db.query(Event).filter(Event.id==event_id).first()
    if event_detail:
        event_seats = {
            "total_seat": event_detail.total_seat,
            "filled_seat": event_detail.filled_seat
        }
        return event_seats
    return []

# ------------------ get target earning ------------------
async def get_targeted_earning(db:Session,event_id:int):

    event_detail=db.query(Event).filter(Event.id==event_id).first()
    if event_detail:

        ticket_price=int(event_detail.event_price)
        total_seat=int(event_detail.total_seat)

        if (total_seat<0):
            return {"target":"No target"}

        event_seats = {
            "target":ticket_price*total_seat
        }
        return event_seats
    return []


# ------------------ get target earning ------------------
async def get_total_sale_info(db:Session,event_id:int):

    event_detail=db.query(Event).filter(Event.id==event_id).first()
    if event_detail:

        ticket_price=int(event_detail.event_price)
        booked_ticket=int(event_detail.filled_seat)

        event_sale = {
            "sale":ticket_price*booked_ticket
        }
        return event_sale
    return []

