"""Billing engine: turns active subscriptions into invoices, one per cycle, never twice, never skipped."""
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Discount, Invoice, InvoiceLine, Plan, Subscription

_STEP = {"daily": "days", "weekly": "weeks", "monthly": "months", "yearly": "years"}


def nth_period_start(start: date, period: str, n: int) -> date:
    """Start of the n-th cycle, always computed from the anchor date (avoids Jan 31 -> Feb 28 -> Mar 28 drift)."""
    return start + relativedelta(**{_STEP[period]: n})


def r2(x: float) -> float:
    return round(x + 1e-9, 2)


def discount_is_usable(d: Discount | None, on: date, subtotal: float, qty: int) -> bool:
    if not d or not d.active:
        return False
    if d.start_date and on < d.start_date:
        return False
    if d.end_date and on > d.end_date:
        return False
    if d.usage_limit is not None and d.used_count >= d.usage_limit:
        return False
    return subtotal >= d.min_purchase and qty >= d.min_quantity


def build_invoice(db: Session, sub: Subscription, cycle: int) -> Invoice:
    plan: Plan = sub.plan
    ps = nth_period_start(sub.start_date, plan.billing_period, cycle)
    pe = nth_period_start(sub.start_date, plan.billing_period, cycle + 1) - timedelta(days=1)

    # raw lines: (description, product_id, qty, unit_price, tax_rate)
    raw = []
    if plan.price:
        raw.append((f"Plan: {plan.name}", None, 1, plan.price, plan.tax.rate if plan.tax else 0.0))
    for l in sub.lines:
        raw.append((l.product_name, l.product_id, l.quantity, l.unit_price, l.tax_rate))

    amounts = [r2(q * p) for _, _, q, p, _ in raw]
    subtotal = r2(sum(amounts))
    qty_total = sum(q for _, _, q, _, _ in raw)

    # discount: applies automatically to each invoice while it stays usable
    disc_shares = [0.0] * len(raw)
    d = sub.discount
    if discount_is_usable(d, ps, subtotal, qty_total):
        idx = [i for i, r in enumerate(raw) if d.product_id is None or r[1] == d.product_id]
        base = sum(amounts[i] for i in idx)
        if base > 0:
            total_disc = r2(base * d.value / 100) if d.kind == "percent" else min(d.value, base)
            total_disc = min(r2(total_disc), base)
            running = 0.0
            for i in idx[:-1]:
                share = r2(total_disc * amounts[i] / base)
                disc_shares[i] = share
                running += share
            disc_shares[idx[-1]] = r2(total_disc - running)
            d.used_count += 1
            if d.usage_limit is not None and d.used_count >= d.usage_limit:
                d.active = False  # limit reached: expires

    inv = Invoice(
        subscription_id=sub.id, customer_id=sub.customer_id, cycle=cycle,
        period_start=ps, period_end=pe, issue_date=ps,
        due_date=ps + timedelta(days=sub.payment_terms_days), status="draft")
    tax_total = disc_total = 0.0
    for (desc, _pid, q, price, rate), amt, dsc in zip(raw, amounts, disc_shares):
        tax = r2((amt - dsc) * rate / 100)
        tax_total += tax
        disc_total += dsc
        inv.lines.append(InvoiceLine(description=desc, quantity=q, unit_price=price, amount=amt,
                                     discount=dsc, tax_rate=rate, tax_amount=tax))
    inv.subtotal, inv.discount_total, inv.tax_total = subtotal, r2(disc_total), r2(tax_total)
    inv.total = r2(subtotal - disc_total + tax_total)
    return inv


def close_finished_plans(db: Session, today: date) -> int:
    res = db.execute(update(Plan).where(Plan.auto_close.is_(True), Plan.status != "closed",
                                        Plan.available_until.is_not(None), Plan.available_until < today)
                     .values(status="closed"))
    return res.rowcount or 0


def run_billing(db: Session, today: date | None = None, auto_confirm: bool = False) -> dict:
    today = today or date.today()
    plans_closed = close_finished_plans(db, today)
    db.commit()

    ids = db.scalars(select(Subscription.id).where(
        Subscription.status == "active", Subscription.next_billing_date <= today)).all()
    created, skipped, closed = 0, 0, 0
    for sid in ids:
        sub = db.get(Subscription, sid)
        try:
            with db.begin_nested():  # one subscription failing never blocks the others
                while True:
                    cycle = sub.billed_cycles
                    ps = nth_period_start(sub.start_date, sub.plan.billing_period, cycle)
                    if ps > today or ps > sub.expiry_date:
                        break
                    exists = db.scalar(select(Invoice.id).where(
                        Invoice.subscription_id == sub.id, Invoice.period_start == ps))
                    if exists:
                        skipped += 1
                    else:
                        inv = build_invoice(db, sub, cycle)
                        if auto_confirm:
                            inv.status = "confirmed"
                        db.add(inv)
                        db.flush()
                        inv.number = f"INV-{inv.id:06d}"
                        created += 1
                    sub.billed_cycles = cycle + 1
                nxt = nth_period_start(sub.start_date, sub.plan.billing_period, sub.billed_cycles)
                sub.next_billing_date = nxt
                if nxt > sub.expiry_date and today > sub.expiry_date:
                    sub.status, sub.next_billing_date = "closed", None
                    closed += 1
        except IntegrityError:
            db.rollback()
            skipped += 1
            continue
        db.commit()
    return {"invoices_created": created, "already_billed": skipped,
            "subscriptions_closed": closed, "plans_closed": plans_closed, "ran_on": today.isoformat()}
