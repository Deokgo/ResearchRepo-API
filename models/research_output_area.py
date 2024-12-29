from . import db

class ResearchOutputArea(db.Model):
    __tablename__ = 'research_output_area'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True)
    research_area_id = db.Column(db.String(15), db.ForeignKey('research_area.research_area_id'), primary_key=True)