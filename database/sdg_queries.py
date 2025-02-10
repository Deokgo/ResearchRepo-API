from config import Session
from sqlalchemy import text

import numpy as np


def get_research_count(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_research_count function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings)
    :param status_filter: List of status filters (list of strings)
    :param college_filter: Optional college filter (list of strings)
    :param program_filter: Optional program filter (list of strings)
    :return: List of dictionaries containing research count per SDG
    """
    session = Session()
    try:
        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_research_count(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
        """)

        # Execute the query with parameters
        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': sdg_filter if sdg_filter else None,
            'status_filter': status_filter if status_filter else None,
            'college_filter': college_filter if college_filter else None,
            'program_filter': program_filter if program_filter else None
        })

        # Process the result into a list of dictionaries
        return [dict(row) for row in result.mappings()]
    finally:
        session.close()