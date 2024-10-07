from . import db

class Status(db.Model):
    __tablename__ = 'status'
    publication_id = db.Column(db.String(16), db.ForeignKey('publications.publication_id'), primary_key=True)
    status = db.Column(db.String(30))
    timestamp = db.Column(db.TIMESTAMP, primary_key=True)