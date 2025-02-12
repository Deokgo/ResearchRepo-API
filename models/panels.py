from models import db
from models.base import BaseModel

class Panel(BaseModel):
    __tablename__ = 'panels'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True,unique=True)
    panel_first_name = db.Column(db.String(30))
    panel_middle_name = db.Column(db.String(2))
    panel_last_name = db.Column(db.String(30))
    panel_suffix = db.Column(db.String(10))