from flask import Blueprint, request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from models import db, Publication , ResearchOutput, Status
from services.auth_services import formatting_id, log_audit_trail
from datetime import datetime


track = Blueprint('track', __name__)

@track.route('/research_status/<research_id>', methods=['GET', 'POST'])
def get_research_status(research_id=None):
    if request.method == 'GET':
        try:
            # Fetch data based on research_id
            query = (
                db.session.query(
                    ResearchOutput.research_id,
                    Publication.publication_id,
                    Status.status
                )
                .join(Publication, Publication.research_id == ResearchOutput.research_id)
                .join(Status, Status.publication_id == Publication.publication_id)
                .filter(ResearchOutput.research_id == research_id)
            )

            result = query.all()

            # Process results into a JSON-serializable format
            data = [
                {
                    'research_id': row.research_id,
                    'publication_id': row.publication_id,
                    'status': row.status
                }
                for row in result
            ]

            if not data:
                return jsonify({"error": f"No data found for research_id {research_id}"}), 404
            
            return jsonify({'dataset': data}), 200

        except SQLAlchemyError as e:
            db.session.rollback()  # Rollback in case of an error
            return jsonify({"error": "Database error occurred", "details": str(e)}), 500

    elif request.method == 'POST':
        try:
            # Retrieve data from request body (JSON)
            data = request.get_json()
            publication_id = data.get('publication_id')
            status_value = data.get('status')

            # Validate input data
            if not all([publication_id, status_value]):
                return jsonify({"error": "publication_id and status are required"}), 400

            # Create a new Status entry
            new_status = Status(
                status_id = formatting_id("ST",Status,'status_id'),
                publication_id=publication_id,
                status=status_value,
                timestamp=datetime.now() 
                
            )

            # Add and commit the new entry to the database
            db.session.add(new_status)
            db.session.commit()
            # send email asynchronously
            # log audit trail here asynchronously

            return jsonify({"message": "Status entry created successfully"}), 201

        except SQLAlchemyError as e:
            db.session.rollback()  # Rollback in case of an error
            return jsonify({"error": "Database error occurred", "details": str(e)}), 500
