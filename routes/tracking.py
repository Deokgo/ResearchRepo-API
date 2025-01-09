from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from models import db, Publication , ResearchOutput, Status, Conference, PublicationFormat
from services.auth_services import formatting_id, log_audit_trail
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from services.tracking_services import insert_status
from sqlalchemy import func, desc, nulls_last
from services.mail import send_notification_email

track = Blueprint('track', __name__)

@track.route('/research_status', methods=['GET'])
@track.route('/research_status/<research_id>', methods=['GET', 'POST'])
@jwt_required()
def get_research_status(research_id=None):
    if request.method == 'GET':
        try:
            # Build the query
            query = (
                db.session.query(
                    ResearchOutput.research_id,
                    Publication.publication_id,
                    Status.status,
                    Status.timestamp,
                    ResearchOutput.date_approved
                )
                .outerjoin(Publication, Publication.research_id == ResearchOutput.research_id)
                .outerjoin(Status, Status.publication_id == Publication.publication_id)
                .order_by(Status.timestamp)  # Always order by most recent timestamp
            )

            # Apply filter if research_id is provided
            if research_id:
                query = query.filter(ResearchOutput.research_id == research_id)

            # Fetch results
            result = query.all()

            # Process results into a JSON-serializable format
            data = [
                {
                    'research_id':row.research_id,
                    'status': row.status if row.status else "READY",
                    'time': row.timestamp.strftime('%B %d, %Y') if row.timestamp else row.date_approved.strftime('%B %d, %Y') 
                }
                for row in result
            ]

            # Return appropriate response based on query results
            if not data:
                return jsonify({
                    "message": "No records found",
                    "research_id": research_id,
                    "dataset": []  # Always return an empty array in the 'dataset' key
                }), 404

            return jsonify(data), 200

        except SQLAlchemyError as e:
            db.session.rollback()  # Rollback in case of an error
            return jsonify({
                "error": "Database error occurred",
                "details": str(e),
                "dataset": []  # Ensure 'dataset' is always an array, even on error
            }), 500

    elif request.method == 'POST':
        try:
            new_status = ""
            # Retrieve data from request body (JSON)
            publication = Publication.query.filter(Publication.research_id == research_id).first()

            if publication is None:
                return jsonify({"message": "Fill in the forms first"}), 400
            
            # Retrieve the latest status
            current_status = Status.query.filter(Status.publication_id == publication.publication_id).order_by(desc(Status.timestamp)).first()

            # Handle case where current_status is None
            if current_status is None:
                # If no status exists, set the initial status to "SUBMITTED"
                new_status = "SUBMITTED"
                # Call the function to insert the new status for the publication
                changed_status, error = insert_status(publication.publication_id, new_status)
            else:
                # If there is a current status, handle status transitions
                if current_status.status == "PULLOUT":
                    return jsonify({"message": "Paper already pulled out"}), 400
                elif current_status.status == "SUBMITTED":
                    new_status = "ACCEPTED"
                elif current_status.status == "ACCEPTED":
                    new_status = "PUBLISHED"
                elif current_status.status == "PUBLISHED":
                    return jsonify({"message": "Paper already published"}), 400

                # Call the function to insert the new status
                changed_status, error = insert_status(current_status.publication_id, new_status)

            # If there was an error inserting the status, handle it
            if error:
                return jsonify({"error": "Database error occurred", "details": error}), 500

            # Send email asynchronously (optional)
            send_notification_email("NEW PUBLICATION STATUS UPDATE",
                                f'Research paper by {research_id} has been updated to {changed_status.status}.')
            
            # Log audit trail here asynchronously (optional)
            # Get the current user's identity
            user_id = get_jwt_identity()
            log_audit_trail(
                user_id=user_id,
                table_name='Publication and Status',
                record_id=research_id,
                operation='UPDATE',
                action_desc='Updated research output status')

            return jsonify({"message": "Status entry created successfully", "status_id": changed_status.status_id}), 201

        except SQLAlchemyError as e:
            db.session.rollback()  # Rollback in case of an error
            return jsonify({"error": "Database error occurred", "details": str(e)}), 500


        
