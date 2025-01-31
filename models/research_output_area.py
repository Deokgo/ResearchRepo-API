from models import db
from models.base import BaseModel

class ResearchOutputArea(BaseModel):
    __tablename__ = 'research_output_area'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True,unique=True)
    research_area_id = db.Column(db.String(6), db.ForeignKey('research_area.research_area_id'), primary_key=True)