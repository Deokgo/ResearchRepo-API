from . import db

class Keywords(db.Model):
    __tablename__ = 'keywords'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True)
    keyword = db.Column(db.String(100))