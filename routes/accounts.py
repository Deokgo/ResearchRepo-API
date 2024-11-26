from flask import Blueprint, request, jsonify, send_file
from models import Account, UserProfile, Role, Visitor, db
from services import auth_services
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import aliased
from datetime import datetime
import pandas as pd
import random
import string
from io import BytesIO

accounts = Blueprint('accounts', __name__)

#created by Nicole Cabansag, for retrieving all users API
@accounts.route('/users', methods=['GET']) 
def get_all_users():
    try:
        results = db.session.query(Account, Visitor, UserProfile, Role).outerjoin(
            Visitor, Visitor.visitor_id == Account.user_id
        ).outerjoin(
            UserProfile, UserProfile.researcher_id == Account.user_id
        ).outerjoin(
            Role, Role.role_id == Account.role_id
        ).all()

        # Processing the results
        data_list = []
        for account, visitor, user_profile, role in results:
            data_list.append({
                "email": account.email,
                "acc_status": account.acc_status,
                "role_id": account.role_id,
                "institution": visitor.institution if visitor else 'Mapúa Malayan Colleges Laguna',
                "researcher_id": user_profile.researcher_id if user_profile else visitor.visitor_id,
                "college_id": user_profile.college_id if user_profile else None,
                "first_name": user_profile.first_name if user_profile else None,
                "role_name": role.role_name if role else None
            })

        # Returning the results
        return jsonify({"researchers": data_list}), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving all users: {str(e)}"}), 404

#created by Nicole Cabansag, for retrieving all user's acc and info by user_id API
@accounts.route('/users/<user_id>', methods=['GET'])
def get_user_acc_by_id(user_id):
    try:
        results = db.session.query(Account, Visitor, UserProfile, Role).outerjoin(
            Visitor, Visitor.visitor_id == Account.user_id
        ).outerjoin(
            UserProfile, UserProfile.researcher_id == Account.user_id
        ).outerjoin(
            Role, Role.role_id == Account.role_id
        ).filter(
            Account.user_id == user_id  # Filter results by user_id
        ).first()  # Use first() instead of all() to retrieve a single result

        if not results:
            return jsonify({"message": "User not found"}), 404

        account, visitor, user_profile, role = results

        return jsonify({
            "account": {
                "acc_status": account.acc_status,
                "email": account.email,
                "role": role.role_id if role else None,  # Handle case where role might be None
                "role_name": role.role_name if role else None,
                "user_id": account.user_id,
                "user_pw": account.user_pw  # Consider avoiding returning the password for security reasons
            },
            "researcher": {
                "college_id": user_profile.college_id if user_profile else None,
                "first_name": user_profile.first_name if user_profile else visitor.first_name if visitor else None,
                "last_name": user_profile.last_name if user_profile else visitor.last_name if visitor else None,
                "middle_name": user_profile.middle_name if user_profile else visitor.middle_name if visitor else None,
                "program_id": user_profile.program_id if user_profile else None,
                "researcher_id": user_profile.researcher_id if user_profile else visitor.visitor_id if visitor else None,
                "suffix": user_profile.suffix if user_profile else visitor.suffix if visitor else None,
                "institution": visitor.institution if visitor else 'Mapúa Malayan Colleges Laguna'
            }
        }), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving user: {str(e)}"}), 500

@accounts.route('/update_acc/<user_id>', methods=['PUT'])
def update_acc(user_id):
    data = request.json
    try:
        user_acc = Account.query.filter_by(user_id=user_id).first()

        if not user_acc:
            return jsonify({"message": "User not found"}), 404
        
        if data.get('acc_status'):
            user_acc.acc_status = data['acc_status']
        if data.get('role_id'):
            user_acc.role_id = data['role_id']  # Ensure correct field assignment

        db.session.commit()
        
        auth_services.log_audit_trail(
            user_id=None,
            table_name='Account',
            record_id=user_acc.user_id,
            operation='UPDATE',
            action_desc='Account status or role updated'
        )
        return jsonify({
            "account": {
                "user_id": user_acc.user_id,
                "acc_status": user_acc.acc_status,
                "role": user_acc.role.role_name  
            }
        }), 200
    except Exception as e:
        db.session.rollback()  # Rollback in case of any error
        return jsonify({"message": f"Failed to update account: {e}"}), 500

