from . import db

class ResearchCategory(db.Model):
    __tablename__ = 'research_category'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True)
    category_id = db.Column(db.String(15), db.ForeignKey('category.category_id'), primary_key=True)