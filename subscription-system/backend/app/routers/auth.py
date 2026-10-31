from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import config
from ..deps import current_user, get_db
from ..mailer import send_email
from ..models import PasswordReset, User, utcnow
from ..schemas import ForgotIn, LoginIn, RegisterIn, ResetIn, TokenOut, UserOut
from ..security import (create_token, hash_password, hash_reset_token, new_reset_token,
                        validate_password, verify_password)

router = APIRouter(prefix="/auth", tags=["auth"])


def email_taken(db: Session, email: str) -> bool:
    return db.scalar(select(User.id).where(func.lower(User.email) == email.lower())) is not None


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if err := validate_password(body.password):
        raise HTTPException(422, err)
    if email_taken(db, body.email):
        raise HTTPException(409, "An account with this email already exists.")
    user = User(email=body.email.lower(), name=body.name.strip(), role="customer",
                password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return TokenOut(access_token=create_token(user.id, user.role), user=user)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Email or password is incorrect.")
    return TokenOut(access_token=create_token(user.id, user.role), user=user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/forgot-password")
def forgot_password(body: ForgotIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if user and user.is_active:
        raw, hashed = new_reset_token()
        db.add(PasswordReset(user_id=user.id, token_hash=hashed,
                             expires_at=utcnow() + timedelta(minutes=config.RESET_MINUTES)))
        db.commit()
        link = f"{config.FRONTEND_URL}/reset-password?token={raw}"
        send_email(user.email, "Reset your password",
                   f"Use this link to choose a new password (valid {config.RESET_MINUTES} minutes):\n\n{link}")
    # same answer either way, so the endpoint can't be used to discover registered emails
    return {"message": "If that email is registered, a reset link is on its way."}


@router.post("/reset-password")
def reset_password(body: ResetIn, db: Session = Depends(get_db)):
    if err := validate_password(body.password):
        raise HTTPException(422, err)
    pr = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == hash_reset_token(body.token)))
    if not pr or pr.used or pr.expires_at < utcnow():
        raise HTTPException(400, "This reset link is invalid or has expired. Request a new one.")
    user = db.get(User, pr.user_id)
    user.password_hash = hash_password(body.password)
    pr.used = True
    db.commit()
    return {"message": "Password updated. You can sign in now."}
