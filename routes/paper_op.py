from flask import Blueprint, request, jsonify, send_file, session
from models import (
    db, 
    ResearchOutput, 
    SDG, 
    Keywords, 
    Publication, 
    ResearchOutputAuthor, 
    Panel, 
    UserProfile, 
    Account, 
    ResearchArea, 
    ResearchOutputArea,
    ResearchTypes,
    PublicationFormat
)
from services import auth_services
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import pytz
import traceback
from flask_jwt_extended import jwt_required, get_jwt_identity
import pickle
from flask_cors import cross_origin
from sqlalchemy.orm import joinedload


paper = Blueprint('paper', __name__)
UPLOAD_FOLDER = './research_repository'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'binary_relevance_model.pkl')

# Use raw string for Windows path or forward slashes

@paper.route('/add_paper', methods=['POST'])
@jwt_required()
def add_paper():
    try:
        # Get the current user's identity
        user_id = get_jwt_identity()
        data = request.form

        # Required Fields
        required_fields = [
            'research_id', 'college_id', 'program_id', 'title', 
            'abstract', 'school_year', 'term', 'research_type', 
            'sdg', 'keywords', 'author_ids', 'research_areas'
        ]

        # Validate non-file fields
        missing_fields = [field for field in required_fields if field not in data or not data[field].strip()]

        # Validate the manuscript (required)
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "Manuscript file is required."}), 400

        if file.content_type != 'application/pdf':
            return jsonify({"error": "Invalid manuscript file type. Only PDF files are allowed."}), 400

        # Check if authors array is empty
        if 'author_ids' in data and not request.form.getlist('author_ids'):
            missing_fields.append('author_ids')
        
        # Check if research areas is empty
        if 'research_areas' in data and not data['research_areas'].strip():
            missing_fields.append('research_areas')
            
        # Skip adviser and panel validation for specific research types
        skip_adviser_and_panel = data['research_type'] not in ['FD']

        if not skip_adviser_and_panel:
            # Check if adviser is missing
            if 'adviser_id' not in data or not data['adviser_id'].strip():
                missing_fields.append('adviser_id')
            
            # Check if panels array is empty
            if 'panel_ids' in data and not request.form.getlist('panel_ids'):
                missing_fields.append('panel_ids')
            
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
        
        # Check for duplicate group code first
        if is_duplicate(data['research_id']):
            return jsonify({"error": "Group Code already exists"}), 400

        # Check for duplicate title and authors
        author_ids = request.form.getlist('author_ids')
        if author_ids:
            # Check for duplicate title (case-insensitive)
            title_match = ResearchOutput.query.filter(
                db.func.lower(ResearchOutput.title) == db.func.lower(data['title'])
            ).first()

            if title_match:
                # If title exists, check for author overlap
                existing_authors = ResearchOutputAuthor.query.filter_by(
                    research_id=title_match.research_id
                ).all()
                existing_author_ids = [str(author.author_id) for author in existing_authors]
                
                # Check if any of the new authors are in the existing authors
                if any(author_id in existing_author_ids for author_id in author_ids):
                    return jsonify({
                        "error": "A paper with this title and these authors already exists"
                    }), 400

        # Save the manuscript
        dir_path = os.path.join(
            UPLOAD_FOLDER, 
            data['research_type'], 
            'manuscript', 
            str(data['school_year']),  # Use school_year instead of date_approved
            data['college_id'],
            data['program_id']
        )
        os.makedirs(dir_path, exist_ok=True)

        filename = secure_filename(f"{data['research_id']}_manuscript.pdf")
        file_path = os.path.normpath(os.path.join(dir_path, filename))
        file.save(file_path)

        # Save the extended abstract (if provided)
        file_path_ea = None
        if 'extended_abstract' in request.files:
            file_ea = request.files['extended_abstract']
            if file_ea:
                dir_path_ea = os.path.join(
                    UPLOAD_FOLDER, 
                    data['research_type'], 
                    'extended_abstract', 
                    str(data['school_year']),  # Use school_year here too
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
        
        # Adviser ID is None if skipped
        adviser_id = None if skip_adviser_and_panel else data.get('adviser_id')

        # Create new research output
        new_research = ResearchOutput(
            research_id=data['research_id'],
            college_id=data['college_id'],
            program_id=data['program_id'],
            title=data['title'],
            abstract=data['abstract'],
            school_year=data['school_year'],
            term=data['term'],
            research_type_id=data['research_type'],
            full_manuscript=file_path,
            extended_abstract=file_path_ea,
            adviser_id=adviser_id,
            user_id=user_id,
            date_uploaded=current_datetime,
            view_count=0,
            download_count=0, 
            unique_views=0
        )
        db.session.add(new_research)
        db.session.flush()

        # Now handle research areas with the generated research_id
        research_areas_str = data.get('research_areas')
        if research_areas_str:
            research_area_ids = research_areas_str.split(';')
            for area_id in research_area_ids:
                if area_id.strip():
                    new_research_area = ResearchOutputArea(
                        research_id=data['research_id'],
                        research_area_id=area_id.strip()
                    )
                    db.session.add(new_research_area)

        # Handle other relationships (SDGs, keywords, authors, panels)
        # Handle multiple SDGs
        sdg_list = data['sdg'].split(';') if data['sdg'] else []
        for sdg_id in sdg_list:
            if sdg_id.strip():
                new_sdg = SDG(
                    research_id=data['research_id'],
                    sdg=sdg_id.strip()
                )
                db.session.add(new_sdg)

        # Handle panels only if required
        if not skip_adviser_and_panel:
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
                        author_order=index
                    )
                    db.session.add(new_author)

            except Exception as e:
                print(f"Error sorting authors: {str(e)}")
                raise e

        # Finally commit everything
        db.session.commit()

        # Log audit trail
        auth_services.log_audit_trail(
            user_id=user_id,
            table_name='Research_Output',
            record_id=new_research.research_id,
            operation='CREATE',
            action_desc='Added research paper'
        )

        return jsonify({
            "message": "Research output and manuscript added successfully", 
            "research_id": new_research.research_id
        }), 201
    
    except Exception as e:
        db.session.rollback()
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        
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
        data = request.form

        # Only validate editable fields
        required_fields = ['abstract']

        # Validate required fields
        missing_fields = [field for field in required_fields if field not in data or not data[field].strip()]
        
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

        # Get the existing paper
        existing_paper = ResearchOutput.query.filter_by(research_id=research_id).first()
        if not existing_paper:
            return jsonify({"error": "Paper not found"}), 404

        # Update only editable fields
        existing_paper.abstract = data['abstract']

        # Handle research areas update
        if 'research_areas' in data and data['research_areas']:
            ResearchOutputArea.query.filter_by(research_id=research_id).delete()
            research_area_ids = data['research_areas'].split(';')
            for area_id in research_area_ids:
                if area_id.strip():
                    new_research_area = ResearchOutputArea(
                        research_id=research_id,
                        research_area_id=area_id.strip()
                    )
                    db.session.add(new_research_area)

        # Handle keywords update
        if 'keywords' in data and data['keywords']:
            # Delete existing keywords
            Keywords.query.filter_by(research_id=research_id).delete()
            
            # Add new keywords
            keywords = data['keywords'].split(';')
            for keyword in keywords:
                if keyword.strip():
                    new_keyword = Keywords(
                        research_id=research_id,
                        keyword=keyword.strip()
                    )
                    db.session.add(new_keyword)

        # Handle SDG update
        if 'sdg' in data:
            existing_paper.sdg = data['sdg']

        # Handle file uploads if present
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename:
                # Your existing file handling code
                pass

        if 'extended_abstract' in request.files:
            extended_abstract = request.files['extended_abstract']
            if extended_abstract and extended_abstract.filename:
                # Your existing extended abstract handling code
                pass

        db.session.commit()
        return jsonify({"message": "Paper updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating paper: {str(e)}")
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
                if view_count.view_count == 0:
                    view_count.view_count = 1  # Start from 1 if None
                    view_count.unique_views = 1  # Initialize unique views to 1
                    db.session.commit()

                else:
                    updated_views = int(view_count.view_count) + 1
                    view_count.view_count = updated_views
                    db.session.commit()

                
            else:
                return jsonify({"message": "Record not found"}), 404
            
            # Get the current user's identity
            user_id = get_jwt_identity()
            try:
                auth_services.log_audit_trail(
                    user_id=user_id,
                    table_name='Research_Output',
                    record_id=research_id,
                    operation='VIEW',
                    action_desc='Viewed research paper'
                )
            except Exception as audit_error:
                print(f"Audit trail logging failed: {audit_error}")
                # Continue execution even if audit trail fails

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

            # Get the current user's identity
            user_id = get_jwt_identity()
            try:
                auth_services.log_audit_trail(
                    user_id=user_id,
                    table_name='Research_Output',
                    record_id=research_id,
                    operation='DOWNLOAD',
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

@paper.route('/research_areas', methods=['GET'])
def get_research_areas():
    try:
        # Query all research areas
        areas = ResearchArea.query.all()
        
        # Convert to list of dictionaries matching the model's field names
        areas_list = [{
            'id': area.research_area_id, 
            'name': area.research_area_name
        } for area in areas]
        
        return jsonify({
            "message": "Research areas retrieved successfully",
            "research_areas": areas_list
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@paper.route('/research_types', methods=['GET'])
def get_research_types():
    try:
        # Query all research types
        types = ResearchTypes.query.all()
        
        # Convert to list of dictionaries matching the model's field names
        types_list = [{
            'id': res_type.research_type_id, 
            'name': res_type.research_type_name
        } for res_type in types]
        
        return jsonify({
            "message": "Research types retrieved successfully",
            "research_types": types_list
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    
@paper.route('/publication_format', methods=['GET'])
def get_pub_formats():
    try:
        # Query all research types
        formats = PublicationFormat.query.all()
        
        # Convert to list of dictionaries matching the model's field names
        formats_list = [{
            'id': pub_format.pub_format_id, 
            'name': pub_format.pub_format_name
        } for pub_format in formats]
        
        return jsonify({
            "message": "Publication formats retrieved successfully",
            "publication_formats": formats_list
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@paper.route('/check_duplicate', methods=['GET'])
def check_duplicate():
    try:
        group_code = request.args.get('group_code')
        title = request.args.get('title')
        author_ids = request.args.get('author_ids')

        response = {
            "isDuplicateTitle": False,
            "isDuplicateAuthors": False
        }
        
        if group_code:
            # Check for duplicate group code
            exists = ResearchOutput.query.filter_by(research_id=group_code).first() is not None
            return jsonify({"isDuplicate": exists}), 200

        if title and author_ids:
            # Split author_ids string into list
            author_id_list = author_ids.split(',')

            # Check for duplicate title (case-insensitive)
            title_match = ResearchOutput.query.filter(
                db.func.lower(ResearchOutput.title) == db.func.lower(title)
            ).first()

            if title_match:
                response["isDuplicateTitle"] = True
                
                # If we found a title match, check if any of the authors match
                existing_authors = ResearchOutputAuthor.query.filter_by(
                    research_id=title_match.research_id
                ).all()
                
                existing_author_ids = [str(author.author_id) for author in existing_authors]
                
                # Check if any of the new authors are in the existing authors
                if any(author_id in existing_author_ids for author_id in author_id_list):
                    response["isDuplicateAuthors"] = True

        return jsonify(response), 200

    except Exception as e:
        print(f"Error checking duplicates: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500