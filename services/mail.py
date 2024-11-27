from flask_mailman import EmailMessage
from flask import current_app
from config import Config
from services.data_fetcher import ResearchDataFetcher
from models import Account

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

def send_notification_email(subject, body):
    users = Account.query.filter(Account.role_id == '02').all()


    if not users:
        print("No users found. No emails will be sent.")
        return  # Exit the function early since there are no users

    # Creating the app context just once for all emails
    with current_app.app_context():
        for user in users:
            try:
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=Config.DEFAULT_SENDER,
                    to=[user.email]
                )
                email.send()  # Send the email
                print(f"Email sent to {user.email}")  # Log for success
            except Exception as e:
                print(f"Failed to send email to {user.email}: {str(e)}")  # Handle failure gracefully
