import os

SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me-before-deploying-0123456789")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./subscriptions.db")
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "480"))
RESET_MINUTES = int(os.getenv("RESET_MINUTES", "60"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
# 0 disables the background billing loop (you can still run billing from the UI/API)
BILLING_INTERVAL_MINUTES = int(os.getenv("BILLING_INTERVAL_MINUTES", "60"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@1234")
# Optional SMTP. Without SMTP_HOST, emails are printed to the server log.
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "billing@example.com")
