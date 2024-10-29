from flask import Blueprint, request, jsonify
from models import db, ResearchOutput, SDG, Keywords, Publication, ResearchOutputAuthor, Panel, UserProfile
from services import auth_services

paper = Blueprint('paper', __name__)

@paper.route('/add_paper', methods=['POST'])
def add_paper():
    #extract data from the request JSON
    data = request.get_json()
    print("Request data:", data)
    
    #validate required fields
    required_fields = ['research_id', 'college_id', 'program_id', 'title', 'abstract', 'date_approved', 'research_type', 'sdg']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
    
    try:
        #create a new ResearchOutput record
        new_paper = ResearchOutput(
            research_id=data['research_id'],
            college_id=data['college_id'],
            program_id=data['program_id'],
            title=data['title'],
            abstract=data['abstract'],
            date_approved=data['date_approved'],
            research_type=data['research_type']
        )

        #create a new SDG record associated with the research_id
        new_paper_sdg = SDG(
            research_id=data['research_id'],
            sdg=data['sdg']
        )
        
        #add to session and commit
        db.session.add(new_paper)
        db.session.add(new_paper_sdg)
        db.session.commit()

        """
        # Audit Log
        auth_services.log_audit_trail(
            user_id=user.user_id,
            table_name='Account',
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