from flask import Blueprint, request, jsonify
from models import db, ResearchOutput, SDG, Keywords, Publication, ResearchOutputAuthor, Panel, UserProfile
from services import auth_services
import os
from werkzeug.utils import secure_filename

paper = Blueprint('paper', __name__)
UPLOAD_FOLDER = './research_repository'

@paper.route('/add_paper', methods=['POST'])
def add_paper():
    #extract data from the request JSON
    data = request.get_json()
    print("Request data:", data)
    
    #validate required fields (add adviser_id, keywords, panels, path for manus)
    required_fields = ['research_id', 'college_id', 'program_id', 'title', 'abstract', 'date_approved', 'research_type', 'sdg']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
    
    try:
        #create a new ResearchOutput record
        """
        add later:
        adviser_id=data['adviser_id']
        """

        if is_duplicate(data['research_id']):   #checking if the inputted research_id/group code is already existing
            return jsonify({"error": f"Group Code already exists"}), 400
        else:  
            new_paper = ResearchOutput(
                research_id=data['research_id'],
                college_id=data['college_id'],
                program_id=data['program_id'],
                title=data['title'],
                abstract=data['abstract'],
                date_approved=data['date_approved'],
                research_type=data['research_type']
            )

            """
            #assuming 'sdg' field may contain multiple sdg separated by ';'
            sdg_list = data['sdg'].split(';')

            #iterate over the split keywords and add each one individually
            for sdg in sdg_list:
                new_keyword = Keywords(
                    research_id=data['research_id'],
                    sdg=sdg.strip()  #remove any leading or trailing whitespace
                )
                db.session.add(new_keyword)

            """

            #create a new SDG record associated with the research_id (delete this after implementing the code above)
            new_paper_sdg = SDG(
                research_id=data['research_id'],
                sdg=data['sdg']
            )


            """
            #assuming 'keywords' field may contain multiple keywords separated by ';'
            keywords_list = data['keywords'].split(';')

            #iterate over the split keywords and add each one individually
            for keyword in keywords_list:
                new_keyword = Keywords(
                    research_id=data['research_id'],
                    keywords=keyword.strip()  #remove any leading or trailing whitespace
                )
                db.session.add(new_keyword)
            """

            """
            # for panels
            panels_list = data['panels'].split(';')
            for panel in panels_list:
                new_panels = Panel(
                    research_id=data['research_id'],
                    panels=panel.strip()
                )
                db.session.add(new_panels)
            """
            
            #add to session and commit
            db.session.add(new_paper)
            db.session.add(new_paper_sdg)
            db.session.commit()

            """
            # Audit Log
            auth_services.log_audit_trail(
                user_id=user.user_id, # should be able to fetch the current user that is logged in
                table_name='Research_Output',
                record_id=new_paper.research_id,
                operation='ADD NEW PAPER',
                action_desc='Added research paper'
            )
            """
            
            return jsonify({"message": "Research output added successfully", "research_id": new_paper.research_id}), 201
    
    except Exception as e:
        #rollback in case of error
        db.session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    
@paper.route('/upload_manuscript', methods=['POST'])
def upload_manuscript():
    try:
        file = request.files['file']
        research_type = request.form['research_type']
        year = request.form['year']
        department = request.form['department']
        program = request.form['program']
        group_code = request.form['group_code']

        # Create directory structure if it doesn't exist
        dir_path = os.path.join(
            UPLOAD_FOLDER, research_type, 'manuscript', year, department, program
        )
        os.makedirs(dir_path, exist_ok=True)

        # Save the file
        filename = secure_filename(group_code + '.pdf')
        file_path = os.path.join(dir_path, filename)
        file.save(file_path)

        return jsonify({"message": "File uploaded successfully."}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def is_duplicate(group_code):
    #check if any record with the given college_id (group_code) exists
    research_output = ResearchOutput.query.filter_by(college_id=group_code).first()
    
    #return True if a record is found, False otherwise
    return research_output is not None
