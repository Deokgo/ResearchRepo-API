from flask import Blueprint, request, jsonify, send_file, Response
from models import Account, UserProfile, Role, Visitor, db
from services import auth_services
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import aliased
from datetime import datetime
import pandas as pd
import random
import string
from flask_jwt_extended import jwt_required, get_jwt_identity
from io import BytesIO, StringIO
import csv
import json


accounts = Blueprint('accounts', __name__)

#created by Nicole Cabansag, for retrieving all users API
@accounts.route('/users', methods=['GET']) 
@jwt_required()
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
@jwt_required()
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
@jwt_required()
def update_acc(user_id):
    data = request.json
    try:
        # Get the current user for audit trail
        current_user = Account.query.get(get_jwt_identity())
        if not current_user:
            return jsonify({"error": "Current user not found"}), 404

        user_acc = Account.query.filter_by(user_id=user_id).first()
        if not user_acc:
            return jsonify({"message": "User not found"}), 404
        
        if data.get('acc_status'):
            user_acc.acc_status = data['acc_status']
        if data.get('role_id'):
            user_acc.role_id = data['role_id']  # Ensure correct field assignment

        db.session.commit()
        
        auth_services.log_audit_trail(
            email=current_user.email,
            role=current_user.role.role_name,
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
        # Get the current user for audit trail
        current_user = Account.query.get(get_jwt_identity())
        if not current_user:
            return jsonify({"error": "Current user not found"}), 404

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

        # Dictionary to track changes
        changes = []

        # Function to update fields and track changes
        def update_fields(target, fields):
            for field in fields:
                if field in data:
                    value = data[field]
                    new_value = None if value is None or value.strip() == '' else value
                    current_value = getattr(target, field, None)
                    if current_value != new_value:  # Track only if there's a change
                        setattr(target, field, new_value)
                        changes.append(f"{field}: '{current_value}' -> '{new_value}'")

        # Update fields for researcher or visitor
        if researcher_info:
            update_fields(researcher_info, ['college_id', 'program_id', 'first_name', 'middle_name', 'last_name', 'suffix'])
        elif visitor_info and user_acc.role_id == '06':
            update_fields(visitor_info, ['first_name', 'middle_name', 'last_name', 'suffix'])

        # Commit changes to the database
        db.session.commit()

        # Log the update event in the Audit_Trail with specific changes
        formatted_changes = "\n".join(changes)
        auth_services.log_audit_trail(
            email=current_user.email,
            role=current_user.role.role_name,
            table_name='Account',
            record_id=user_acc.user_id,
            operation='UPDATE',
            action_desc=f'Account profile updated:\n{formatted_changes}'
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

@accounts.route('/update_status/<user_id>', methods=['PUT'])
def update_status(user_id):
    try:
        data = request.json

        # Validate that 'acc_status' is provided in the request body
        if 'acc_status' not in data:
            return jsonify({"message": "Missing 'acc_status' in request body"}), 400

        new_status = data['acc_status']

        # Retrieve the user's account and associated information
        user_acc = Account.query.filter_by(user_id=user_id).first()
        if not user_acc:
            return jsonify({"message": "User not found"}), 404

        # Update the acc_status field
        user_acc.acc_status = new_status

        # Commit changes to the database
        db.session.commit()

        # Log the update event in the Audit_Trail
        auth_services.log_audit_trail(
            email=user_acc.email,
            role=user_acc.role.role_name,
            table_name='Account',
            record_id=user_acc.user_id,
            operation='UPDATE',
            action_desc=f"Account status updated to '{new_status}'"
        )

        # Return the updated account status
        return jsonify({
            "researcher": {
                "status": user_acc.acc_status
            }
        }), 200

    except Exception as e:
        db.session.rollback()  # Rollback in case of any error
        return jsonify({"message": f"Failed to update status account: {e}"}), 500

    finally:
        db.session.close()  # Ensure the session is closed


@accounts.route('/search_user', methods=['GET'])
@accounts.route('/search_user/<college_id>', methods=['GET'])
@jwt_required()
def search_users(college_id=None):
    query = request.args.get('query', '')
    
    # Base query
    user_query = UserProfile.query.join(Account, UserProfile.researcher_id == Account.user_id)\
                .filter(Account.role_id.in_(['04', '05', '06']))
    
    # Add filter for college_id if provided
    if college_id:
        user_query = user_query.filter(UserProfile.college_id == college_id)
    
    # Add search filters if query parameter is provided
    if query:
        user_query = user_query.filter(
            (UserProfile.first_name.ilike(f'%{query}%')) | 
            (UserProfile.last_name.ilike(f'%{query}%')) |
            (Account.email.ilike(f'%{query}%'))
        )
    
    # Add required columns to the query
    users = user_query.add_columns(
        UserProfile.researcher_id, 
        UserProfile.first_name, 
        UserProfile.last_name, 
        Account.email
    ).all()
    
    # Format the result
    result = [
        {
            "user_id": user.researcher_id, 
            "first_name": first_name, 
            "last_name": last_name, 
            "email": email
        } 
        for user, researcher_id, first_name, last_name, email in users
    ]
    
    return jsonify({"users": result}), 200


@accounts.route('/fetch_roles', methods=['GET'])
@jwt_required()
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
@jwt_required()
def update_password(user_id):
    try:
        data = request.json
        required_fields = ['newPassword', 'confirmPassword']

        # Check if all required fields are present
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"{field} is required."}), 400

        user_acc = Account.query.filter_by(user_id=user_id).first()

        if not user_acc:
            return jsonify({"message": "User not found"}), 404

        new_pw = data.get('newPassword')

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
                email=user_acc.email,
                role=user_acc.role.role_name,
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

    except Exception as e:
        return jsonify({"message": f"An unexpected error occurred: {str(e)}"}), 500
    

