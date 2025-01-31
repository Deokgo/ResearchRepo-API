from models import db
from models.base import BaseModel

class ArchiveEA(BaseModel):
    __tablename__ = 'archive_ea'
    timestamp = db.Column(db.TIMESTAMP, primary_key=True)
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'))
    extended_abstract = db.Column(db.String(100))