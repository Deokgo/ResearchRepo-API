from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate #install this module in your terminal
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from models import db
from config import Config
from flask_mailman import Mail
import redis

def initialize_redis(app):
    """Initialize Redis and attach it to the app."""
    redis_client = redis.StrictRedis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        db=app.config['REDIS_DB'],
        decode_responses=True
    )
    app.redis_client = redis_client

#Initialize the app
app = Flask(__name__)

CORS(app)

#database Configuration
app.config.from_object(Config)


# Initialize the database
db.init_app(app)
mail = Mail(app)
migrate = Migrate(app, db)
initialize_redis(app)



# Function that checks the database if it exists or not
def check_db(db_name, user, password, host='localhost', port='5432'):
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
        if connection:
            cursor.close()
            connection.close()

# Function to check if the tables have any data
def has_table_data(session, table_model):
    return session.query(table_model).first() is not None


# Check if the database exists and create it if not
check_db('Research_Data_Integration_System', 'postgres', 'Papasa01!')

# Ensure tables are created after the database check
with app.app_context():
    db.create_all()  # This will create all the tables based on your SQLAlchemy models
    print("Tables created successfully.")



from routes.auth import auth
from routes.conference import conference
from routes.accounts import accounts
from routes.dept_prog import deptprogs
from routes.dataset import dataset
from routes.paper_op import paper
from routes.tracking import track
from routes.fetch_data import data
from routes.users import users


# Register the blueprint for routes
app.register_blueprint(auth, url_prefix='/auth')
app.register_blueprint(conference, url_prefix='/conference')
app.register_blueprint(accounts, url_prefix='/accounts')
app.register_blueprint(deptprogs, url_prefix='/deptprogs')
app.register_blueprint(dataset, url_prefix='/dataset')
app.register_blueprint(paper, url_prefix='/paper')
app.register_blueprint(track, url_prefix='/track')
app.register_blueprint(data, url_prefix='/data')
app.register_blueprint(users, url_prefix='/users')

from dashboards.main_dashboard import create_main_dashboard
from dashboards.main_dash import MainDashboard
from dashboards.pub_dash import PublicationDash
from knowledgegraph.knowledgegraph import create_kg_sdg
import dash_bootstrap_components as dbc
from models import ResearchOutput

# Created by Jelly Mallari | Create Dash apps and link them to Flask app
# Create Dash apps and link them to Flask app
def create_dash_apps(app):
    with app.app_context():
        session = db.session

        # Check if key tables have data before proceeding
        if has_table_data(session, ResearchOutput):
            MainDashboard(app)
            PublicationDash(app)
            create_main_dashboard(app)
            create_kg_sdg(app)
            # print("Dash apps created successfully.")
            # print("Available routes:")
            # for rule in app.url_map.iter_rules():
            #     print(rule)
        else:
            print("Dash apps cannot be created as no data is present in the ResearchOutput table.")


if __name__ == "__main__":
    create_dash_apps(app)
    app.run(debug=True)
