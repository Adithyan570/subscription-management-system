import logging
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from . import config

log = logging.getLogger("mailer")
OUTBOX = config.BASE_DIR / "outbox"


def _security() -> str:
    if config.SMTP_SECURITY != "auto":
        return config.SMTP_SECURITY
    return {465: "ssl", 587: "starttls"}.get(config.SMTP_PORT, "none")


def email_is_configured() -> bool:
    return bool(config.SMTP_HOST)


def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Send an email. Returns True on success; never raises (a mail problem must not break a request).

    With SMTP_HOST set it is delivered through that SMTP server. Otherwise it is printed to the
    console and saved as a .eml file in backend/outbox/ (development mode, nothing is delivered).
    """
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = f"{config.APP_NAME} <{config.MAIL_FROM}>", to, subject
    msg["Date"], msg["Message-ID"] = formatdate(localtime=True), make_msgid()
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    if not config.SMTP_HOST:
        OUTBOX.mkdir(exist_ok=True)
        (OUTBOX / f"{datetime.now():%Y%m%d-%H%M%S}-{to}.eml").write_bytes(bytes(msg))
        print(f"\n--- EMAIL (dev mode, NOT delivered; set SMTP_HOST to send for real) ---\n"
              f"To: {to}\nSubject: {subject}\n\n{text}\n---------------------------------------------\n", flush=True)
        return True

    mode = _security()
    try:
        if mode == "ssl":
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=20, context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20)
        with server:
            if mode == "starttls":
                server.starttls(context=ssl.create_default_context())
            if config.SMTP_USER:
                server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        log.info("Email sent to %s (%s)", to, subject)
        return True
    except Exception as exc:  # noqa: BLE001 - report every kind of failure the same way
        log.error("EMAIL FAILED to %s via %s:%s (%s): %s", to, config.SMTP_HOST, config.SMTP_PORT, mode, exc)
        return False
