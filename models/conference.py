from . import db

class Conference(db.Model):
    __tablename__ = 'conference'
    conference_id = db.Column(db.String(15), primary_key=True)
    conference_title = db.Column(db.String(100))
    location = db.Column(db.String(100))
    country = db.Column(db.String(30))
    conference_date = db.Column(db.Date)
    date_added = db.Column(db.TIMESTAMP)
    date_modified = db.Column(db.TIMESTAMP)