from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import customer_only, get_db
from ..models import Plan, Product, Subscription, User
from ..schemas import PlanOut, PortalRequestIn, ProductPublic, SubscriptionOut
from .sales import check_min_qty, do_transition, make_lines, plan_is_sellable

router = APIRouter(prefix="/portal", tags=["customer portal"])


@router.get("/catalog")
def catalog(db: Session = Depends(get_db), me: User = Depends(customer_only)):
    today = date.today()
    plans = [p for p in db.scalars(select(Plan).where(Plan.status == "active")).unique()
             if not plan_is_sellable(p, today)]
    products = db.scalars(select(Product).where(Product.active.is_(True))).all()
    return {"plans": [PlanOut.model_validate(p) for p in plans],
            "products": [ProductPublic.model_validate(p) for p in products]}


@router.get("/subscriptions", response_model=list[SubscriptionOut])
def my_subscriptions(db: Session = Depends(get_db), me: User = Depends(customer_only)):
    rows = db.scalars(select(Subscription).where(Subscription.customer_id == me.id, Subscription.status != "draft")
                      .order_by(Subscription.id.desc())).unique().all()
    return rows


@router.post("/subscriptions", response_model=SubscriptionOut, status_code=201)
def request_subscription(body: PortalRequestIn, db: Session = Depends(get_db), me: User = Depends(customer_only)):
    """Customer asks for a plan; it lands as a Quotation for the team to confirm."""
    plan = db.get(Plan, body.plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found.")
    if msg := plan_is_sellable(plan, date.today()):
        raise HTTPException(422, msg)
    for l in body.lines:  # customers can't set their own prices or taxes
        l.unit_price, l.tax_id = None, None
    lines = make_lines(db, body.lines)
    check_min_qty(plan, lines)
    today = date.today()
    sub = Subscription(customer_id=me.id, plan_id=plan.id, start_date=today,
                       expiry_date=today + timedelta(days=365), payment_terms_days=0,
                       status="quotation", quote_valid_until=today + timedelta(days=30), created_by_id=me.id)
    sub.lines[:] = lines
    db.add(sub)
    db.flush()
    sub.number = f"SUB-{sub.id:06d}"
    db.commit()
    return sub


@router.post("/subscriptions/{sid}/close", response_model=SubscriptionOut)
def close_mine(sid: int, db: Session = Depends(get_db), me: User = Depends(customer_only)):
    sub = db.get(Subscription, sid)
    if not sub or sub.customer_id != me.id:
        raise HTTPException(404, "Subscription not found.")
    if sub.status != "active":
        raise HTTPException(409, "Only active subscriptions can be closed.")
    do_transition(db, sub, "closed")
    db.commit()
    return sub
