from flask import Flask, request, jsonify
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash
from server import mail 
from models import db

import pyotp
import datetime

otp_storage = {}  # Temporary in-memory storage

# Generate and send OTP (with Flask-Mail)
def create_otp(email):
    try:
        otp_secret = pyotp.random_base32()
        totp = pyotp.TOTP(otp_secret)
        otp_code = totp.now()

        # Store OTP in memory with a timestamp
        otp_storage[email] = {
            "otp_secret": otp_secret,
            "otp_code": otp_code,
            "created_at": datetime.datetime.now()
        }

        # Send OTP email
        send_otp(email, otp_code)

        return {"message": "OTP sent successfully to email."}, 200
    except Exception as e:
        return {"error": str(e)}, 500


# Function to send OTP via email using Flask-Mail
def send_otp(email, otp_code):
    try:
        msg = Message("Your OTP Code", recipients=[email])
        msg.body = f"Your OTP code is {otp_code}. It is valid for 5 minutes."
        mail.send(msg)
    except Exception as e:
        raise Exception("Error sending OTP email: " + str(e))
