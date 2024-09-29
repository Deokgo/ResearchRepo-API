from . import db

class Publisher(db.Model):
    __tablename__ = 'publisher'
    publisher_id = db.Column(db.String(16), primary_key=True)
    publisher_name = db.Column(db.String(70))
