from models import db
from models.base import BaseModel

class ArchUserEngagement(BaseModel):
    __tablename__ = 'arch_user_engagement'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True)
    user_id = db.Column(db.String(15), db.ForeignKey('account.user_id'), primary_key=True)
    timestamp = db.Column(db.TIMESTAMP, primary_key=True)
    view = db.Column(db.Integer)
    download = db.Column(db.Integer)