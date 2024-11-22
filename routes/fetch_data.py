from flask import Blueprint, request, jsonify, json
from models import db,Conference,Role, UserProfile,Program,College
from flask_jwt_extended import get_jwt_identity,jwt_required,get_jwt
#from services.logs import formatting_id,log_audit_trail
#from decorators.acc_decorators import roles_required



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

@data.route('/colleges', methods =['GET','POST','DELETE'])
@data.route('/colleges/<current_college>', methods =['GET','PUT'])
#@jwt_required()
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
            data = request.get_json()  # Assuming the request body contains a JSON payload

            # Extracting values from the JSON data
            college_id = data.get('college_id')
            college_name = data.get('college_name')

            # Check if data is valid
            if not college_id or not college_name:
                return jsonify({'error': 'College ID and Name are required'}), 400

            # Check if the college already exists
            existing_college = College.query.filter((College.college_id == college_id) | (College.college_name == college_name)).first()

            if existing_college:
                return jsonify({'error': 'College with this ID or Name already exists'}), 400

            # Create a new college instance
            new_college = College(college_id=college_id, college_name=college_name)

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

            data = request.get_json()  # Assuming the request body contains a JSON payload

            # Extracting values from the JSON data
            college_name = data.get('college_name')

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

            # Update the college name
            college.college_name = college_name
            db.session.commit()
            #log_audit_trail(user_id=current_user, table_name='College', record_id=None,
            #                          operation='UPDATED COLLEGE', action_desc=f'Updated {college.college_id}.')

            return jsonify({'message': 'College updated successfully'}), 200

        except Exception as e:
            # If an error occurs, return a 400 error with the message
            return jsonify({'error': str(e)}), 400
        
    if request.method == 'DELETE':
        try:
            data = request.get_json()  # Expecting a list of college IDs to delete

            # Validate that the input is a list
            print(data)
            if not isinstance(data, list):
                return jsonify({'error': 'Request body must be a list of college IDs'}), 400

            # Collect college IDs that exist in the database
            colleges_to_delete = College.query.filter(College.college_id.in_(data)).all()

            if not colleges_to_delete:
                return jsonify({'error': 'No matching colleges found'}), 404

            # Delete colleges from the database
            for college in colleges_to_delete:
                db.session.delete(college)

            db.session.commit()
            #log_audit_trail(user_id=current_user, table_name='College', record_id=None,
            #                          operation='DELETED COLLEGE', action_desc=f'deleted {colleges_to_delete}.')

            return jsonify({'message': f'{len(colleges_to_delete)} colleges deleted successfully'}), 200

        except Exception as e:
            # If an error occurs, return a 400 error with the message
            return jsonify({'error': str(e)}), 400
        
    
@data.route('/programs', methods =['GET','DELETE'])
@data.route('/programs/<college>', methods =['GET','POST'])
#@jwt_required()
def programs(college=None):
    #current_user = get_jwt_identity()
    if request.method == 'GET':
        try:
            query = db.session.query(College,Program).join(Program, Program.college_id==College.college_id).order_by(College.college_id,Program.program_id)

            if college:
                query = query.filter(College.college_id==college)
            
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
        # Handle POST request to create a new program
        print(college)
        if college is None:
            return jsonify({'error': 'Please specify the college'}), 401
        try:
            data = request.get_json()
            program_id = data.get('program_id')
            program_name = data.get('program_name')

            if not program_id or not program_name:
                return jsonify({'error': 'Missing college_id or program_name'}), 400
            
            program_exists = Program.query.filter(Program.program_id==program_id,Program.program_name==program_name).first() is not None

            if program_exists:
                return jsonify({'error': 'Program is already existing.'}), 401
            
            new_program = Program(program_id=program_id,college_id = college, program_name=program_name)
            db.session.add(new_program)
            db.session.commit()

            return jsonify({
                'message': 'Program created successfully',
            }), 201

        except Exception as e:
            return jsonify({'error': str(e)}), 400

    elif request.method == 'DELETE':
        # Handle DELETE request to remove multiple programs using program_id
        try:
            data = request.get_json()  # Expecting a list of program_ids in the body

            if not isinstance(data, list):
                return jsonify({'error': 'Missing program_ids or program_ids is not a list'}), 400

            # Fetch the programs to delete by program_id
            programs_to_delete = Program.query.filter(Program.program_id.in_(data)).all()

            if not programs_to_delete:
                return jsonify({'error': 'No programs found with the given program_ids'}), 404

            # Delete the programs
            for program in programs_to_delete:
                db.session.delete(program)
            db.session.commit()

            return jsonify({'message': f'{len(programs_to_delete)} program(s) deleted successfully'}), 200

        except Exception as e:
            return jsonify({'error': str(e)}), 400
