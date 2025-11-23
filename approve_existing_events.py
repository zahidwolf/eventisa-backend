"""
Script to approve all existing events in the database
Run this once to set all existing events to 'approved' status
"""
import sys
import os

# Add the app directory to the path
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_dir)

from server.database import SessionLocal
from server.models.user_model import User
from server.models.host_model import Host
from server.models.event_model import Event
from server.models.participant_model import Participant
from server.models.qrcode_model import QRCode
from server.models.otp_records_model import OTPRecord

def approve_all_events():
    """Set all existing events to approved status"""
    db = SessionLocal()
    try:
        # Get all events
        events = db.query(Event).all()
        
        # Update each event to approved
        updated_count = 0
        for event in events:
            # Check if approval_status exists, if not set it, if it exists and not approved, update it
            if not hasattr(event, 'approval_status'):
                # If the column doesn't exist yet, we'll skip (shouldn't happen if migration ran)
                print(f"Warning: Event {event.id} doesn't have approval_status attribute")
                continue
            if event.approval_status != 'approved':
                event.approval_status = 'approved'
                updated_count += 1
        
        # Commit the changes
        db.commit()
        
        print(f"Successfully approved {updated_count} events out of {len(events)} total events.")
        return updated_count
    except Exception as e:
        db.rollback()
        print(f"Error approving events: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting to approve existing events...")
    try:
        count = approve_all_events()
        print(f"✅ Completed! {count} events have been set to 'approved' status.")
    except Exception as e:
        print(f"❌ Failed to approve events: {str(e)}")
        sys.exit(1)

