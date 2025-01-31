from models import db
from models.base import BaseModel

class Role(BaseModel):
    __tablename__ = 'roles'
    role_id = db.Column(db.String(2), primary_key=True, unique=True)
    role_name = db.Column(db.String(50))
