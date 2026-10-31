from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..deps import get_db, staff_or_admin
from ..models import User
from ..schemas import PersonCreate, PersonUpdate, UserOut
from ..security import hash_password, validate_password
from .auth import email_taken

router = APIRouter(prefix="/people", tags=["people"])


@router.get("", response_model=list[UserOut])
def list_people(group: str = Query("customer", pattern="^(customer|team)$"), q: str = "",
                db: Session = Depends(get_db), me: User = Depends(staff_or_admin)):
    if group == "team" and me.role != "admin":
        raise HTTPException(403, "Only admins can see the team list.")
    roles = ["customer"] if group == "customer" else ["admin", "staff"]
    stmt = select(User).where(User.role.in_(roles))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.name.ilike(like)))
    return db.scalars(stmt.order_by(User.id.desc()).limit(500)).all()


@router.post("", response_model=UserOut, status_code=201)
def create_person(body: PersonCreate, db: Session = Depends(get_db), me: User = Depends(staff_or_admin)):
    if body.role != "customer" and me.role != "admin":
        raise HTTPException(403, "Only admins can add staff.")
    if err := validate_password(body.password):
        raise HTTPException(422, err)
    if email_taken(db, body.email):
        raise HTTPException(409, "An account with this email already exists.")
    u = User(email=body.email.lower(), name=body.name.strip(), role=body.role,
             password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    return u


@router.put("/{uid}", response_model=UserOut)
def update_person(uid: int, body: PersonUpdate, db: Session = Depends(get_db), me: User = Depends(staff_or_admin)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "Not found.")
    if u.role != "customer" and me.role != "admin":
        raise HTTPException(403, "Only admins can change staff.")
    if u.id == me.id and body.is_active is False:
        raise HTTPException(400, "You can't deactivate your own account.")
    if body.name is not None:
        u.name = body.name.strip()
    if body.is_active is not None:
        u.is_active = body.is_active
    db.commit()
    return u
