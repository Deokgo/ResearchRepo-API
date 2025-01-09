from . import db

class AggrUserEngagement(db.Model):
    __tablename__ = 'aggr_user_engagement'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True)
    day = db.Column(db.Date, primary_key=True)
    total_views = db.Column(db.Integer)
    total_downloads = db.Column(db.Integer)
    unique_views = db.Column(db.Integer)