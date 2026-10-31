import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # the backend/ folder
load_dotenv(BASE_DIR / ".env")  # settings in backend/.env are picked up automatically

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me-before-deploying-0123456789")
# Absolute path, so the same database is used no matter which folder you start the server from.
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'subscriptions.db').as_posix()}")
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "480"))
RESET_MINUTES = int(os.getenv("RESET_MINUTES", "60"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
# 0 disables the background billing loop (you can still run billing from the UI/API)
BILLING_INTERVAL_MINUTES = int(os.getenv("BILLING_INTERVAL_MINUTES", "60"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@1234")

# ---- Email. Without SMTP_HOST, emails are printed to the console and saved in backend/outbox/.
SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "")  # Gmail app passwords are shown with spaces
SMTP_SECURITY = os.getenv("SMTP_SECURITY", "auto").lower()  # auto | starttls | ssl | none
MAIL_FROM = os.getenv("MAIL_FROM", "").strip() or SMTP_USER or "billing@example.com"
APP_NAME = os.getenv("APP_NAME", "Subscription Manager")
