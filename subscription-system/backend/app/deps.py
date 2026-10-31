from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue.")
    if not cred:
        raise err
    try:
        payload = decode_token(cred.credentials)
        user = db.get(User, int(payload["sub"]))
    except Exception:
        raise err
    if not user or not user.is_active:
        raise err
    return user


def require_roles(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't do this.")
        return user
    return dep


admin_only = require_roles("admin")
staff_or_admin = require_roles("admin", "staff")
customer_only = require_roles("customer")
