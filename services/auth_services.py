import datetime
from flask import Blueprint, request, jsonify, current_app, session, make_response
from models import db
import jwt
import re
from functools import wraps
from models.account import Account

# Function for generating a new ID (for Primary Key)
def formatting_id(indicator, model_class, id_field):
    """Generate a new ID based on the current date and last entry."""
    current_date_str = datetime.datetime.now().strftime('%Y%m%d')

    # Query the last entry for the current date to get the latest ID
    last_entry = model_class.query.filter(getattr(model_class, id_field).like(f'{indicator}-{current_date_str}-%')) \
                                  .order_by(getattr(model_class, id_field).desc()) \
                                  .first()

    # Determine the next sequence number
    if last_entry:
        last_sequence = int(getattr(last_entry, id_field).split('-')[-1])
        next_sequence = f"{last_sequence + 1:03d}"
    else:
        next_sequence = "001"  # Start with 001 if no previous entry

    # Generate the new ID
    generated_id = f"{indicator}-{current_date_str}-{next_sequence}"
    return generated_id

# Function for logging audit trails
def log_audit_trail(user_id, table_name, record_id, operation, action_desc):
    """Log an audit trail entry."""
    from models.audit_trail import AuditTrail
    try:
        audit_id = formatting_id('AUD', AuditTrail, 'audit_id')

        # Create the audit trail entry
        new_audit = AuditTrail(
            audit_id=audit_id,
            user_id=user_id,
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

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'message': 'Token is missing!'}), 401

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            # Decode the token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            user_id = data['user_id']
            
            # Store user_id in session
            session['user_id'] = user_id

            # Verify if user still exists in database
            current_user = Account.query.get(user_id)
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401

        return f(*args, **kwargs)

    return decorated

def generate_tokens(user_id):
    """Generate both access and refresh tokens for the user."""
    # Access token - short lived (15 minutes)
    access_token_payload = {
        'user_id': user_id,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15),
        'type': 'access'
    }
    
    # Refresh token - longer lived (7 days)
    refresh_token_payload = {
        'user_id': user_id,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
        'type': 'refresh'
    }
    
    try:
        access_token = jwt.encode(access_token_payload, current_app.config['SECRET_KEY'], algorithm='HS256')
        refresh_token = jwt.encode(refresh_token_payload, current_app.config['REFRESH_SECRET_KEY'], algorithm='HS256')
        return access_token, refresh_token
    except Exception as e:
        print(f"Error generating tokens: {e}")
        return None, None

def set_refresh_token_cookie(response, refresh_token):
    """Set refresh token as HTTP-only cookie"""
    response.set_cookie(
        'refresh_token',
        refresh_token,
        httponly=True,
        secure=True,  # Only send over HTTPS
        samesite='Strict',
        max_age=7 * 24 * 60 * 60  # 7 days in seconds
    )
    return response
