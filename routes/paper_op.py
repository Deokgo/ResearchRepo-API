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
    try:
        # Get the file and form data
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No file provided"}), 400

        data = request.form.to_dict()  # Get form data
        
        required_fields = ['research_id', 'college_id', 'program_id', 'title', 'abstract', 'date_approved', 'research_type', 'sdg']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        if is_duplicate(data['research_id']):
            return jsonify({"error": f"Group Code already exists"}), 400

        # First try to save the file
        dir_path = os.path.join(
            UPLOAD_FOLDER, 
            data['research_type'], 
            'manuscript', 
            str(datetime.strptime(data['date_approved'], '%Y-%m-%d').year),
            data['college_id'],
            data['program_id']
        )
        os.makedirs(dir_path, exist_ok=True)

        filename = secure_filename(f"{data['research_id']}_manuscript.pdf")
        file_path = os.path.normpath(os.path.join(dir_path, filename))
        file.save(file_path)
        
        # If file save succeeds, proceed with database operations
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
            full_manuscript=file_path,  # Save the file path
            adviser_id=data['adviser_id'],
            date_uploaded=current_datetime
        )
        db.session.add(new_paper)
        db.session.commit()

        # Handle multiple SDGs
        sdg_list = data['sdg'].split(';') if data['sdg'] else []
        for sdg_id in sdg_list:
            if sdg_id.strip():
                new_sdg = SDG(
                    research_id=data['research_id'],
                    sdg=sdg_id.strip()
                )
                db.session.add(new_sdg)

        # Handle panels if present
        panel_ids = request.form.getlist('panel_ids[]')  # Adjust based on how you're sending panel_ids
        if panel_ids:
            for panel_id in panel_ids:
                new_panel = Panel(
                    research_id=data['research_id'],
                    panel_id=panel_id
                )
                db.session.add(new_panel)

        # Handle keywords if present
        keywords_str = data.get('keywords')
        if keywords_str:
            keywords_list = keywords_str.split(';')
            for keyword in keywords_list:
                if keyword.strip():  # Only add non-empty keywords
                    new_keyword = Keywords(
                        research_id=data['research_id'],
                        keyword=keyword.strip()
                    )
                    db.session.add(new_keyword)

        db.session.commit()

        return jsonify({
            "message": "Research output and manuscript added successfully", 
            "research_id": new_paper.research_id
        }), 201
    
    except Exception as e:
        # If anything fails, rollback database changes and delete the file if it exists
        db.session.rollback()
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass  # If file deletion fails, continue with error response
        
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
        
    finally:
        db.session.close()


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

        # Send the file for viewing and downloading
        return send_file(file_path, as_attachment=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
def is_duplicate(group_code):
    # Check if any record with the given research_id (group_code) exists
    research_output = ResearchOutput.query.filter_by(research_id=group_code).first()
    
    # Return True if a record is found, False otherwise
    return research_output is not None

@paper.route('/increment_views/<research_id>', methods=['PUT'])
def increment_views(research_id):
    try:
        updated_views = 0
        # Get user_id from request body instead of session
        data = request.get_json()
        user_id = data.get('user_id', 'anonymous')
        
        # Fetch the record using SQLAlchemy query
        view_count = ResearchOutput.query.filter_by(research_id=research_id).first()
        if view_count:
            if view_count.view_count is None:
                updated_views = 1  # Start from 1 if None
            else:
                updated_views = int(view_count.view_count) + 1

            view_count.view_count = updated_views
            download_count = view_count.download_count or 0  # Default to 0 if None
            db.session.commit()

            # Log audit trail only if user_id is available
            if user_id != 'anonymous':
                try:
                    auth_services.log_audit_trail(
                        user_id=user_id,
                        table_name='Research_Output',
                        record_id=research_id,
                        operation='VIEW PAPER',
                        action_desc='Viewed research paper'
                    )
                except Exception as audit_error:
                    print(f"Audit trail logging failed: {audit_error}")
                    # Continue execution even if audit trail fails

            return jsonify({
                "message": "View count incremented", 
                "updated_views": updated_views,
                "download_count": download_count
            }), 200
        else:
            return jsonify({"message": "Record not found"}), 404
    
    except Exception as e:
        db.session.rollback()
        print(f"Error in increment_views: {str(e)}")  # Add detailed error logging
        return jsonify({"message": f"Failed to update view counts: {str(e)}"}), 500
    
    finally:
        db.session.close()


@paper.route('/increment_downloads/<research_id>', methods=['PUT'])
def increment_downloads(research_id):
    try:
        updated_downloads = 0
        # Get user_id from request body
        data = request.get_json()
        user_id = data.get('user_id', 'anonymous')
        
        # Fetch the record using SQLAlchemy query
        download_count = ResearchOutput.query.filter_by(research_id=research_id).first()
        if download_count:
            if download_count.download_count is None:
                updated_downloads = 1  # Start from 1 if None
            else:
                updated_downloads = int(download_count.download_count) + 1

            download_count.download_count = updated_downloads
            db.session.commit()

            # Log audit trail only if user_id is available
            if user_id != 'anonymous':
                try:
                    auth_services.log_audit_trail(
                        user_id=user_id,
                        table_name='Research_Output',
                        record_id=research_id,
                        operation='DOWNLOAD PAPER',
                        action_desc='Downloaded research paper'
                    )
                except Exception as audit_error:
                    print(f"Audit trail logging failed: {audit_error}")
                    # Continue execution even if audit trail fails

            return jsonify({
                "message": "Download count incremented", 
                "updated_downloads": updated_downloads
            }), 200
        else:
            return jsonify({"message": "Record not found"}), 404
    
    except Exception as e:
        db.session.rollback()
        print(f"Error in increment_downloads: {str(e)}")  # Add detailed error logging
        return jsonify({"message": f"Failed to update download counts: {str(e)}"}), 500
    
    finally:
        db.session.close()