from config import Session
from sqlalchemy import text
import pandas as pd  # Import pandas

def get_filtered_kgdata(selected_area, selected_sdg, start_year=None, end_year=None, selected_colleges=None):
    session = Session()
    try:
        result = session.execute(
            text(
                """
                SELECT * FROM get_filtered_research_data_kg(:selected_area, :selected_sdg, :start_year, :end_year, :selected_colleges)
                """
            ),
            {
                "selected_area": selected_area,
                "selected_sdg": selected_sdg,
                "start_year": start_year,
                "end_year": end_year,
                "selected_colleges": selected_colleges,
            },
        )

        rows = result.fetchall()
        column_names = result.keys()
        data = [dict(zip(column_names, row)) for row in rows]
        
        df = pd.DataFrame(data)
        return df

    except Exception as e:
        print(f"Error executing query: {e}")
        return None

    finally:
        session.close()

def get_filtered_sdg_counts(start_year=None, end_year=None, selected_colleges=None):
    session = Session()
    try:
        # Convert numpy array to list if needed
        if selected_colleges is not None:
            selected_colleges = list(selected_colleges)

        result = session.execute(
            text(
                """
                SELECT * FROM get_filtered_sdg_counts(:start_year, :end_year, :selected_colleges)
                """
            ),
            {
                "start_year": start_year,
                "end_year": end_year,
                "selected_colleges": selected_colleges,
            },
        )

        rows = result.fetchall()
        column_names = result.keys()
        data = [dict(zip(column_names, row)) for row in rows]
        
        df = pd.DataFrame(data)
        return df

    except Exception as e:
        print(f"Error executing query: {e}")
        return pd.DataFrame()  # Return empty DataFrame instead of None

    finally:
        session.close()

def get_filtered_research_area_counts(selected_sdg=None, start_year=None, end_year=None, selected_colleges=None):
    """
    Get filtered research area counts for SDG visualization
    """
    session = Session()
    try:
        # Convert numpy array to list if needed
        if selected_colleges is not None:
            selected_colleges = list(selected_colleges)

        result = session.execute(
            text(
                """
                SELECT * FROM get_filtered_research_area_counts(:selected_sdg, :start_year, :end_year, :selected_colleges)
                """
            ),
            {
                "selected_sdg": selected_sdg,
                "start_year": start_year,
                "end_year": end_year,
                "selected_colleges": selected_colleges,
            },
        )

        rows = result.fetchall()
        column_names = result.keys()
        data = [dict(zip(column_names, row)) for row in rows]
        
        df = pd.DataFrame(data)
        return df

    except Exception as e:
        print(f"Error executing query: {e}")
        return pd.DataFrame()  # Return empty DataFrame instead of None

    finally:
        session.close()


def get_program_research_aggregation(start_year=None, end_year=None, selected_colleges=None):
    """
    Get aggregated research data for programs
    """
    session = Session()
    try:
        # Convert numpy array to list if needed
        if selected_colleges is not None:
            selected_colleges = list(selected_colleges)

        result = session.execute(
            text(
                """
                SELECT * FROM get_program_research_aggregation(:start_year, :end_year, :selected_colleges)
                """
            ),
            {
                "start_year": start_year,
                "end_year": end_year,
                "selected_colleges": selected_colleges,
            },
        )

        rows = result.fetchall()
        column_names = result.keys()
        data = [dict(zip(column_names, row)) for row in rows]
        
        df = pd.DataFrame(data)
        return df

    except Exception as e:
        print(f"Error executing query: {e}")
        return pd.DataFrame()  # Return empty DataFrame instead of None

    finally:
        session.close()