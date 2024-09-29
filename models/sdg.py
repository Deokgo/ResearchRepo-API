from . import db

class SDG(db.Model):
    __tablename__ = 'sdg'
    sdg_id = db.Column(db.String(6), primary_key=True)
    sdg_desc = db.Column(db.String(50))
