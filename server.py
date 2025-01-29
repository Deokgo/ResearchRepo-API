from flask import Flask, request
from flask_cors import CORS
from flask_migrate import Migrate #install this module in your terminal
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from models import db, check_db
from config import Config
from flask_mailman import Mail
import redis
from flask_jwt_extended import JWTManager, get_jwt, create_access_token, get_jwt_identity
from datetime import datetime, timezone, timedelta
import json
from urllib.parse import urlparse

def initialize_redis(app):
    """Initialize Redis and attach it to the app."""
    redis_client = redis.StrictRedis(
        host=app.config['REDIS_HOST'],
        port=app.config['REDIS_PORT'],
        db=app.config['REDIS_DB'],
        decode_responses=True
    )
    app.redis_client = redis_client

def initialize_db(app):
    """Initialize the database and check table creation."""
    db.init_app(app)
    database_uri = app.config['SQLALCHEMY_DATABASE_URI']
    parsed_uri = urlparse(database_uri)

    db_user = parsed_uri.username
    db_password = parsed_uri.password
    db_host = parsed_uri.hostname
    db_port = parsed_uri.port
    db_name = parsed_uri.path.lstrip('/')

    check_db(
        db_name=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port
    )
    
    with app.app_context():
        db.create_all()

#Initialize the app
app = Flask(__name__)

CORS(app, supports_credentials=True)

#database Configuration
app.config.from_object(Config)

initialize_db(app)
mail = Mail(app)
migrate = Migrate(app, db)
initialize_redis(app)
jwt = JWTManager(app)

@app.after_request
def refresh_expiring_jwts(response):
    try:
        exp_timestamp = get_jwt()["exp"]
        now = datetime.now(timezone.utc)
        target_timestamp = datetime.timestamp(now + timedelta(minutes=30))
        
        # If token has expired
        if datetime.timestamp(now) > exp_timestamp:
            # Log the token expiration
            from services import auth_services
            user_id = get_jwt_identity()
            auth_services.log_audit_trail(
                user_id=user_id,
                table_name='Account',
                record_id=None,
                operation='LOGOUT',
                action_desc='Token expired'
            )
            return response
            
        # If token is about to expire (less than 30 min remaining)
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            data = response.get_json()
            if type(data) is dict:
                data["token"] = access_token
                response.data = json.dumps(data)
        return response
    except (RuntimeError, KeyError):
        # Case where there is no valid JWT
        return response


# Function to check if the tables have any data
def has_table_data(session, table_model):
    return session.query(table_model).first() is not None

from routes.auth import auth
from routes.conference import conference
from routes.accounts import accounts
from routes.dept_prog import deptprogs
from routes.dataset import dataset
from routes.paper_op import paper
from routes.tracking import track
from routes.fetch_data import data
from routes.users import users
from routes.auditlogs import auditlogs
from routes.pydash import pydash
from routes.backup import backup

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
app.register_blueprint(auditlogs, url_prefix='/auditlogs')
app.register_blueprint(pydash, url_prefix='/dash')
app.register_blueprint(backup, url_prefix='/backup')

from dashboards.main_dashboard import create_main_dashboard
from dashboards.main_dash import MainDashboard
from dashboards.pub_dash import PublicationDash
from knowledgegraph.knowledgegraph import create_kg_area
from knowledgegraph.collectionkg import collection_kg
from dashboards.college_dash import CollegeDashApp
from dashboards.program_dash import ProgDashApp
import dash_bootstrap_components as dbc
from models import ResearchOutput
from dashboards.sdg_dash import SDG_Dash
from dashboards.sdg_college import SDG_College
from dashboards.sdg_map_overall import SDG_Map
from dashboards.sdg_map_college import SDG_Map_College
from dashboards.engage_dash import Engage_Dash
from dashboards.engage_college import Engage_College

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
            create_kg_area(app)
            collection_kg(app)
            CollegeDashApp(app)
            ProgDashApp(app)
            SDG_Dash(app)
            SDG_College(app)
            SDG_Map(app)
            SDG_Map_College(app)
            Engage_Dash(app)
            Engage_College(app)
            # print("Dash apps created successfully.")
            # print("Available routes:")
            # for rule in app.url_map.iter_rules():
            #     print(rule)
        else:
            print("Dash apps cannot be created as no data is present in the ResearchOutput table.")


if __name__ == "__main__":
    create_dash_apps(app)
    app.run(debug=True)
