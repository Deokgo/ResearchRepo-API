from models import db
from models.base import BaseModel

class Keywords(BaseModel):
    __tablename__ = 'keywords'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True,unique=True)
    keyword = db.Column(db.String(100), primary_key=True)