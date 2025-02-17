from config import Session
from sqlalchemy import text
import numpy as np
import pandas as pd



def get_research_count(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    session = Session()
    try:
        # Convert numpy arrays to lists if needed
        if isinstance(status_filter, np.ndarray):
            status_filter = status_filter.tolist()
        if isinstance(college_filter, np.ndarray):
            college_filter = college_filter.tolist()

        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_research_count(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
        """)

        # Execute the query with parameters
        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': sdg_filter or None,
            'status_filter': status_filter or None,
            'college_filter': college_filter or None,
            'program_filter': program_filter or None
        })

        return [dict(row) for row in result.mappings()]
    except Exception as e:
        print(f"Error executing query: {e}")
        return []
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


def get_sdg_research(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_sdg_research function in PostgreSQL and checks if any data is retrieved.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings)
    :param status_filter: List of status filters (list of strings)
    :param college_filter: Optional college filter (list of strings)
    :param program_filter: Optional program filter (list of strings)
    :return: List of dictionaries containing SDG and research_id
    """
    session = Session()
    try:
        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_sdg_research(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
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

        # Convert to list of dictionaries
        data = [dict(row) for row in result.mappings()]
        
        # Check if any data is retrieved
        if not data:
            print("🔍 No SDG research data found for the given filters.")
        else:
            print(f"✅ Retrieved {len(data)} records.")
            for i, row in enumerate(data[:5]):  # Print only the first 5 rows for preview
                print(f"  {i+1}: {row}")

        return data

    finally:
        session.close()

def count_sdg_impact(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the count_sdg_impact function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings)
    :param status_filter: List of status filters (list of strings)
    :param college_filter: List of college filters (list of strings)
    :param program_filter: List of program filters (list of strings)
    :return: List of dictionaries containing research count per SDG
    """
    session = Session()
    try:
        # Normalize filters: If a filter is an empty list or None, convert it to None
        sdg_filter = None if sdg_filter is None or len(sdg_filter) == 0 else sdg_filter
        status_filter = None if status_filter is None or len(status_filter) == 0 else status_filter
        college_filter = None if college_filter is None or len(college_filter) == 0 else college_filter
        program_filter = None if program_filter is None or len(program_filter) == 0 else program_filter

        # Prepare the SQL query
        query = text("""
            SELECT * FROM count_sdg_impact(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
        """)

        # Execute the query with parameters
        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': sdg_filter,
            'status_filter': status_filter,
            'college_filter': college_filter,
            'program_filter': program_filter
        })

        # Process the result into a list of dictionaries
        return [dict(row) for row in result.mappings()]
    finally:
        session.close()

def get_proceeding_research(start_year, end_year, sdg_filter=None, status_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_proceeding_research function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings, optional)
    :param status_filter: List of status filters (list of strings, optional)
    :param college_filter: List of college filters (list of strings, optional)
    :param program_filter: List of program filters (list of strings, optional)
    :return: List of dictionaries containing SDG, research ID, and country for proceedings
    """
    session = Session()
    try:
        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_proceeding_research(:start_year, :end_year, :sdg_filter, :status_filter, :college_filter, :program_filter)
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