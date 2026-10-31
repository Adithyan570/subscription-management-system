import html
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from ..billing import run_billing
from ..deps import current_user, get_db, staff_or_admin
from ..mailer import send_email
from ..models import Invoice, Payment, Subscription, User, utcnow
from ..schemas import InvoiceDetail, InvoiceOut, Page, PaymentIn, PaymentOut

router = APIRouter(tags=["finance"])

OWED = Invoice.total - Invoice.amount_paid


def overdue_clause(today: date):
    return and_(Invoice.status == "confirmed", Invoice.due_date < today, OWED > 0.004)


def visible_invoice(db: Session, iid: int, me: User) -> Invoice:
    inv = db.get(Invoice, iid)
    if not inv:
        raise HTTPException(404, "Invoice not found.")
    if me.role == "customer" and (inv.customer_id != me.id or inv.status in ("draft", "cancelled")):
        raise HTTPException(404, "Invoice not found.")
    return inv


# ------------------------------------------------------------------ invoices
@router.get("/invoices", response_model=Page, dependencies=[Depends(staff_or_admin)])
def list_invoices(status: str = "", overdue: bool = False, customer_id: int | None = None,
                  subscription_id: int | None = None, q: str = "",
                  date_from: date | None = None, date_to: date | None = None,
                  limit: int = Query(25, le=200), offset: int = 0, db: Session = Depends(get_db)):
    stmt = select(Invoice).join(User, User.id == Invoice.customer_id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    if overdue:
        stmt = stmt.where(overdue_clause(date.today()))
    if customer_id:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    if subscription_id:
        stmt = stmt.where(Invoice.subscription_id == subscription_id)
    if date_from:
        stmt = stmt.where(Invoice.issue_date >= date_from)
    if date_to:
        stmt = stmt.where(Invoice.issue_date <= date_to)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Invoice.number.ilike(like), User.name.ilike(like), User.email.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.order_by(Invoice.id.desc()).limit(limit).offset(offset)).unique().all()
    return Page(items=[InvoiceOut.model_validate(r) for r in rows], total=total)


@router.get("/invoices/{iid}", response_model=InvoiceDetail)
def get_invoice(iid: int, db: Session = Depends(get_db), me: User = Depends(current_user)):
    return visible_invoice(db, iid, me)


@router.post("/invoices/{iid}/confirm", response_model=InvoiceDetail, dependencies=[Depends(staff_or_admin)])
def confirm_invoice(iid: int, db: Session = Depends(get_db)):
    inv = db.get(Invoice, iid)
    if not inv:
        raise HTTPException(404, "Invoice not found.")
    if inv.status != "draft":
        raise HTTPException(409, f"Only draft invoices can be confirmed (this one is {inv.status}).")
    inv.status = "confirmed"
    db.commit()
    return inv


@router.post("/invoices/{iid}/cancel", response_model=InvoiceDetail, dependencies=[Depends(staff_or_admin)])
def cancel_invoice(iid: int, db: Session = Depends(get_db)):
    inv = db.get(Invoice, iid)
    if not inv:
        raise HTTPException(404, "Invoice not found.")
    if inv.status not in ("draft", "confirmed"):
        raise HTTPException(409, f"A {inv.status} invoice can't be cancelled.")
    if inv.amount_paid > 0:
        raise HTTPException(409, "This invoice has payments recorded, so it can't be cancelled.")
    inv.status = "cancelled"  # the cycle stays consumed: it will not be billed again
    db.commit()
    return inv


@router.post("/invoices/{iid}/send", response_model=InvoiceDetail, dependencies=[Depends(staff_or_admin)])
def send_invoice(iid: int, db: Session = Depends(get_db)):
    inv = db.get(Invoice, iid)
    if not inv:
        raise HTTPException(404, "Invoice not found.")
    if inv.status not in ("confirmed", "paid"):
        raise HTTPException(409, "Confirm the invoice before sending it.")
    send_email(inv.customer.email, f"Invoice {inv.number}",
               f"Hello {inv.customer_name},\n\nInvoice {inv.number} for {inv.total:.2f} "
               f"is due on {inv.due_date}.\nPeriod: {inv.period_start} to {inv.period_end}.\n\nThank you.")
    inv.sent_at = utcnow()
    db.commit()
    return inv


