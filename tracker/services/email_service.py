import json
import urllib.request

from tracker.core.config import settings


def send_email(to: str, subject: str, body: str, html_body: str = None) -> None:
    try:
        url = settings.EMAIL_SCRIPT_URL
        secret = settings.EMAIL_SCRIPT_SECRET
        if not url or not secret:
            print("EMAIL_ERR:EMAIL_SCRIPT_URL or EMAIL_SCRIPT_SECRET not set", flush=True)
            return
        payload = {
            "secret": secret,
            "to": to,
            "subject": subject,
            "html": html_body or body,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"EMAIL_SENT:{to} {resp.read().decode()}", flush=True)
    except Exception as exc:
        print(f"EMAIL_ERR:{exc}", flush=True)