import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from . import config


def validate_password(pw: str) -> str | None:
    """Return an error message, or None if the password is acceptable."""
    if len(pw) <= 8:
        return "Password must be longer than 8 characters."
    if not re.search(r"[A-Z]", pw):
        return "Password needs at least one uppercase letter."
    if not re.search(r"[a-z]", pw):
        return "Password needs at least one lowercase letter."
    if not re.search(r"[^A-Za-z0-9]", pw):
        return "Password needs at least one special character."
    if len(pw.encode()) > 72:
        return "Password must be at most 72 bytes."
    return None


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user_id: int, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_MINUTES)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, config.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, config.SECRET_KEY, algorithms=["HS256"])


def new_reset_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode()).hexdigest()


def hash_reset_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
