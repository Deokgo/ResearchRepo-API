from models import db
from models.base import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import relationship
from .user_profile import UserProfile
from datetime import datetime

class Account(BaseModel):
    __tablename__ = 'account'
    user_id = db.Column(db.String(15), primary_key=True, unique=True)
    email = db.Column(db.String(80))
    user_pw = db.Column(db.String(256))
    acc_status = db.Column(db.String(20), server_default=text("'ACTIVATED'"))
    role_id = db.Column(db.String(2), db.ForeignKey('roles.role_id'))
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    role = db.relationship('Role', backref=db.backref('accounts', lazy=True))

    # Define a relationship to UserProfile with cascade delete
    user_profile = relationship(
        'UserProfile', 
        backref=db.backref('account', lazy=True),
        uselist=False, 
        primaryjoin="Account.user_id == UserProfile.researcher_id",
        cascade="all, delete-orphan"
    )
    visitor = relationship(
        'Visitor', 
        backref=db.backref('account', lazy=True),
        uselist=False, 
        primaryjoin="Account.user_id == Visitor.visitor_id",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Account {self.user_id}>"
