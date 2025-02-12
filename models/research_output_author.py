from models import db
from models.base import BaseModel

class ResearchOutputAuthor(BaseModel):
    __tablename__ = 'research_output_authors'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True, unique=True)
    author_order = db.Column(db.Integer)
    author_first_name = db.Column(db.String(30))
    author_middle_name = db.Column(db.String(2))
    author_last_name = db.Column(db.String(30))
    author_suffix = db.Column(db.String(10))
