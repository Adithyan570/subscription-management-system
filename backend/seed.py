"""Load demo data.   python seed.py            -> small demo set
                    python seed.py --bulk 3000 -> also create ~N customers/subscriptions and their invoices
"""
import random
import sys
from datetime import date, timedelta

from app.billing import run_billing
from app.db import Base, SessionLocal, engine
from app.main import init_db
from app.models import (Discount, Payment, Plan, Product, ProductVariant, Subscription, SubscriptionLine, Tax, User)
from app.security import hash_password

random.seed(7)
init_db()
bulk = int(sys.argv[sys.argv.index("--bulk") + 1]) if "--bulk" in sys.argv else 0

with SessionLocal() as db:
    if db.query(Plan).count():
        sys.exit("Database already has data; delete subscriptions.db to reseed.")
    gst = Tax(name="GST 18%", rate=18)
    db.add_all([gst, Tax(name="GST 5%", rate=5)])
    db.flush()
    db.add(User(email="staff@example.com", name="Sam Staff", role="staff", password_hash=hash_password("Staff@1234")))
    db.add(User(email="customer@example.com", name="Casey Customer", role="customer", password_hash=hash_password("Cust@12345")))
    prods = [Product(name="Smart Router", type="goods", sales_price=2400, cost_price=1500, default_tax_id=gst.id,
                     variants=[ProductVariant(attribute="Brand", value="Acme", extra_price=560),
                               ProductVariant(attribute="Brand", value="Nimbus", extra_price=900)]),
             Product(name="Support Desk", type="service", sales_price=500, cost_price=200, default_tax_id=gst.id),
             Product(name="Cloud Storage 1TB", type="service", sales_price=250, cost_price=90, default_tax_id=gst.id)]
    db.add_all(prods)
    plans = [Plan(name="Starter Monthly", price=299, billing_period="monthly"),
             Plan(name="Business Yearly", price=2999, billing_period="yearly", tax_id=gst.id),
             Plan(name="Weekly Trial", price=49, billing_period="weekly", auto_close=True,
                  available_until=date.today() + timedelta(days=90))]
    db.add_all(plans)
    db.add(Discount(name="Welcome 10%", kind="percent", value=10, usage_limit=3))
    db.add(Discount(name="₹100 off big orders", kind="fixed", value=100, min_purchase=1000))
    db.commit()

    cust_hash = hash_password("Cust@12345")
    n = max(bulk, 12)
    custs = [User(email=f"cust{i}@example.com", name=f"Customer {i}", role="customer", password_hash=cust_hash) for i in range(n)]
    db.add_all(custs)
    db.flush()
    today = date.today()
    for i, cu in enumerate(custs):
        plan = plans[i % 2]
        start = today - timedelta(days=random.randint(30, 700))
        sub = Subscription(customer_id=cu.id, plan_id=plan.id, status="active", start_date=start,
                           expiry_date=start + timedelta(days=1100), payment_terms_days=random.choice([0, 15, 30]),
                           next_billing_date=start, billed_cycles=0, discount_id=None)
        p = random.choice(prods)
        sub.lines.append(SubscriptionLine(product_id=p.id, quantity=random.randint(1, 3), unit_price=p.sales_price,
                                          tax_id=gst.id))
        db.add(sub)
        db.flush()
        sub.number = f"SUB-{sub.id:06d}"
    db.commit()
    res = run_billing(db, auto_confirm=True)
    print("billing:", res)

    # pay roughly 70% of invoices
    from app.models import Invoice
    for inv in db.query(Invoice).filter(Invoice.status == "confirmed").all():
        if random.random() < 0.7:
            db.add(Payment(invoice_id=inv.id, method=random.choice(["card", "bank transfer", "cash"]),
                           amount=inv.total, paid_on=min(today, inv.issue_date + timedelta(days=random.randint(0, 20)))))
            inv.amount_paid, inv.status = inv.total, "paid"
    db.commit()
    print(f"seeded: {db.query(User).count()} users, {db.query(Subscription).count()} subscriptions, "
          f"{db.query(Invoice).count()} invoices, {db.query(Payment).count()} payments")
