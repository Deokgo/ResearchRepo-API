from flask import Blueprint, jsonify
from models import Account, Researcher, db

accounts = Blueprint('account', __name__)

#created by Nicole Cabansag, for retrieving all users API
@accounts.route('/users', methods=['GET']) 
def get_all_users():
    try:
        # Join Account and Researcher table
        researchers = db.session.query(Researcher, Account).join(Account, Researcher.researcher_id == Account.user_id).order_by(Researcher.researcher_id.asc()).all()

        researchers_list = []
        for researcher,account in researchers:
            researchers_list.append({
                "researcher_id": researcher.researcher_id,
                "college_id": researcher.college_id,
                "program_id": researcher.program_id,
                "first_name": researcher.first_name,
                "middle_name": researcher.middle_name,
                "last_name": researcher.last_name,
                "suffix": researcher.suffix,
                "email": account.live_account  # Adding email from Account table
            })

        #return the list of researchers in JSON format
        return jsonify({"researchers": researchers_list}), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving all users: {str(e)}"}), 404

#created by Nicole Cabansag, for retrieving all user's acc and info by user_id API
@accounts.route('/users/<user_id>', methods=['GET']) 
def get_user_acc_by_id(user_id):
    try:
        user_acc = Account.query.filter_by(user_id=user_id).one()
        researcher_info = Researcher.query.filter_by(researcher_id=user_id).one()

        #construct the response in JSON format
        return jsonify({
            "account": {
                "user_id": user_acc.user_id,
                "live_account": user_acc.live_account,
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

