import datetime
from flask import Blueprint, request, jsonify, current_app, session, make_response
from models import db
from models.audit_trail import AuditTrail
import jwt
import re
from functools import wraps
from models.account import Account
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    set_refresh_cookies,
    unset_jwt_cookies
)

def formatting_id(indicator, model_class, id_field):
    """
    Generate a new ID based on the current date and last entry.
    
    For 'AUD', format as 'AUD-YYYYMMDD-XXXXX' with five-digit increment.
    For others, format as 'indicator-YYYYMMDD-XXX' with three-digit increment.
    """
    current_date_str = datetime.datetime.now().strftime('%Y%m%d')
    
    # Set the format and increment based on the indicator
    if indicator == "AUD":
        sequence_length = 5
    else:
        sequence_length = 3
    
    # Query the last entry for the current date to get the latest ID
    last_entry = model_class.query.filter(getattr(model_class, id_field).like(f'{indicator}-{current_date_str}-%')) \
                                  .order_by(getattr(model_class, id_field).desc()) \
                                  .first()
    
    # Determine the next sequence number
    if last_entry:
        last_sequence = int(getattr(last_entry, id_field).split('-')[-1])
        next_sequence = f"{last_sequence + 1:0{sequence_length}d}"
    else:
        next_sequence = f"{1:0{sequence_length}d}"  # Start with the correct zero-padded sequence
    
    # Generate the new ID
    generated_id = f"{indicator}-{current_date_str}-{next_sequence}"
    return generated_id

# Function for logging audit trails
def log_audit_trail(email, role, table_name, record_id, operation, action_desc):
    try:
        audit_id = formatting_id('AUD', AuditTrail, 'audit_id')

        # Create the audit trail entry
        new_audit = AuditTrail(
            audit_id=audit_id,
            email=email,
            role=role,
            table_name=table_name,
            record_id=record_id,
            operation=operation,
            change_datetime=datetime.datetime.now(),
            action_desc=action_desc
        )

        # Add and commit the new audit log
        db.session.add(new_audit)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        # Log the error message to a file or monitoring system
        print(f"Error logging audit trail: {e}")  # Change this to a logging call in production
    
# Password Validation Function
def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return "Password must contain at least one number."
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return "Password must contain at least one special character."
    return None

def generate_tokens(user_id):
    """Generate access token for the user."""
    access_token = create_access_token(identity=user_id)
    return access_token

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        # Get the current user's identity (user_id)
        current_user_id = get_jwt_identity()
        
        # Query the user's role from the database
        user = Account.query.filter_by(user_id=current_user_id).first()
        
        # Check if user exists and has admin role (role_id = "01")
        if not user or user.role_id != "01":
            return jsonify({"error": "Admin privileges required"}), 403
            
        return f(*args, **kwargs)
    return decorated_function