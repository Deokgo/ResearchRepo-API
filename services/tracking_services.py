from models import db, Status, Account
from services.auth_services import formatting_id, log_audit_trail
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, desc, nulls_last
from models import db, Publication, ResearchOutput, Status, Conference, PublicationFormat
from datetime import datetime
from services.mail import send_notification_email
from flask_jwt_extended import get_jwt_identity

# Function to create and insert a Status entry
def insert_status(publication_id, status_value):
    try:
        status_id = formatting_id("ST", Status, 'status_id')
        # Create a new Status entry
        new_status = Status(
            status_id=status_id,
            publication_id=publication_id,
            status=status_value,
            timestamp=datetime.now()
        )

        # Add and commit the new entry to the database
        db.session.add(new_status)
        db.session.commit()

        return new_status, None  # Return the created status and no error

    except SQLAlchemyError as e:
        db.session.rollback()  # Rollback in case of an error
        return None, str(e)  # Return no status and the error message
    

def update_status(research_id):
    try:
        new_status = ""
        # Get the current user for audit trail
        current_user = Account.query.get(get_jwt_identity())
        if not current_user:
            return False

        # Retrieve data from request body (JSON)
        publication = Publication.query.filter(Publication.research_id == research_id).first()

        if publication is None:
            return False
        
        # Retrieve the latest status
        current_status = Status.query.filter(Status.publication_id == publication.publication_id).order_by(desc(Status.timestamp)).first()

        # Handle case where current_status is None
        if current_status is None:
            new_status = "SUBMITTED"
            changed_status, error = insert_status(publication.publication_id, new_status)
        else:
            # If there is a current status, handle status transitions
            if current_status.status == "PULLOUT":
                return None
            elif current_status.status == "SUBMITTED":
                new_status = "ACCEPTED"
            elif current_status.status == "ACCEPTED":
                new_status = "PUBLISHED"
            elif current_status.status == "PUBLISHED":
                return None

            # Call the function to insert the new status
            changed_status, error = insert_status(current_status.publication_id, new_status)

        # If there was an error inserting the status, handle it
        if error:
            print(error)
            return False

        # Send email asynchronously
        send_notification_email("NEW PUBLICATION STATUS UPDATE",
                            f'Research paper by {research_id} has been updated to {changed_status.status}.')
        
        # Log the status update in audit trail
        log_audit_trail(
            email=current_user.email,
            role=current_user.role.role_name,
            table_name='Status',
            record_id=changed_status.status_id,
            operation='CREATE',
            action_desc=f'Updated research status to {new_status}'
        )

        return True

    except Exception as e:
        print(f"Error updating status: {str(e)}")
        return False

