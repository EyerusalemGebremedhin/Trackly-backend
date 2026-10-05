import smtplib
from email.message import EmailMessage

from tracker.core.config import settings


def send_email(to: str, subject: str, body: str) -> None:
    if not settings.SMTP_HOST:
        print("\n----- EMAIL (SMTP not set up, printed here instead) -----")
        print(f"To: {to}")
        print(f"Subject: {subject}\n")
        print(body)
        print("---------------------------------------------------------\n", flush=True)
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM or settings.SMTP_USER
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)