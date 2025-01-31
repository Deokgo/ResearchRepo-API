from models import db
from models.base import BaseModel

class PublicationFormat(BaseModel):
    __tablename__ = 'publication_format'
    pub_format_id = db.Column(db.String(6), primary_key=True, unique=True)
    pub_format_name = db.Column(db.String(50))