from flask_sqlalchemy import SQLAlchemy
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

db = SQLAlchemy()

from .account import Account
from .audit_trail import AuditTrail
from .college import College
from .conference import Conference
from .program import Program
from .publication import Publication
from .user_profile import UserProfile
from .research_outputs import ResearchOutput
from .research_output_author import ResearchOutputAuthor
from .roles import Role
from .status import Status
from .keywords import Keywords
from .panels import Panel
from .sdg import SDG
from .visitor import Visitor

def check_db(db_name, user, password, host='localhost', port='5432'):
    cursor = None  # Initialize cursor outside try block
    connection = None
    try:
        # Connect to the default 'postgres' database to manage other databases
        connection = psycopg2.connect(user=user, password=password, host=host, port=port, dbname='postgres')
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # To execute CREATE DATABASE outside transactions
        cursor = connection.cursor()

        # Use parameterized query to prevent SQL injection
        cursor.execute(sql.SQL("SELECT 1 FROM pg_database WHERE datname = %s"), [db_name])
        exists = cursor.fetchone()

        if not exists:
            # Create the new database if it doesn't exist
            cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(db_name)))
            print(f"Database '{db_name}' created successfully.")
        else:
            print(f"Database '{db_name}' already exists.")
    except Exception as error:
        print(f"Error while creating or checking database: {error}")
    finally:
        # Ensure that the cursor and connection are closed properly
        if cursor:
            cursor.close()
        if connection:
            connection.close()