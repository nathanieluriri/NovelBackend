from string import Template

email_template_string=Template("""
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="UTF-8"/>
    <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
    <meta name="viewport" content="width=device-width, initial-scale=
=1.0"/>

    <title>Mei</title>
</head>

<head>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        *:focus {
            outline: none;
        }

        html {
            font: 62.5% / 1.15 sans-serif; /* 1rem */
            max-width: 100%;
        }

        body {
            margin: 0;
            font-family: sans-serif;
            background: #f7f8fa;
        }

        table {
            border-spacing: 0;
            box-sizing: border-box;
            margin: 0;
            width: 100%;
        }

        td {
            padding: 0;
        }

        .wrapper {
            margin: 0 auto;
            table-layout: fixed;
            width: 100%;
            max-width: 1000px;
            padding: 14px;
            background: #f7f8fa;
            border: 1px solid #f7f8fa;
        }

        .main {
            width: 100%;
            /*max-width: 720px;*/
            background-color: #ffffff;
            font-family: 'DM Sans', sans-serif;
            box-shadow: 0px 4px 36px 1px rgba(0, 0, 0, 0.06);
            overflow: hidden;
        }

        .mei-email-template--header {
            padding: 48px 0 20px;
            text-align: center;
            border-bottom: 2px solid #f7f5f5;
        }

        .mei-email-template--header > img {
            width: 200px;
        }

        .mei-email-template--body-wrapper {
            margin: 28px auto;
            padding: 24px 36px 0;
            width: 100%;
            max-width: 772px;
            font-family: 'DM Sans', sans-serif;
            font-style: normal;
            font-weight: 400;
            font-size: 18px;
            line-height: 226%;
            letter-spacing: -0.003em;
            color: #393939 !important;
        }

        .mei-email-template--body-wrapper > h4 {
            text-align: left;
            margin-bottom: 0;
        }

        .mei-email-template--body-wrapper > p {
            text-align: justify;
            width: 100%;
            max-width: 630px;
        }

        .mei-email-template--body-wrapper > p > a {
            color: #365899;
        }

        .thank-you-text {
            margin: 50px 0 16px;
        }

        .mei-email-template--otp-code {
            width: 100%;
            max-width: 772px;
            margin: 20px auto 32px;
            padding: 14px 0;
            border-style: solid;
            border-width: 1px;
            border-left: 0;
            border-right: 0;
            border-image: linear-gradient(45deg, #405896, #4a8eb9) 1;
        }

        .mei-email-template--otp-code > p {
            font-family: 'Mori Gothic', sans-serif;
            font-style: normal;
            font-weight: 400;
            font-size: 48px;
            line-height: 200%;
            letter-spacing: -0.003em;
            color: #365899;
            text-align: center;
        }

        .mei-email-template--app-and-sales {
            margin: 16px auto 48px;
            padding: 0 36px;
            width: 100%;
            max-width: 772px;
            font-family: 'Mori Gothic', sans-serif;
            font-style: normal;
            font-weight: 400;
            font-size: 16px;
            line-height: 26px;
            letter-spacing: -0.003em;
            color: #393939;
        }

        .app-stores {
            margin: 20px 0;
        }

        .app-stores > a:not(:last-child) {
            margin-right: 24px;
        }

        .app-stores > a > img {
            width: 194px;
        }

        .mei-email-template--app-and-sales > span {
            margin: 16px 0 0;
        }

        .mei-email-template--app-and-sales > div {
            margin: 8px 0;
        }

        .mei-email-template--app-and-sales > a,
        .mei-email-template--app-and-sales > div > a {
            color: #393939;
        }


        .mei-email-template--footer {
            width: 100%;
            padding: 0 0 36px;
            text-align: center;
            background: #f7f8fa;
        }

        .footer-border-gradient {
            margin-bottom: 256px;
            display: block;
            width: 100%;
            height: 5px;
            background: #405896;
            background: linear-gradient(45deg, #405896, #4a8eb9);
        }

        .mei-email-template--footer > img {
            width: 78px;
        }

        .mei-email-template--footer > p {
            font-family: 'Mori Gothic', sans-serif;
            font-style: normal;
            font-weight: 400;
            font-size: 18px;
            line-height: 29px;
            letter-spacing: -0.003em;
            color: #000000;
            margin: 16px 0;
            text-align: center;
        }

        .footer-text {
            width: 100%;
            padding: 0 22px;
            max-width: 772px;
            font-family: 'Mori Gothic', sans-serif;
            font-style: normal;
            font-weight: 300;
            font-size: 16px;
            line-height: 176%;
            text-align: center;
            letter-spacing: -0.003em;
            margin: 0 auto;
            color: #757474;
        }

        .footer-text > span.unsubscribe {
            font-weight: 400;
        }

        .footer-text > span.user-email {
            text-decoration: underline;
        }

        .footer-text > span > a {
            color: #757474;
        }

        @media screen and (max-width: 432px) {
            .main {
                border-radius: 16px;
                font-size: 14px;
            }

            .mei-email-template--header {
                margin: 0 12px;
                padding: 16px 0;
                border-bottom: 1px solid #f7f5f5;
            }

            .mei-email-template--header > img {
                width: 100px;
            }

            .mei-email-template--body-wrapper {
                margin: 20px 0 0;
                font-size: 14px;
                padding: 30px 12px 0;
            }

            .mei-email-template--body-wrapper > .thank-you-text {
                margin: 30px 0 16px;
            }

            .mei-email-template--app-and-sales {
                margin: 20px 0;
                font-size: 14px;
                padding: 0 12px;
            }

            .app-stores {
                margin: 20px 0;
            }

            .app-stores > a:not(:last-child) {
                margin-right: 12px;
            }

            .app-stores > a > img {
                width: 120px;
            }

            .mei-email-template--footer {
                border: none;
            }

            .mei-email-template--footer > img {
                width: 45px;
            }

            .mei-email-template--footer > p {
                font-size: 16px;
            }

            .footer-text {
                font-size: 14px;
            }
        }
    </style>
</head>
<body>
<div class="wrapper">
    <table class="main" width="100%">
        <tr>
            <td>
                <table>
                    <tr>
                        <td class="mei-email-template--header">
                        </td>
                    </tr>
                </table>
                <table>
                    <tr>
                        <td>
                            <div style="align-items: center; justify-self: center;" class="mei-email-template--body-wrapp=
er">
                                <h4>Hello <strong>there</strong>, </h4>
                                <p>
                                   Copy the One Time Password (OTP) below and paste it in the app to verify you are the user logging in.
                                </p>
                            </div>
                        </td>
                    </tr>
                </table>

                <table>
                    <tr>
                        <td>
                            <div class="mei-email-template--otp-code">
                                <p>$otp_code</p>
                            </div>
                        </td>
                    </tr>
                </table>

                <table >
                    <tr>
                        <td>
                            <div style="justify-self: center;" class="mei-email-template--body-wrapp=
er">
                                <p>
                                    DO NOT SHARE OR SEND THIS CODE TO ANYONE!
                                </p>
                            </div>
                        </td>
                    </tr>
                </table>

                <table style="height: 300px;">
                    <tr>
                        <td>
                            <div class="mei-email-template--footer">
                                <div class="footer-border-gradient"></div=
>
                                <img  style="width: 50px; height: 50px; border-radius: 25%; margin-top:10px ;"  src="https://res.cloudinary.com/dfmzougki/image/upload/fl_preserve_transparency/v1747719299/mei-logo_sfv8nl.jpg?_s=public-apps" alt=
="mei Logo"/>
                                <p style="padding: 0 22px">Mei. All rights reserved.</p>
                                <div class="footer-text">
                                    This email was intended for <span class=
="user-email">$user_email</span>. This message
                                    is intended only for the personal and c=
onfidential use of the designated recipient(s). If you
                                    are not the intended recipient of this =
message you are hereby notified that any review,
                                    dissemination, distribution or copying =
of this message is strictly prohibited.
                                    
                                </div>
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</div>
</body>
</html>

""")

def generate_email_from_template(otp_code,user_email):
    generated_email = email_template_string.substitute(otp_code=otp_code,user_email=user_email)
    return generated_email


from schemas.email_schema import ClientData
from repositories.email_repo import create_email_log
import os
import yagmail
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
        "timezone":data.get("timezone",None)
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
    email_body_content = generate_email_from_template(otp_code=otp,user_email=receiver_email)
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