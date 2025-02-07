from config import Session
from sqlalchemy import text

import numpy as np

def get_filtered_data_with_term(selected_colleges=None, selected_status=None, selected_years=None, selected_terms=None):
    """
    Fetches filtered dataset based on the given parameters.
    """
    session = Session()
    try:
        query = text("""
            SELECT * FROM get_filtered_data_with_term(:selected_colleges, :selected_status, :selected_years, :selected_terms)
        """)

        result = session.execute(query, {
            'selected_colleges': selected_colleges,
            'selected_status': selected_status,
            'selected_years': selected_years,
            'selected_terms': selected_terms
        })

        filtered_data_with_term = [dict(row) for row in result.mappings()]
        return filtered_data_with_term
    finally:
        session.close()