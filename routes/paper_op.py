from flask import Blueprint, request, jsonify, send_file, session
from models import db, ResearchOutput, SDG, Keywords, Publication, ResearchOutputAuthor, Panel, UserProfile, Account
from services import auth_services
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import pytz
import traceback
from flask_jwt_extended import jwt_required, get_jwt_identity

paper = Blueprint('paper', __name__)
UPLOAD_FOLDER = './research_repository'


@paper.route('/add_paper', methods=['POST'])
@jwt_required()
def add_paper():
    try:
        # Get the current user's identity
        user_id = get_jwt_identity()

        data = request.form  # Get form data
        
        # Required Fields
        required_fields = [
            'research_id', 'college_id', 'program_id', 'title', 
            'abstract', 'date_approved', 'research_type', 
            'adviser_id', 'sdg', 'keywords', 'author_ids', 'panel_ids'
        ]

        # Validate non-file fields
        missing_fields = [field for field in required_fields if field not in data or not data[field].strip()]

       # Validate the manuscript (required)
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "Manuscript file is required."}), 400

        if file.content_type != 'application/pdf':
            return jsonify({"error": "Invalid manuscript file type. Only PDF files are allowed."}), 400

        # Validate the extended abstract (optional)
        file_ea = request.files.get('extended_abstract')
        if file_ea and file_ea.content_type != 'application/pdf':
            return jsonify({"error": "Invalid extended abstract file type. Only PDF files are allowed."}), 400

        print("Received file:", request.files.get("file"))
        print("Received extended abstract:", request.files.get("extended_abstract"))
        
        # Check if authors array is empty
        if 'author_ids' in data and not request.form.getlist('author_ids'):
            missing_fields.append('author_ids')
            
        # Check if panels array is empty
        if 'panel_ids' in data and not request.form.getlist('panel_ids'):
            missing_fields.append('panel_ids')
            
        # Check if keywords is empty
        if 'keywords' in data and not data['keywords'].strip():
            missing_fields.append('keywords')

        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        if is_duplicate(data['research_id']):
            return jsonify({"error": "Group Code already exists"}), 400

        # Save the manuscript
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

        # Save the extended abstract (if provided)
        file_path_ea = None  # Default to None if no extended abstract is provided
        if file_ea:
            dir_path_ea = os.path.join(
                UPLOAD_FOLDER, 
                data['research_type'], 
                'extended_abstract', 
                str(datetime.now().year),  # Use the current year
                data['college_id'],
                data['program_id']
            )
            os.makedirs(dir_path_ea, exist_ok=True)

            filename_ea = secure_filename(f"{data['research_id']}_extended_abstract.pdf")
            file_path_ea = os.path.normpath(os.path.join(dir_path_ea, filename_ea))
            file_ea.save(file_path_ea)
        
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
            full_manuscript=file_path,  # Save the manuscript file path
            extended_abstract=file_path_ea,  # This could be None
            adviser_id=data['adviser_id'],
            user_id=user_id,
            date_uploaded=current_datetime,
            view_count=0,
            download_count=0
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

        # Handle panels
        panel_ids = request.form.getlist('panel_ids')
        if panel_ids:
            for panel_id in panel_ids:
                new_panel = Panel(
                    research_id=data['research_id'],
                    panel_id=panel_id
                )
                db.session.add(new_panel)

        # Handle keywords 
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

        # Handle authors 
        author_ids = request.form.getlist('author_ids')

        if author_ids:
            try:
                # Query author information including last names
                author_info = db.session.query(
                    Account.user_id,
                    UserProfile.last_name
                ).join(
                    UserProfile,
                    Account.user_id == UserProfile.researcher_id
                ).filter(
                    Account.user_id.in_(author_ids)
                ).all()

                # Create a dictionary of author_id to last_name for sorting
                author_dict = {str(author.user_id): author.last_name for author in author_info}
                
                # Sort author_ids based on last names
                sorted_author_ids = sorted(author_ids, key=lambda x: author_dict[x].lower())

                # Add authors with order based on sorted last names
                for index, author_id in enumerate(sorted_author_ids, start=1):
                    new_author = ResearchOutputAuthor(
                        research_id=data['research_id'],
                        author_id=author_id,
                        author_order=index  # Order based on sorted last names
                    )
                    db.session.add(new_author)

            except Exception as e:
                print(f"Error sorting authors: {str(e)}")
                raise e

        db.session.commit()

        # Log audit trail
        auth_services.log_audit_trail(
            user_id=user_id,
            table_name='Research_Output',
            record_id=new_paper.research_id,
            operation='CREATE',
            action_desc='Added research paper'
        )

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


