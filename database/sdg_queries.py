from config import Session
from sqlalchemy import text
from sqlalchemy import bindparam
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
import numpy as np
import pandas as pd



def get_research_count(start_year, end_year, sdg_filter=None, status_filter=None, pub_format_filter=None, college_filter=None, program_filter=None):
    

    session = Session()
    try:
        # Convert numpy arrays to lists if needed
        sdg_filter = sdg_filter.tolist() if isinstance(sdg_filter, np.ndarray) else sdg_filter
        status_filter = status_filter.tolist() if isinstance(status_filter, np.ndarray) else status_filter
        pub_format_filter = pub_format_filter.tolist() if isinstance(pub_format_filter, np.ndarray) else pub_format_filter
        college_filter = college_filter.tolist() if isinstance(college_filter, np.ndarray) else college_filter
        program_filter = program_filter.tolist() if isinstance(program_filter, np.ndarray) else program_filter

        query = text("""
            SELECT * FROM get_research_count(
                :start_year, 
                :end_year, 
                :sdg_filter, 
                :status_filter, 
                :pub_format_filter, 
                :college_filter, 
                :program_filter
            )
        """).bindparams(
            bindparam('sdg_filter', type_=ARRAY(TEXT)),
            bindparam('status_filter', type_=ARRAY(TEXT)),
            bindparam('pub_format_filter', type_=ARRAY(TEXT)),
            bindparam('college_filter', type_=ARRAY(TEXT)),
            bindparam('program_filter', type_=ARRAY(TEXT))
        )

        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': sdg_filter,
            'status_filter': status_filter,
            'pub_format_filter': pub_format_filter,
            'college_filter': college_filter,
            'program_filter': program_filter
        })

        return [dict(row) for row in result.mappings()]
    except Exception as e:
        print(f"Error executing query: {e}")
        return []
    finally:
        session.close()