def generate_password(length=8):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Content-Type': 'multipart/form-data'
@accounts.route('/bulk', methods=['POST'])
@jwt_required()
def add_bulk_users():
    try:
        # Get the user data
        users_data = request.form.get('users')  # This will be a JSON string
        user_id = get_jwt_identity()
        if not users_data:
            return jsonify({"error": "Missing user data"}), 400
            
        users = json.loads(users_data)
        
        # Process users
        records = []
        for user in users:
            email = user['email'].strip()
            
            # Check if user exists
            if Account.query.filter_by(email=email).first():
                continue
                
            password = generate_password()
            hashed_password = generate_password_hash(password)
            
            # Create user account
            acc_id = auth_services.formatting_id('US', Account, 'user_id')
            new_account = Account(
                user_id=acc_id,
                email=email,
                user_pw=hashed_password,
                role_id=user['roleId']
            )
            db.session.add(new_account)
            
            # Create user profile
            profile = UserProfile(
                researcher_id=acc_id,
                college_id=user['collegeId'],
                program_id=user['programId'],
                first_name=user['firstName'],
                middle_name=user['middleInitial'],
                last_name=user['surname'],
                suffix=user['suffix']
            )
            db.session.add(profile)
            
            # Add to records for CSV output
            records.append({
                'email': email,
                'password': password,
                'first_name': user['firstName'],
                'middle_initial': user['middleInitial'],
                'surname': user['surname'],
                'suffix': user['suffix']
            })
            
            # Log the audit trail for each user created
            auth_services.log_audit_trail(
                email=user_id,
                role=user_id,
                table_name='Account',
                record_id=acc_id,
                operation='CREATE',
                action_desc='Added user'
            )
            
        db.session.commit()
        
        # Create output CSV
        if records:
            output_df = pd.DataFrame(records)
            output = BytesIO()
            output_df.to_csv(output, index=False)
            output.seek(0)
            
            current_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return send_file(
                output,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f"{current_timestamp}_Accounts.csv"
            )
        
        return jsonify({"message": "No new users were added. All emails already exist."}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@accounts.route('/get_template', methods=['GET'])
def generate_csv_template():
    # Define the fields
    fields = ["email", "first_name", "middle_initial", "surname", "suffix"]
    
    # Create an in-memory buffer for the CSV data
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields)
    
    # Write the header
    writer.writeheader()
    
    # Return the buffer as a response
    response = Response(buffer.getvalue(), content_type='text/csv')
    response.headers["Content-Disposition"] = "attachment; filename=import_accounts_template.csv"
    return response
    
@accounts.route('/check_email', methods=['GET'])
def check_email():
    email = request.args.get('email')
    exists = Account.query.filter_by(email=email).first() is not None
    return jsonify({"exists": exists}), 200
    