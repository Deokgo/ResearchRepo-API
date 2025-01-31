from models import db
from models.base  import BaseModel

class UserProfile(BaseModel):
    __tablename__ = 'user_profile'
    researcher_id = db.Column(db.String(15), db.ForeignKey('account.user_id'), primary_key=True,unique=True)
    college_id = db.Column(db.String(6), db.ForeignKey('college.college_id'))
    program_id = db.Column(db.String(5), db.ForeignKey('program.program_id'))
    first_name = db.Column(db.String(30))
    middle_name = db.Column(db.String(2))
    last_name = db.Column(db.String(30))
    suffix = db.Column(db.String(10))

    # Define relationships to College and Program
    college = db.relationship('College', backref=db.backref('user_profiles', lazy=True))
    program = db.relationship('Program', backref=db.backref('user_profiles', lazy=True))