@paper.route('/update_paper/<research_id>', methods=['PUT'])
@jwt_required()
def update_paper(research_id):
    try:
        # Get the current user's identity
        user_id = get_jwt_identity()

        # Check if paper exists
        existing_paper = ResearchOutput.query.filter_by(research_id=research_id).first()
        if not existing_paper:
            return jsonify({"error": "Research paper not found"}), 404

        # Get the files and form data
        file = request.files.get('file')
        file_ea = request.files.get('extended_abstract')
        data = request.form

        # Update required fields list
        required_fields = [
            'college_id', 'program_id', 'title', 
            'abstract', 'date_approved', 'research_type', 
            'adviser_id', 'sdg', 'keywords', 'author_ids', 'panel_ids'
        ]
        missing_fields = [field for field in required_fields if field not in data]

        # Check if authors array is empty
        if 'author_ids' in data and not request.form.getlist('author_ids'):
            missing_fields.append('author_ids')
            
        # Check if panels array is empty
        if 'panel_ids' in data and not request.form.getlist('panel_ids'):
            missing_fields.append('panel_ids')
            
        # Check if keywords is empty
        if 'keywords' in data and not data['keywords'].strip():
            missing_fields.append('keywords')

        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Handle full manuscript update if new file is provided
        if file:
            # Create directory structure
            dir_path = os.path.join(
                UPLOAD_FOLDER, 
                data['research_type'], 
                'manuscript', 
                str(datetime.strptime(data['date_approved'], '%Y-%m-%d').year),
                data['college_id'],
                data['program_id']
            )
            os.makedirs(dir_path, exist_ok=True)

            # Delete old file if it exists
            if existing_paper.full_manuscript and os.path.exists(existing_paper.full_manuscript):
                os.remove(existing_paper.full_manuscript)

            # Save new file
            filename = secure_filename(f"{research_id}_manuscript.pdf")
            file_path = os.path.normpath(os.path.join(dir_path, filename))
            file.save(file_path)
            existing_paper.full_manuscript = file_path

        # Handle extended abstract update if new file is provided
        if file_ea:
            # Create directory structure for extended abstract
            dir_path_ea = os.path.join(
                UPLOAD_FOLDER, 
                data['research_type'], 
                'extended_abstract', 
                str(datetime.strptime(data['date_approved'], '%Y-%m-%d').year),
                data['college_id'],
                data['program_id']
            )
            os.makedirs(dir_path_ea, exist_ok=True)

            # Delete old extended abstract if it exists
            if existing_paper.extended_abstract and os.path.exists(existing_paper.extended_abstract):
                os.remove(existing_paper.extended_abstract)

            # Save new extended abstract
            filename_ea = secure_filename(f"{research_id}_extended_abstract.pdf")
            file_path_ea = os.path.normpath(os.path.join(dir_path_ea, filename_ea))
            file_ea.save(file_path_ea)
            existing_paper.extended_abstract = file_path_ea

        # Update basic paper information
        existing_paper.college_id = data['college_id']
        existing_paper.program_id = data['program_id']
        existing_paper.title = data['title']
        existing_paper.abstract = data['abstract']
        existing_paper.date_approved = data['date_approved']
        existing_paper.research_type = data['research_type']
        existing_paper.adviser_id = data['adviser_id']

        # Update SDGs
        # Delete existing SDGs
        SDG.query.filter_by(research_id=research_id).delete()
        # Add new SDGs
        sdg_list = data['sdg'].split(';') if data['sdg'] else []
        for sdg_id in sdg_list:
            if sdg_id.strip():
                new_sdg = SDG(
                    research_id=research_id,
                    sdg=sdg_id.strip()
                )
                db.session.add(new_sdg)

        # Update panels
        # Delete existing panels
        Panel.query.filter_by(research_id=research_id).delete()
        # Add new panels
        panel_ids = request.form.getlist('panel_ids')
        if panel_ids:
            for panel_id in panel_ids:
                new_panel = Panel(
                    research_id=research_id,
                    panel_id=panel_id
                )
                db.session.add(new_panel)

        # Update keywords
        # Delete existing keywords
        Keywords.query.filter_by(research_id=research_id).delete()
        # Add new keywords
        keywords_str = data.get('keywords')
        if keywords_str:
            keywords_list = keywords_str.split(';')
            for keyword in keywords_list:
                if keyword.strip():
                    new_keyword = Keywords(
                        research_id=research_id,
                        keyword=keyword.strip()
                    )
                    db.session.add(new_keyword)

        # Update authors
        # Delete existing authors
        ResearchOutputAuthor.query.filter_by(research_id=research_id).delete()
        # Add new authors
        author_ids = request.form.getlist('author_ids')
        if author_ids:
            try:
                # Query author information including last names
                author_info = db.session.query(
                    Account.user_id,
                    UserProfile.last_name
                ).join(
                    UserProfile,
                    Account.user_id == UserProfile.researcher_id
                ).filter(
                    Account.user_id.in_(author_ids)
                ).all()

                # Create a dictionary of author_id to last_name for sorting
                author_dict = {str(author.user_id): author.last_name for author in author_info}
                
                # Sort author_ids based on last names
                sorted_author_ids = sorted(author_ids, key=lambda x: author_dict[x].lower())

                # Add authors with order based on sorted last names
                for index, author_id in enumerate(sorted_author_ids, start=1):
                    new_author = ResearchOutputAuthor(
                        research_id=research_id,
                        author_id=author_id,
                        author_order=index
                    )
                    db.session.add(new_author)

            except Exception as e:
                print(f"Error sorting authors: {str(e)}")
                raise e

        db.session.commit()

        # Log audit trail
        auth_services.log_audit_trail(
            user_id=user_id,
            table_name='Research_Output',
            record_id=research_id,
            operation='UPDATE',
            action_desc='Updated research paper'
        )

        return jsonify({
            "message": "Research output updated successfully",
            "research_id": research_id
        }), 200

    except Exception as e:
        # If anything fails, rollback database changes
        db.session.rollback()
        # If we were in the process of saving a new file, try to delete it
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
        
    finally:
        db.session.close()

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
@jwt_required()
def increment_views(research_id):
    try:
        # Get query parameter
        is_increment = request.args.get('is_increment', 'false').lower() == 'true'
        updated_views = 0

        # Get user_id from request body
        data = request.get_json()

        # Fetch the record using SQLAlchemy query
        view_count = ResearchOutput.query.filter_by(research_id=research_id).first()
        if is_increment:
            if view_count:
                if view_count.view_count is None:
                    updated_views = 1  # Start from 1 if None
                else:
                    updated_views = int(view_count.view_count) + 1

                view_count.view_count = updated_views
                db.session.commit()
            else:
                return jsonify({"message": "Record not found"}), 404

        return jsonify({
            "message": "View count updated",
            "updated_views": view_count.view_count,
            "download_count": view_count.download_count or 0,
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error in increment_views: {str(e)}")  # Add detailed error logging
        return jsonify({"message": f"Failed to update view counts: {str(e)}"}), 500

    finally:
        db.session.close()


@paper.route('/increment_downloads/<research_id>', methods=['PUT'])
@jwt_required()
def increment_downloads(research_id):
    try:
        updated_downloads = 0
        # Get user_id from request body
        data = request.get_json()
        
        # Fetch the record using SQLAlchemy query
        download_count = ResearchOutput.query.filter_by(research_id=research_id).first()
        if download_count:
            if download_count.download_count is None:
                updated_downloads = 1  # Start from 1 if None
            else:
                updated_downloads = int(download_count.download_count) + 1

            download_count.download_count = updated_downloads
            db.session.commit()

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

@paper.route('/view_extended_abstract/<research_id>', methods=['GET'])
def view_extended_abstract(research_id):
    try:
        # Query the database for the extended_abstract using the research_id
        research_output = ResearchOutput.query.filter_by(research_id=research_id).first()

        # Check if research_output exists and if the handle for the extended abstract is available
        if not research_output or not research_output.extended_abstract:
            return jsonify({"error": "Extended abstract not found."}), 404

        file_path = os.path.normpath(research_output.extended_abstract)

        # Check if the file exists
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found."}), 404

        # Send the file for viewing
        return send_file(file_path, as_attachment=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500