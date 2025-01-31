from models import db
from models.base import BaseModel

class Status(BaseModel):
    __tablename__ = 'status'
    status_id = db.Column(db.String(15), primary_key=True, unique=True) # ST-YYYYMMDD-XXX
    publication_id = db.Column(db.String(16), db.ForeignKey('publications.publication_id'))
    status = db.Column(db.String(30))
    timestamp = db.Column(db.TIMESTAMP)