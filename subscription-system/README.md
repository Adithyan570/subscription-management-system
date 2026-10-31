# Subscription Management System

FastAPI + SQLAlchemy (SQLite) backend, React + Vite + Tailwind frontend.
Plans, subscriptions, automatic recurring billing, discounts, payments and a finance dashboard, with three roles: **admin**, **internal staff** and **customer**.

## Run it

**Backend** (Python 3.10+)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python seed.py                    # optional demo data; add  --bulk 3000  to load thousands of records
uvicorn app.main:app --reload     # http://localhost:8000  (API docs at /docs)
```

**Frontend** (Node 18+)

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173  (proxies /api to :8000)
```

**Sign in**

| Role | Email | Password |
| --- | --- | --- |
| Admin (created on first start) | admin@example.com | Admin@1234 |
| Staff (from seed.py) | staff@example.com | Staff@1234 |
| Customer (from seed.py) | customer@example.com | Cust@12345 |

Change the admin password and set `SECRET_KEY` before deploying (see `backend/.env.example`).

Run the tests: `cd backend && python -m pytest`

## What each role can do

| | Admin | Staff | Customer |
| --- | --- | --- | --- |
| Products, plans, taxes, discounts, templates | create / edit / delete | view | – |
| Add staff members | yes | – | – |
| Add customers | yes | yes | self-register |
| Subscriptions, invoices, payments, billing run, dashboard | yes | yes | – |
| Own subscriptions & invoices, request a plan, close own subscription, print invoices | – | – | yes |

## How the rules are implemented

- **Passwords**: longer than 8 characters, with an uppercase letter, a lowercase letter and a special character. Enforced on register, reset and staff-created accounts. One account per email (case-insensitive).
- **Password reset**: `POST /api/auth/forgot-password` emails a single-use link valid for 60 minutes. The answer is identical whether or not the email exists. Without `SMTP_HOST` the email is printed in the server console.
- **Variants**: a variant adds a fixed amount to the product price (Brand: Acme, +560).
- **Plan lifecycle** (decided plan by plan): *auto-close on end date*, *can be closed early*, *can be paused*, *can be renewed*. A paused or closed plan can't take new subscriptions; existing subscriptions keep billing until they close.
- **Subscription stages**: Draft → Quotation → Confirmed → Active → Closed. The API rejects skipping or going back. Quotations expire after the template's validity (default 30 days). Only drafts can be edited or deleted.
- **Billing engine** (`app/billing.py`): runs hourly in the background (`BILLING_INTERVAL_MINUTES`) and on demand from Invoices → *Run billing now*. It creates one invoice per cycle, catches up cycles missed while the server was off, and never creates a cycle twice: the database has a unique constraint on (subscription, period start). Cycle dates are computed from the start date, so monthly billing doesn't drift after short months. Cancelling an invoice does *not* free its cycle for re-billing.
- **Tax**: each product has a default tax, and a plan can tax its own fee. Tax is computed per line on the amount after discount.
- **Discounts**: attached to a subscription, fixed or percent, optionally limited to one product, with minimum purchase / quantity, start and end dates and a usage limit. Each invoice that uses a discount counts once; at the limit the discount switches itself off.
- **Invoices**: Draft → Confirmed → Paid (or Cancelled). Payments can only be recorded on confirmed invoices and can't exceed the balance. Overdue = confirmed, unpaid balance, past due date.
- **Dashboard**: active subscriptions, revenue collected (by payment date), total still owed, overdue invoices, a billed/collected/overdue bar for the chosen period, and 12-month collections. With 3,000 subscriptions and ~20,000 invoices the dashboard and list endpoints answered in 17–175 ms locally.

## Notes and next steps

- Money is stored as floats rounded to 2 decimals at every step. For a production ledger, switch the money columns to integer minor units or `Numeric` on Postgres/MySQL.
- SQLite is great for development and modest production loads. To move to Postgres or MySQL, change `DATABASE_URL` and install the driver; the code is database-neutral.
- Invoice emails and reset emails need `SMTP_*` settings to actually be delivered.
- No payment gateway is wired in; payments are recorded by staff.
