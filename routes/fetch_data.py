from flask import Blueprint, request, jsonify, json
from models import db,Conference,Role, UserProfile,Program,College,Account
from services import auth_services
from flask_jwt_extended import get_jwt_identity,jwt_required,get_jwt
#from services.logs import formatting_id,log_audit_trail
#from decorators.acc_decorators import roles_required
import os
from flask import session

data = Blueprint('data',__name__)

def convert(records,model):
    try:
        # Convert the result to a list of dictionaries
        records_list = []
        for record in records:
            # Dynamically generate a dictionary for each record
            record_data = {column.name: getattr(record, column.name) for column in model.__table__.columns}
            records_list.append(record_data)

        return records_list
    except Exception as e:
        # Handle any errors
        return str(e)

@data.route('/conferences', methods =['GET'])
def conferences(conference_id=None):
    try:
        if request.method == 'GET':
            # Use the generic function to get all conference records
            conference_list = Conference.query.distinct(Conference.conference_title).order_by(Conference.conference_title.asc()).all()

            conference_list = convert(conference_list,Conference)
            
            # Return the conference data as a JSON response
            return jsonify({"conferences": conference_list}), 200

    except Exception as e:
        # If an error occurs, return a 400 error with the message
        return jsonify({'error': str(e)}), 400
    
@data.route('/conference_details/<cf_id>', methods =['GET'])
@jwt_required()
def conference_details(cf_id=None):
    try:
        if request.method == 'GET':
            conference_details = Conference.query.filter(Conference.conference_id==cf_id).first()

            conference_details = convert(conference_details, Conference)

            # Return the conference data as a JSON response
            return jsonify({"conference_details": conference_details}), 200

    except Exception as e:
        # If an error occurs, return a 400 error with the message
        return jsonify({'error': str(e)}), 400
    
@data.route('/roles', methods =['GET'])
@jwt_required()
def user_roles():
    try:
        if request.method == 'GET':
            # Use the generic function to get all conference records
            roles = Role.query.all()

            roles = convert(roles,Role)
            
            # Return the conference data as a JSON response
            return jsonify(roles), 200

    except Exception as e:
        # If an error occurs, return a 400 error with the message
        return jsonify({'error': str(e)}), 400

@data.route('/college', methods=['GET'])
@jwt_required()
def college():
    try:
        # Example researcher ID for testing
        researcher_id = get_jwt_identity()

        # Query the database
        college = (
            db.session.query(UserProfile.college_id)
            .filter(UserProfile.researcher_id == researcher_id)
            .first()
        )

        if college:
            # Serialize the result
            session['college_id'] = college.college_id
            return jsonify({'college_id': college.college_id}), 200
        else:
            return jsonify({'error': 'College not found for the given researcher ID'}), 404

    except Exception as e:
        # Return an error response
        return jsonify({'error': str(e)}), 400
    
@data.route('/colleges', methods =['GET','POST'])
@data.route('/colleges/<current_college>', methods =['GET'])
@jwt_required()
def colleges(current_college=None):
    #current_user = get_jwt_identity()
    if request.method == 'GET':
        try:
            # Use the generic function to get all conference records
            query = db.session.query(College)

            if current_college:
                query = query.filter(College.college_id==current_college)

            colleges = query.all()
            colleges = convert(colleges,College)
            
            # Return the conference data as a JSON response
            return jsonify(colleges), 200

        except Exception as e:
            # If an error occurs, return a 400 error with the message
            return jsonify({'error': str(e)}), 400
    elif request.method == 'POST':
        try:
            # Get the current user for audit trail
            current_user = Account.query.get(get_jwt_identity())
            if not current_user:
                return jsonify({"error": "Current user not found"}), 404

            data = request.form  # Get form data
            
            # Required fields list
            required_fields = [
                'college_id', 'college_name'
            ]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

            # Check if the college already exists
            existing_college = College.query.filter((College.college_id == data['college_id']) | (College.college_name == data['college_name'])).first()

            if existing_college:
                return jsonify({'error': 'College with this ID or Name already exists'}), 400               

            # Create a new college instance       
            new_college = College(
                college_id=data['college_id'],
                college_name=data['college_name'],
                color_code=data.get('college_color')
            )

            # Add to the session and commit to the database
            db.session.add(new_college)
            db.session.commit()

            # Log audit trail
            auth_services.log_audit_trail(
                email=current_user.email,
                role=current_user.role.role_name,
                table_name='College',
                record_id=data['college_id'],
                operation='CREATE',
                action_desc='Added college department'
            )

            return jsonify({'message': 'College added successfully'}), 201
        except Exception as e:
            # If an error occurs, return a 400 error with the message
            return jsonify({'error': str(e)}), 400
        
    
@data.route('/programs', methods =['GET','POST'])
@data.route('/programs/<current_program>', methods =['GET'])
@jwt_required()
def programs(current_program=None):
    #current_user = get_jwt_identity()
    if request.method == 'GET':
        try:
            query = db.session.query(College,Program).join(Program, Program.college_id==College.college_id).order_by(College.college_id,Program.program_id)

            if current_program:
                query = query.filter(Program.program_id==current_program)
            
            query = query.all()

            programs_data = []
            for colleges, programs in query:
                pg_data={
                    'college_id':colleges.college_id,
                    'college_name': colleges.college_name,
                    'program_id':programs.program_id,
                    'program_name':programs.program_name
                }
                programs_data.append(pg_data)
                
            return jsonify(programs_data), 200

        except Exception as e:
            # If an error occurs, return a 400 error with the message
            return jsonify({'error': str(e)}), 400
    elif request.method == 'POST':
        try:
            # Get the current user for audit trail
            current_user = Account.query.get(get_jwt_identity())
            if not current_user:
                return jsonify({"error": "Current user not found"}), 404

            data = request.form  # Get form data
            
            # Required fields list
            required_fields = [
                'college_id', 'program_id', 'program_name'
            ]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

            # Check if the college exists
            existing_college = College.query.filter(College.college_id == data['college_id']).first()

            if not existing_college:
                return jsonify({'error': 'College should be existing, please try again!'}), 400  

            # Check if the program exists
            existing_program = Program.query.filter((Program.program_id == data['program_id']) | (Program.program_name == data['program_name'])).first()

            if existing_program:
                return jsonify({'error': 'Program with this ID or Name already exists'}), 400             

            # Create a new college instance       
            new_program = Program(
                program_id=data['program_id'],
                college_id=data['college_id'],
                program_name=data['program_name'],
            )

            # Add to the session and commit to the database
            db.session.add(new_program)
            db.session.commit()

            # Log audit trail
            auth_services.log_audit_trail(
                email=current_user.email,
                role=current_user.role.role_name,
                table_name='Program',
                record_id=data['program_id'],
                operation='CREATE',
                action_desc='Added program'
            )

            return jsonify({'message': 'Program added successfully'}), 201

        except Exception as e:
            return jsonify({'error': str(e)}), 400
