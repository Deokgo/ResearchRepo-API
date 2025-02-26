from flask import Blueprint, request, jsonify, current_app, session
from models.account import Account, db
from models.user_profile import UserProfile
from models.visitor import Visitor
from werkzeug.security import check_password_hash, generate_password_hash
from services import auth_services, user_srv
from sqlalchemy.orm import joinedload
from services.mail import send_otp_email
from services.otp import generate_otp
import re
from datetime import datetime,timedelta,timezone
from flask_jwt_extended import (
    get_jwt_identity,
    create_access_token,
    jwt_required
)
import json

auth = Blueprint('auth', __name__)

def get_redis_client():
    redis_client = current_app.redis_client
    return redis_client


@auth.route('/login', methods=['POST']) 
def login():
    data = request.json
    if data:
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400

        try:
            user = Account.query.filter_by(email=email).one_or_none()
            

            if user is None:
                return jsonify({"message": "User not found"}), 404

            if user.acc_status == 'INACTIVE':
                return jsonify({"message": "Account is deactivated. Please contact support."}), 403

            if not check_password_hash(user.user_pw, password):
                return jsonify({"message": "Invalid password"}), 401

            # Generate just the access token
            access_token = create_access_token(identity=user.user_id)
            
            response = jsonify({
                "message": "Login successful",
                "token": access_token
            })
            
            # Log successful login
            auth_services.log_audit_trail(
                email=user.email,
                role=user.role.role_name,
                table_name='Account',
                record_id=None,
                operation='LOGIN',
                action_desc='User logged in'
            )

            # Inside your login route after successful authentication
            user.last_login = datetime.utcnow()
            db.session.commit()

            return response, 200

        except Exception as e:
            return jsonify({"message": str(e)}), 500

#created by Nicole Cabansag, for signup API VISITORS // Modified by Jelly Anne Mallari
@auth.route('/signup', methods=['POST']) 
@jwt_required()
def add_user():
    data = request.json

    #ensure all required fields are present
    required_fields = ['firstName', 'lastName', 'email', 'institution', 'reason', 'password', 'confirmPassword']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"message": f"{field} is required."}), 400
        
    #email validation
    email = data.get('email')
    found_email = Account.query.filter_by(email=email).one_or_none()
    if found_email:
            return jsonify({"message": "Email already exists"}), 409
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        return jsonify({"message": "Invalid email format."}), 400
    
    #password validation
    password = data.get('password')
    if len(password) < 8:
        return jsonify({"message": "Password must be at least 8 characters long."}), 400
    if not re.search(r'[A-Z]', password):
        return jsonify({"message": "Password must contain at least one uppercase letter."}), 400
    if not re.search(r'[a-z]', password):
        return jsonify({"message": "Password must contain at least one lowercase letter."}), 400
    if not re.search(r'[0-9]', password):
        return jsonify({"message": "Password must contain at least one number."}), 400
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return jsonify({"message": "Password must contain at least one special character."}), 400
    
    #ensure passwords match
    if password != data.get('confirmPassword'):
        return jsonify({"message": "Passwords do not match."}), 400
    
    user_id = auth_services.formatting_id('US', Account, 'user_id')
    response, status_code = user_srv.add_new_user(user_id, data)  #role_id assigned to Researcher by default
    
    if status_code == 201:
        # Generate a token for the user
        token = create_access_token(identity=user_id)

        # Modify the response to include the token
        response_data = response.get_json()  # Extract the JSON data from the original response
        response_data['token'] = token  # Add the token

        # Log the successful login in the Audit_Trail
        auth_services.log_audit_trail(
            email=email,
            role='RESEARCHER',
            table_name='Account and Visitor',
            record_id=None,
            operation='SIGNUP',
            action_desc='Created Account'
        )

        return jsonify(response_data), status_code

    return response, status_code

