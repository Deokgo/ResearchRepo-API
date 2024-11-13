from flask import Blueprint, request, jsonify, current_app, session
from models.account import Account
from models.user_profile import UserProfile
from models.visitor import Visitor
from werkzeug.security import check_password_hash
from services import auth_services, user_srv
import jwt
import datetime
from sqlalchemy.orm import joinedload

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['POST']) 
def login():
    session.clear() # making sure that the session is empty before we store the session

    data = request.json
    if data:
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400

        try:
            # Retrieve the account with the joined user profile, college, and program data
            user = (
                Account.query
                .filter_by(email=email)
                .options(
                    joinedload(Account.user_profile)
                    .joinedload(UserProfile.college),
                    joinedload(Account.user_profile)
                    .joinedload(UserProfile.program)
                )
                .one_or_none()
            )

            if user is None:
                return jsonify({"message": "User not found"}), 404

            # Compare hashed password with the provided plain password
            if check_password_hash(user.user_pw, password):
                # Generate token on successful login
                token = auth_services.generate_token(user.user_id)
                session['user_id'] = user.user_id

                # Log successful login in the Audit_Trail
                auth_services.log_audit_trail(
                    user_id=user.user_id,
                    table_name='Account',
                    record_id=None,
                    operation='LOGIN',
                    action_desc='User logged in'
                )

                return jsonify({
                    "message": "Login successful",
                    "user_id": user.user_id,
                    "role": user.role.role_id,
                    "college": user.user_profile.college.college_id if user.user_profile.college else None,
                    "program": user.user_profile.program.program_id if user.user_profile.program else None,
                    "token": token
                }), 200
            else:
                return jsonify({"message": "Invalid password"}), 401

        except Exception as e:
            return jsonify({"message": str(e)}), 500

#created by Nicole Cabansag, for signup API // Modified by Jelly Anne Mallari
@auth.route('/signup', methods=['POST']) 
def add_user():
    data = request.json

    #ensure all required fields are present
    required_fields = ['firstName', 'lastName', 'email', 'institution', 'reason', 'password', 'confirmPassword']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"message": f"{field} is required."}), 400
        
    user_id = auth_services.formatting_id('US', Visitor, 'visitor_id')

    response, status_code=user_srv.add_new_user(user_id,data) #role_id assigned to Researcher by default
    
    if status_code == 201:
        # Generate a token for the user
        token = auth_services.generate_token(user_id)

        # Modify the response to include the token
        response_data = response.get_json()  # Extract the JSON data from the original response
        response_data['token'] = token  # Add the token

        #log the successful login in the Audit_Trail
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