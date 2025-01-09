from models import db

class ResearchDataFetcher:
    def __init__(self, model):
        self.model = model

    def get_data_from_model(self):
        # Querying the database using SQLAlchemy's session
        data = db.session.query(self.model).all()  # Fetches all records
        return data


def get_field_attribute(model, field):
    """
    Dynamically gets the distinct field attribute from a given model.

    :param model: SQLAlchemy model class.
    :param field: The name of the field (column) to retrieve.
    :return: A list of distinct field values if found, else None.
    """
    field_attribute = getattr(model, field, None)
    
    if field_attribute is None:
        return None

    # Query the database for the specified field with distinct values
    results = db.session.query(field_attribute).distinct().all()

    # If no results found
    if not results:
        return None

    # Extract the distinct values from the result tuple
    field_values = [result[0] for result in results]
    return field_values