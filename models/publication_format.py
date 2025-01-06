from . import db

class PublicationFormat(db.Model):
    __tablename__ = 'publication_format'
    pub_format_id = db.Column(db.String(6), primary_key=True)
    pub_format_name = db.Column(db.String(50))