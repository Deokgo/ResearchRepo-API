from flask import Blueprint, request, jsonify, current_app
from models.account import Account
from models.researchers import Researcher
from models.roles import Role

from models import db
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from services import auth_services


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
                token = jwt.encode({
                    'user_id': user.user_id,
                    'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)  # Token expires in 1 day
                }, current_app.config['SECRET_KEY'], algorithm='HS256')

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
        
#created by Nicole Cabansag, for signup API
@auth.route('/signup', methods=['POST']) 
def add_user():
    data = request.json

    #ensure all required fields are present
    required_fields = ['firstName', 'lastName', 'email', 'password', 'confirmPassword', 'department', 'program', 'role_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"message": f"{field} is required."}), 400
        
    #generate the new user_id with the incremented sequence number
    user_id = auth_services.formatting_id('US', Researcher, 'researcher_id')

    try:
        # Insert data into the Account table
        new_account = Account(
            user_id=user_id,  #assuming email is used as the user_id
            live_account=data['email'],  #mapúa MCL live account
            user_pw=generate_password_hash(data['password']),
            acc_status='ACTIVATED',  #assuming account is actived by default, change as needed
            role_id=data.get('role_id'),  
        )
        db.session.add(new_account)

        #insert data into the Researcher table
        new_researcher = Researcher(
            researcher_id=new_account.user_id,  #use the user_id from Account
            college_id=data['department'],  #department corresponds to college_id
            program_id=data['program'],  #program corresponds to program_id
            first_name=data['firstName'],
            middle_name=data.get('middleName'),  #allowing optional fields
            last_name=data['lastName'],
            suffix=data.get('suffix')  #allowing optional suffix
        )
        db.session.add(new_researcher)

        #commit both operations
        db.session.commit()

        #log the account creation in the Audit_Trail
        auth_services.log_audit_trail(user_id=new_account.user_id, table_name='Account', record_id=None,
                        operation='CREATE', action_desc='New account created')
        
         # Generate JWT token for immediate login
        token = jwt.encode({
            'user_id': new_account.user_id,
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)  # Token expires in 1 day
        }, current_app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
                    "message": "Signup successful",
                    "user_id": user_id,
                    "token": token
                }), 200

    except Exception as e:
        db.session.rollback()  #rollback in case of error
        return jsonify({"message": f"Failed to add user: {e}"}), 500

    finally:
        db.session.close()  #close the session
