from models import db
from models.base import BaseModel

class SDG(BaseModel):
    __tablename__ = 'sdg'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True, unique=True)
    sdg = db.Column(db.String(50))