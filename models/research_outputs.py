from models import db
from models.base import BaseModel

class ResearchOutput(BaseModel):
    __tablename__ = 'research_outputs'
    research_id = db.Column(db.String(15), primary_key=True, unique=True)
    college_id = db.Column(db.String(6), db.ForeignKey('college.college_id'))
    program_id = db.Column(db.String(5), db.ForeignKey('program.program_id'))
    title = db.Column(db.String(1000))
    abstract = db.Column(db.String(5000))
    full_manuscript = db.Column(db.String(100))
    extended_abstract = db.Column(db.String(100))
    user_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))
    adviser_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))
    research_type_id = db.Column(db.String(6), db.ForeignKey('research_types.research_type_id'))
    date_uploaded = db.Column(db.DateTime, nullable=False)
    research_areas = db.relationship(
        'ResearchArea',
        secondary='research_output_area',
        lazy='joined'
    )
    school_year = db.Column(db.String(4))
    term = db.Column(db.String(1))