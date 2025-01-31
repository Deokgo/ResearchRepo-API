from models import db
from models.base import BaseModel

class AuditTrail(BaseModel):
    __tablename__ = 'audit_trail'
    audit_id = db.Column(db.String(18), primary_key=True)
    user_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.String(23))
    operation = db.Column(db.String(50))
    change_datetime = db.Column(db.TIMESTAMP)
    action_desc = db.Column(db.String(10000))



