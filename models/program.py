from . import db

class Program(db.Model):
    __tablename__ = 'program'
    program_id = db.Column(db.String(5), primary_key=True)
    college_id = db.Column(db.String(6), db.ForeignKey('college.college_id'))
    program_name = db.Column(db.String(200))
    college = db.relationship('College', backref=db.backref('programs', lazy=True))
