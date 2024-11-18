from flask import Blueprint, request, jsonify
from models import Account, UserProfile, Role, db
from services import auth_services
from werkzeug.security import generate_password_hash, check_password_hash
import re

accounts = Blueprint('accounts', __name__)

#created by Nicole Cabansag, for retrieving all users API
@accounts.route('/users', methods=['GET']) 
def get_all_users():
    try:
        # Join Account, Researcher, and Role tables
        researchers = db.session.query(UserProfile, Account, Role).join(Account, UserProfile.researcher_id == Account.user_id) \
            .join(Role, Account.role_id == Role.role_id).order_by(UserProfile.researcher_id.asc()).all()

        researchers_list = []
        for researcher, account, role in researchers:
            researchers_list.append({
                "researcher_id": researcher.researcher_id,
                "college_id": researcher.college_id,
                "program_id": researcher.program_id,
                "first_name": researcher.first_name,
                "middle_name": researcher.middle_name,
                "last_name": researcher.last_name,
                "suffix": researcher.suffix,
                "email": account.email,  # Adding email from Account table
                "acc_status": account.acc_status,
                "role_id": account.role_id,
                "role_name": role.role_name  # Adding role from Role table
            })

        # Return the list of researchers in JSON format
        return jsonify({"researchers": researchers_list}), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving all users: {str(e)}"}), 404

#created by Nicole Cabansag, for retrieving all user's acc and info by user_id API
@accounts.route('/users/<user_id>', methods=['GET']) 
def get_user_acc_by_id(user_id):
    try:
        user_acc = Account.query.filter_by(user_id=user_id).one()
        researcher_info = UserProfile.query.filter_by(researcher_id=user_id).one()

        #construct the response in JSON format
        return jsonify({
            "account": {
                "user_id": user_acc.user_id,
                "email": user_acc.email,
                "user_pw": user_acc.user_pw,
                "acc_status": user_acc.acc_status,
                "role": user_acc.role.role_name  
            },
            "researcher": {
                "researcher_id": researcher_info.researcher_id,
                "college_id": researcher_info.college_id,
                "program_id": researcher_info.program_id,
                "first_name": researcher_info.first_name,
                "middle_name": researcher_info.middle_name,
                "last_name": researcher_info.last_name,
                "suffix": researcher_info.suffix
            }
        }), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving user profile: {str(e)}"}), 404

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

        # Retrieve the user's account and researcher information
        user_acc = Account.query.filter_by(user_id=user_id).first()
        researcher_info = UserProfile.query.filter_by(researcher_id=user_id).first()

        if not user_acc or not researcher_info:
            return jsonify({"message": "User not found"}), 404

        # Validate required fields
        required_fields = ['college_id', 'program_id', 'first_name', 'last_name']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return jsonify({
                "message": "College department, program, first name, and last name are required.",
                "missing_fields": missing_fields
            }), 400

        # Update researcher fields if provided in the request
        if data.get('college_id'):
            researcher_info.college_id = data['college_id']
        if data.get('program_id'):
            researcher_info.program_id = data['program_id']
        if data.get('first_name'):
            researcher_info.first_name = data['first_name']

        if 'middle_name' in data and (data['middle_name'] is None or data['middle_name'].strip() == ''):
            researcher_info.middle_name = None  # Set to null if empty or null
        elif data.get('middle_name'):
            researcher_info.middle_name = data['middle_name']

        if 'suffix' in data and (data['suffix'] is None or data['suffix'].strip() == ''):
            researcher_info.suffix = None  # Set to null if empty or null
        elif data.get('suffix'):
            researcher_info.suffix = data['suffix']
            
        if data.get('last_name'):
            researcher_info.last_name = data['last_name']

        # Commit changes to the database
        db.session.commit()

        # Log the update event in the Audit_Trail
        auth_services.log_audit_trail(user_id=user_acc.user_id, table_name='Account', record_id=user_acc.user_id,
                                      operation='UPDATE', action_desc='Account information updated')

        # Return the updated account and researcher data
        return jsonify({
            "researcher": {
                "researcher_id": researcher_info.researcher_id,
                "college_id": researcher_info.college_id,
                "program_id": researcher_info.program_id,
                "first_name": researcher_info.first_name,
                "middle_name": researcher_info.middle_name,
                "last_name": researcher_info.last_name,
                "suffix": researcher_info.suffix
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