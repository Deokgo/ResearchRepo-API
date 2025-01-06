from . import db

class ResearchOutput(db.Model):
    __tablename__ = 'research_outputs'
    research_id = db.Column(db.String(15), primary_key=True)
    college_id = db.Column(db.String(6), db.ForeignKey('college.college_id'))
    program_id = db.Column(db.String(5), db.ForeignKey('program.program_id'))
    title = db.Column(db.String(1000))
    abstract = db.Column(db.String(5000))
    full_manuscript = db.Column(db.String(100))
    extended_abstract = db.Column(db.String(100))
    user_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))
    date_approved = db.Column(db.Date)
    adviser_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))
    research_type_id = db.Column(db.String(6), db.ForeignKey('research_types.research_type_id'))
    view_count = db.Column(db.Integer)
    download_count = db.Column(db.Integer)
    date_uploaded = db.Column(db.DateTime, nullable=False)
    unique_views = db.Column(db.Integer)
    research_areas = db.relationship(
        'ResearchArea',
        secondary='research_output_area',
        lazy='joined'
    )