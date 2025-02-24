from config import Session
from sqlalchemy import text
import pandas as pd  # Import pandas

def get_filtered_kgdata(start_year=None, end_year=None, selected_colleges=None):
    session = Session()
    try:
        result = session.execute(
            text(
                """
                SELECT * FROM get_filtered_research_data_kg(:start_year, :end_year, :selected_colleges)
                """
            ),
            {
                "start_year": start_year,
                "end_year": end_year,
                "selected_colleges": selected_colleges,
            },
        )

        rows = result.fetchall()

        # Explicitly create dictionaries with keys and values
        column_names = result.keys()  # Get column names from the result
        data = [dict(zip(column_names, row)) for row in rows]

        # Create a pandas DataFrame
        df = pd.DataFrame(data)
        return df

    except Exception as e:
        print(f"Error executing query: {e}")
        return None

    finally:
        session.close()