@track.route('next_status/<research_id>',methods=['GET'])
@jwt_required()
def get_next_status(research_id):
    new_status=""
    # Retrieve data from request body (JSON)
    try:

        publication = Publication.query.filter(Publication.research_id==research_id).first()

        if publication is None:
            new_status="SUBMITTED"
        
        current_status = Status.query.filter(Status.publication_id == publication.publication_id).order_by(desc(Status.timestamp)).first()
        if current_status.status == "PULLOUT":
            new_status="PULLOUT"
        elif current_status.status is None:
            new_status="SUBMITTED"
        elif current_status.status == "SUBMITTED":
            new_status="ACCEPTED"
        elif current_status.status == "ACCEPTED":
            new_status="PUBLISHED"
        elif current_status.status == "PUBLISHED":
            new_status="COMPLETED"

        return jsonify(new_status), 200
    except Exception as e:
        
        new_status="SUBMITTED"
        db.session.rollback()  # Rollback in case of error
        return jsonify(new_status), 200



@track.route('research_status/pullout/<research_id>',methods=['POST'])    
@jwt_required()
def pullout_paper(research_id):
    publication = Publication.query.filter(Publication.research_id==research_id).first()
    if publication is None:
        return jsonify({"message": "No publication."}), 400
    
    current_status = Status.query.filter(Status.publication_id == publication.publication_id).order_by(desc(Status.timestamp)).first()
    if current_status.status is None:
        return jsonify({"message": "No submission occured."}), 400
    elif current_status.status == "PUBLISHED":
        return jsonify({"message": "Paper already published"}), 400
    else:
        changed_status, error = insert_status(current_status.publication_id, "PULLOUT")
        if error:
                return jsonify({"error": "Database error occurred", "details": error}), 500

            # Send email asynchronously (optional)
        send_notification_email("NOTIFICATION",
                                f'Research paper by {research_id} has been pulled out.')

        # Log audit trail here asynchronously (optional)
        # Get the current user's identity
        user_id = get_jwt_identity()
        log_audit_trail(
                user_id=user_id,
                table_name='Publication and Status',
                record_id=research_id,
                operation='UPDATE',
                action_desc='Updated research output status')
            
        return jsonify({"message": "Status entry created successfully", "status_id": changed_status.status_id}), 201


