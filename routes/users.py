from flask import Blueprint, request, jsonify, json,send_file
from werkzeug.security import generate_password_hash,check_password_hash
from app.models import db,Conference,Role, UserProfile,Program,College,Account,Role
from flask_jwt_extended import get_jwt_identity,jwt_required,get_jwt
from app.decorators.acc_decorators import roles_required
from app.services.logs import formatting_id,log_audit_trail
from uuid import UUID
from datetime import datetime
import pandas as pd
import random
import string
from io import BytesIO

users = Blueprint('users',__name__)
def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Content-Type': 'multipart/form-data'
@users.route('/bulk', methods=['POST'])
#@jwt_required()
def add_bulk_users():
    #current_user = get_jwt_identity()

    try:
        # Validate and retrieve `role_id`
        role_id = request.form.get('role_id')
        if not role_id:
            return jsonify({"error": "Role ID is required"}), 400
        
        roles = Role.query.filter_by(role_id=role_id).first()
        if not roles:
            return jsonify({"error": f"Role with ID {role_id} not found"}), 404
        
        role_name = roles.role_name

        # Validate file upload
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({"error": "Only CSV files are allowed"}), 400

        # Read and process CSV
        df = pd.read_csv(file)
        df.columns = df.columns.str.lower()
        
        if 'email' not in df.columns:
            return jsonify({"error": "'email' column not found in the uploaded CSV"}), 400

        # Clean up the data
        df = df.dropna(subset=['email'])
        df = df[df['email'].str.strip() != '']
        
        # Track successful records
        records = []
        for email in df['email']:
            email = email.strip()
            password = generate_password()
            hashed_password = generate_password_hash(password)
            
            # Check if user already exists
            if Account.query.filter_by(email=email).first():
                print(f"{email} already exists")
                continue

            # Create new user
            user = Account(email=email, user_pw=hashed_password, role_id=role_id)
            db.session.add(user)
            db.session.commit()

            # Append record for output file
            records.append({'email': email, 'password': password})

        # If no new users were created
        if not records:
            return jsonify({"message": "No new users were added. All emails already exist."}), 200

        # Create output CSV
        output_df = pd.DataFrame(records)
        output = BytesIO()
        output_df.to_csv(output, index=False)
        output.seek(0)
        
        #log_audit_trail(user_id=current_user, table_name='Account', record_id=None,
        #                              operation='CREATE ACCOUNTS', action_desc=f'Created {len(output_df)} accounts through csv file.')

        current_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Return the file as an attachment
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"{current_timestamp}_Accounts_{role_name}.csv"
        )

    except Exception as e:
        # Handle any other exceptions gracefully
        return jsonify({'error': str(e)}), 400
    
