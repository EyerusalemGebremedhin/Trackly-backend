from email.message import EmailMessage
import smtplib
import ssl

from tracker.core.config import settings


def send_email(to: str, subject: str, body: str, html_body: str = None) -> None:
    try:
        message = EmailMessage()
        from_addr = settings.SMTP_FROM or "trackly15@gmail.com"
        message["From"] = from_addr
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, int(settings.SMTP_PORT), timeout=10) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        print(f"EMAIL_SENT:{to}", flush=True)
    except Exception as exc:
        print(f"EMAIL_ERR:{exc}", flush=True)
