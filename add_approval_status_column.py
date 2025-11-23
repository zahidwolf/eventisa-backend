"""
Migration script to add approval_status column to events table
and set all existing events to 'approved'
"""
import sys
import os

# Add the app directory to the path
app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app')
sys.path.insert(0, app_dir)

from server.database import SessionLocal, engine
from sqlalchemy import text

def add_approval_status_column():
    """Add approval_status column and set all existing events to approved"""
    db = SessionLocal()
    try:
        print("Adding approval_status column to events table...")
        
        # Check if column already exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='events' AND column_name='approval_status'
        """)
        result = db.execute(check_query).fetchone()
        
        if result:
            print("Column 'approval_status' already exists. Updating existing events...")
        else:
            # Add the column with default value 'pending'
            print("Adding 'approval_status' column...")
            alter_query = text("""
                ALTER TABLE events 
                ADD COLUMN approval_status VARCHAR DEFAULT 'pending'
            """)
            db.execute(alter_query)
            db.commit()
            print("✅ Column added successfully!")
        
        # Update all existing events to 'approved'
        print("Updating all existing events to 'approved' status...")
        update_query = text("""
            UPDATE events 
            SET approval_status = 'approved' 
            WHERE approval_status IS NULL OR approval_status = 'pending'
        """)
        result = db.execute(update_query)
        db.commit()
        
        updated_count = result.rowcount
        print(f"✅ Successfully updated {updated_count} events to 'approved' status.")
        
        return updated_count
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting migration to add approval_status column...")
    try:
        count = add_approval_status_column()
        print(f"\n✅ Migration completed successfully! {count} events are now approved.")
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        sys.exit(1)

