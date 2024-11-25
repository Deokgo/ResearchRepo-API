# app configuration (database settings)

import os
from datetime import datetime,timedelta,timezone

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', "b'\x06F\x83X\xe1\x94\xd6\x1f\x89bU\xf5\xbfd\xa4\xda\xb2T\xf7\x0b{\xc0\xaf\xc2'")
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:Papasa01!@localhost:5432/Research_Data_Integration_System'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_TYPE="redis"
    SESSION_PERMANENT=False
    SESSION_USE_SIGNER = True

    REDIS_HOST = 'localhost' 
    REDIS_PORT = 6379  
    REDIS_DB = 0 

    JWT_TOKEN_EXPIRES = timedelta(hours=4)

    MAIL_SERVER = "dev.institutional-repository.mcl-ccis.net"
    MAIL_PORT = 465  # Using SSL, as recommended
    MAIL_USE_SSL = True
    MAIL_USE_TLS = False  # SSL and TLS are mutually exclusive
    MAIL_USERNAME = "info@dev.institutional-repository.mcl-ccis.net"
    MAIL_PASSWORD = ";b_DcJ;SRU$n"  # Replace with the actual email account password
    DEFAULT_SENDER = "info@dev.institutional-repository.mcl-ccis.net"
