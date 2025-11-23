import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random
import smtplib
from server.constant_file  import (eventisa_email,
                                   eventisa_email_password,
                                   password_reset_subject,
                                   Otp_verification_subject)


def generate_otp():
    return ''.join(random.choices('0123456789', k=6))

async def send_email(email: str, otp: str,msg:str):
    # Function body that performs the actual sending operation
    def send_blocking_email():
        # NOTE: This inner function is synchronous (no 'async def')
        try:
            message = MIMEMultipart() 
            message['From'] = eventisa_email
            message['To'] = email
            subject=""
            if msg=="reset":
                subject=password_reset_subject
            elif msg=="verification":
                subject=Otp_verification_subject
            message['Subject'] = subject

            email_message = f"Your OTP is <b>{otp}</b>. This OTP will expire in 5 minutes."
            message.attach(MIMEText(email_message, 'html'))
            
            # --- Blocking SMTP Execution ---
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(eventisa_email, eventisa_email_password) 
            text = message.as_string()
            server.sendmail(eventisa_email, email, text) 
            server.quit()
            return True
        

        
        except Exception as e:
            print(f"SMTP Error: {e}")
            return False

    try:
        # Run the blocking operation in a separate thread, freeing the event loop.
        # This is the crucial performance improvement.
        return await asyncio.to_thread(send_blocking_email)
        
    except Exception as e:
        print(f"Email Composition Error (or unexpected thread error): {e}")
        return False
