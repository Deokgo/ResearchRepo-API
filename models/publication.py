from models import db
from models.base import BaseModel

class Publication(BaseModel):
    __tablename__ = 'publications'
    publication_id = db.Column(db.String(16), primary_key=True, unique=True)
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'))
    publication_name = db.Column(db.String(100))
    conference_id = db.Column(db.String(15), db.ForeignKey('conference.conference_id'))
    pub_format_id = db.Column(db.String(6), db.ForeignKey('publication_format.pub_format_id'))
    user_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))
    date_published = db.Column(db.Date)
    scopus = db.Column(db.String(30))
    date_submitted = db.Column(db.Date)
    publication_paper = db.Column(db.String(100))