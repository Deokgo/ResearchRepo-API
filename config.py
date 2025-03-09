# app configuration (database settings)

import os
import platform
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

load_dotenv()
def detect_pg_bin():
    if platform.system() == 'Windows':
        # Look for PostgreSQL in Program Files
        pg_base = r'C:\Program Files\PostgreSQL'
        if os.path.exists(pg_base):
            # Get the latest version installed
            versions = [d for d in os.listdir(pg_base) if os.path.isdir(os.path.join(pg_base, d))]
            if versions:
                latest_version = sorted(versions)[-1]
                return os.path.join(pg_base, latest_version, 'bin')
    else:
        # For Linux/Mac, assume PostgreSQL is in PATH
        return '/usr/bin'  # Default Linux/Mac location
    return None

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', "default_secret_key")
    SQLALCHEMY_DATABASE_URI = os.getenv('DB_CONNECTION_STRING')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_TYPE="redis"
    SESSION_PERMANENT=False
    SESSION_USE_SIGNER = True

    REDIS_HOST = 'localhost' 
    REDIS_PORT = 6379  
    REDIS_DB = 0 

    # JWT Configuration
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=3)
    
    # Mail Configuration
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    DEFAULT_SENDER = os.getenv('DEFAULT_SENDER')

    # Add these new configurations
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BACKUP_ROOT = os.path.join(BASE_DIR, 'backups')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

    # Create directories if they don't exist
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Set PG_BIN using the detection function
    PG_BIN = detect_pg_bin()
    PGDATA = 'C:/Program Files/PostgreSQL/16/data'  # Adjust this path to match your PostgreSQL data directory

# Initialize the engine and session factory based on the config
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Session = sessionmaker(bind=engine)

# Download necessary NLTK datasets
# Download required NLTK resources
nltk.download('punkt', force=True)
nltk.download('stopwords', force=True)
nltk.download('averaged_perceptron_tagger', force=True)  # Needed for POS tagging

custom_stopwords = set([
    "title", "study", "researchers", "respondents", "methodology", "data", 
    "survey", "analysis", "findings", "result", "participants", "questionnaire",
    "research", "objective", "aim", "sample", "participant", "approach", "researcher",
    "keywords","results","test","abstract","use","using","used"
])

# Combine default NLTK stopwords with custom stopwords
stop_words = set(stopwords.words("english")).union(custom_stopwords)
lemmatizer = WordNetLemmatizer()

    