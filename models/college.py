from . import db

class College(db.Model):
    __tablename__ = 'college'
    college_id = db.Column(db.String(6), primary_key=True)
    college_name = db.Column(db.String(50))
