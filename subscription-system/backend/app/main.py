import asyncio
import logging
import warnings
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select

from . import config
from .billing import run_billing
from .db import Base, SessionLocal, engine
from .models import User
from .routers import auth, catalog, finance, people, portal, sales
from .security import hash_password

log = logging.getLogger("billing")


def init_db():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(func.count(User.id)).where(User.role == "admin")):
            db.add(User(email=config.ADMIN_EMAIL.lower(), name="Administrator", role="admin",
                        password_hash=hash_password(config.ADMIN_PASSWORD)))
            db.commit()
            log.warning("Created first admin %s - change the password.", config.ADMIN_EMAIL)


async def billing_loop():
    while True:
        try:
            def job():
                with SessionLocal() as db:
                    return run_billing(db)
            result = await asyncio.to_thread(job)
            if result["invoices_created"]:
                log.warning("Billing run: %s", result)
        except Exception:
            log.exception("Scheduled billing run failed")
        await asyncio.sleep(config.BILLING_INTERVAL_MINUTES * 60)


@asynccontextmanager
async def lifespan(_app):
    init_db()
    task = asyncio.create_task(billing_loop()) if config.BILLING_INTERVAL_MINUTES > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Subscription Management System", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
for r in (auth, people, catalog, sales, portal, finance):
    app.include_router(r.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}
