import psycopg2
import schedule
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_migrate import Migrate #install this module in your terminal
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
from models import Account


def update_to_inactive():
    print('Updating the status of the accounts to INACTIVE')
    database_uri = app.config['SQLALCHEMY_DATABASE_URI']
    parsed_uri = urlparse(database_uri)
    db_user = parsed_uri.username
    db_password = parsed_uri.password
    db_name = parsed_uri.path.lstrip('/')
    
    conn = psycopg2.connect(f"dbname={db_name} user={db_user} password={db_password}")
    cur = conn.cursor()
    cur.execute("""
        UPDATE account 
        SET acc_status = 'INACTIVE'
        WHERE acc_status = 'ACTIVE' 
        AND last_login <= NOW() - INTERVAL '180 days';
    """)
    conn.commit()
    cur.close()
    conn.close()

schedule.every().day.at("10:49").do(update_to_inactive) # Happens every 12AM

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

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

# Initialize the app
app = Flask(__name__,
           static_url_path='/static',
           static_folder='static')

CORS(app, resources={
    r"/*": {
        "origins": "http://localhost:3000",  # Specify your exact frontend domain
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"],
        "supports_credentials": True,  # Enable this for authenticated requests
        "expose_headers": ["Content-Type", "Authorization"]
    }
})

@app.route('/')
def index():
    return jsonify({"message": "API is running"})

# Database Configuration
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
        
        if datetime.timestamp(now) > exp_timestamp:
            from services import auth_services
            user_id = get_jwt_identity()
            user = Account.query.get(user_id)
            if user:
                auth_services.log_audit_trail(
                    email=user.email,
                    role=user.role.role_name,
                    table_name='Account',
                    record_id=None,
                    operation='LOGOUT',
                    action_desc='Token expired'
                )
            return response
        
        if target_timestamp > exp_timestamp:
            access_token = create_access_token(identity=get_jwt_identity())
            data = response.get_json()
            if type(data) is dict:
                data["token"] = access_token
                response.data = json.dumps(data)
        return response
    except (RuntimeError, KeyError):
        return response

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


from dashboards.main_dash import MainDashboard
from knowledgegraph.knowledgegraph import create_kg_area
from knowledgegraph.keywordskg import create_research_network
from dashboards.college_dash import CollegeDashApp
from dashboards.program_dash import ProgDashApp
import dash_bootstrap_components as dbc
from models import ResearchOutput
from dashboards.user_engagement_dash import UserEngagementDash
from dashboards.sdg_impact_dash import SDG_Impact_Dash
from dashboards.sdg_impact_college import SDG_Impact_College
from dashboards.institutional_performance_dash import Institutional_Performance_Dash

def create_dash_apps(app):
    with app.app_context():
        session = db.session
        if has_table_data(session, ResearchOutput):
            MainDashboard(app)
            create_kg_area(app)
            create_research_network(app)
            CollegeDashApp(app)
            ProgDashApp(app)
            UserEngagementDash(app)
            SDG_Impact_Dash(app)
            SDG_Impact_College(app)
            Institutional_Performance_Dash(app)
        else:
            print("Dash apps cannot be created as no data is present in the ResearchOutput table.")

create_dash_apps(app)

if __name__ == "__main__":
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    app.run(host="0.0.0.0",debug=True, port=5000)