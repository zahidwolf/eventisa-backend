from sqlalchemy.orm import Session
from server.models.user_model import User
from server.models.event_model import Event
from server.controller.qr_code_sender import send_qr_ticket_email
from server.models.qrcode_model import QRCode
from server.models.participant_model import Participant
from datetime import datetime
import qrcode
import base64
from io import BytesIO
import re

async def add_qrcode_data(db, participant:Participant,user:User,event:Event):
    
    host = participant.host_id

    print(participant.id)


    qr_codes = []

    for ticket_no in range(1, participant.total_booked + 1):
        qr_payload = (
            f"uid:*{user.id}*"
            f"uname:*{user.name}*"
            f"eid:*{event.id}*"
            f"ename:*{event.event_title}\n*"
            f"ticket:*{participant.id}.{ticket_no}\n*"
            f"uemail:*{user.email}*"
            
        )

        qr_img = qrcode.make(qr_payload)
        buffered = BytesIO()
        qr_img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        new_qrcode = QRCode(
            host_id=host,
            event_id=event.id,
            user_id=user.id,
            participant_id=participant.id,
            user_email=user.email,
            user_name=user.name,
            qr_data=qr_base64,
            created_at=datetime.utcnow()
        )
        db.add(new_qrcode)
        db.commit()
        db.refresh(new_qrcode)


        print("come 1")

        # Send one email per ticket
        await send_qr_ticket_email(
            email=user.email,
            user_name=user.name,
            event_name=event.event_title,
            event_location=event.event_location,
            event_date=event.event_date,
            event_time=event.event_time,
            ticket_no=ticket_no,
            qr_data=qr_base64
        )

        qr_codes.append({
            "id": new_qrcode.id,
            "ticket_no": ticket_no,
            "participant_id": participant.id,
            "event_id": event.id,
            "user_id": user.id,
            "qr_data": qr_base64
        })

    return qr_codes


async def verify_qr_code(db: Session, qr_text: str):
    try:
        # Extract key:*value* pairs using regex
        matches = re.findall(r"(\w+):\*(.*?)\*", qr_text)
        qr_info = {k: v for k, v in matches}

        required_keys = {"uid", "uname", "eid", "ename", "ticket", "uemail"}
        if not required_keys.issubset(qr_info.keys()):
            return {"status": "invalid", "message": "Malformed QR payload."}

        # Validate user, event, and QR record
        user = db.query(User).filter(User.id == int(qr_info["uid"])).first()
        event = db.query(Event).filter(Event.id == int(qr_info["eid"])).first()
        qr_record = db.query(QRCode).filter(
            QRCode.user_id == int(qr_info["uid"]),
            QRCode.event_id == int(qr_info["eid"]),
            QRCode.user_email == qr_info["uemail"]
        ).first()

        if not user or not event or not qr_record:
            return {"status": "invalid", "message": "User, event, or QR code not found."}

        # Prevent reuse
        if qr_record.verified == "verified":
            return {"status": "reused", "message": "This ticket has already been used."}

        # Mark as verified and set scanned_at
        qr_record.verified = "verified"
        qr_record.scanned_at = datetime.utcnow()
        db.commit()

        # Check event date
        if event.event_date and isinstance(event.event_date, datetime):
            if event.event_date < datetime.utcnow():
                return {"status": "expired", "message": "Event date has passed."}

        return {
            "status": "valid",
            "message": "QR verified successfully.",
            "user": {"id": user.id, "name": user.name, "email": user.email},
            "event": {
                "id": event.id,
                "title": event.event_title,
                "location": event.event_location,
            },
            "ticket": qr_info["ticket"],
            "verified_at": qr_record.scanned_at.isoformat()
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}