@router.get("/invoices/{iid}/print", response_class=HTMLResponse)
def print_invoice(iid: int, db: Session = Depends(get_db), me: User = Depends(current_user)):
    inv = visible_invoice(db, iid, me)
    e = html.escape
    rows = "".join(
        f"<tr><td>{e(l.description)}</td><td class=n>{l.quantity}</td><td class=n>{l.unit_price:.2f}</td>"
        f"<td class=n>{l.discount:.2f}</td><td class=n>{l.tax_rate:g}%</td><td class=n>{l.amount - l.discount + l.tax_amount:.2f}</td></tr>"
        for l in inv.lines)
    return HTMLResponse(f"""<!doctype html><meta charset=utf-8><title>{e(inv.number)}</title>
<style>body{{font:14px/1.5 system-ui,sans-serif;max-width:760px;margin:40px auto;color:#16202a}}
table{{width:100%;border-collapse:collapse;margin:24px 0}}th,td{{padding:8px;border-bottom:1px solid #d8dde3;text-align:left}}
.n{{text-align:right;font-variant-numeric:tabular-nums}}h1{{margin:0}}.t td{{border:0;padding:2px 8px}}
@media print{{body{{margin:0}}}}</style>
<h1>Invoice {e(inv.number)}</h1><p>Status: {e(inv.status)} &middot; Subscription {e(inv.subscription_number)}<br>
Billed to: {e(inv.customer_name)} ({e(inv.customer.email)})<br>Period: {inv.period_start} to {inv.period_end}<br>
Issued {inv.issue_date} &middot; Due {inv.due_date}</p>
<table><tr><th>Description</th><th class=n>Qty</th><th class=n>Unit price</th><th class=n>Discount</th><th class=n>Tax</th><th class=n>Total</th></tr>{rows}</table>
<table class=t style="width:300px;margin-left:auto"><tr><td>Subtotal</td><td class=n>{inv.subtotal:.2f}</td></tr>
<tr><td>Discount</td><td class=n>-{inv.discount_total:.2f}</td></tr><tr><td>Tax</td><td class=n>{inv.tax_total:.2f}</td></tr>
<tr><td><b>Total</b></td><td class=n><b>{inv.total:.2f}</b></td></tr><tr><td>Paid</td><td class=n>{inv.amount_paid:.2f}</td></tr>
<tr><td><b>Balance due</b></td><td class=n><b>{inv.outstanding:.2f}</b></td></tr></table>""")


@router.post("/invoices/{iid}/payments", response_model=InvoiceDetail)
def record_payment(iid: int, body: PaymentIn, db: Session = Depends(get_db), me: User = Depends(staff_or_admin)):
    inv = db.get(Invoice, iid)
    if not inv:
        raise HTTPException(404, "Invoice not found.")
    if inv.status != "confirmed":
        raise HTTPException(409, "Payments can only be recorded against confirmed invoices.")
    if body.amount > inv.outstanding + 0.004:
        raise HTTPException(422, f"That's more than the {inv.outstanding:.2f} still owed on this invoice.")
    db.add(Payment(invoice_id=inv.id, method=body.method, amount=body.amount, notes=body.notes,
                   paid_on=body.paid_on or date.today(), recorded_by_id=me.id))
    inv.amount_paid = round(inv.amount_paid + body.amount, 2)
    if inv.total - inv.amount_paid <= 0.004:
        inv.status = "paid"
    db.commit()
    db.refresh(inv)
    return inv


@router.get("/customer-invoices", response_model=list[InvoiceOut])
def my_invoices(db: Session = Depends(get_db), me: User = Depends(current_user)):
    if me.role != "customer":
        raise HTTPException(403, "This list is for customers.")
    return db.scalars(select(Invoice).where(Invoice.customer_id == me.id, Invoice.status.in_(("confirmed", "paid")))
                      .order_by(Invoice.id.desc())).unique().all()


