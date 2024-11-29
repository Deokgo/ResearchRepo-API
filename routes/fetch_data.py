from flask import Blueprint, request, jsonify, json
from models import db,Conference,Role, UserProfile,Program,College
from flask_jwt_extended import get_jwt_identity,jwt_required,get_jwt
#from services.logs import formatting_id,log_audit_trail
#from decorators.acc_decorators import roles_required
import os



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

@data.route('/colleges', methods =['GET','POST'])
@data.route('/colleges/<current_college>', methods =['GET','PUT','DELETE'])
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
            # Get user_id from form data 
            user_id = request.form.get('user_id')
            if not user_id:
                return jsonify({"error": "User must be logged in to add college"}), 401

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

            #log_audit_trail(user_id=current_user, table_name='College', record_id=None,
            #                          operation='ADDED COLLEGE', action_desc=f'Added {new_college.college_id}.')

            return jsonify({'message': 'College added successfully'}), 201
        except Exception as e:
            # If an error occurs, return a 400 error with the message
            return jsonify({'error': str(e)}), 400
    elif request.method == 'PUT':
        try:   
            if current_college is None:
                return jsonify({'error': 'College is required'}), 400

            data = request.form

            # Extracting values from the JSON data
            college_name = data.get('college_name')
            color_code = data.get('color_code')

            # Check if the data is valid
            if not college_name:
                return jsonify({'error': 'College Name is required'}), 400

            # Check if the college exists
            college = College.query.filter_by(college_id=current_college).first()
            if not college:
                return jsonify({'error': 'College not found'}), 404

            # Check if the new college name already exists (excluding the current college)
            existing_college = College.query.filter(College.college_name == college_name, College.college_id != current_college).first()
            if existing_college:
                return jsonify({'error': 'College with this name already exists'}), 400

            # Update the college name and color_code if given
            college.college_name = college_name
            
            if color_code:
                college.colo_code = color_code

            db.session.commit()
            #log_audit_trail(user_id=current_user, table_name='College', record_id=None,
            #                          operation='UPDATED COLLEGE', action_desc=f'Updated {college.college_id}.')

            return jsonify({'message': 'College updated successfully'}), 200

        except Exception as e:
            # If an error occurs, return a 400 error with the message
            return jsonify({'error': str(e)}), 400
        
    if request.method == 'DELETE':
        try:
            if current_college is None:
                return jsonify({'error': 'College is required'}), 400

            # Check if the college exists
            college = College.query.filter_by(college_id=current_college).first()
        
            if not college:
                return jsonify({'error': 'No matching college found'}), 404
            
             # Delete college from the database
            db.session.delete(college)
            db.session.commit()

            #log_audit_trail(user_id=current_user, table_name='College', record_id=None,
            #                          operation='DELETED COLLEGE', action_desc=f'deleted {colleges_to_delete}.')

            return jsonify({'message': f'{current_college} college deleted successfully'}), 200

        except Exception as e:
            # If an error occurs, return a 400 error with the message
            return jsonify({'error': str(e)}), 400
        
    
@data.route('/programs', methods =['GET','POST'])
@data.route('/programs/<current_program>', methods =['GET','PUT','DELETE'])
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
            # Get user_id from form data 
            user_id = request.form.get('user_id')
            if not user_id:
                return jsonify({"error": "User must be logged in to add college"}), 401

            data = request.form  # Get form data
            
            # Required fields list
            required_fields = [
                'college_id', 'program_id', 'program_name'
            ]
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

            # Check if the college exists
            existing_college = Program.query.filter(Program.college_id == data['college_id']).first()

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

            #log_audit_trail(user_id=current_user, table_name='Program', record_id=None,
            #                          operation='ADDED PROGRAM', action_desc=f'Added {new_program.program_id}.')

            return jsonify({'message': 'Program added successfully'}), 201

        except Exception as e:
            return jsonify({'error': str(e)}), 400

    elif request.method == 'PUT':
        try:   
            if current_program is None:
                return jsonify({'error': 'Program is required'}), 400

            data = request.form

            # Extracting values from the JSON data
            programe_name = data.get('program_name')

            # Check if the data is valid
            if not programe_name:
                return jsonify({'error': 'Program Name is required'}), 400

            # Check if the program exists
            program = Program.query.filter_by(program_id=current_program).first()
            if not program:
                return jsonify({'error': 'Program not found'}), 404

            # Check if the new program name already exists (excluding the current program)
            existing_program = Program.query.filter(Program.program_name == programe_name, Program.program_id != current_program).first()
            if existing_program:
                return jsonify({'error': 'Program with this name already exists'}), 400

            # Update the program name
            program.program_name = programe_name

            db.session.commit()
            #log_audit_trail(user_id=current_user, table_name='Program', record_id=None,
            #                          operation='UPDATED PROGRAM', action_desc=f'Updated {program.program_id}.')

            return jsonify({'message': 'Program updated successfully'}), 200

        except Exception as e:
            # If an error occurs, return a 400 error with the message
            return jsonify({'error': str(e)}), 400
        
    if request.method == 'DELETE':
        try:
            if current_program is None:
                return jsonify({'error': 'College is required'}), 400

            # Check if the program exists
            program = Program.query.filter_by(program_id=current_program).first()
        
            if not program:
                return jsonify({'error': 'No matching program found'}), 404
            
             # Delete program from the database
            db.session.delete(program)
            db.session.commit()

            #log_audit_trail(user_id=current_user, table_name='Program', record_id=None,
            #                          operation='DELETED PROGRAM', action_desc=f'deleted {program}.')

            return jsonify({'message': f'{current_program} program deleted successfully'}), 200

        except Exception as e:
            # If an error occurs, return a 400 error with the message
            return jsonify({'error': str(e)}), 400
