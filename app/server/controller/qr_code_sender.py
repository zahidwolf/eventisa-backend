import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
from datetime import datetime
import base64
from server.constant_file import eventisa_email, eventisa_email_password


async def send_qr_ticket_email(email: str, user_name: str, event_name: str,
                               event_location: str, event_date, event_time,
                               ticket_no: int, qr_data: str):

    def send_blocking_email():
        try:
            def safe_format(value, fmt):
                if isinstance(value, datetime):
                    return value.strftime(fmt)
                try:
                    return datetime.fromisoformat(str(value)).strftime(fmt)
                except Exception:
                    return str(value)

            formatted_date = safe_format(event_date, '%B %d, %Y')
            formatted_time = safe_format(event_time, '%I:%M %p')

            message = MIMEMultipart("related")
            message['From'] = eventisa_email
            message['To'] = email
            message['Subject'] = f"{event_name} - Your Ticket #{ticket_no}"

            # HTML with embedded QR code via CID
            html_body = f"""
            <html>
            <head>
                <style>
                    body {{
                        font-family: 'Segoe UI', Arial, sans-serif;
                        background-color: #f4f6f9;
                        color: #333;
                        margin: 0;
                        padding: 0;
                    }}
                    .ticket-container {{
                        background-color: #fff;
                        border: 2px solid #007bff;
                        border-radius: 15px;
                        padding: 25px;
                        margin: 30px auto;
                        width: 600px;
                        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        text-align: center;
                        color: #007bff;
                        font-size: 24px;
                        font-weight: bold;
                        margin-bottom: 15px;
                    }}
                    .details {{
                        text-align: center;
                        font-size: 16px;
                        margin-bottom: 20px;
                    }}
                    .qr-code {{
                        text-align: center;
                        margin: 20px 0;
                    }}
                    .footer {{
                        text-align: center;
                        font-size: 14px;
                        color: #666;
                    }}
                </style>
            </head>
            <body>
                <div class="ticket-container">
                    <div class="header">{event_name} - Ticket Confirmation</div>
                    <div class="details">
                        <p>Hi <b>{user_name}</b>,</p>
                        <p>Thank you for booking! Here’s your <b>Ticket #{ticket_no}</b>.</p>
                        <p>📍 <b>Location:</b> {event_location}<br>
                           📅 <b>Date:</b> {formatted_date}<br>
                           ⏰ <b>Time:</b> {formatted_time}</p>
                    </div>
                    <div class="qr-code">
                        <img src="cid:qrimage" alt="QR Code Ticket {ticket_no}" width="200" height="200"/>
                    </div>
                    <div class="footer">
                        Please show this ticket at the event entrance.<br>
                        Wishing you a fantastic experience! 🎉
                    </div>
                </div>
            </body>
            </html>
            """

            # Attach HTML body
            alt = MIMEMultipart("alternative")
            alt.attach(MIMEText(html_body, 'html'))
            message.attach(alt)

            # Decode base64 QR and attach as inline image
            qr_bytes = base64.b64decode(qr_data)
            img = MIMEImage(qr_bytes, name=f"ticket_{ticket_no}.png")
            img.add_header('Content-ID', '<qrimage>')
            img.add_header('Content-Disposition', 'inline', filename=f"ticket_{ticket_no}.png")
            message.attach(img)

            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(eventisa_email, eventisa_email_password)
            server.sendmail(eventisa_email, email, message.as_string())
            server.quit()

            print(f"✅ Ticket #{ticket_no} with QR sent to {email}")
            return True

        except Exception as e:
            print(f"❌ SMTP Error while sending ticket {ticket_no}: {e}")
            return False

    return await asyncio.to_thread(send_blocking_email)
