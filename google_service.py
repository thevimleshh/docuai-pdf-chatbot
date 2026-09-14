import os
import smtplib

from email.message import EmailMessage
from dotenv import load_dotenv


load_dotenv()

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def send_verification_email(receiver_email: str, verification_code: str):
    message = EmailMessage()

    message["Subject"] = "DocuAI Email Verification Code"
    message["From"] = GMAIL_ADDRESS
    message["To"] = receiver_email

    message.set_content(
        f"""
Hello,

Your DocuAI email verification code is:

{verification_code}

This code is valid for a short time.

If you did not create a DocuAI account, you can ignore this email.

Regards,
DocuAI Team
"""
    )

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(message)