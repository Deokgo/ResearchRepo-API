from . import db

class AggrUserEngagement(db.Model):
    __tablename__ = 'aggr_user_engagement'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'))
    day = db.Column(db.Date)
    total_views = db.Column(db.Integer)
    total_downloads = db.Column(db.Integer)
    unique_views = db.Column(db.Integer)
