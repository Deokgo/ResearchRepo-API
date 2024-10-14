from . import db

class SDG(db.Model):
    __tablename__ = 'sdg'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True)
    sdg = db.Column(db.String(50))