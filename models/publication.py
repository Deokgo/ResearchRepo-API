from . import db

class Publication(db.Model):
    __tablename__ = 'publications'
    publication_id = db.Column(db.String(16), primary_key=True)
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'))
    publication_format = db.Column(db.String(20))
    conference_id = db.Column(db.String(15), db.ForeignKey('conference.conference_id'))
    publisher_id = db.Column(db.String(16), db.ForeignKey('publisher.publisher_id'))
    publication_name = db.Column(db.String(100))
    status = db.Column(db.String(20))
    date_submitted = db.Column(db.TIMESTAMP)
    date_modified = db.Column(db.TIMESTAMP)
    user_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))
