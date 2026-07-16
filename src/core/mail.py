import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.config import settings


def _smtp_config():
    host = settings.SMTP_HOST
    port = settings.SMTP_PORT
    user = settings.SMTP_USER
    password = settings.SMTP_PASSWORD
    from_name = settings.SMTP_FROM_NAME
    notify = settings.NOTIFY_EMAIL
    return host, port, user, password, from_name, notify


def send_email(to: str, subject: str, body_html: str) -> bool:
    host, port, user, password, from_name, _ = _smtp_config()
    if not host or not user:
        print(f"[mail] SMTP not configured — would send to {to}: {subject}")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[mail] Failed to send to {to}: {e}")
        return False


def notify_new_subscriber(name: str, email: str) -> bool:
    subject = f"New Brownies sign-up: {name}"
    body = f"""
    <h2>New Waitlist Sign-up</h2>
    <p><strong>Name:</strong> {name}</p>
    <p><strong>Email:</strong> {email}</p>
    <hr>
    <p style="color:#888;font-size:12px">Brownies Landing Page</p>
    """
    _, _, _, _, _, notify = _smtp_config()
    return send_email(notify, subject, body)
