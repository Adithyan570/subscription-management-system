# Subscription Management System

end to customer*).

1. **Dev mode (default)**: with no email settings the message is printed in the backend console and saved in `backend/outbox/`. Nothing is delivered.
2. **Local test mail server**: run `python dev_mail_server.py` in a second terminal, and put `SMTP_HOST=127.0.0.1`, `SMTP_PORT=1025`, `SMTP_SECURITY=none` in `backend/.env`. Emails then arrive in that terminal and in `backend/mailbox/`. Good for checking the whole flow without an account.
3. **Real delivery**: put your provider's SMTP details in `backend/.env` (copy `.env.example`). Example for Gmail: turn on 2-Step Verification, create an *App password* at <https://myaccount.google.com/apppasswords>, then set `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`, `SMTP_USER=you@gmail.com`, `SMTP_PASSWORD=<app password>`, `MAIL_FROM=you@gmail.com`.

Check your settings any time with `python send_test_email.py you@example.com`; it prints the exact error if sending fails. Restart the backend after editing `.env`. If your frontend isn't at `http://localhost:5173`, set `FRONTEND_URL` so the link in the email points to the right place.

Mail problems never break the page: they are logged in the backend console (look for `EMAIL FAILED`).

## Troubleshooting

- **A user "isn't added"**: the red message above the Save button says why. The usual causes are a password that doesn't meet the rules (the checklist under the field turns green as you type) or an email that's already registered.
- **Users or data disappeared**: the database is `backend/subscriptions.db` regardless of where you start the server. Delete it to start fresh.
- **Frontend can't reach the API**: make sure the backend is running on port 8000 before `npm run dev`.

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
