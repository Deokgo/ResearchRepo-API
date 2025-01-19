from models import db, Status
from services.auth_services import formatting_id, log_audit_trail
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, desc, nulls_last
from models import db, Publication , ResearchOutput, Status, Conference, PublicationFormat
from datetime import datetime
from services.mail import send_notification_email

# Function to create and insert a Status entry
def insert_status( publication_id, status_value):
    try:
        status_id=formatting_id("ST", Status, 'status_id')
        # Create a new Status entry
        new_status = Status(
            status_id=status_id,  # Assuming you have a formatting function for status_id
            publication_id=publication_id,
            status=status_value,
            timestamp=datetime.now()  # Set the current timestamp
        )

        # Add and commit the new entry to the database
        db.session.add(new_status)
        db.session.commit()

        return new_status, None  # Return the created status and no error

    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of an error
        return None, str(e)  # Return no status and the error message
    

