import logging
import smtplib
from email.message import EmailMessage

from . import config

log = logging.getLogger("mailer")


def send_email(to: str, subject: str, body: str) -> None:
    """Send via SMTP when configured; otherwise print to the server log (dev mode)."""
    if not config.SMTP_HOST:
        log.warning("EMAIL (dev, not sent)\nTo: %s\nSubject: %s\n\n%s", to, subject, body)
        print(f"\n--- EMAIL to {to} ---\n{subject}\n\n{body}\n---------------------\n", flush=True)
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = config.MAIL_FROM, to, subject
    msg.set_content(body)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as s:
        s.starttls()
        if config.SMTP_USER:
            s.login(config.SMTP_USER, config.SMTP_PASSWORD)
        s.send_message(msg)
