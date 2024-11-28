from flask import Blueprint, request, jsonify, current_app, session
from models.account import Account
from models.user_profile import UserProfile
from models.visitor import Visitor
from werkzeug.security import check_password_hash
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

            if user.acc_status == 'DEACTIVATED':
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
                user_id=user.user_id,
                table_name='Account',
                record_id=None,
                operation='LOGIN',
                action_desc='User logged in'
            )

            return response, 200

        except Exception as e:
            return jsonify({"message": str(e)}), 500

#created by Nicole Cabansag, for signup API VISITORS // Modified by Jelly Anne Mallari
@auth.route('/signup', methods=['POST']) 
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
    
    #generate user ID and proceed with user creation
    user_id = auth_services.formatting_id('US', Visitor, 'visitor_id')
    response, status_code = user_srv.add_new_user(user_id, data)  #role_id assigned to Researcher by default
    
    if status_code == 201:
        # Generate a token for the user
        token = auth_services.generate_tokens(user_id)

        # Modify the response to include the token
        response_data = response.get_json()  # Extract the JSON data from the original response
        response_data['token'] = token  # Add the token

        # Log the successful login in the Audit_Trail
        auth_services.log_audit_trail(user_id=user_id, table_name='Account and Visitor', record_id=None,
                    operation='SIGNUP', action_desc='Created Account')

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
        user = Account.query.get(user_id)
        if not user:
            return jsonify({"message": "User not found"}), 404

        user_profile = UserProfile.query.filter_by(researcher_id=user.user_id).one_or_none()
        
        return jsonify({
            "user_id": user.user_id,
            "role": user.role.role_id,
            "college": user_profile.college_id if user_profile else None,
            "program": user_profile.program_id if user_profile else None
        }), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

@auth.route('/validate-session', methods=['GET'])
@jwt_required()
def validate_session():
    """Endpoint to validate the current session/token"""
    return jsonify({"message": "Token is valid"}), 200

@auth.route('/logout', methods=['POST'])
def logout():
    return jsonify({"message": "Logout successful"}), 200

@auth.route('/send_otp', methods=['POST'])
def send_registration_otp():
    try:
        email = request.json['email']

        # Check if the user already exists
        user_exists = Account.query.filter_by(email=email).first() is not None
        if user_exists:
            return jsonify({"error": "User already exists"}), 409

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