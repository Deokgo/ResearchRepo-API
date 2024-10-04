# app configuration (database settings)

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', "b'\x06F\x83X\xe1\x94\xd6\x1f\x89bU\xf5\xbfd\xa4\xda\xb2T\xf7\x0b{\xc0\xaf\xc2'")
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:Papasa01!@localhost:5432/Research_Data_Integration_System'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Mail configuration for sending OTP
    MAIL_SERVER = 'smtp.gmail.com'  # Use your mail server, e.g., Gmail
    MAIL_PORT = 465  # SMTP SSL port
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'your_email@gmail.com'
    MAIL_PASSWORD = 'your_email_password'
    MAIL_DEFAULT_SENDER = 'your_email@gmail.com'
    
