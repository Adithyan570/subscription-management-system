"""Check your email settings:   python send_test_email.py you@example.com"""
import sys

from app import config
from app.mailer import email_is_configured, send_email

if len(sys.argv) < 2:
    sys.exit("Usage: python send_test_email.py recipient@example.com")
print(f"SMTP host: {config.SMTP_HOST or '(not set, dev mode)'}  port: {config.SMTP_PORT}  user: {config.SMTP_USER or '(none)'}  from: {config.MAIL_FROM}")
ok = send_email(sys.argv[1], f"Test email from {config.APP_NAME}", "If you can read this, your email settings work.")
if not email_is_configured():
    print("SMTP_HOST is not set, so nothing was delivered. See the README section 'Real email'.")
print("SENT" if ok else "FAILED: see the error above (wrong password, port, or security mode?)")
sys.exit(0 if ok else 1)
