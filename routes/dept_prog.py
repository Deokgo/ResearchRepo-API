#created by Nicole Cabansag (Oct. 4, 2024)

from flask import Blueprint, jsonify, request
from models import College, Program

deptprogs = Blueprint('deptprogs', __name__)

@deptprogs.route('/college_depts', methods=['GET'])
def get_all_college_depts():
    try:
        #retrieve all colleges from the database
        depts = College.query.order_by(College.college_id.asc()).all()
        dept_list = [{
            "college_id": dept.college_id,
            "college_name": dept.college_name
        } for dept in depts]

        #return the list of colleges
        return jsonify({"colleges": dept_list}), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving all college departments: {str(e)}"}), 404

#route to get all programs by college_id
@deptprogs.route('/programs', methods=['GET']) 
def get_programs_by_college():
    try:
        #get the department from the request query parameters
        department = request.args.get('department')

        if not department:
            return jsonify({"message": "department parameter is required"}), 400

        #retrieve programs by the provided college_id
        progs = Program.query.filter_by(college_id=department).all()

        if not progs:
            return jsonify({"message": "No programs found for this college_id"}), 404

        #prepare a list of programs
        prog_list = [{
            "program_id": prog.program_id,
            "college_id": prog.college_id,
            "program_name": prog.program_name
        } for prog in progs]

        #return the list of programs
        return jsonify({"programs": prog_list}), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving all programs: {str(e)}"}), 500

@deptprogs.route('/fetch_programs', methods=['GET'])
def get_all_programs():
    try:
        #retrieve all programs from the database
        progs = Program.query.order_by(Program.program_id.asc()).all()
        prog_list = [{
            "program_id": prog.program_id,
            "program_name": prog.program_name
        } for prog in progs]

        #return the list of programs
        return jsonify({"programs": prog_list}), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving all college departments: {str(e)}"}), 404