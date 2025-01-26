from . import db
import datetime
from services import auth_services

class Backup(db.Model):
    __tablename__ = 'backup'
    backup_id = db.Column(db.String(18), primary_key=True)
    backup_date = db.Column(db.TIMESTAMP)
    database_backup_location = db.Column(db.String(255))
    files_backup_location = db.Column(db.String(255))
    total_size = db.Column(db.Integer)



