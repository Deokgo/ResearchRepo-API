from . import db

class ArchiveEA(db.Model):
    __tablename__ = 'archive_ea'
    timestamp = db.Column(db.TIMESTAMP, primary_key=True)
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'))
    extended_abstract = db.Column(db.String(100))