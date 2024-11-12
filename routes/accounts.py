from flask import Blueprint, request, jsonify
from models import Account, UserProfile, Role, db
from services import auth_services
from werkzeug.security import generate_password_hash

accounts = Blueprint('account', __name__)

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
                "role": role.role_name  # Adding role from Role table
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

# created by Jelly Mallari for Updating Account API
@accounts.route('/update_account/<user_id>', methods=['PUT'])
def update_account(user_id):
    data = request.json

    try:
        # Retrieve the user's account and researcher information
        user_acc = Account.query.filter_by(user_id=user_id).first()
        researcher_info = UserProfile.query.filter_by(researcher_id=user_id).first()

        if not user_acc or not researcher_info:
            return jsonify({"message": "User not found"}), 404

        # Update account fields if provided in the request
        if data.get('password'):
            user_acc.user_pw = generate_password_hash(data['password'])
        if data.get('acc_status'):
            user_acc.acc_status = data['acc_status']

        # email and role_id cannot be updated
        if 'email' in data or 'role_id' in data:
            return jsonify({"message": "email and role_id cannot be updated."}), 400

        # Update researcher fields if provided in the request
        if data.get('college_id'):
            researcher_info.college_id = data['college_id']
        if data.get('program_id'):
            researcher_info.program_id = data['program_id']
        if data.get('first_name'):
            researcher_info.first_name = data['first_name']
        if data.get('middle_name'):
            researcher_info.middle_name = data.get('middle_name')  # Optional
        if data.get('last_name'):
            researcher_info.last_name = data['last_name']
        if data.get('suffix'):
            researcher_info.suffix = data.get('suffix')  # Optional

        # Commit changes to the database
        db.session.commit()

        # Log the update event in the Audit_Trail
        auth_services.log_audit_trail(user_id=user_acc.user_id, table_name='Account', record_id=None,
                                      operation='UPDATE', action_desc='Account information updated')

        # Return the updated account and researcher data
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
        db.session.rollback()  # Rollback in case of any error
        return jsonify({"message": f"Failed to update account: {e}"}), 500

    finally:
        db.session.close()  # Ensure the session is closed

@accounts.route('/search_user', methods=['GET'])
def search_advisers():
    query = request.args.get('query', '')
    if query:
        advisers = UserProfile.query.join(Account, UserProfile.researcher_id == Account.user_id)\
                    .filter((UserProfile.first_name.ilike(f'%{query}%')) | 
                            (UserProfile.last_name.ilike(f'%{query}%')) |
                            (Account.email.ilike(f'%{query}%')))\
                    .add_columns(UserProfile.researcher_id, UserProfile.first_name, UserProfile.last_name, Account.email)\
                    .all()

        result = [{"user_id": adviser.researcher_id, 
                   "first_name": first_name, 
                   "last_name": last_name, 
                   "email": email} for adviser, researcher_id, first_name, last_name, email in advisers]

        return jsonify({"advisers": result}), 200
    return jsonify({"advisers": []}), 200



