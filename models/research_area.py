from . import db

class ResearchArea(db.Model):
    __tablename__ = 'research_area'
    research_area_id = db.Column(db.String(15), primary_key=True)
    research_area_name = db.Column(db.String(50))