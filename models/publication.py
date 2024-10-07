from . import db

class Publication(db.Model):
    __tablename__ = 'publications'
    publication_id = db.Column(db.String(16), primary_key=True)
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'))
    publication_name = db.Column(db.String(100))
    conference_id = db.Column(db.String(15), db.ForeignKey('conference.conference_id'))
    journal = db.Column(db.String(30))
    user_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))
    date_published = db.Column(db.Date)
