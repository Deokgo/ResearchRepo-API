from models import db
from models.base import BaseModel

class ResearchTypes(BaseModel):
    __tablename__ = 'research_types'
    research_type_id = db.Column(db.String(6), primary_key=True, unique=True)
    research_type_name = db.Column(db.String(50))