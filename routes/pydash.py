from flask import Blueprint, request, jsonify, json, redirect
from models import db,Conference,Role, UserProfile,Program,College, Account
from flask_jwt_extended import get_jwt_identity,jwt_required,get_jwt


pydash = Blueprint('dash',__name__)

@pydash.route('/sampledash', methods=['GET'])
@jwt_required()
def start_dash():
    try:
        user_id = get_jwt_identity()

        # Query the database for user profile
        query = UserProfile.query.filter(UserProfile.researcher_id == user_id).join(Account, user_id== Account.user_id).first()
        

        if not query:
            return jsonify({"error": "User profile not found"}), 404
        
        print(f"user_id: {user_id}, role_id: {query.role_id}, email: {query.email}")

        print(f"college_id: {query.college_id}, program_id: {query.program_id}")

        # Generate the full URL for the Dash app
        base_url = "http://localhost:5000"  # Adjust to your Dash app's URL
        
        # Dynamically create the query string with multiple parameters
        query_params = {
            "user-role": query.role_id,
            "college": query.college_id,
            "program": query.program_id,
        }

        # Ensure all query parameters are valid (non-null)
        query_string = '&'.join(f"{key}={value}" for key, value in query_params.items() if value is not None)

        if query.role_id =="02":
            dash_url=f"{base_url}/dashboard/overview/"
        else:
            dash_url = f"{base_url}/sample/?{query_string}"

        print(f"Generated Dash URL: {dash_url}")

        # Return the URL of the Dash app as JSON
        return jsonify({"url": dash_url}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500








