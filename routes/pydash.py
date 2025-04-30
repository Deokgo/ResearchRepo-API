from flask import Blueprint, request, jsonify, redirect, session
from models import db, Conference, Role, UserProfile, Program, College, Account
from flask_jwt_extended import get_jwt_identity, jwt_required

pydash = Blueprint('dash', __name__)

@pydash.route('/sampledash', methods=['GET'])
@jwt_required()
def start_dash():
    try:
        user_id = get_jwt_identity()

        # Query the database for user profile
        account_info = db.session.query(Account).filter(Account.user_id == user_id).first()
        user_prof = db.session.query(UserProfile).filter(UserProfile.researcher_id == user_id).first()

        if not account_info:
            return jsonify({"error": "Account information not found"}), 404
        
        if not user_prof:
            return jsonify({"error": "User profile not found"}), 404

        print(f"user_id: {user_id}, role_id: {account_info.role_id}, email: {account_info.email}")
        print(f"college_id: {user_prof.college_id}, program_id: {user_prof.program_id}")

        # Generate the full URL for the Dash app
        base_url = "http://localhost:5000"  # Adjust to your Dash app's URL
        
        # Dynamically create the query string with multiple parameters
        query_params = {
            "user-role": account_info.role_id,
            "college": user_prof.college_id,
            "program": user_prof.program_id,
        }

        # Ensure all query parameters are valid (non-null)
        query_string = '&'.join(f"{key}={value}" for key, value in query_params.items() if value is not None)

        if account_info.role_id == "02":
            dash_url = f"{base_url}/dashboard/overview/"
        elif account_info.role_id == "04":
            dash_url = f"{base_url}/sample/?{query_string}"
        elif account_info.role_id == "05":
            #dash_url = f"{base_url}/sample/?{query_string}"
            dash_url = f"{base_url}/progchairdash/?{query_string}"

        print(f"Generated Dash URL: {dash_url}")

        # Return the URL of the Dash app as JSON
        return jsonify({"url": dash_url}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pydash.route('/analytics', methods=['GET'])
@jwt_required()
def analytics_dash():
    try:
        user_id = get_jwt_identity()

        # Query the database for user profile
        account_info = db.session.query(Account).filter(Account.user_id == user_id).first()
        user_prof = db.session.query(UserProfile).filter(UserProfile.researcher_id == user_id).first()

        if not account_info:
            return jsonify({"error": "Account information not found"}), 404
        
        if not user_prof:
            return jsonify({"error": "User profile not found"}), 404

        print(f"user_id: {user_id}, role_id: {account_info.role_id}, email: {account_info.email}")
        print(f"college_id: {user_prof.college_id}, program_id: {user_prof.program_id}")

        # Generate the full URL for the Dash app
        base_url = "http://localhost:5000"  # Adjust to your Dash app's URL
        
        # Dynamically create the query string with multiple parameters
        query_params = {
            "user-role": account_info.role_id,
            "college": user_prof.college_id,
            "program": user_prof.program_id,
        }

        # Ensure all query parameters are valid (non-null)
        query_string = '&'.join(f"{key}={value}" for key, value in query_params.items() if value is not None)

        if account_info.role_id == "02":
            dash_url = f"{base_url}/sdg/map/"
        elif account_info.role_id == "04":
            dash_url = f"{base_url}/sdg/map/college/?{query_string}"

        print(f"Generated Dash URL: {dash_url}")

        # Return the URL of the Dash app as JSON
        return jsonify({"url": dash_url}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@pydash.route('/engagement', methods=['GET'])
@jwt_required()
def engage_dash():
    try:
        user_id = get_jwt_identity()

        # Query the database for user profile
        account_info = db.session.query(Account).filter(Account.user_id == user_id).first()
        user_prof = db.session.query(UserProfile).filter(UserProfile.researcher_id == user_id).first()

        if not account_info:
            return jsonify({"error": "Account information not found"}), 404
        
        if not user_prof:
            return jsonify({"error": "User profile not found"}), 404

        print(f"user_id: {user_id}, role_id: {account_info.role_id}, email: {account_info.email}")
        print(f"college_id: {user_prof.college_id}, program_id: {user_prof.program_id}")

        # Generate the full URL for the Dash app
        base_url = "http://localhost:5000"  # Adjust to your Dash app's URL
        
        # Dynamically create the query string with multiple parameters
        query_params = {
            "user-role": account_info.role_id,
            "college": user_prof.college_id,

        }

        # Ensure all query parameters are valid (non-null)
        query_string = '&'.join(f"{key}={value}" for key, value in query_params.items() if value is not None)

        if account_info.role_id == "02":
            dash_url = f"{base_url}/engage/?user-role=02"
        elif account_info.role_id == "04":
            dash_url = f"{base_url}/engage/?{query_string}"


        print(f"Generated Dash URL: {dash_url}")

        # Return the URL of the Dash app as JSON
        return jsonify({"url": dash_url}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@pydash.route('/combineddash', methods=['GET'])
@jwt_required()
def combined_dash():
    try:
        user_id = get_jwt_identity()

        account_info = db.session.query(Account).filter(Account.user_id == user_id).first()
        user_prof = db.session.query(UserProfile).filter(UserProfile.researcher_id == user_id).first()

        if not account_info:
            return jsonify({"error": "Account information not found"}), 404
        
        if not user_prof:
            return jsonify({"error": "User profile not found"}), 404

        print(f"user_id: {user_id}, role_id: {account_info.role_id}, email: {account_info.email}")
        print(f"college_id: {user_prof.college_id}, program_id: {user_prof.program_id}")

        base_url = "http://localhost:5000" 

        query_params = {
            "user-role": account_info.role_id,
            "college": user_prof.college_id,
            "program": user_prof.program_id,
        }
        query_string = '&'.join(f"{key}={value}" for key, value in query_params.items() if value is not None)

        if account_info.role_id == "02":
            sample_url = f"{base_url}/institutional-performance/?user-role=02"
            analytics_url = f"{base_url}/sdg-impact/?user-role=02"
            engage_url = f"{base_url}/engage/?user-role=02"
            return jsonify({
                "overview": sample_url,
                "sdg": analytics_url,
                "engagement": engage_url,
            }), 200
        elif account_info.role_id == "03":
            sample_url = f"{base_url}/institutional-performance/?user-role=03"
            analytics_url = f"{base_url}/sdg-impact/?user-role=03"
            engage_url = f"{base_url}/engage/?user-role=03"
            return jsonify({
                "overview": sample_url,
                "sdg": analytics_url,
                "engagement": engage_url,
            }), 200
        elif account_info.role_id == "04":
            sample_url = f"{base_url}/institutional-performance/college/?{query_string}"
            analytics_url = f"{base_url}/sdg-impact/college/?{query_string}"
            engage_url = f"{base_url}/engage/?{query_string}"
            return jsonify({
                "overview": sample_url,
                "sdg": analytics_url,
                "engagement": engage_url,
            }), 200

        else:
            if account_info.role_id == "05":
                sample_url = f"{base_url}/institutional-performance/?{query_string}"
            return jsonify({
                "overview": sample_url
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500