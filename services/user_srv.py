import datetime
import jwt
from flask import Blueprint, request, jsonify, current_app
from models import db, UserProfile, Account
from werkzeug.security import generate_password_hash, check_password_hash



def add_new_user(user_id,data, assigned='04'):
    """Add a new user to the database."""
    
    try:
        # Insert data into the Account table
        new_account = Account(
            user_id=user_id,  # assuming email is used as the user_id
            live_account=data['email'],  # Mapúa MCL live account
            user_pw=generate_password_hash(data['password']),
            acc_status='ACTIVATED',  # assuming account is activated by default
            role_id=assigned,  
        )
        db.session.add(new_account)

        # Insert data into the Researcher table
        new_researcher = UserProfile(
            researcher_id=new_account.user_id,  # use the user_id from Account
            college_id=data['department'],  # department corresponds to college_id
            program_id=data['program'],  # program corresponds to program_id
            first_name=data['firstName'],
            middle_name=data.get('middleName'),  # allowing optional fields
            last_name=data['lastName'],
            suffix=data.get('suffix')  # allowing optional suffix
        )
        db.session.add(new_researcher)

        # Commit both operations
        db.session.commit()

        # Return success response with the user ID (without token)
        return jsonify({
            "message": f"User {new_account.user_id} successfully added!",
            "user_id":user_id
        }), 201

    except Exception as e:
        db.session.rollback()  # rollback in case of error
        return jsonify({"message": f"Failed to add user: {e}"}), 500

    finally:
        db.session.close()  # close the session