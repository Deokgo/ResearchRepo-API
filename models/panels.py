from models import db
from models.base import BaseModel

class Panel(BaseModel):
    __tablename__ = 'panels'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True,unique=True)
    panel_id = db.Column(db.String(15), db.ForeignKey('account.user_id'), primary_key=True)