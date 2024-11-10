# created by Nicole Cabansag (Nov. 10, 2024)

from flask import Blueprint, jsonify, request
from models import UserProfile, Account
from sqlalchemy.orm import joinedload

adviserpanels = Blueprint('adviserpanels', __name__)

@adviserpanels.route('/get_adviserpanels', methods=['GET'])
@adviserpanels.route('/get_adviserpanels/<college>', methods=['GET'])
def get_adviserpanels(college=None):
    try:
        # Base query joining UserProfile and Account with role filter
        query = UserProfile.query.join(Account, Account.user_id == UserProfile.researcher_id).filter(
            Account.role_id.in_(['04', '05', '06'])
        )

        # Apply college filter if a college ID is provided
        if college:
            query = query.filter(UserProfile.college_id == college)

        # Execute the query and fetch the results
        advisers = query.all()

        if not advisers:
            if college:
                return jsonify({"message": f"No advisers found for the college: {college}"}), 404
            else:
                return jsonify({"message": "No advisers found"}), 404

        # Prepare a list of advisers
        advisers_list = [{
            "adviser_id": adv.researcher_id,
            "adviser_name": f'{adv.first_name} {adv.last_name}'
        } for adv in advisers]

        # Return the list of advisers
        return jsonify({"advisers": advisers_list}), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving advisers: {str(e)}"}), 500