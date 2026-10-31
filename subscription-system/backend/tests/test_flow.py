from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

PW = "Strong#Pass1"


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:
        yield client


def hdr(tok):
    return {"Authorization": f"Bearer {tok}"}


def login(c, email, pw):
    r = c.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return hdr(r.json()["access_token"])


def test_password_rules_and_unique_email(c):
    for bad in ["Short1!", "alllowercase1!", "ALLUPPERCASE1!", "NoSpecialChar1", "12345678!"]:
        assert c.post("/api/auth/register", json={"email": "a@x.com", "password": bad}).status_code == 422, bad
    assert c.post("/api/auth/register", json={"email": "a@x.com", "password": PW}).status_code == 201
    assert c.post("/api/auth/register", json={"email": "A@X.com", "password": PW}).status_code == 409


def test_full_flow(c):
    admin = login(c, "admin@example.com", "Admin@1234")
    # RBAC: customers can't touch the catalog or dashboard; staff can't write the catalog
    cust = login(c, "a@x.com", PW)
    assert c.get("/api/products", headers=cust).status_code == 403
    assert c.get("/api/dashboard", headers=cust).status_code == 403
    assert c.post("/api/people", headers=admin, json={"email": "s@x.com", "password": PW, "role": "staff"}).status_code == 201
    staff = login(c, "s@x.com", PW)
    assert c.post("/api/taxes", headers=staff, json={"name": "GST", "rate": 10}).status_code == 403
    assert c.get("/api/people?group=team", headers=staff).status_code == 403
    assert c.post("/api/people", headers=staff, json={"email": "z@x.com", "password": PW, "role": "staff"}).status_code == 403

    tax = c.post("/api/taxes", headers=admin, json={"name": "GST 10", "rate": 10}).json()
    prod = c.post("/api/products", headers=admin, json={
        "name": "Gym gear", "sales_price": 1000, "cost_price": 600, "default_tax_id": tax["id"],
        "variants": [{"attribute": "Brand", "value": "Acme", "extra_price": 560}]}).json()
    vid = prod["variants"][0]["id"]
    plan = c.post("/api/plans", headers=admin, json={
        "name": "Monthly", "price": 100, "billing_period": "monthly", "min_quantity": 1}).json()
    disc = c.post("/api/discounts", headers=admin, json={
        "name": "10% off", "kind": "percent", "value": 10, "usage_limit": 2}).json()

    me = c.get("/api/auth/me", headers=cust).json()
    start = date.today() - timedelta(days=65)  # ~3 monthly cycles already due
    sub = c.post("/api/subscriptions", headers=staff, json={
        "customer_id": me["id"], "plan_id": plan["id"], "discount_id": disc["id"],
        "start_date": start.isoformat(), "expiry_date": (start + timedelta(days=400)).isoformat(),
        "payment_terms_days": 15,
        "lines": [{"product_id": prod["id"], "variant_id": vid, "quantity": 2}]}).json()
    assert sub["lines"][0]["unit_price"] == 1560  # base + fixed variant amount
    assert sub["number"].startswith("SUB-")

    # lifecycle is strictly step by step
    assert c.post(f"/api/subscriptions/{sub['id']}/transition", headers=staff, json={"to": "active"}).status_code == 409
    for stage in ("quotation", "confirmed", "active"):
        r = c.post(f"/api/subscriptions/{sub['id']}/transition", headers=staff, json={"to": stage})
        assert r.status_code == 200 and r.json()["status"] == stage

    # billing: catches up every due cycle, exactly once
    r = c.post("/api/billing/run?auto_confirm=true", headers=staff).json()
    assert r["invoices_created"] == 3, r
    again = c.post("/api/billing/run", headers=staff).json()
    assert again["invoices_created"] == 0

    invs = c.get("/api/invoices?limit=50", headers=staff).json()["items"]
    assert len(invs) == 3
    first = min(invs, key=lambda i: i["period_start"])
    det = c.get(f"/api/invoices/{first['id']}", headers=staff).json()
    # lines: plan 100 + 2 x 1560 = 3220; 10% discount = 322; tax 10% of (3220-322)=289.80
    assert det["subtotal"] == 3220 and det["discount_total"] == 322
    assert det["tax_total"] == 280.80  # 10% of (3120 - 312); the plan line itself is untaxed
    assert det["total"] == 3178.80
    # discount had a usage limit of 2: third invoice has none
    third = max(invs, key=lambda i: i["period_start"])
    assert third["discount_total"] == 0

    # payments
    assert c.post(f"/api/invoices/{first['id']}/payments", headers=staff,
                  json={"method": "card", "amount": det["total"] + 5}).status_code == 422
    r = c.post(f"/api/invoices/{first['id']}/payments", headers=staff,
               json={"method": "card", "amount": det["total"], "notes": "ok"}).json()
    assert r["status"] == "paid" and r["outstanding"] == 0
    assert c.post(f"/api/invoices/{first['id']}/cancel", headers=staff).status_code == 409

    d = c.get("/api/dashboard?date_from=2000-01-01", headers=staff).json()
    assert d["active_subscriptions"] == 1
    assert d["revenue_collected"] == det["total"]
    assert d["overdue_count"] >= 1 and d["amount_owed"] > 0

    # customer portal sees only own, non-draft invoices
    mine = c.get("/api/customer-invoices", headers=cust).json()
    assert len(mine) == 3
    assert c.get(f"/api/invoices/{first['id']}/print", headers=cust).status_code == 200
    other = c.post("/api/auth/register", json={"email": "b@x.com", "password": PW}).json()["access_token"]
    assert c.get(f"/api/invoices/{first['id']}", headers=hdr(other)).status_code == 404


def test_plan_rules_and_reset(c, capsys):
    admin = login(c, "admin@example.com", "Admin@1234")
    p = c.post("/api/plans", headers=admin, json={"name": "Locked", "allow_pause": False}).json()
    assert c.post(f"/api/plans/{p['id']}/pause", headers=admin).status_code == 409
    q = c.post("/api/plans", headers=admin, json={"name": "Flexible"}).json()
    assert c.post(f"/api/plans/{q['id']}/pause", headers=admin).json()["status"] == "paused"

    assert c.post("/api/auth/forgot-password", json={"email": "nobody@x.com"}).status_code == 200
    assert c.post("/api/auth/forgot-password", json={"email": "a@x.com"}).status_code == 200
    out = capsys.readouterr().out
    token = out.split("token=")[1].split()[0]
    assert c.post("/api/auth/reset-password", json={"token": token, "password": "weak"}).status_code == 422
    assert c.post("/api/auth/reset-password", json={"token": token, "password": "New#Passw0rd"}).status_code == 200
    assert c.post("/api/auth/reset-password", json={"token": token, "password": "New#Passw0rd"}).status_code == 400
    login(c, "a@x.com", "New#Passw0rd")
