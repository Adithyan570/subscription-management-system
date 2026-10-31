from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..deps import get_db, staff_or_admin
from ..models import (Discount, Plan, Product, ProductVariant, QuotationTemplate, Subscription,
                      SubscriptionLine, User)
from ..schemas import Page, SubLineIn, SubscriptionIn, SubscriptionOut, TransitionIn

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

# strictly one step forward; closing is only possible from Active
NEXT = {"draft": "quotation", "quotation": "confirmed", "confirmed": "active", "active": "closed"}


def plan_is_sellable(plan: Plan, today: date) -> str | None:
    if plan.status != "active":
        return f"Plan “{plan.name}” is {plan.status} and can't take new subscriptions."
    if plan.available_from and today < plan.available_from:
        return f"Plan “{plan.name}” isn't available until {plan.available_from}."
    if plan.available_until and today > plan.available_until:
        return f"Plan “{plan.name}” is no longer available."
    return None


def make_lines(db: Session, items: list[SubLineIn]) -> list[SubscriptionLine]:
    out = []
    for it in items:
        prod = db.get(Product, it.product_id)
        if not prod or not prod.active:
            raise HTTPException(422, "A product on this subscription doesn't exist or is inactive.")
        extra = 0.0
        if it.variant_id:
            var = db.get(ProductVariant, it.variant_id)
            if not var or var.product_id != prod.id:
                raise HTTPException(422, f"That variant doesn't belong to {prod.name}.")
            extra = var.extra_price
        price = it.unit_price if it.unit_price is not None else round(prod.sales_price + extra, 2)
        out.append(SubscriptionLine(product_id=prod.id, variant_id=it.variant_id, quantity=it.quantity,
                                    unit_price=price, tax_id=it.tax_id if it.tax_id else prod.default_tax_id))
    return out


def check_min_qty(plan: Plan, lines: list):
    qty = sum(l.quantity for l in lines) or 1
    if qty < plan.min_quantity:
        raise HTTPException(422, f"Plan “{plan.name}” needs a minimum quantity of {plan.min_quantity}.")


def build(db: Session, body: SubscriptionIn, me: User, sub: Subscription | None = None) -> Subscription:
    cust = db.get(User, body.customer_id)
    if not cust or cust.role != "customer":
        raise HTTPException(422, "Choose a customer.")
    tpl = db.get(QuotationTemplate, body.template_id) if body.template_id else None
    plan_id = body.plan_id or (tpl.plan_id if tpl else None)
    plan = db.get(Plan, plan_id) if plan_id else None
    if not plan:
        raise HTTPException(422, "Choose a plan.")
    if msg := plan_is_sellable(plan, date.today()):
        raise HTTPException(422, msg)
    if body.expiry_date <= body.start_date:
        raise HTTPException(422, "Expiry date must be after the start date.")
    if body.discount_id and not db.get(Discount, body.discount_id):
        raise HTTPException(422, "That discount doesn't exist.")
    items = body.lines or ([SubLineIn(product_id=l.product_id, variant_id=l.variant_id, quantity=l.quantity)
                            for l in tpl.lines] if tpl else [])
    lines = make_lines(db, items)
    check_min_qty(plan, lines)
    sub = sub or Subscription(created_by_id=me.id)
    sub.customer_id, sub.plan_id, sub.template_id = cust.id, plan.id, tpl.id if tpl else None
    sub.discount_id, sub.start_date, sub.expiry_date = body.discount_id, body.start_date, body.expiry_date
    sub.payment_terms_days = body.payment_terms_days
    sub.lines[:] = lines
    return sub


def load(db: Session, sid: int) -> Subscription:
    sub = db.get(Subscription, sid)
    if not sub:
        raise HTTPException(404, "Subscription not found.")
    return sub


def do_transition(db: Session, sub: Subscription, to: str):
    if NEXT.get(sub.status) != to:
        raise HTTPException(409, f"A {sub.status} subscription can't move to {to}. "
                                 f"Stages go Draft → Quotation → Confirmed → Active → Closed.")
    today = date.today()
    if to == "quotation":
        days = sub.template_id and db.get(QuotationTemplate, sub.template_id).validity_days or 30
        sub.quote_valid_until = today + timedelta(days=days)
    elif to == "confirmed":
        if sub.quote_valid_until and sub.quote_valid_until < today:
            raise HTTPException(409, "This quotation has expired. Create a new one.")
        if msg := plan_is_sellable(sub.plan, today):
            raise HTTPException(409, msg)
        check_min_qty(sub.plan, sub.lines)
    elif to == "active":
        sub.billed_cycles, sub.next_billing_date = 0, sub.start_date
    elif to == "closed":
        sub.next_billing_date = None
    sub.status = to


@router.get("", response_model=Page, dependencies=[Depends(staff_or_admin)])
def list_subs(status: str = "", customer_id: int | None = None, plan_id: int | None = None, q: str = "",
              limit: int = Query(25, le=200), offset: int = 0, db: Session = Depends(get_db)):
    stmt = select(Subscription).join(User, User.id == Subscription.customer_id)
    if status:
        stmt = stmt.where(Subscription.status == status)
    if customer_id:
        stmt = stmt.where(Subscription.customer_id == customer_id)
    if plan_id:
        stmt = stmt.where(Subscription.plan_id == plan_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Subscription.number.ilike(like), User.name.ilike(like), User.email.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.order_by(Subscription.id.desc()).limit(limit).offset(offset)).unique().all()
    return Page(items=[SubscriptionOut.model_validate(r) for r in rows], total=total)


@router.post("", response_model=SubscriptionOut, status_code=201)
def create_sub(body: SubscriptionIn, db: Session = Depends(get_db), me: User = Depends(staff_or_admin)):
    sub = build(db, body, me)
    db.add(sub)
    db.flush()
    sub.number = f"SUB-{sub.id:06d}"
    db.commit()
    return sub


@router.get("/{sid}", response_model=SubscriptionOut, dependencies=[Depends(staff_or_admin)])
def get_sub(sid: int, db: Session = Depends(get_db)):
    return load(db, sid)


@router.put("/{sid}", response_model=SubscriptionOut)
def update_sub(sid: int, body: SubscriptionIn, db: Session = Depends(get_db), me: User = Depends(staff_or_admin)):
    sub = load(db, sid)
    if sub.status != "draft":
        raise HTTPException(409, "Only draft subscriptions can be edited.")
    build(db, body, me, sub)
    db.commit()
    return sub


@router.post("/{sid}/transition", response_model=SubscriptionOut, dependencies=[Depends(staff_or_admin)])
def transition(sid: int, body: TransitionIn, db: Session = Depends(get_db)):
    sub = load(db, sid)
    do_transition(db, sub, body.to)
    db.commit()
    return sub


@router.delete("/{sid}", status_code=204, dependencies=[Depends(staff_or_admin)])
def delete_draft(sid: int, db: Session = Depends(get_db)):
    sub = load(db, sid)
    if sub.status != "draft":
        raise HTTPException(409, "Only draft subscriptions can be deleted. Close active ones instead.")
    db.delete(sub)
    db.commit()