# Created by Jelly Anne Mallari, for adding user (admin side)
@auth.route('/create_account', methods=['POST']) 
def create_account():
    data = request.json

    #ensure all required fields are present
    required_fields = ['firstName', 'lastName', 'email', 'password', 'confirmPassword', 'department', 'program', 'role_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"message": f"{field} is required."}), 400
        
    user_id = auth_services.formatting_id('US', UserProfile, 'researcher_id')

    response, status_code=user_srv.add_new_user(user_id,data,assigned=data.get('role_id'))
    
    if status_code == 201:
        # Generate a token for the user
        token = auth_services.generate_token(user_id)

        # Modify the response to include the token
        response_data = response.get_json()  # Extract the JSON data from the original response
        response_data['token'] = token  # Add the token

        return jsonify(response_data), status_code

    return response, status_code

@auth.route('/me', methods=['GET'])
@jwt_required()
def get_user_details():
    user_id = get_jwt_identity()

    try:
        # Fetch the user with role, visitor, and profile in one query
        user = (
            Account.query
            .options(joinedload(Account.role), joinedload(Account.visitor), joinedload(Account.user_profile))
            .filter_by(user_id=user_id)
            .first()
        )

        if not user:
            return jsonify({"message": "User not found"}), 404

        # Extracting role information safely
        role_id = user.role.role_id if user.role else None
        role_name = user.role.role_name if user.role else None

        # Extract profile info from either visitor or researcher
        visitor = user.visitor
        user_profile = user.user_profile

        data = {
            "user_id": user.user_id,
            "role": role_id,
            "role_name": role_name,
            "email": user.email,
            "first_name": None,
            "last_name": None,
            "college": None,
            "program": None
        }

        if visitor:
            data.update({
                "first_name": visitor.first_name,
                "last_name": visitor.last_name,
                "institution": visitor.institution,
            })
        elif user_profile:
            data.update({
                "first_name": user_profile.first_name,
                "last_name": user_profile.last_name,
                "college": user_profile.college_id,
                "program": user_profile.program_id
            })

        return jsonify(data), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500


@auth.route('/validate-session', methods=['GET'])
@jwt_required()
def validate_session():
    """Endpoint to validate the current session/token"""
    return jsonify({"message": "Token is valid"}), 200

@auth.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # Get the current user's identity
    user_id = get_jwt_identity()
    
    # Get user details for audit trail
    user = Account.query.get(user_id)
    if user:
        # Log the logout operation
        auth_services.log_audit_trail(
            email=user.email,
            role=user.role.role_name,
            table_name='Account',
            record_id=None,
            operation='LOGOUT',
            action_desc='User logged out'
        )
    return jsonify({"message": "Logout successful"}), 200

@auth.route('/send_otp', methods=['POST'])
def send_registration_otp():
    try:
        email = request.json['email']
        is_password_reset = request.json.get('isPasswordReset', False)

        if not is_password_reset:
            user_exists = Account.query.filter_by(email=email).first() is not None
            if user_exists:
                return jsonify({"error": "User already exists"}), 409
        else:
            user_exists = Account.query.filter_by(email=email).first() is not None
            if not user_exists:
                return jsonify({"error": "No account found with this email"}), 404

        redis_client = get_redis_client()
        otp_key = f"otp:{email}"  # Unique key for each user (using email)
        
        # Check if an OTP already exists
        existing_otp = redis_client.get(otp_key)
        if existing_otp:
            return jsonify({"error": "An OTP has already been sent. Please wait before requesting a new one."}), 429

        # Generate and store a new OTP
        otp = generate_otp()
        redis_client.setex(otp_key, timedelta(minutes=5), otp)

        # Send OTP email
        send_otp_email(email, 'Your OTP Code', f'Your OTP code is {otp}')
        
        return jsonify({"message": "OTP sent successfully. Please verify your email.", "otp": otp})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    
@auth.route('/verify_otp', methods=['POST'])
def verify_registration_otp():
    try:
        email = request.json['email']
        otp_input = request.json['otp']

        redis_client = get_redis_client()
        otp_key = f"otp:{email}"
        otp_stored = redis_client.get(otp_key)

        if otp_stored is None:
            return jsonify({"error": "OTP request not found or expired."}), 400

        # Verify OTP
        if otp_input != otp_stored:
            return jsonify({"error": "Invalid OTP."}), 400

        # OTP is valid, proceed to next step of registration
        # Cleanup: Delete the OTP from Redis after it has been used
        redis_client.delete(otp_key)

        return jsonify({"message": "OTP verified. You can now complete your registration."})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@auth.route('/reset_password', methods=['POST'])
def reset_password():
    try:
        data = request.json
        email = data.get('email')
        new_password = data.get('newPassword')

        if not email or not new_password:
            return jsonify({"message": "Email and new password are required"}), 400

        # Find the user account
        user = Account.query.filter_by(email=email).first()
        if not user:
            return jsonify({"message": "User not found"}), 404

        # Validate password strength
        password_error = auth_services.validate_password(new_password)
        if password_error:
            return jsonify({"message": password_error}), 400

        try:
            # Update the password
            user.user_pw = generate_password_hash(new_password)
            db.session.commit()

            # Log the password reset
            auth_services.log_audit_trail(
                email=user.email,
                role=user.role.role_name,
                table_name='Account',
                record_id=user.user_id,
                operation='UPDATE',
                action_desc='Password reset completed'
            )

            return jsonify({"message": "Password reset successful"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"message": f"Database error: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"message": f"An error occurred: {str(e)}"}), 500