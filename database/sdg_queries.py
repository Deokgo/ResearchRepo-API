from config import Session
from sqlalchemy import text
import numpy as np
import pandas as pd



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

def get_research_percentage(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_research_percentage function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings)
    :param status_filter: List of status filters (list of strings)
    :param college_filter: Optional college filter (list of strings)
    :param program_filter: Optional program filter (list of strings)
    :return: List of dictionaries containing research percentage per SDG
    """
    session = Session()
    try:
        # Prepare the SQL query
        query = text(""" 
            SELECT * FROM get_research_percentage(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
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


def get_research_type_distribution(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_research_type_distribution function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings)
    :param status_filter: List of status filters (list of strings)
    :param college_filter: Optional college filter (list of strings)
    :param program_filter: Optional program filter (list of strings)
    :return: List of dictionaries containing research type distribution
    """
    session = Session()
    try:
        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_research_type_distribution(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
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

def get_research_status_distribution(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_research_status_distribution function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings)
    :param status_filter: List of status filters (list of strings)
    :param college_filter: Optional college filter (list of strings)
    :param program_filter: Optional program filter (list of strings)
    :return: List of dictionaries containing SDG status distribution
    """
    # Database connection setup (Modify with actual database credentials)
    session = Session()
    
    try:
        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_research_status_distribution(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
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

def get_geographical_distribution(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_geographical_distribution function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings, optional)
    :param status_filter: List of status filters (list of strings, optional)
    :param college_filter: List of college filters (list of strings, optional)
    :param program_filter: List of program filters (list of strings, optional)
    :return: List of dictionaries containing research count per city and country
    """
    session = Session()
    try:
        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_geographical_distribution(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
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


def get_conference_participation(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_conference_participation function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings, optional)
    :param status_filter: List of status filters (list of strings, optional)
    :param college_filter: List of college filters (list of strings, optional)
    :param program_filter: List of program filters (list of strings, optional)
    :return: List of dictionaries containing conference participation count per SDG per year
    """
    session = Session()
    try:
        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_conference_participation(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
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

def get_local_vs_foreign_participation(start_year, end_year, country_name, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_local_vs_foreign_participation function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param country_name: Name of the country considered 'Local' (string)
    :param sdg_filter: List of SDG filters (list of strings, optional)
    :param status_filter: List of status filters (list of strings, optional)
    :param college_filter: List of college filters (list of strings, optional)
    :param program_filter: List of program filters (list of strings, optional)
    :return: List of dictionaries containing Local vs. Foreign research counts
    """
    session = Session()
    try:
        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_local_vs_foreign_participation(
                :start_year, :end_year, :country_name, :sdg_filter, :status_filter, :college_filter, :program_filter
            )
        """)

        # Execute the query with parameters
        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'country_name': country_name,
            'sdg_filter': sdg_filter if sdg_filter else None,
            'status_filter': status_filter if status_filter else None,
            'college_filter': college_filter if college_filter else None,
            'program_filter': program_filter if program_filter else None
        })

        # Process the result into a list of dictionaries
        return [dict(row) for row in result.mappings()]
    finally:
        session.close()

def get_research_with_keywords(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_research_with_keywords function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings, optional)
    :param status_filter: List of status filters (list of strings, optional)
    :param college_filter: List of college filters (list of strings, optional)
    :param program_filter: List of program filters (list of strings, optional)
    :return: List of dictionaries containing research ID, title, abstract, and keywords
    """
    session = Session()
    try:
        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_research_with_keywords(
                :start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter
            )
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
def get_research_area_data(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_research_area_sdg function in PostgreSQL and retrieves research data.
    """
    session = Session()
    try:
        # Ensure parameters are converted to native Python types
        def convert_to_python_type(value):
            if isinstance(value, np.ndarray):
                return value.item() if value.size == 1 else value.tolist()  # Extract scalar if array has only one element
            return value

        # Convert start_year and end_year to integers safely
        start_year = convert_to_python_type(start_year)
        end_year = convert_to_python_type(end_year)

        if isinstance(start_year, list):  # Extract first element if it's a list
            start_year = start_year[0]
        if isinstance(end_year, list):
            end_year = end_year[0]

        start_year = int(start_year)  # Ensure final type is integer
        end_year = int(end_year)

        params = {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': convert_to_python_type(sdg_filter) if sdg_filter else None,
            'status_filter': convert_to_python_type(status_filter) if status_filter else None,
            'college_filter': convert_to_python_type(college_filter) if college_filter else None,
            'program_filter': convert_to_python_type(program_filter) if program_filter else None
        }

        print(f"Query Params: {params}")  # Debugging line to check data types

        query = text("""
            SELECT * FROM get_research_area_sdg(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
        """)

        result = session.execute(query, params)
        return pd.DataFrame(result.mappings())

    finally:
        session.close()