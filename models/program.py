from models import db
from models.base import BaseModel

class Program(BaseModel):
    __tablename__ = 'program'
    program_id = db.Column(db.String(5), primary_key=True, unique=True)
    college_id = db.Column(db.String(6), db.ForeignKey('college.college_id'))
    program_name = db.Column(db.String(200))
    college = db.relationship('College', backref=db.backref('programs', lazy=True))
