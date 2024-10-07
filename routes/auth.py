from flask import Blueprint, request, jsonify, current_app
from models.account import Account
from models.user_profile import UserProfile
from werkzeug.security import check_password_hash
import jwt
import datetime
from services import auth_services,user_srv


auth = Blueprint('auth', __name__)


#modified by Nicole Cabansag, added comparing hashed values for user_pw
@auth.route('/login', methods=['POST']) 
def login():
    data = request.json
    if data:
        live_account = data.get('email')
        password = data.get('password')

        if not live_account or not password:
            return jsonify({"message": "Email and password are required"}), 400

        try:
            #retrieve user from the database
            user = Account.query.filter_by(live_account=live_account).one()

            #compare hashed password with the provided plain password
            if check_password_hash(user.user_pw, password):
                #if login successful...

                # Send this token to client to authenticate user
                token = auth_services.generate_token(user.user_id)

                #log the successful login in the Audit_Trail
                auth_services.log_audit_trail(user_id=user.user_id, table_name='Account', record_id=None,
                                operation='LOGIN', action_desc='User logged in')
                
                return jsonify({
                    "message": "Login successful",
                    "user_id": user.user_id,
                    "role": user.role.role_name,
                    "token": token
                }), 200
            else:
                return jsonify({"message": "Invalid password"}), 401

        except:
            return jsonify({"message": "User not found"}), 404
        
#created by Nicole Cabansag, for signup API // Modified by Jelly Anne Mallari
@auth.route('/signup', methods=['POST']) 
def add_user():
    data = request.json

    #ensure all required fields are present
    required_fields = ['firstName', 'lastName', 'email', 'password', 'confirmPassword', 'department', 'program']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"message": f"{field} is required."}), 400
        
    user_id = auth_services.formatting_id('US', UserProfile, 'researcher_id')

    response, status_code=user_srv.add_new_user(user_id,data) #role_id assigned to Researcher by default
    
    if status_code == 201:
        # Generate a token for the user
        token = auth_services.generate_token(user_id)

        # Modify the response to include the token
        response_data = response.get_json()  # Extract the JSON data from the original response
        response_data['token'] = token  # Add the token

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

