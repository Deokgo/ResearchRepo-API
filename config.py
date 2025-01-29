# app configuration (database settings)

import os
import platform
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
    SECRET_KEY = os.environ.get('SECRET_KEY', "b'\x06F\x83X\xe1\x94\xd6\x1f\x89bU\xf5\xbfd\xa4\xda\xb2T\xf7\x0b{\xc0\xaf\xc2'")
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:Papasa01!@localhost:5432/Research_Data_Integration_System"
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
    
    MAIL_SERVER = "dev.institutional-repository.mcl-ccis.net"
    MAIL_PORT = 465  # Using SSL, as recommended
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False  # SSL and TLS are mutually exclusive
    MAIL_USERNAME = "info@dev.institutional-repository.mcl-ccis.net"
    MAIL_PASSWORD = ";b_DcJ;SRU$n"  # Replace with the actual email account password
    DEFAULT_SENDER = "info@dev.institutional-repository.mcl-ccis.net"

    # Add these new configurations
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BACKUP_ROOT = os.path.join(BASE_DIR, 'backups')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

    # Create directories if they don't exist
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Set PG_BIN using the detection function
    PG_BIN = detect_pg_bin()