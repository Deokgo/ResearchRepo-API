from models import db
from models.base import BaseModel

class College(BaseModel):
    __tablename__ = 'college'
    college_id = db.Column(db.String(6), primary_key=True, unique=True)
    college_name = db.Column(db.String(50))
    color_code = db.Column(db.String(10))