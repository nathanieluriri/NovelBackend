from email_templates.otp_template import generate_login_otp_email_from_template
from email_templates.invitation_template import generate_invitation_from_template
from schemas.email_schema import ClientData
from schemas.admin_schema import AllowedAdminCreate
from repositories.email_repo import create_email_log
from repositories.admin_repo import create_allowed_admin
import os
from datetime import datetime ,timezone
from dotenv import load_dotenv
from fastapi import  Request
import httpx
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr # To properly format sender name and email
import logging

async def get_location(request: Request)->ClientData:
    client_ip = request.client.host
    # use your public IP for testing instead of 127.0.0.1
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://ipapi.co/{client_ip}/json/")
        data = response.json()
    return {
        "ip": client_ip,
        "city": data.get("city",None),
        "region": data.get("region",None),
        "country": data.get("country_name",None),
        "latitude": data.get("latitude",None),
        "longitude": data.get("longitude",None),
        "Network":data.get("org",None),
        "timezone":data.get("timezone",None),
        "dateTime":datetime.now(timezone.utc).isoformat()
    }
    
        
load_dotenv()
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_HOST = os.getenv("EMAIL_HOST")

async def save_log_of_sent_emails(location:ClientData):
    saved_data = await create_email_log(client_data=location)
    return saved_data


def send_html_email_optimized(
    sender_email: str,
    sender_display_name: str, # Added for display name
    receiver_email: str,
    subject: str,
    html_content: str,
    plain_text_content: str, # Added for plain text alternative
    smtp_server: str,
    smtp_port: int,
    smtp_login: str,
    smtp_password: str
):
    """
    Sends an HTML email with a plain text alternative and a display name.

    Args:
        sender_email: The actual email address of the sender.
        sender_display_name: The name to be displayed as the sender.
        receiver_email: The email address of the recipient.
        subject: The subject of the email.
        html_content: The HTML content of the email body.
        plain_text_content: The plain text equivalent of the email body.
        smtp_server: The SMTP server hostname (e.g., 'smtp.hostinger.com').
        smtp_port: The SMTP server port (e.g., 465 for implicit SSL, 587 for explicit TLS).
        smtp_login: The username for SMTP authentication.
        smtp_password: The password for SMTP authentication (consider using app passwords).
    """

    # 1. Format the sender's "From" header with display name
    # This ensures correct display like "Your Company <your_email@example.com>"
    formatted_from_address = formataddr((sender_display_name, sender_email))

    # 2. Create the email message (MIMEMultipart for HTML + Plain Text)
    msg = MIMEMultipart("alternative")
    msg["From"] = formatted_from_address # Use the formatted address here
    msg["To"] = receiver_email
    msg["Subject"] = subject

    # 3. Attach the plain text part first (important for email clients to prioritize)
    # This also helps with spam filters and accessibility
    plain_part = MIMEText(plain_text_content, "plain")
    msg.attach(plain_part)

    # 4. Attach the HTML part
    html_part = MIMEText(html_content, "html")
    msg.attach(html_part)

    # 5. Connect and send email
    server = None # Initialize server to None
    try:
        if smtp_port == 465:
            # Use SSL directly for port 465 (implicit SSL/TLS)
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            logging.info(f"Connecting to SMTP server {smtp_server}:{smtp_port} using SSL.")
        elif smtp_port == 587 or smtp_port == 25:
            # Use regular SMTP and then upgrade to TLS for ports like 587 or 25
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo() # Identify yourself to the ESMTP server
            server.starttls() # Upgrade connection to secure
            server.ehlo() # Re-identify after starting TLS
            logging.info(f"Connecting to SMTP server {smtp_server}:{smtp_port} using STARTTLS.")
        else:
            logging.error(f"Unsupported SMTP port: {smtp_port}. Please use 465 or 587.")
            raise ValueError("Unsupported SMTP port.")

        server.login(smtp_login, smtp_password)
        logging.info(f"Successfully logged in to {smtp_login}.")

        server.sendmail(sender_email, receiver_email, msg.as_string())
        logging.info(f"Email sent successfully to {receiver_email} from {sender_email} (Display: {sender_display_name}).")

    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"Authentication failed. Check username and password: {e}")
        raise # Re-raise for caller to handle
    except smtplib.SMTPConnectError as e:
        logging.error(f"SMTP connection failed: {e}")
        raise
    except smtplib.SMTPException as e:
        logging.error(f"An SMTP error occurred: {e}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise
    finally:
        if server:
            server.quit() # Always ensure the connection is closed
            logging.info("SMTP connection closed.")



async def send_email(location:ClientData,receiver_email:str,otp:str):
    email_body_content = generate_login_otp_email_from_template(otp_code=otp,user_email=receiver_email)
    sender_email = EMAIL_USERNAME
    sender_display_name = "Nat from Mei" # The display name for the sender
    subject = "OTP FOR ADMIN LOGIN"
    smtp_server = EMAIL_HOST
    smtp_port = 465 
    smtp_login = EMAIL_USERNAME
    smtp_password = EMAIL_PASSWORD # Use your actual app password/email password here

    try:
      
        email_body_content = email_body_content.replace('<br>','')
        send_html_email_optimized(
        sender_email=sender_email,
        sender_display_name=sender_display_name,
        receiver_email=receiver_email,
        subject=subject,
        html_content=email_body_content,
        plain_text_content=f"Enter this {otp} to log in",
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        smtp_login=smtp_login,
        smtp_password=smtp_password
    )


    except Exception as e:
        print(f"Error sending email: {e}")
        return 1
    try:
        data = await save_log_of_sent_emails(location=location)
        print(data)
    except Exception as e:
        print(f"couldn't save logs because {e}")
        
    # TODO: After logging email to database write script to send the templated email string to the user trying to login
    
    
async def send_invitation(firstName,invitedEmail,lastName,inviterEmail):
    allowedAdmin = AllowedAdminCreate(email=invitedEmail,invitedBy=inviterEmail)
    await create_allowed_admin(user_data=allowedAdmin)
    email_body_content = generate_invitation_from_template(first_name=firstName,invitee_email_address=invitedEmail,last_name=lastName,main_website_link="https://knowyourmeme.com/memes/05-gpa-activities-tiktok-trend",register_link="https://knowyourmeme.com/memes/05-gpa-activities-tiktok-trend",)
    sender_email = EMAIL_USERNAME
    sender_display_name = f"{firstName} from MEI" # The display name for the sender
    subject = "Admin Registration Invitation"
    smtp_server = EMAIL_HOST
    smtp_port = 465 
    smtp_login = EMAIL_USERNAME
    smtp_password = EMAIL_PASSWORD # Use your actual app password/email password here
    try:
      
        email_body_content = email_body_content.replace('<br>','')
        send_html_email_optimized(
        sender_email=sender_email,
        sender_display_name=sender_display_name,
        receiver_email=invitedEmail,
        subject=subject,
        html_content=email_body_content,
        plain_text_content="You have been invited to register as an admin",
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        smtp_login=smtp_login,
        smtp_password=smtp_password
    )


    except Exception as e:
        print(f"Error sending email: {e}")
        return 1
   
        
    # TODO: Log this invitation and send warning message to the person that sent the invitation incase they didn't knowingly invite this new admin 