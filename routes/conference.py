from flask import Blueprint, request, jsonify, session
from models import db, Conference, Account
from services import auth_services
from datetime import datetime
import traceback
from flask_jwt_extended import jwt_required, get_jwt_identity

conference = Blueprint('conference', __name__)

@conference.route('/add_conference', methods=['POST'])
@jwt_required()
def add_conference():
    try:
        # Get the current user for audit trail
        current_user = Account.query.get(get_jwt_identity())
        if not current_user:
            return jsonify({"error": "Current user not found"}), 401

        data = request.form  # Get form data
        
        # Required fields list
        required_fields = [
            'conference_title', 'country', 'city', 'conference_date', 
        ]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        date_obj = datetime.strptime(data['conference_date'], '%Y-%m-%d')
        conference_date = date_obj.strftime('%Y%m%d')
        
        # Query the last entry for the current date to get the latest ID
        last_entry = Conference.query.filter(getattr(Conference, 'conference_id').like(f'CF-{conference_date}-%')) \
                                    .order_by(getattr(Conference, 'conference_id').desc()) \
                                    .first()

        # Determine the next sequence number
        if last_entry:
            last_sequence = int(getattr(last_entry, 'conference_id').split('-')[-1])
            next_sequence = f"{last_sequence + 1:03d}"
        else:
            next_sequence = "001"  # Start with 001 if no previous entry

        # Generate the new ID
        generated_id = f"CF-{conference_date}-{next_sequence}"

        # Format conference venue
        venue = f"{data['country']}, {data['city']}"
        
        new_conference = Conference(
            conference_id=generated_id,
            conference_title=data['conference_title'],
            conference_venue=venue,
            conference_date=conference_date
        )
        db.session.add(new_conference)
        db.session.commit()

        # Log audit trail
        auth_services.log_audit_trail(
            email=current_user.email,
            role=current_user.role.role_name,
            table_name='Conference',
            record_id=new_conference.conference_id,
            operation='CREATE',
            action_desc='Added new conference'
        )

        return jsonify({
            "message": "Conference added successfully", 
            "conference_id": new_conference.conference_id
        }), 201
    
    except Exception as e:     
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
        
    finally:
        db.session.close()