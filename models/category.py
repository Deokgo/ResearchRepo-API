from . import db

class Category(db.Model):
    __tablename__ = 'category'
    category_id = db.Column(db.String(15), primary_key=True)
    category_name = db.Column(db.String(50))