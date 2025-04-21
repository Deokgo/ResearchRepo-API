from flask import Blueprint, request, jsonify, send_file, session, Response
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
    PublicationFormat,
    UserEngagement,
    Program,
    College
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
from sqlalchemy import func
import pandas as pd
from io import StringIO, BytesIO
import re
import pikepdf
from pikepdf import Pdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

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
        
        # Get user details for audit trail
        user = Account.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

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

        # Validate the extended abstract (required)
        extended_abstract = request.files.get('extended_abstract')
        if not extended_abstract:
            return jsonify({"error": "Extended Abstract file is required."}), 400

        if extended_abstract.content_type != 'application/pdf':
            return jsonify({"error": "Invalid extended abstract file type. Only PDF files are allowed."}), 400

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
        print(f'adviser_id: {adviser_id}')

        adviser = None
        if adviser_id is not None:
            adviser = UserProfile.query.get(adviser_id)

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
            adviser_first_name=adviser.first_name if adviser else None,
            adviser_middle_name=adviser.middle_name if adviser else None,
            adviser_last_name=adviser.last_name if adviser else None,
            adviser_suffix=adviser.suffix if adviser else None,
            date_uploaded=current_datetime,
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
            print(f'panel_ids: {panel_ids}')
            
            if panel_ids:
                for panel_id in panel_ids:
                    panel = UserProfile.query.get(panel_id) if panel_id else None
                    
                    new_panel = Panel(
                        research_id=data['research_id'],
                        panel_first_name=panel.first_name if panel else None,
                        panel_middle_name=panel.middle_name if panel else None,
                        panel_last_name=panel.last_name if panel else None,
                        panel_suffix=panel.suffix if panel else None
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
                # Get user IDs
                accounts = db.session.query(Account.user_id).filter(Account.user_id.in_(author_ids)).all()
                account_ids = [account.user_id for account in accounts]

                # Get UserProfile details separately
                author_info = db.session.query(
                    UserProfile.researcher_id,
                    UserProfile.first_name,
                    UserProfile.middle_name,
                    UserProfile.last_name,
                    UserProfile.suffix
                ).filter(UserProfile.researcher_id.in_(account_ids)).all()

                # Create a dictionary of author_id to last_name for sorting
                author_dict = {str(author.researcher_id): author.last_name for author in author_info}

                # Sort author_ids based on last names
                sorted_author_ids = sorted(author_ids, key=lambda x: author_dict[x].lower())

                # Add authors with order based on sorted last names
                for index, author_id in enumerate(sorted_author_ids, start=1):
                    author = UserProfile.query.get(author_id)  # Fetch the full author details
                    
                    new_author = ResearchOutputAuthor(
                        research_id=data['research_id'],
                        author_order=index,
                        author_first_name=author.first_name,
                        author_middle_name=author.middle_name,
                        author_last_name=author.last_name,
                        author_suffix=author.suffix
                    )
                    db.session.add(new_author)

            except Exception as e:
                print(f"Error sorting authors: {str(e)}")
                raise e

        # Finally commit everything
        db.session.commit()

        # Modified audit trail logging
        auth_services.log_audit_trail(
            email=user.email,
            role=user.role.role_name,
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
        
        # Get user details for audit trail
        user = Account.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.form
        file = request.files.get('file')
        file_ea = request.files.get('extended_abstract')

        # Get the existing paper
        existing_paper = ResearchOutput.query.filter_by(research_id=research_id).first()
        if not existing_paper:
            return jsonify({"error": "Paper not found"}), 404

        # Track changes for action description
        changes = []
        philippine_tz = pytz.timezone('Asia/Manila')
        current_datetime = datetime.now(philippine_tz).replace(tzinfo=None)

        # Manuscript update
        if file:
            if not file.content_type == 'application/pdf':
                return jsonify({"error": "Invalid manuscript file type. Only PDF files are allowed."}), 400

            # Save new manuscript (replacing old one)
            dir_path = os.path.join(
                UPLOAD_FOLDER,
                existing_paper.research_type_id,
                'manuscript',
                str(existing_paper.school_year),
                existing_paper.college_id,
                existing_paper.program_id
            )
            os.makedirs(dir_path, exist_ok=True)

            filename = secure_filename(f"{research_id}_manuscript.pdf")
            file_path = os.path.normpath(os.path.join(dir_path, filename))
            
            # Remove old file if it exists
            if os.path.exists(file_path):
                os.remove(file_path)
                
            file.save(file_path)
            changes.append("Changed full manuscript file")
            existing_paper.full_manuscript = file_path

        # Extended abstract update
        if file_ea:
            if not file_ea.content_type == 'application/pdf':
                return jsonify({"error": "Invalid extended abstract file type. Only PDF files are allowed."}), 400

            # Save new extended abstract (replacing old one)
            dir_path_ea = os.path.join(
                UPLOAD_FOLDER,
                existing_paper.research_type_id,
                'extended_abstract',
                str(existing_paper.school_year),
                existing_paper.college_id,
                existing_paper.program_id
            )
            os.makedirs(dir_path_ea, exist_ok=True)

            filename_ea = secure_filename(f"{research_id}_extended_abstract.pdf")
            file_path_ea = os.path.normpath(os.path.join(dir_path_ea, filename_ea))
            
            # Remove old file if it exists
            if os.path.exists(file_path_ea):
                os.remove(file_path_ea)
                
            file_ea.save(file_path_ea)
            changes.append("Changed extended abstract file")
            existing_paper.extended_abstract = file_path_ea

        # Update basic fields
        if 'abstract' in data and existing_paper.abstract != data['abstract']:
            changes.append(f"Abstract: '{existing_paper.abstract}' -> '{data['abstract']}'")
            existing_paper.abstract = data['abstract']

        # Handle research areas update
        if 'research_areas' in data and data['research_areas']:
            old_research_areas = [area.research_area_id for area in ResearchOutputArea.query.filter_by(research_id=research_id).all()]
            new_research_areas = [area_id.strip() for area_id in data['research_areas'].split(';') if area_id.strip()]
            if set(old_research_areas) != set(new_research_areas):
                changes.append(f"Research Areas: {old_research_areas} -> {new_research_areas}")
                ResearchOutputArea.query.filter_by(research_id=research_id).delete()
                for area_id in new_research_areas:
                    new_research_area = ResearchOutputArea(
                        research_id=research_id,
                        research_area_id=area_id
                    )
                    db.session.add(new_research_area)

        # Handle keywords update
        if 'keywords' in data and data['keywords']:
            old_keywords = [kw.keyword for kw in Keywords.query.filter_by(research_id=research_id).all()]
            new_keywords = [kw.strip() for kw in data['keywords'].split(';') if kw.strip()]
            if set(old_keywords) != set(new_keywords):
                changes.append(f"Keywords: {old_keywords} -> {new_keywords}")
                Keywords.query.filter_by(research_id=research_id).delete()
                for keyword in new_keywords:
                    new_keyword = Keywords(
                        research_id=research_id,
                        keyword=keyword
                    )
                    db.session.add(new_keyword)

        # Handle SDGs update
        from sqlalchemy import func
        if 'sdg' in data and data['sdg']:
            # Create the subquery to retrieve concatenated SDGs for each research_id
            sdg_subquery = db.session.query(
                SDG.research_id,
                func.string_agg(SDG.sdg, '; ').label('concatenated_sdg')
            ).group_by(SDG.research_id).subquery()

            # Retrieve concatenated SDGs for the specific research_id
            concatenated_sdgs = db.session.query(sdg_subquery.c.concatenated_sdg).filter(
                sdg_subquery.c.research_id == research_id
            ).scalar()  # Use scalar to get the single value

            # Split the concatenated string into a list of SDGs
            old_sdgs = concatenated_sdgs.split('; ') if concatenated_sdgs else []
            print(f"Old SDGs: {old_sdgs}")

            # Process the new SDGs from the input data
            new_sdgs = [sdg.strip() for sdg in data['sdg'].split(';') if sdg.strip()]
            print(f"New SDGs: {new_sdgs}")
            
            print(f"{set(old_sdgs)} != {set(new_sdgs)}")
            if set(old_sdgs) != set(new_sdgs):
                changes.append(f"SDGs: {old_sdgs} -> {', '.join(new_sdgs)}")
                
                # Delete old SDGs associated with this research ID
                SDG.query.filter(SDG.research_id == research_id).delete()

                # Add new SDGs to the database
                for sdg in new_sdgs:
                    new_sdg = SDG(
                        research_id=research_id,
                        sdg=sdg
                    )
                    db.session.add(new_sdg)
                
                db.session.commit()  # Commit changes to the database

        db.session.commit()

        # Modified audit trail logging
        formatted_changes = "\n".join(changes)
        auth_services.log_audit_trail(
            email=user.email,
            role=user.role.role_name,
            table_name='Research_Output',
            record_id=research_id,
            operation='UPDATE',
            action_desc=f"Updated research paper with the following changes:\n{formatted_changes}"
        )

        print(f"Updated research paper with the following changes:\n{formatted_changes}")

        return jsonify({"message": "Paper updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating paper: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

    finally:
        db.session.close()

def add_footer_to_pdf(input_path, source_url="https://mmcl-researchrepository.com/"):
    """
    Adds a footer to each page of a PDF file with source URL and download date
    """
    try:
        # Get current date in Philippine timezone
        philippine_tz = pytz.timezone('Asia/Manila')
        current_date = datetime.now(philippine_tz).strftime("%B %d, %Y")
        
        # Footer text
        footer_text = f"Downloaded from {source_url} on {current_date}"
        
        # Create an in-memory output PDF
        output_buffer = BytesIO()
        
        # Use pikepdf for the operation
        with pikepdf.open(input_path) as pdf:
            # For each page in the PDF
            for i, page in enumerate(pdf.pages):
                # Get the MediaBox which defines page boundaries
                mediabox = page.MediaBox
                
                # Calculate page dimensions properly
                x0, y0, x1, y1 = [float(mediabox[i]) for i in range(4)]
                width = x1 - x0
                height = y1 - y0
                
                # Create a new PDF with ReportLab to draw the footer
                temp_buffer = BytesIO()
                c = canvas.Canvas(temp_buffer, pagesize=(width, height))
                
                # Set font properties for better visibility
                c.setFont("Helvetica", 10)
                c.setFillColorRGB(0.3, 0.3, 0.3)  # Darker gray for better visibility
                
                # Position at bottom of page (higher y value to be visible)
                y_position = 30  # Higher position from bottom
                c.drawCentredString(width/2, y_position, footer_text)
                c.save()
                
                # Get the content as a PDF
                temp_buffer.seek(0)
                overlay_pdf = pikepdf.open(temp_buffer)
                
                # Apply the overlay to the current page
                page.add_overlay(overlay_pdf.pages[0])
            
            # Save the modified PDF to the output buffer
            pdf.save(output_buffer)
        
        # Return buffer at beginning for reading
        output_buffer.seek(0)
        return output_buffer
        
    except Exception as e:
        # Print detailed error for debugging
        print(f"Error adding footer to PDF: {str(e)}")
        traceback.print_exc()  # Print the full traceback for debugging
        return None

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

        # Add footer to the PDF
        pdf_with_footer = add_footer_to_pdf(file_path)
        
        if pdf_with_footer:
            # Send the modified file with footer
            return send_file(
                pdf_with_footer, 
                mimetype='application/pdf',
                as_attachment=False,
                download_name=f"{research_id}_manuscript.pdf"
            )
        else:
            # If footer addition fails, fall back to original file
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
        user_id = get_jwt_identity()
        philippine_tz = pytz.timezone('Asia/Manila')

        # Fetch the record using SQLAlchemy query
        research_output = ResearchOutput.query.filter_by(research_id=research_id).first()
        if not research_output:
            return jsonify({"message": "Research record not found"}), 404

        if is_increment:
            # Log user engagement
            new_engagement = UserEngagement(
                research_id=research_id,
                user_id=user_id,
                timestamp=datetime.now(philippine_tz).replace(tzinfo=None),
                view=1,
                download=0
            )
            db.session.add(new_engagement)
            db.session.commit()

        # Aggregate views for the research_id in UserEngagement
        total_views = (
            db.session.query(func.sum(UserEngagement.view))
            .filter(UserEngagement.research_id == research_id)
            .scalar()
        )
        total_downloads = (
                db.session.query(func.sum(UserEngagement.download))
                .filter(UserEngagement.research_id == research_id)
                .scalar()
            )
        print(f'total views: {total_views}')

        return jsonify({
            "message": "View count updated",
            "updated_views": total_views or 0,
            "download_count": total_downloads or 0
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error in increment_views: {str(e)}")  # Detailed error logging
        return jsonify({"message": f"Failed to update view counts: {str(e)}"}), 500

    finally:
        db.session.close()


@paper.route('/increment_downloads/<research_id>', methods=['PUT'])
@jwt_required()
def increment_downloads(research_id):
    try:
        # Get query parameter
        user_id = get_jwt_identity()
        philippine_tz = pytz.timezone('Asia/Manila')

        # Fetch the research record using SQLAlchemy query
        research_output = ResearchOutput.query.filter_by(research_id=research_id).first()
        if not research_output:
            return jsonify({"message": "Research record not found"}), 404

        # Check if the user has already downloaded this research
        existing_download = UserEngagement.query.filter_by(
            research_id=research_id,
            user_id=user_id,
            download=1
        ).first()

        if existing_download:
            # If a download already exists, do not record a new one
            total_downloads = (
                db.session.query(func.sum(UserEngagement.download))
                .filter(UserEngagement.research_id == research_id)
                .scalar()
            )
            print(f'existing download: {total_downloads}')
            return jsonify({
                "message": "Download already recorded for this user",
                "updated_downloads": total_downloads
            }), 200

        # Log user engagement for a new download
        new_engagement = UserEngagement(
            research_id=research_id,
            user_id=user_id,
            timestamp=datetime.now(philippine_tz).replace(tzinfo=None),
            view=0,
            download=1
        )
        db.session.add(new_engagement)
        db.session.commit()

        # Aggregate downloads for the research_id in UserEngagement
        total_downloads = (
            db.session.query(func.sum(UserEngagement.download))
            .filter(UserEngagement.research_id == research_id)
            .scalar()
        )

        print(f'total downloads: {total_downloads}')

        return jsonify({
            "message": "Download count incremented",
            "updated_downloads": total_downloads or 0
        }), 200

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

        # Add footer to the PDF
        pdf_with_footer = add_footer_to_pdf(file_path)
        
        if pdf_with_footer:
            # Send the modified file with footer
            return send_file(
                pdf_with_footer, 
                mimetype='application/pdf',
                as_attachment=False,
                download_name=f"{research_id}_extended_abstract.pdf"
            )
        else:
            # If footer addition fails, fall back to original file
            return send_file(file_path, as_attachment=False)
    except Exception as e:
        print(str(e))
        return jsonify({"error": str(e)}), 500
    
@paper.route('/view_fs_copy/<research_id>', methods=['GET'])
def view_fs_Copy(research_id):
    try:
        # Query the database for the extended_abstract using the research_id
        research_output = ResearchOutput.query.filter_by(research_id=research_id).first()

        # Check if research_output exists and if the handle for the extended abstract is available
        if not research_output:
            return jsonify({"error": "Research Output not found."}), 404
        
        publication = Publication.query.filter(Publication.research_id == research_id).first()
        if not publication or not publication.publication_paper:
            return jsonify({"error": "Final Submitted Copy not found."}), 404

        file_path = os.path.normpath(publication.publication_paper)

        # Check if the file exists
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found."}), 404

        # Send the file for viewing
        return send_file(file_path, as_attachment=False)
    except Exception as e:
        print(str(e))
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

@paper.route('/check_files/<research_id>', methods=['GET'])
def check_files(research_id):
    try:
        research_output = ResearchOutput.query.filter_by(research_id=research_id).first()
        
        if not research_output:
            return jsonify({
                "manuscript": False,
                "extendedAbstract": False
            }), 200
            
        manuscript_available = bool(research_output.full_manuscript and os.path.exists(research_output.full_manuscript))
        ea_available = bool(research_output.extended_abstract and os.path.exists(research_output.extended_abstract))
        
        return jsonify({
            "manuscript": manuscript_available,
            "extendedAbstract": ea_available
        }), 200
        
    except Exception as e:
        print(f"Error checking file availability: {str(e)}")
        return jsonify({"error": str(e)}), 500

@paper.route('/bulk_upload', methods=['POST'])
@jwt_required()
def bulk_upload_papers():
    try:
        # Get the current user's identity
        user_id = get_jwt_identity()
        user = Account.query.get(user_id)
        user_prog = UserProfile.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        try:
            # Read CSV file with explicit encoding
            csv_content = StringIO(file.stream.read().decode("UTF8"))
            df = pd.read_csv(csv_content)
            print("CSV file read successfully")  # Debug log
            print("Columns found:", df.columns.tolist())  # Debug log
        except Exception as e:
            print(f"Error reading CSV: {str(e)}")
            return jsonify({"error": f"Error reading CSV file: {str(e)}"}), 400

        # Validate required columns
        required_columns = [
            'research_id', 'college_id', 'program_id', 'title', 
            'abstract', 'school_year', 'term', 'research_type',
            'authors', 'keywords'
        ]
        # Optional columns
        optional_columns = ['adviser', 'panels']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({
                "error": f"Missing required columns: {', '.join(missing_columns)}"
            }), 400

        print(f"Processing {len(df)} rows")  # Debug log

        # Validation errors collection
        validation_errors = []
        
        # First pass: validate all rows before committing any changes
        for index, row in df.iterrows():
            row_num = index + 1
            try:
                # Check if research_id already exists
                existing_research = ResearchOutput.query.filter_by(research_id=row['research_id'].strip()).first()
                if existing_research:
                    validation_errors.append(f"Row {row_num}: Research ID '{row['research_id'].strip()}' already exists in the database\n")
                    continue

                # Get user's program and college IDs for validation
                user_program_id = user_prog.program_id
                user_college_id = user_prog.college_id

                # Validate user's program and college authorization
                # First validate that college_id and program_id exist in the database
                college = College.query.filter_by(college_id=str(row['college_id']).strip()).first()
                if not college:
                    validation_errors.append(f"Row {row_num}: College ID '{row['college_id'].strip()}' does not exist in the database\n")
                    continue

                program = Program.query.filter_by(program_id=str(row['program_id']).strip()).first()
                if not program:
                    validation_errors.append(f"Row {row_num}: Program ID '{row['program_id'].strip()}' does not exist in the database\n")
                    continue

                # Then proceed with authorization check
                if str(row['program_id']).strip() != str(user_program_id) or str(row['college_id']).strip() != str(user_college_id):
                    validation_errors.append(f"Row {row_num}: You are not authorized to add papers for program ID {row['program_id'].strip()} and college ID {row['college_id'].strip()}\n")
                    continue
                
                # Validate research_type FD condition for adviser and panel
                research_type = str(row['research_type']).strip()
                has_adviser = pd.notna(row.get('adviser'))
                has_panel = pd.notna(row.get('panels'))

                if research_type not in ["FD", "CD", "CM", "GF", "MT"]:
                    validation_errors.append(f"Row {row_num}: Research type '{research_type}' is invalid\n")
                    continue

                # Validate that FD research type must have both adviser and panels
                if research_type == "FD" and (not has_adviser or not has_panel):
                    validation_errors.append(f"Row {row_num}: Research type 'FD' must have both adviser and panel fields filled\n")
                    continue

                if research_type != "FD" and (has_adviser or has_panel):
                    validation_errors.append(f"Row {row_num}: Research type '{research_type}' should not have adviser or panel\n")
                    continue

                # Validate term (should only be 1, 2, or 3)
                if str(row['term']).strip() not in {'1', '2', '3'}:
                    validation_errors.append(f"Row {row_num}: Term '{row['term']}' is invalid. It must be 1, 2, or 3.\n")
                    continue

                # Validate school_year format (YYYY-YYYY) with a one-year interval
                school_year_pattern = re.compile(r'^\d{4}-\d{4}$')
                school_year = str(row['school_year']).strip()

                if not school_year_pattern.match(school_year):
                    validation_errors.append(f"Row {row_num}: School year '{school_year}' is not in the correct format (YYYY-YYYY)\n")
                    continue

                start_year, end_year = map(int, school_year.split('-'))
                if end_year - start_year != 1:
                    validation_errors.append(f"Row {row_num}: School year '{school_year}' does not have a valid one-year interval\n")
                    continue

                # Define valid SDG values
                valid_sdgs = {f"SDG {i}" for i in range(1, 18)}

                # Validate SDG format
                if 'sdg' in row and pd.notna(row['sdg']):
                    sdg_values = [sdg.strip() for sdg in str(row['sdg']).split(';')]
                    
                    # Check if each SDG is valid
                    invalid_sdgs = [sdg for sdg in sdg_values if sdg not in valid_sdgs]
                    
                    if invalid_sdgs:
                        validation_errors.append(f"Row {row_num}: Invalid SDG(s) found: {', '.join(invalid_sdgs)}. Valid format: 'SDG 1; SDG 2; ... SDG 17'\n")
                        continue  # Skip this row if SDG validation fails

                # Validate adviser exists in same college
                if has_adviser:
                    adviser_name = row['adviser'].strip()
                    
                    # Validate adviser name format (LastName, FirstName MiddleInitial.)
                    if ',' not in adviser_name:
                        validation_errors.append(f"Row {row_num}: Adviser '{adviser_name}' does not follow the format 'LastName, FirstName MiddleInitial.'\n")
                        continue
                        
                    parts = adviser_name.split(',')
                    if len(parts) == 2:
                        adviser_last_name = parts[0].strip()
                        first_part = parts[1].strip()
                        
                        # Process name parts
                        words = first_part.split()
                        adviser_middle_name = words[-1][0] if words and words[-1].endswith('.') else ''
                        adviser_first_name = ' '.join(words[:-1]) if words and words[-1].endswith('.') else first_part
                        
                        # Check if adviser exists in the database and in the same college
                        adviser = UserProfile.query.filter(
                            UserProfile.last_name == adviser_last_name,
                            UserProfile.first_name == adviser_first_name,
                            UserProfile.college_id == row['college_id'].strip()
                        ).first()
                        
                        if not adviser:
                            validation_errors.append(f"Row {row_num}: Adviser '{adviser_name}' not found in the college with ID {row['college_id'].strip()}\n")
                            continue
                    else:
                        validation_errors.append(f"Row {row_num}: Adviser '{adviser_name}' does not follow the format 'LastName, FirstName MiddleInitial.'\n")
                        continue

                # Validate authors exist in database
                if pd.notna(row['authors']):
                    authors_list = [author.strip() for author in str(row['authors']).split(';')]
                    
                    # Check if any authors are in an invalid format
                    for author_str in authors_list:
                        if ',' not in author_str:
                            validation_errors.append(f"Row {row_num}: Author '{author_str}' does not follow the format 'LastName, FirstName MiddleInitial.'\n")
                            continue
                    
                    # Continue with detailed author validation
                    for author_str in authors_list:
                        parts = author_str.split(',')
                        if len(parts) == 2:
                            last_name = parts[0].strip()
                            first_part = parts[1].strip()
                            
                            words = first_part.split()
                            middle_name = words[-1][0] if words and words[-1].endswith('.') else ''
                            first_name = ' '.join(words[:-1]) if words and words[-1].endswith('.') else first_part
                            
                            # Check if author exists in UserProfile
                            author = UserProfile.query.filter(
                                UserProfile.last_name == last_name,
                                UserProfile.first_name == first_name
                            ).first()
                            
                            if not author:
                                validation_errors.append(f"Row {row_num}: Author '{author_str}' not found in the database\n")
                                break  # Skip to next row if any author is not found
                        else:
                            validation_errors.append(f"Row {row_num}: Author '{author_str}' does not follow the format 'LastName, FirstName MiddleInitial.'\n")
                            break  # Skip to next row if any author has invalid format
                    
                    # If we found an error with any author, continue to next row
                    if any(f"Row {row_num}: Author" in error for error in validation_errors):
                        continue

                # Validate panels exist in database
                if has_panel:
                    panel_list = [panel.strip() for panel in str(row['panels']).split(';')]
                    
                    # Check if any panels are in an invalid format
                    for panel_str in panel_list:
                        if ',' not in panel_str:
                            validation_errors.append(f"Row {row_num}: Panel member '{panel_str}' does not follow the format 'LastName, FirstName MiddleInitial.'\n")
                            continue
                    
                    # Continue with detailed panel validation
                    for panel_str in panel_list:
                        parts = panel_str.split(',')
                        if len(parts) == 2:
                            panel_last_name = parts[0].strip()
                            first_part = parts[1].strip()
                            
                            words = first_part.split()
                            panel_middle_name = words[-1][0] if words and words[-1].endswith('.') else ''
                            panel_first_name = ' '.join(words[:-1]) if words and words[-1].endswith('.') else first_part
                            
                            # Check if panel exists in UserProfile
                            panel = UserProfile.query.filter(
                                UserProfile.last_name == panel_last_name,
                                UserProfile.first_name == panel_first_name
                            ).first()
                            
                            if not panel:
                                validation_errors.append(f"Row {row_num}: Panel member '{panel_str}' not found in the database\n")
                                break  # Skip to next row if any panel member is not found
                        else:
                            validation_errors.append(f"Row {row_num}: Panel member '{panel_str}' does not follow the format 'LastName, FirstName MiddleInitial.'\n")
                            break  # Skip to next row if any panel has invalid format
                    
                    # If we found an error with any panel, continue to next row
                    if any(f"Row {row_num}: Panel" in error for error in validation_errors):
                        continue

            except Exception as row_error:
                validation_errors.append(f"Row {row_num}: Validation error: {str(row_error)}\n")
        
        # Check if there are validation errors after checking all rows
        if validation_errors:
            return jsonify({
                "error": validation_errors
            }), 400
        
        # List to store successfully added research IDs for audit log
        successfully_added_research_ids = []
                
        # If all validations pass, proceed with adding the records
        for index, row in df.iterrows():
            try:
                print(f"Processing row {index + 1}")
                
                # Get research ID and clean it
                research_id = row['research_id'].strip()

                # Extract starting year from school year format (YYYY-YYYY)
                school_year = str(row['school_year']).strip().split('-')[0]

                # Process adviser information if provided
                adviser_first_name = None
                adviser_middle_name = None
                adviser_last_name = None
                adviser_suffix = ''

                if pd.notna(row.get('adviser')):
                    parts = row['adviser'].strip().split(',')
                    if len(parts) == 2:
                        adviser_last_name = parts[0].strip()
                        first_part = parts[1].strip()
                        
                        # Split the first part into words
                        words = first_part.split()
                        
                        # Check if last word ends with a period (middle initial)
                        if words and words[-1].endswith('.'):
                            # Get the middle initial without the period
                            adviser_middle_name = words[-1][0]
                            # Join all words except the last one for first name
                            adviser_first_name = ' '.join(words[:-1])
                        else:
                            # No middle initial
                            adviser_first_name = first_part
                            adviser_middle_name = ''

                # Create new research output with adviser information
                new_research = ResearchOutput(
                    research_id=research_id,
                    college_id=row['college_id'].strip(),
                    program_id=row['program_id'].strip(),
                    title=row['title'].strip(),
                    abstract=row['abstract'].strip(),
                    school_year=school_year,
                    term=int(row['term']),
                    research_type_id=row['research_type'].strip(),
                    date_uploaded=datetime.now(),
                    adviser_first_name=adviser_first_name,
                    adviser_middle_name=adviser_middle_name,
                    adviser_last_name=adviser_last_name,
                    adviser_suffix=adviser_suffix
                )
                db.session.add(new_research)
                db.session.flush()

                # Process panels if provided
                if pd.notna(row.get('panels')):
                    panel_list = [panel.strip() for panel in str(row['panels']).split(';')]
                    for panel_str in panel_list:
                        parts = panel_str.split(',')
                        if len(parts) == 2:
                            panel_last_name = parts[0].strip()
                            first_part = parts[1].strip()
                            
                            words = first_part.split()
                            
                            if words and words[-1].endswith('.'):
                                panel_middle_name = words[-1][0]
                                panel_first_name = ' '.join(words[:-1])
                            else:
                                panel_first_name = first_part
                                panel_middle_name = ''
                            
                            new_panel = Panel(
                                research_id=research_id,
                                panel_first_name=panel_first_name,
                                panel_middle_name=panel_middle_name,
                                panel_last_name=panel_last_name,
                                panel_suffix=''
                            )
                            db.session.add(new_panel)

                # Process SDGs
                if pd.notna(row.get('sdg')):
                    sdg_entries = str(row['sdg']).split(';')
                    for sdg_entry in sdg_entries:
                        sdg_entry = sdg_entry.strip()
                        if sdg_entry.startswith('SDG '):
                            sdg_number = sdg_entry[4:].strip()
                            if sdg_number.isdigit():
                                new_sdg = SDG(
                                    research_id=research_id,
                                    sdg=f"SDG {sdg_number}"
                                )
                                db.session.add(new_sdg)

                # Process keywords
                if pd.notna(row['keywords']):
                    keywords_list = [k.strip() for k in str(row['keywords']).split(';')]
                    for keyword in keywords_list:
                        if keyword:
                            new_keyword = Keywords(
                                research_id=research_id,
                                keyword=keyword
                            )
                            db.session.add(new_keyword)

                # Process authors
                if pd.notna(row['authors']):
                    authors_list = [author.strip() for author in str(row['authors']).split(';')]
                    for idx, author_str in enumerate(authors_list, start=1):
                        parts = author_str.split(',')
                        if len(parts) == 2:
                            last_name = parts[0].strip()
                            first_part = parts[1].strip()
                            
                            # Split the first part into words
                            words = first_part.split()
                            
                            # Check if last word ends with a period (middle initial)
                            if words and words[-1].endswith('.'):
                                # Get the middle initial without the period
                                middle_name = words[-1][0]  # Take just the letter before the period
                                # Join all words except the last one for first name
                                first_name = ' '.join(words[:-1])
                            else:
                                # No middle initial
                                first_name = first_part
                                middle_name = ''
                            
                            new_author = ResearchOutputAuthor(
                                research_id=research_id,
                                author_order=idx,
                                author_first_name=first_name,
                                author_middle_name=middle_name,
                                author_last_name=last_name,
                                author_suffix=''
                            )
                            db.session.add(new_author)

                # Add the research ID to the list of successfully added research IDs
                successfully_added_research_ids.append(research_id)
                
                # Commit all changes for this row if everything is successful
                db.session.commit()
                print(f"Successfully added research output {research_id} with all related data")

            except Exception as row_error:
                print(f"Error processing row {index + 1}: {str(row_error)}")
                db.session.rollback()
                return jsonify({"error": f"Error in row {index + 1}: {str(row_error)}"}), 500

        # Log the audit trail after all research outputs have been added successfully
        if successfully_added_research_ids:
            # Create a comma-separated string of all added research IDs
            research_ids_str = ", ".join(successfully_added_research_ids)
            
            # Log the audit trail
            auth_services.log_audit_trail(
                email=user.email,
                role=user.role.role_name,
                table_name='Research_Output',
                record_id=successfully_added_research_ids[0],  # Use the first ID as the main record
                operation='CREATE',  # Changed from UPDATE to CREATE since this is adding new papers
                action_desc=f"Added research papers: {research_ids_str}"
            )

        return jsonify({
            "message": "Papers uploaded successfully", 
            "research_ids": successfully_added_research_ids
        }), 201

    except Exception as e:
        print(f"Unexpected error in bulk_upload: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        db.session.close()

@paper.route('/get_template', methods=['GET'])
def get_paper_template():
    try:
        example_data = {
            'research_id': ['Required - Group Code (e.g., 2025CS002)'],
            'college_id': ['Required - College ID (e.g., CCIS)'],
            'program_id': ['Required - Program ID (e.g., CS)'],
            'title': ['Required - Full Research Title'],
            'abstract': ['Required - Research Abstract'],
            'school_year': ['Required - Format: YYYY-YYYY (e.g., 2023-2024)'],
            'term': ['Required - Values: 1, 2, or 3'],
            'research_type': ['Required - Research Type ID:\nCD - College-Driven\nCM - Commissioned\nFD - Faculty-Driven\nGF - Government-Funded\nMT - Mentored'],
            'authors': ['Required - Format: Lastname, Firstname MI.; Lastname2, Firstname2 MI2.'],
            'keywords': ['Required - Keywords separated by semicolon (e.g., AI; Machine Learning)'],
            'sdg': ['Optional - Format: SDG 1; SDG 2; SDG 3'],
            'adviser': ['Optional - Format: Lastname, Firstname MI.'],
            'panels': ['Optional - Format: Lastname, Firstname MI.; Lastname2, Firstname2 MI2.']
        }
        
        # Create DataFrame with example data
        df = pd.DataFrame(example_data)
        
        # Create a buffer to store the CSV
        output = StringIO()
        df.to_csv(output, index=False)
        
        # Create the response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=paper_upload_template.csv',
                'Content-Type': 'text/csv'
            }
        )
        
    except Exception as e:
        print(f"Error generating template: {str(e)}")
        return jsonify({"error": str(e)}), 500