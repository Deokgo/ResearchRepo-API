from . import db

class Panel(db.Model):
    __tablename__ = 'panels'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True)
    panel_id = db.Column(db.String(15), db.ForeignKey('account.user_id'), primary_key=True)