def get_research_percentage(start_year, end_year, sdg_filter=None, status_filter=None, pub_format_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_research_percentage function in PostgreSQL.
    """
    session = Session()
    try:
        # Convert numpy arrays to lists if needed
        sdg_filter = sdg_filter.tolist() if isinstance(sdg_filter, np.ndarray) else sdg_filter
        status_filter = status_filter.tolist() if isinstance(status_filter, np.ndarray) else status_filter
        pub_format_filter = pub_format_filter.tolist() if isinstance(pub_format_filter, np.ndarray) else pub_format_filter
        college_filter = college_filter.tolist() if isinstance(college_filter, np.ndarray) else college_filter
        program_filter = program_filter.tolist() if isinstance(program_filter, np.ndarray) else program_filter

        query = text("""
            SELECT * FROM get_research_percentage(
                :start_year, 
                :end_year, 
                :sdg_filter, 
                :status_filter, 
                :college_filter, 
                :program_filter,
                :pub_format_filter
            )
        """).bindparams(
            bindparam('sdg_filter', type_=ARRAY(TEXT)),
            bindparam('status_filter', type_=ARRAY(TEXT)),
            bindparam('college_filter', type_=ARRAY(TEXT)),
            bindparam('program_filter', type_=ARRAY(TEXT)),
            bindparam('pub_format_filter', type_=ARRAY(TEXT))
        )

        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': sdg_filter,
            'pub_format_filter': pub_format_filter,
            'status_filter': status_filter,
            'college_filter': college_filter,
            'program_filter': program_filter
            
        })

        return [dict(row) for row in result.mappings()]
    
    except Exception as e:
        print(f"Error executing query: {e}")
        return []
    
    finally:
        session.close()



def get_research_type_distribution(start_year, end_year, sdg_filter=None, status_filter=None, pub_format_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_research_type_distribution function in PostgreSQL.
    
    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List or array of SDG filters (optional)
    :param status_filter: List or array of status filters (optional)
    :param pub_format_filter: List or array of publication format filters (optional)
    :param college_filter: List or array of college filters (optional)
    :param program_filter: List or array of program filters (optional)
    :return: List of dictionaries containing research type distribution
    """
    session = Session()
    try:
        # Convert numpy arrays to lists if needed
        sdg_filter = sdg_filter.tolist() if isinstance(sdg_filter, np.ndarray) else sdg_filter
        status_filter = status_filter.tolist() if isinstance(status_filter, np.ndarray) else status_filter
        pub_format_filter = pub_format_filter.tolist() if isinstance(pub_format_filter, np.ndarray) else pub_format_filter
        college_filter = college_filter.tolist() if isinstance(college_filter, np.ndarray) else college_filter
        program_filter = program_filter.tolist() if isinstance(program_filter, np.ndarray) else program_filter

        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_research_type_distribution(
                :start_year, 
                :end_year, 
                :sdg_filter, 
                :status_filter, 
                :pub_format_filter, 
                :college_filter, 
                :program_filter
            )
        """).bindparams(
            bindparam('sdg_filter', type_=ARRAY(TEXT)),
            bindparam('status_filter', type_=ARRAY(TEXT)),
            bindparam('pub_format_filter', type_=ARRAY(TEXT)),
            bindparam('college_filter', type_=ARRAY(TEXT)),
            bindparam('program_filter', type_=ARRAY(TEXT))
        )

        # Execute the query with parameters
        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': sdg_filter,
            'status_filter': status_filter,
            'pub_format_filter': pub_format_filter,
            'college_filter': college_filter,
            'program_filter': program_filter
        })

        # Process and return the result
        return [dict(row) for row in result.mappings()]

    except Exception as e:
        print(f"Error executing query: {e}")
        return []

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

from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
import numpy as np

def get_research_with_keywords(start_year, end_year, sdg_filter=None, status_filter=None, pub_format_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_research_with_keywords function in PostgreSQL.
    
    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List or array of SDG filters (optional)
    :param status_filter: List or array of status filters (optional)
    :param pub_format_filter: List or array of publication format filters (optional)
    :param college_filter: List or array of college filters (optional)
    :param program_filter: List or array of program filters (optional)
    :return: List of dictionaries containing research ID, title, abstract, and keywords
    """
    session = Session()
    try:
        # Convert numpy arrays to lists if needed
        sdg_filter = sdg_filter.tolist() if isinstance(sdg_filter, np.ndarray) else sdg_filter
        status_filter = status_filter.tolist() if isinstance(status_filter, np.ndarray) else status_filter
        pub_format_filter = pub_format_filter.tolist() if isinstance(pub_format_filter, np.ndarray) else pub_format_filter
        college_filter = college_filter.tolist() if isinstance(college_filter, np.ndarray) else college_filter
        program_filter = program_filter.tolist() if isinstance(program_filter, np.ndarray) else program_filter

        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_research_with_keywords(
                :start_year, 
                :end_year, 
                :sdg_filter, 
                :status_filter, 
                :pub_format_filter, 
                :college_filter, 
                :program_filter
            )
        """).bindparams(
            bindparam('sdg_filter', type_=ARRAY(TEXT)),
            bindparam('status_filter', type_=ARRAY(TEXT)),
            bindparam('pub_format_filter', type_=ARRAY(TEXT)),
            bindparam('college_filter', type_=ARRAY(TEXT)),
            bindparam('program_filter', type_=ARRAY(TEXT))
        )

        # Execute the query with parameters
        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': sdg_filter,
            'status_filter': status_filter,
            'pub_format_filter': pub_format_filter,
            'college_filter': college_filter,
            'program_filter': program_filter
        })

        # Process and return the result
        return [dict(row) for row in result.mappings()]
    
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

    finally:
        session.close()



def get_research_area_data(start_year, end_year, sdg_filter=None, status_filter=None, pub_format_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_research_area_sdg function in PostgreSQL and retrieves research data.

    :param start_year: Start school year (integer or list or numpy array)
    :param end_year: End school year (integer or list or numpy array)
    :param sdg_filter: List or array of SDG filters (optional)
    :param status_filter: List or array of status filters (optional)
    :param pub_format_filter: List or array of publication format filters (optional)
    :param college_filter: List or array of college filters (optional)
    :param program_filter: List or array of program filters (optional)
    :return: List of dictionaries containing research data
    """
    session = Session()
    
    try:
        # Convert numpy arrays to lists if needed
        sdg_filter = sdg_filter.tolist() if isinstance(sdg_filter, np.ndarray) else sdg_filter
        status_filter = status_filter.tolist() if isinstance(status_filter, np.ndarray) else status_filter
        pub_format_filter = pub_format_filter.tolist() if isinstance(pub_format_filter, np.ndarray) else pub_format_filter
        college_filter = college_filter.tolist() if isinstance(college_filter, np.ndarray) else college_filter
        program_filter = program_filter.tolist() if isinstance(program_filter, np.ndarray) else program_filter

        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_research_area_sdg(
                :start_year, 
                :end_year, 
                :sdg_filter, 
                :status_filter, 
                :pub_format_filter, 
                :college_filter, 
                :program_filter
            )
        """).bindparams(
            bindparam('sdg_filter', type_=ARRAY(TEXT)),
            bindparam('status_filter', type_=ARRAY(TEXT)),
            bindparam('pub_format_filter', type_=ARRAY(TEXT)),
            bindparam('college_filter', type_=ARRAY(TEXT)),
            bindparam('program_filter', type_=ARRAY(TEXT))
        )

        # Execute the query with parameters
        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': sdg_filter,
            'status_filter': status_filter,
            'pub_format_filter': pub_format_filter,
            'college_filter': college_filter,
            'program_filter': program_filter
        })

        # Process the result into a list of dictionaries
        return [dict(row) for row in result.mappings()]
    
    except Exception as e:
        print(f"Error executing query: {e}")
        return []
    
    finally:
        session.close()





def get_sdg_research(start_year, end_year, sdg_filter=None, status_filter=None, pub_format_filter=None, college_filter=None, program_filter=None):
    """
    Calls the get_sdg_research function in PostgreSQL and checks if any data is retrieved.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings)
    :param status_filter: List of status filters (list of strings)
    :param pub_format_filter: Optional publication format filter (list of strings)
    :param college_filter: Optional college filter (list of strings)
    :param program_filter: Optional program filter (list of strings)
    :return: List of dictionaries containing SDG and research_id
    """
    session = Session()
    
    try:
        # Convert numpy arrays to lists if needed
        sdg_filter = sdg_filter.tolist() if isinstance(sdg_filter, np.ndarray) else sdg_filter
        status_filter = status_filter.tolist() if isinstance(status_filter, np.ndarray) else status_filter
        pub_format_filter = pub_format_filter.tolist() if isinstance(pub_format_filter, np.ndarray) else pub_format_filter
        college_filter = college_filter.tolist() if isinstance(college_filter, np.ndarray) else college_filter
        program_filter = program_filter.tolist() if isinstance(program_filter, np.ndarray) else program_filter

        # Prepare the SQL query
        query = text("""
            SELECT * FROM get_sdg_research(
                :start_year, 
                :end_year, 
                :sdg_filter, 
                :status_filter, 
                :pub_format_filter, 
                :college_filter, 
                :program_filter
            )
        """).bindparams(
            bindparam('sdg_filter', type_=ARRAY(TEXT)),
            bindparam('status_filter', type_=ARRAY(TEXT)),
            bindparam('pub_format_filter', type_=ARRAY(TEXT)),
            bindparam('college_filter', type_=ARRAY(TEXT)),
            bindparam('program_filter', type_=ARRAY(TEXT))
        )

        # Execute the query
        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': sdg_filter,
            'status_filter': status_filter,
            'pub_format_filter': pub_format_filter,
            'college_filter': college_filter,
            'program_filter': program_filter
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

    except Exception as e:
        print(f"Error executing query: {e}")
        return []
    
    finally:
        session.close()


def count_sdg_impact(start_year, end_year, sdg_filter=None, status_filter=None, pub_format_filter=None, college_filter=None, program_filter=None):
    """
    Calls the count_sdg_impact function in PostgreSQL.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings)
    :param status_filter: List of status filters (list of strings)
    :param pub_format_filter: List of publication format filters (list of strings)
    :param college_filter: List of college filters (list of strings)
    :param program_filter: List of program filters (list of strings)
    :return: List of dictionaries containing research count per SDG
    """
    session = Session()
    try:
        # Convert numpy arrays to lists if needed
        sdg_filter = sdg_filter.tolist() if isinstance(sdg_filter, np.ndarray) else sdg_filter
        status_filter = status_filter.tolist() if isinstance(status_filter, np.ndarray) else status_filter
        pub_format_filter = pub_format_filter.tolist() if isinstance(pub_format_filter, np.ndarray) else pub_format_filter
        college_filter = college_filter.tolist() if isinstance(college_filter, np.ndarray) else college_filter
        program_filter = program_filter.tolist() if isinstance(program_filter, np.ndarray) else program_filter

        query = text("""
            SELECT * FROM count_sdg_impact(
                :start_year, 
                :end_year, 
                :sdg_filter, 
                :status_filter, 
                :pub_format_filter, 
                :college_filter, 
                :program_filter
            )
        """).bindparams(
            bindparam('sdg_filter', type_=ARRAY(TEXT)),
            bindparam('status_filter', type_=ARRAY(TEXT)),
            bindparam('pub_format_filter', type_=ARRAY(TEXT)),
            bindparam('college_filter', type_=ARRAY(TEXT)),
            bindparam('program_filter', type_=ARRAY(TEXT))
        )

        result = session.execute(query, {
            'start_year': start_year,
            'end_year': end_year,
            'sdg_filter': sdg_filter,
            'status_filter': status_filter,
            'pub_format_filter': pub_format_filter,
            'college_filter': college_filter,
            'program_filter': program_filter
        })

        return [dict(row) for row in result.mappings()]
    
    except Exception as e:
        print(f"Error executing query: {e}")
        return []
    
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