@track.route('/publication/<research_id>',methods=['GET','POST','PUT'])
@jwt_required()
def publication_papers(research_id=None):
    if request.method == 'GET':
    
        query = (db.session.query(
            PublicationFormat.pub_format_name,
            Conference.conference_title,
            Conference.conference_venue,
            Conference.conference_date,
            Publication.publication_id,
            Publication.publication_name,        
            Publication.date_published,
            Publication.scopus

        )).join(ResearchOutput,Publication.research_id==ResearchOutput.research_id)\
        .outerjoin(Conference, Conference.conference_id==Publication.conference_id)\
        .outerjoin(PublicationFormat, PublicationFormat.pub_format_id==Publication.pub_format_id)\
        .filter(ResearchOutput.research_id == research_id)

        result=query.all()

        data = [
            {
                'publication_id': row.publication_id,
                'journal': row.pub_format_name,
                'conference_title': row.conference_title,
                'city': (
                    row.conference_venue.split(',', 1)[0].strip() 
                    if row.conference_venue else None
                    ),
                'country': (
                    row.conference_venue.split(',', 1)[1].strip() 
                    if row.conference_venue and ',' in row.conference_venue else None
                    ),
                'conference_date': (
                    row.conference_date.strftime("%B %d, %Y") 
                    if row.conference_date else None
                ),
                'publication_name': row.publication_name,
                'date_published': (
                    row.date_published.strftime("%B %d, %Y") 
                    if row.date_published else None
                ),
                'scopus': row.scopus
            }
            for row in result
        ]
         
        return jsonify({"dataset": [dict(row) for row in data]}), 200
    elif request.method == 'POST':
        # Get data from form submission
        try:
            # Check if ResearchOutput exists
            research_output = db.session.query(ResearchOutput).filter(ResearchOutput.research_id == research_id).first()

            if not research_output:
                return jsonify({'message': 'ResearchOutput not found'}), 404
            
            publication = db.session.query(Publication).filter(Publication.research_id == research_id).first() is None

            if not publication:
                return jsonify({'message': 'Publication Details already existing'}), 400

            # Check if conference exists or create a new one
            conference_title = request.form.get('conference_title')
            conference = db.session.query(Conference).filter(Conference.conference_title.ilike(conference_title)).first()

            if not conference:
                # Generate a unique conference_id
                cf_id = formatting_id("CF", Conference, 'conference_id')

                # Parse conference_date into a datetime object
                conference_date = (
                    datetime.strptime(request.form.get('conference_date'), '%Y-%m-%d') 
                    if request.form.get('conference_date') else None
                )

                # Create a new Conference
                conference = Conference(
                    conference_id=cf_id,
                    conference_title=request.form.get('conference_title'),
                    conference_venue=request.form.get('city') + ", " + request.form.get('country'),
                    conference_date=conference_date
                )
                db.session.add(conference)
            else:
                cf_id = conference.conference_id  # Use existing conference_id
            if request.form.get('journal')=='journal':
                cf_id=None

            # Parse date_published into a datetime object
            date_published = (
                datetime.strptime(request.form.get('date_published'), '%Y-%m-%d') 
                if request.form.get('date_published') else None
            )

            # Generate a unique publication_id
            publication_id = formatting_id("PBC", Publication, 'publication_id')

            # Create Publication
            new_publication = Publication(
                publication_id=publication_id,
                research_id=research_id,
                publication_name=request.form.get('publication_name'),
                conference_id=cf_id,
                journal=request.form.get('journal'),
                date_published=date_published,
                scopus=request.form.get('scopus')
            )
            db.session.add(new_publication)
            db.session.commit()

            # Audit trail logging
            # Get the current user's identity
            user_id = get_jwt_identity()
            log_audit_trail(
                user_id=user_id,
                table_name='Publication and Conference',
                record_id=new_publication.publication_id,
                operation='CREATE',
                action_desc='Added Publication and associated Conference details')

            return jsonify({'message': 'Publication and Conference created successfully'}), 201

        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            return jsonify({'error': str(e)}), 400
    if request.method == 'PUT':
        # Handle PUT request - Update an existing publication entry
        data = request.form  # Use form-data instead of JSON
        print("Form Data:", dict(request.form))

        try:
            # Check if ResearchOutput exists
            research_output = db.session.query(ResearchOutput).filter(ResearchOutput.research_id == research_id).first()
            
            if research_output:
                # Now update the Publication
                publication = db.session.query(Publication).filter(Publication.research_id == research_id).first()
                print("Publication Content:", vars(publication))

                if publication:
                
                    # Handle journal or proceeding logic
                    if data.get('journal') == "journal":
                        publication.conference_id = None
                    elif data.get('journal') == "proceeding":
                        print("proceeding!!")
                        conferences = db.session.query(Conference).filter(Conference.conference_title == data.get('conference_title')).first()
                        print("Conferences:", vars(conferences))
                        # Create a new conference if needed
                        if not conferences:
                            print("new cf!!")
                            cf_id = formatting_id("CF", Conference, 'conference_id')
                            conference = Conference(
                                conference_title=data.get('conference_title'),
                                conference_venue=data.get('conference_venue'),
                                conference_date=data.get('conference_date'),
                            )
                            db.session.add(conference)
                        else:
                            publication.conference_id = conferences.conference_id

                     # Update publication fields
                    publication.journal = data.get('journal', publication.journal)
                    publication.publication_name = data.get('publication_name', publication.publication_name)
                    publication.date_published = parse_date(data.get('date_published')) or publication.date_published
                    publication.scopus = data.get('scopus', publication.scopus)
                    db.session.commit()
                    publication = db.session.query(Publication).filter(Publication.research_id == research_id).first()
                    print("Publication UPDATED Content:", vars(publication))

                    # Log audit trail here asynchronously (optional)
                    # Get the current user's identity
                    user_id = get_jwt_identity()
                    log_audit_trail(
                            user_id=user_id,
                            table_name='Publication and Status',
                            record_id=research_id,
                            operation='UPDATE',
                            action_desc='Updated research output publication data')
                    
                    return jsonify({'message': 'Publication updated successfully'}), 200
                else:
                    return jsonify({'message': 'Publication not found'}), 404
            else:
                return jsonify({'message': 'ResearchOutput not found'}), 404
        
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            return jsonify({'error': str(e)}), 400

from datetime import datetime
def parse_date(date_string):
    """Parse a date string or return None if invalid."""
    try:
        if date_string:  # Check if the value is not None or empty
            return datetime.strptime(date_string, "%Y-%m-%d").date()
        return None
    except (ValueError, TypeError):
        return None
    
@track.route('/published_paper/<research_id>', methods=['GET'])
def check_uploaded_paper(research_id=None):
    if research_id:
        # Query the database for the research output with the given ID
        query = ResearchOutput.query.filter_by(research_id=research_id).first()
        
        # Check if the research output exists
        if query is None:
            return jsonify({"message": "No research output exists"}), 404
        
        # Check if the extended abstract is uploaded
        if query.extended_abstract is None:
            return jsonify({"message": "No extended abstract uploaded. Please upload one."}), 400  # Bad request
        
        # Return success if the research output and extended abstract are found
        return jsonify({
            "message": "Research output and extended abstract found"
        }), 200
    
    # Return a message if research_id is not provided
    return jsonify({"message": "No research ID provided"}), 400

        

