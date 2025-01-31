from flask_sqlalchemy import SQLAlchemy
from models import db


class BaseModel(db.Model):
    """Base model to inherit common properties."""
    __abstract__ = True
    
    @classmethod
    def query_all(cls):
        """Retrieve all records from the table."""
        return cls.query.all()

    @classmethod
    def query_by(cls, **kwargs):
        """Retrieve records based on filter criteria."""
        return cls.query.filter_by(**kwargs).all()

    @classmethod
    def query_first(cls, **kwargs):
        """Retrieve the first matching record."""
        return cls.query.filter_by(**kwargs).first()

    @classmethod
    def query_filter(cls, *filters):
        """Retrieve records using custom filters."""
        return cls.query.filter(*filters).all()

    @classmethod
    def query_paginate(cls, page=1, per_page=10):
        """Retrieve paginated results."""
        return cls.query.paginate(page=page, per_page=per_page, error_out=False)

    @classmethod
    def create(cls, **kwargs):
        """Create and save a new record."""
        instance = cls(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance

    @classmethod
    def update(cls, record_id, **kwargs):
        """Update a record by ID."""
        record = cls.query.get(record_id)
        if record:
            for key, value in kwargs.items():
                setattr(record, key, value)
            db.session.commit()
        return record

    @classmethod
    def delete(cls, record_id):
        """Delete a record by ID."""
        record = cls.query.get(record_id)
        if record:
            db.session.delete(record)
            db.session.commit()
        return record