# ------------------------------------------------------------------ billing
@router.post("/billing/run", dependencies=[Depends(staff_or_admin)])
def billing_run(auto_confirm: bool = False, on: date | None = None, db: Session = Depends(get_db)):
    return run_billing(db, today=on, auto_confirm=auto_confirm)


# ------------------------------------------------------------------ dashboard
@router.get("/dashboard", dependencies=[Depends(staff_or_admin)])
def dashboard(date_from: date | None = None, date_to: date | None = None, plan_id: int | None = None,
              db: Session = Depends(get_db)):
    today = date.today()
    date_to = date_to or today
    date_from = date_from or today.replace(day=1)

    def plan_join(stmt):
        return stmt.join(Subscription, Subscription.id == Invoice.subscription_id).where(
            Subscription.plan_id == plan_id) if plan_id else stmt

    active_stmt = select(func.count(Subscription.id)).where(Subscription.status == "active")
    if plan_id:
        active_stmt = active_stmt.where(Subscription.plan_id == plan_id)
    active = db.scalar(active_stmt)

    pay_stmt = select(func.coalesce(func.sum(Payment.amount), 0)).join(Invoice, Invoice.id == Payment.invoice_id)
    pay_stmt = plan_join(pay_stmt).where(Payment.paid_on.between(date_from, date_to))
    collected = db.scalar(pay_stmt)

    # all-time money still owed, and the overdue share of it
    o = plan_join(select(
        func.coalesce(func.sum(OWED), 0),
        func.coalesce(func.sum(case((overdue_clause(today), OWED), else_=0)), 0),
        func.count(case((overdue_clause(today), 1))),
    ).where(Invoice.status == "confirmed"))
    owed, overdue_amount, overdue_count = db.execute(o).one()

    # ledger for invoices issued in the selected range
    led = plan_join(select(
        func.coalesce(func.sum(Invoice.total), 0),
        func.coalesce(func.sum(Invoice.amount_paid), 0),
        func.coalesce(func.sum(case((overdue_clause(today), OWED), else_=0)), 0),
    ).where(Invoice.status.in_(("confirmed", "paid")), Invoice.issue_date.between(date_from, date_to)))
    billed, led_paid, led_overdue = db.execute(led).one()

    counts = dict(db.execute(plan_join(select(Invoice.status, func.count()).group_by(Invoice.status))).all())

    # collections per month for the last 12 months (bucketed in Python so it works on any database)
    start12 = (today.replace(day=1) - timedelta(days=330)).replace(day=1)
    per_day = db.execute(plan_join(select(Payment.paid_on, func.sum(Payment.amount)).join(
        Invoice, Invoice.id == Payment.invoice_id)).where(Payment.paid_on >= start12).group_by(Payment.paid_on)).all()
    months: dict[str, float] = {}
    for d, amt in per_day:
        months[d.strftime("%Y-%m")] = months.get(d.strftime("%Y-%m"), 0) + amt

    worst = db.scalars(plan_join(select(Invoice)).where(overdue_clause(today))
                       .order_by(Invoice.due_date).limit(10)).unique().all()
    return {
        "range": {"from": date_from, "to": date_to},
        "active_subscriptions": active,
        "revenue_collected": round(collected, 2),
        "amount_owed": round(owed, 2),
        "overdue_amount": round(overdue_amount, 2),
        "overdue_count": overdue_count,
        "ledger": {"billed": round(billed, 2), "collected": round(led_paid, 2),
                   "overdue": round(led_overdue, 2),
                   "open": round(max(billed - led_paid - led_overdue, 0), 2)},
        "invoice_counts": counts,
        "monthly_collections": [{"month": k, "amount": round(v, 2)} for k, v in sorted(months.items())],
        "overdue_invoices": [InvoiceOut.model_validate(i) for i in worst],
    }
