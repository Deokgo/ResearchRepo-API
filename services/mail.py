from flask_mailman import EmailMessage
from flask import current_app
from config import Config
from services.data_fetcher import ResearchDataFetcher
from models import Account

def send_otp_email(to_email, subject, body):
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50; text-align: center;">MMCL Institutional Research Repository</h2>
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
            <p style="color: #2c3e50; font-size: 16px;">Hello,</p>
            <p style="color: #2c3e50; font-size: 16px;">Your one-time password (OTP) is:</p>
            <div style="background-color: #ffffff; padding: 15px; text-align: center; border-radius: 5px; margin: 20px 0;">
                <h1 style="color: #2c3e50; letter-spacing: 5px; margin: 0;">{body.split()[-1]}</h1>
            </div>
            <p style="color: #2c3e50; font-size: 14px;">This code will expire in 5 minutes.</p>
            <p style="color: #2c3e50; font-size: 14px;">If you didn't request this code, please ignore this email.</p>
        </div>
        <p style="color: #7f8c8d; font-size: 12px; text-align: center; margin-top: 20px;">
            This is an automated message, please do not reply.
        </p>
    </div>
    """
    # Create and send the email
    email = EmailMessage(
        subject=subject,
        body=html_content,
        from_email=Config.DEFAULT_SENDER,
        to=[to_email]
    )

    email.content_subtype = "html"

    with current_app.app_context():
        email.send()

def send_notification_email(subject, body):
    users = Account.query.filter(Account.role_id == '02').all()
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50; text-align: center;">MMCL Institutional Research Repository Notification</h2>
        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px;">
            <p style="color: #2c3e50; font-size: 16px;">Hello,</p>
            <div style="background-color: #ffffff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="color: #2c3e50; font-size: 16px; margin: 0;">{body}</p>
            </div>
            <p style="color: #2c3e50; font-size: 14px;">Please check the research repository for more details.</p>
        </div>
        <p style="color: #7f8c8d; font-size: 12px; text-align: center; margin-top: 20px;">
            This is an automated message, please do not reply.
        </p>
    </div>
    """

    if not users:
        print("No users found. No emails will be sent.")
        return  # Exit the function early since there are no users

    # Creating the app context just once for all emails
    with current_app.app_context():
        for user in users:
            try:
                email = EmailMessage(
                    subject=subject,
                    body=html_content,
                    from_email=Config.DEFAULT_SENDER,
                    to=[user.email]
                )
                email.content_subtype = "html"
                email.send()  # Send the email
                print(f"Email sent to {user.email}")  # Log for success
            except Exception as e:
                print(f"Failed to send email to {user.email}: {str(e)}")  # Handle failure gracefully
