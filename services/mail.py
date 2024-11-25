from flask_mailman import EmailMessage
from flask import current_app
from config import Config

def send_otp_email(to_email, subject, body):
    
    # Create and send the email
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=Config.DEFAULT_SENDER,
        to=[to_email]
    )
    with current_app.app_context():
        email.send()

def send_notification_email(to_email, subject, body):
    # Create and send the email
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=Config.DEFAULT_SENDER,
        to=[to_email]
    )
    with current_app.app_context():
        email.send()