# created by Jelly Mallari for Updating Account API
@accounts.route('/update_account/<user_id>', methods=['PUT'])
def update_account(user_id):
    try:
        data = request.json

        # Retrieve the user's account and associated information
        user_acc = Account.query.filter_by(user_id=user_id).first()
        if not user_acc:
            return jsonify({"message": "User not found"}), 404

        researcher_info = UserProfile.query.filter_by(researcher_id=user_id).first()
        visitor_info = Visitor.query.filter_by(visitor_id=user_id).first()

        # Determine required fields and validation message
        required_fields = ['first_name', 'last_name']
        message = 'First name and last name are required.'
        
        if researcher_info and user_acc.role_id not in ['01', '02', '03']:
            required_fields = ['college_id', 'program_id'] + required_fields
            message = 'College department, program, first name, and last name are required.'

        # Validate required fields
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({"message": message, "missing_fields": missing_fields}), 400

        # Function to update fields
        def update_fields(target, fields):
            for field in fields:
                if field in data:
                    value = data[field]
                    setattr(target, field, None if value is None or value.strip() == '' else value)

        # Update fields for researcher or visitor
        if researcher_info:
            update_fields(researcher_info, ['college_id', 'program_id', 'first_name', 'middle_name', 'last_name', 'suffix'])
        elif visitor_info and user_acc.role_id == '06':
            update_fields(visitor_info, ['first_name', 'middle_name', 'last_name', 'suffix'])

        # Commit changes to the database
        db.session.commit()

        # Log the update event in the Audit_Trail
        auth_services.log_audit_trail(
            user_id=user_acc.user_id, table_name='Account', record_id=user_acc.user_id,
            operation='UPDATE', action_desc='Account information updated'
        )

        # Return the updated account and researcher/visitor data
        return jsonify({
            "researcher": {
                "researcher_id": researcher_info.researcher_id if researcher_info else visitor_info.visitor_id if visitor_info else None,
                "college_id": getattr(researcher_info, 'college_id', None),
                "program_id": getattr(researcher_info, 'program_id', None),
                "first_name": getattr(researcher_info, 'first_name', getattr(visitor_info, 'first_name', None)),
                "middle_name": getattr(researcher_info, 'middle_name', getattr(visitor_info, 'middle_name', None)),
                "last_name": getattr(researcher_info, 'last_name', getattr(visitor_info, 'last_name', None)),
                "suffix": getattr(researcher_info, 'suffix', getattr(visitor_info, 'suffix', None))
            }
        }), 200

    except Exception as e:
        db.session.rollback()  # Rollback in case of any error
        return jsonify({"message": f"Failed to update account: {e}"}), 500

    finally:
        db.session.close()  # Ensure the session is closed

@accounts.route('/search_user', methods=['GET'])
def search_users():
    query = request.args.get('query', '')
    if query:
        users = UserProfile.query.join(Account, UserProfile.researcher_id == Account.user_id)\
                    .filter(Account.role_id.in_(['04', '05', '06']))\
                    .filter((UserProfile.first_name.ilike(f'%{query}%')) | 
                            (UserProfile.last_name.ilike(f'%{query}%')) |
                            (Account.email.ilike(f'%{query}%')))\
                    .add_columns(UserProfile.researcher_id, UserProfile.first_name, UserProfile.last_name, Account.email)\
                    .all()

        result = [{"user_id": user.researcher_id, 
                   "first_name": first_name, 
                   "last_name": last_name, 
                   "email": email} for user, researcher_id, first_name, last_name, email in users]

        return jsonify({"users": result}), 200
    return jsonify({"users": []}), 200

@accounts.route('/fetch_roles', methods=['GET'])
def fetch_roles():
    try:
        #retrieve all roles from the database
        roles = Role.query.order_by(Role.role_id.asc()).all()
        roles_list = [{
            "role_id": role.role_id,
            "role_name": role.role_name
        } for role in roles]

        #return the list of roles
        return jsonify({"roles": roles_list}), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving all roles: {str(e)}"}), 404
    
@accounts.route('/update_password/<user_id>', methods=['PUT'])
def update_password(user_id):
    try:
        data = request.json
        required_fields = ['currentPassword', 'newPassword', 'confirmPassword']
        
        # Check if all required fields are present
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"{field} is required."}), 400
        
        current_pw = data.get('currentPassword')
        user_acc = Account.query.filter_by(user_id=user_id).first()

        if not user_acc:
            return jsonify({"message": "User not found"}), 404

        # Compare hashed password with the provided plain password
        if check_password_hash(user_acc.user_pw, current_pw):
            new_pw = data.get('newPassword')
            if new_pw == current_pw:
                return jsonify({"message": "The new password should be different from the current password."}), 404
            
            # Validate new password strength
            password_error = auth_services.validate_password(new_pw)
            if password_error:
                return jsonify({"message": password_error}), 400
            
            # Ensure passwords match
            if new_pw != data.get('confirmPassword'):
                return jsonify({"message": "Passwords do not match."}), 400
            
            # Update password
            user_acc.user_pw = generate_password_hash(new_pw)

            # Log the audit trail
            try:
                auth_services.log_audit_trail(
                    user_id=user_acc.user_id,  # Pass actual user_id here
                    table_name='Account',
                    record_id=user_acc.user_id,
                    operation='UPDATE',
                    action_desc='Account password updated'
                )
            except Exception as e:
                return jsonify({"message": f"Error logging audit trail: {str(e)}"}), 500

            return jsonify({
                "message": "Password successfully updated.",
                "account": {
                    "user_id": user_acc.user_id
                }
            }), 200
        else:
            return jsonify({"message": "Incorrect current password."}), 400

    except Exception as e:
        return jsonify({"message": f"An unexpected error occurred: {str(e)}"}), 500
    

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Content-Type': 'multipart/form-data'
@accounts.route('/bulk', methods=['POST'])
def add_bulk_users():

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
            user_id = auth_services.formatting_id('US', Account, 'user_id')
            print(user_id)
            user = Account(user_id=user_id,email=email, user_pw=hashed_password, role_id=role_id)
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
    