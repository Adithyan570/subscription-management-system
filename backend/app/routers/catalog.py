from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import admin_only, get_db, staff_or_admin
from ..models import (Discount, Plan, Product, ProductVariant, QuotationTemplate, Tax, TemplateLine)
from ..schemas import (DiscountIn, DiscountOut, PlanIn, PlanOut, ProductIn, ProductOut, TaxIn, TaxOut,
                       TemplateIn, TemplateOut)

router = APIRouter(tags=["catalog"])


def crud(path, Model, In, Out, hook=None):
    """Admin writes, staff+admin reads."""
    @router.get(f"/{path}", name=f"{path}_list", response_model=list[Out], dependencies=[Depends(staff_or_admin)])
    def list_(db: Session = Depends(get_db)):
        return db.scalars(select(Model).order_by(Model.id.desc())).all()

    @router.post(f"/{path}", name=f"{path}_create", response_model=Out, status_code=201, dependencies=[Depends(admin_only)])
    def create(body: In, db: Session = Depends(get_db)):
        obj = Model(**body.model_dump(exclude=hook_fields(hook)))
        if hook:
            hook(db, obj, body)
        db.add(obj)
        commit(db)
        return obj

    @router.put(f"/{path}/{{oid}}", name=f"{path}_update", response_model=Out, dependencies=[Depends(admin_only)])
    def update(oid: int, body: In, db: Session = Depends(get_db)):
        obj = db.get(Model, oid)
        if not obj:
            raise HTTPException(404, "Not found.")
        for k, v in body.model_dump(exclude=hook_fields(hook)).items():
            setattr(obj, k, v)
        if hook:
            hook(db, obj, body)
        commit(db)
        return obj

    @router.delete(f"/{path}/{{oid}}", name=f"{path}_delete", status_code=204, dependencies=[Depends(admin_only)])
    def delete(oid: int, db: Session = Depends(get_db)):
        obj = db.get(Model, oid)
        if not obj:
            raise HTTPException(404, "Not found.")
        db.delete(obj)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "This item is used by subscriptions or invoices. Mark it inactive instead.")


def hook_fields(hook):
    return getattr(hook, "fields", set())


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(422, "A referenced tax, product, variant or plan doesn't exist.")


def sync_variants(db, product, body):
    keep = {v.id: v for v in body.variants if v.id}
    existing = {v.id: v for v in product.variants}
    product.variants[:] = [v for v in product.variants if v.id in keep]
    for vid, data in keep.items():
        if vid in existing:
            for k in ("attribute", "value", "extra_price"):
                setattr(existing[vid], k, getattr(data, k))
    for data in body.variants:
        if not data.id or data.id not in existing:
            product.variants.append(ProductVariant(attribute=data.attribute, value=data.value,
                                                   extra_price=data.extra_price))
sync_variants.fields = {"variants"}


def sync_template_lines(db, tpl, body):
    tpl.lines[:] = [TemplateLine(**l.model_dump()) for l in body.lines]
sync_template_lines.fields = {"lines"}


def check_discount(db, obj, body):
    if body.kind == "percent" and body.value > 100:
        raise HTTPException(422, "A percentage discount can't exceed 100.")
    if body.start_date and body.end_date and body.end_date < body.start_date:
        raise HTTPException(422, "End date must be after the start date.")


crud("taxes", Tax, TaxIn, TaxOut)
crud("products", Product, ProductIn, ProductOut, sync_variants)
crud("plans", Plan, PlanIn, PlanOut)
crud("templates", QuotationTemplate, TemplateIn, TemplateOut, sync_template_lines)
crud("discounts", Discount, DiscountIn, DiscountOut, check_discount)


# ---- plan lifecycle (rules are per plan)
def _plan(db, pid):
    p = db.get(Plan, pid)
    if not p:
        raise HTTPException(404, "Plan not found.")
    return p


@router.post("/plans/{pid}/pause", response_model=PlanOut, dependencies=[Depends(admin_only)])
def pause_plan(pid: int, db: Session = Depends(get_db)):
    p = _plan(db, pid)
    if not p.allow_pause:
        raise HTTPException(409, "This plan isn't set up to be paused.")
    if p.status != "active":
        raise HTTPException(409, "Only active plans can be paused.")
    p.status = "paused"
    db.commit()
    return p


@router.post("/plans/{pid}/resume", response_model=PlanOut, dependencies=[Depends(admin_only)])
def resume_plan(pid: int, db: Session = Depends(get_db)):
    p = _plan(db, pid)
    if p.status != "paused":
        raise HTTPException(409, "Only paused plans can be resumed.")
    p.status = "active"
    db.commit()
    return p


@router.post("/plans/{pid}/close", response_model=PlanOut, dependencies=[Depends(admin_only)])
def close_plan(pid: int, db: Session = Depends(get_db)):
    p = _plan(db, pid)
    ended = p.available_until and p.available_until <= date.today()
    if not p.allow_early_close and not ended:
        raise HTTPException(409, "This plan can't be closed before its end date.")
    if p.status == "closed":
        raise HTTPException(409, "Plan is already closed.")
    p.status = "closed"
    db.commit()
    return p


@router.post("/plans/{pid}/renew", response_model=PlanOut, dependencies=[Depends(admin_only)])
def renew_plan(pid: int, new_end: date, db: Session = Depends(get_db)):
    p = _plan(db, pid)
    if not p.allow_renew:
        raise HTTPException(409, "This plan isn't set up to be renewed.")
    if new_end <= date.today():
        raise HTTPException(422, "The new end date must be in the future.")
    p.available_until, p.status = new_end, "active"
    db.commit()
    return p
