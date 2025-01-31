from models import db
from models.base import BaseModel

class Conference(BaseModel):
    __tablename__ = 'conference'
    conference_id = db.Column(db.String(15), primary_key=True,unique=True)
    conference_title = db.Column(db.String(100))
    conference_venue = db.Column(db.String(100))
    conference_date = db.Column(db.Date)