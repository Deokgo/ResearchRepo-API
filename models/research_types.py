from . import db

class ResearchTypes(db.Model):
    __tablename__ = 'research_types'
    research_type_id = db.Column(db.String(6), primary_key=True)
    research_type_name = db.Column(db.String(50))