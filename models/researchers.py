from . import db

class Researcher(db.Model):
    __tablename__ = 'researchers'
    researcher_id = db.Column(db.String(15), db.ForeignKey('account.user_id'), primary_key=True)
    college_id = db.Column(db.String(6), db.ForeignKey('college.college_id'))
    program_id = db.Column(db.String(5), db.ForeignKey('program.program_id'))
    first_name = db.Column(db.String(30))
    middle_name = db.Column(db.String(2))
    last_name = db.Column(db.String(30))
    suffix = db.Column(db.String(10))
