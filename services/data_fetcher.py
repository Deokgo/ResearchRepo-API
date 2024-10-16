from models import db

class ResearchDataFetcher:
    def __init__(self, model):
        self.model = model

    def get_data_from_model(self):
        # Querying the database using SQLAlchemy's session
        data = db.session.query(self.model).all()  # Fetches all records
        return data