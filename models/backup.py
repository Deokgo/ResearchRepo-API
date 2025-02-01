from models import db
from models.base import BaseModel

class Backup(BaseModel):
    __tablename__ = 'backup'
    backup_id = db.Column(db.String(23), primary_key=True,unique=True)
    backup_type = db.Column(db.String(20), nullable=False)
    backup_date = db.Column(db.DateTime, nullable=False)
    database_backup_location = db.Column(db.String(255), nullable=False)
    files_backup_location = db.Column(db.String(255), nullable=False)
    total_size = db.Column(db.BigInteger)
    parent_backup_id = db.Column(db.String(50), db.ForeignKey('backup.backup_id'), nullable=True)
    wal_lsn = db.Column(db.String(50), nullable=True)