@users.route('/accounts',methods=['GET'])
@users.route('/accounts/<user_id>',methods=['GET','POST','PUT'])
#@jwt_required()
def user_accounts(user_id = None):
    #current_user = get_jwt_identity()

    if request.method=='GET':
        try:
            query = db.session.query(Account, UserProfile, Role).\
                outerjoin(UserProfile, UserProfile.researcher_id == Account.user_id).\
                outerjoin(Role, Role.role_id == Account.role_id)
            if user_id:
                query = query.filter(Account.user_id == user_id)

            researchers = query.all()

            researchers_data = []
            for account, researcher, role in researchers:
                researcher_data = {
                    'researcher_id': account.user_id,
                    'first_name': researcher.first_name if researcher else "None",
                    'middle_name': researcher.middle_name if researcher else "",
                    'last_name': researcher.last_name if researcher else "None",
                    'college_id': researcher.college_id if researcher else "None",
                    'program_id': researcher.program_id if researcher else "None",
                    'email': account.email if account else "None",
                    'role_id': role.role_name if role else "None",
                    'status':account.acc_status
                }
                researchers_data.append(researcher_data)

            return jsonify(researchers_data), 200

        except Exception as e:
            return jsonify({"message": f"Error retrieving all users: {str(e)}"}), 404
    elif request.method=='POST':
        try:
            data = request.json

            college_id = data.get('college_id')
            program_id = data.get('program_id') 
            first_name = data.get('first_name', None) 
            middle_name = data.get('middle_name', None) 
            last_name = data.get('last_name', None) 
            suffix = data.get('suffix', None) 

            if not user_id:
                return jsonify({"error": "Unauthorized Access"}), 401
            
            user_exists = UserProfile.query.filter_by(researcher_id=user_id).first() is not None
            if user_exists:
                return jsonify({"error":"User already exists"}), 409
            
            user_info = UserProfile(
                researcher_id=user_id,
                college_id=college_id,
                program_id=program_id,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                suffix=suffix
            )

            db.session.add(user_info)
            db.session.commit()

            #log_audit_trail(user_id=current_user, table_name='User Profile', record_id=None,
            #                          operation='CREATE USER PROFILE', action_desc=f'Added User Profile to user {user_id}')

            return jsonify({"message": "User profile created successfully!"}), 201
            
        except Exception as e:
            return jsonify({"message": f"Error retrieving all users: {str(e)}"}), 404
        
    elif request.method == 'PUT':
        try:
            if not user_id:
                return jsonify({"error": "User ID is required for updating."}), 400
             # Retrieve user profile and associated account data
            user_info = UserProfile.query.filter_by(researcher_id=user_id).first()

            if user_info is None:
                return jsonify({"error":"User profile not found"}), 404

            data = request.json

            user_info.college_id = data.get('college_id', user_info.college_id)
            user_info.program_id = data.get('program_id', user_info.program_id)
            user_info.first_name = data.get('first_name', user_info.first_name)
            user_info.middle_name = data.get('middle_name', user_info.middle_name)
            user_info.last_name = data.get('last_name', user_info.last_name)
            user_info.suffix = data.get('suffix', user_info.suffix)

            db.session.commit()
            #log_audit_trail(user_id=current_user, table_name='User Profile', record_id=None,
            #                          operation='EDIT USER PROFILE', action_desc=f'Edited User Profile of user {user_id}')

            return jsonify({"message": "User profile updated successfully!"}), 200

        except Exception as e:
            return jsonify({"message": f"Error updating user profile: {str(e)}"}), 500
        

@users.route('/accounts/deactivate', methods=['PUT'])
#@jwt_required()
def deactivate_multiple_accounts():
    #current_user = get_jwt_identity()
    try:
        emails = request.json.get('emails')

        if not emails or not isinstance(emails, list):
            return jsonify({"error": "A list of email addresses is required."}), 400

        # Validate that all emails are properly formatted
        if not all(isinstance(email, str) and '@' in email for email in emails):
            return jsonify({"error": "One or more email addresses are invalid."}), 400

        # Fetch the accounts based on email, not researcher_id
        accounts_to_deactivate = Account.query.filter(Account.email.in_(emails)).all()
        print(accounts_to_deactivate)

        if not accounts_to_deactivate:
            return jsonify({"error": "No accounts found for the provided email addresses."}), 404

        for account in accounts_to_deactivate:
            print(account.acc_status)
            account.acc_status = 'DEACTIVATED'

        db.session.commit()

        #log_audit_trail(user_id=current_user, table_name='Accounts', record_id=None,
        #                operation='DEACTIVATE ACCOUNTS', action_desc=f'Deactivated accounts emails: {", ".join(emails)}')

        return jsonify({"message": f"Accounts deactivated successfully for emails: {', '.join(emails)}"}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    
@users.route('/accounts/activate', methods=['PUT'])
#@jwt_required()
def activate_multiple_accounts():
    #current_user = get_jwt_identity()
    try:
        emails = request.json.get('emails')

        if not emails or not isinstance(emails, list):
            return jsonify({"error": "A list of email addresses is required."}), 400

        # Validate that all emails are properly formatted
        if not all(isinstance(email, str) and '@' in email for email in emails):
            return jsonify({"error": "One or more email addresses are invalid."}), 400

        # Fetch the accounts based on email, not researcher_id
        accounts_to_activate = Account.query.filter(Account.email.in_(emails)).all()
        print(accounts_to_activate)

        if not accounts_to_activate:
            return jsonify({"error": "No accounts found for the provided email addresses."}), 404

        for account in accounts_to_activate:
            account.acc_status = 'ACTIVATED'

        db.session.commit()

        #log_audit_trail(user_id=current_user, table_name='Accounts', record_id=None,
        #                operation='ACTIVATE ACCOUNTS', action_desc=f'Activated accounts emails: {", ".join(emails)}')

        return jsonify({"message": f"Accounts activated successfully for emails: {', '.join(emails)}"}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500