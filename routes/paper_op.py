from flask import Blueprint, request, jsonify, send_file, session
from models import db, ResearchOutput, SDG, Keywords, Publication, ResearchOutputAuthor, Panel, UserProfile
from services import auth_services
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import pytz
import traceback

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
            philippine_tz = pytz.timezone('Asia/Manila')
            current_datetime = datetime.now(philippine_tz).replace(tzinfo=None)
            new_paper = ResearchOutput(
                research_id=data['research_id'],
                college_id=data['college_id'],
                program_id=data['program_id'],
                title=data['title'],
                abstract=data['abstract'],
                date_approved=data['date_approved'],
                research_type=data['research_type'],
                full_manuscript=data.get('full_manuscript', None),
                adviser_id=data['adviser_id'],
                date_uploaded=current_datetime
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

            if 'panel_ids' in data:
                for panel_id in data['panel_ids']:
                    new_panel = Panel(
                        research_id=data['research_id'],
                        panel_id=panel_id
                    )
                    db.session.add(new_panel)
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
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    
@paper.route('/upload_manuscript', methods=['POST'])
def upload_manuscript():
    try:
        # Get file and form data
        file = request.files['file']
        research_type = request.form['research_type']
        year = request.form['year']
        department = request.form['department']
        program = request.form['program']
        research_id = request.form['group_code']

        # Create directory structure if it doesn't exist
        dir_path = os.path.join(
            UPLOAD_FOLDER, research_type, 'manuscript', year, department, program
        )
        os.makedirs(dir_path, exist_ok=True)

        # Save the file
        filename = secure_filename(f"{research_id}_manuscript.pdf")
        file_path = os.path.join(dir_path, filename)
        file_path = os.path.normpath(file_path)
        file.save(file_path)

        # Update handle of research output
        print(f"Group Code for Manuscript Upload: {research_id}")
        research_output = ResearchOutput.query.filter_by(research_id=research_id).first()

        if research_output:
            research_output.full_manuscript = file_path
            db.session.commit()
            print(f"Updated Manuscript Path in Database: {file_path}")
        else:
            return jsonify({"error": "Research output not found for the given group code."}), 404

        return jsonify({"message": "File uploaded successfully."}), 201

    except Exception as e:
        # Log the error
        print(f"Error during manuscript upload: {e}")
        return jsonify({"error": str(e)}), 500


@paper.route('/view_manuscript/<research_id>', methods=['GET'])
def view_manuscript(research_id):
    try:
        # Query the database for the full_manuscript handle using the research_id
        research_output = ResearchOutput.query.filter_by(research_id=research_id).first()

        # Check if research_output exists and if the handle for the manuscript is available
        if not research_output or not research_output.full_manuscript:
            return jsonify({"error": "Manuscript not found."}), 404

        file_path = os.path.normpath(research_output.full_manuscript)

        # Check if the file exists
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found."}), 404
        
        increment_downloads(research_id) # increment download_count

        # Send the file for viewing and downloading
        return send_file(file_path, as_attachment=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def is_duplicate(group_code):
    #check if any record with the given college_id (group_code) exists
    research_output = ResearchOutput.query.filter_by(college_id=group_code).first()
    
    #return True if a record is found, False otherwise
    return research_output is not None

@paper.route('/increment_views/<research_id>', methods=['PUT'])
def increment_views(research_id):
    try:
        updated_views = 0
        #fetch the record using SQLAlchemy query
        view_count = ResearchOutput.query.filter_by(research_id=research_id).first()
        if view_count:
            if view_count.view_count is None:
                updated_views = 0
            else:
                updated_views = int(view_count.view_count) + 1

            view_count.view_count = updated_views
            download_count = view_count.download_count
            db.session.commit()

            auth_services.log_audit_trail(
                user_id=str(session['user_id']), # should be able to fetch the current user that is logged in
                table_name='Research_Output',
                record_id=research_id,
                operation='VIEW PAPER',
                action_desc='Viewed research paper'
            )

            return jsonify({"message": "View count incremented", 
                            "updated_views": updated_views,
                            "download_count": download_count}), 200
        else:
            return jsonify({"message": "Record not found"}), 404
    
    except Exception as e:
        db.session.rollback()  #rollback in case of any error
        return jsonify({"message": f"Failed to update view counts: {e}"}), 500
    
    finally:
        db.session.close()  #ensure the session is closed


#@paper.route('/increment_downloads/<research_id>', methods=['PUT'])
def increment_downloads(research_id):
    try:
        updated_downloads = 0
        #fetch the record using SQLAlchemy query
        download_count = ResearchOutput.query.filter_by(research_id=research_id).first()
        if download_count:
            if download_count.download_count is None:
                updated_downloads = 0
            else:
                updated_downloads = int(download_count.download_count) + 1

            download_count.download_count = updated_downloads
            db.session.commit()

            auth_services.log_audit_trail(
                user_id=str(session['user_id']), # should be able to fetch the current user that is logged in
                table_name='Research_Output',
                record_id=research_id,
                operation='DOWNLOAD PAPER',
                action_desc='Downloaded research paper'
            )
            return jsonify({"message": "Download count incremented", "updated_downloads": updated_downloads}), 200
        else:
            return jsonify({"message": "Record not found"}), 404
    
    except Exception as e:
        db.session.rollback()  #rollback in case of any error
        return jsonify({"message": f"Failed to update download counts: {e}"}), 500
    
    finally:
        db.session.close()  #ensure the session is closed