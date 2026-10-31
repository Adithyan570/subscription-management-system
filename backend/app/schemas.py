from datetime import date, datetime
import re
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s.]+$")


def _clean_email(v: str) -> str:
    v = v.strip().lower()
    if len(v) > 254 or not _EMAIL.match(v):
        raise ValueError("Enter a valid email address, like name@company.com.")
    return v


# Deliberately lenient: also accepts dev-style domains such as name@company.local
EmailStr = Annotated[str, AfterValidator(_clean_email)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth / users
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str = Field("", max_length=200)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(ORM):
    id: int
    email: str
    name: str
    role: str
    is_active: bool

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class ForgotIn(BaseModel):
    email: EmailStr

class ResetIn(BaseModel):
    token: str
    password: str

class PersonCreate(BaseModel):
    email: EmailStr
    name: str = Field("", max_length=200)
    password: str
    role: Literal["admin", "staff", "customer"] = "customer"

class PersonUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None


# ---- catalog
class TaxIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rate: float = Field(ge=0, le=100)
    active: bool = True

class TaxOut(TaxIn, ORM):
    id: int

class VariantIn(BaseModel):
    id: int | None = None
    attribute: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=100)
    extra_price: float = 0

class VariantOut(ORM):
    id: int
    attribute: str
    value: str
    extra_price: float

class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = "service"
    sales_price: float = Field(0, ge=0)
    cost_price: float = Field(0, ge=0)
    notes: str = ""
    default_tax_id: int | None = None
    active: bool = True
    variants: list[VariantIn] = []

class ProductOut(ORM):
    id: int
    name: str
    type: str
    sales_price: float
    cost_price: float
    notes: str
    default_tax_id: int | None
    active: bool
    variants: list[VariantOut]

class ProductPublic(ORM):  # no cost price for customers
    id: int
    name: str
    type: str
    sales_price: float
    variants: list[VariantOut]

class PlanIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(0, ge=0)
    billing_period: Literal["daily", "weekly", "monthly", "yearly"] = "monthly"
    min_quantity: int = Field(1, ge=1)
    available_from: date | None = None
    available_until: date | None = None
    tax_id: int | None = None
    auto_close: bool = False
    allow_early_close: bool = True
    allow_pause: bool = True
    allow_renew: bool = True

class PlanOut(PlanIn, ORM):
    id: int
    status: str

class TemplateLineIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(1, ge=1)

class TemplateLineOut(ORM):
    product_id: int
    variant_id: int | None
    quantity: int

class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    plan_id: int
    validity_days: int = Field(30, ge=1)
    active: bool = True
    lines: list[TemplateLineIn] = []

class TemplateOut(TemplateIn, ORM):
    id: int
    lines: list[TemplateLineOut]

class DiscountIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["fixed", "percent"]
    value: float = Field(gt=0)
    min_purchase: float = Field(0, ge=0)
    min_quantity: int = Field(0, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    usage_limit: int | None = Field(None, ge=1)
    product_id: int | None = None
    active: bool = True

class DiscountOut(DiscountIn, ORM):
    id: int
    used_count: int


# ---- subscriptions
class SubLineIn(BaseModel):
    product_id: int
    variant_id: int | None = None
    quantity: int = Field(1, ge=1)
    unit_price: float | None = Field(None, ge=0)  # defaults to product price + variant extra
    tax_id: int | None = None                    # defaults to the product's tax

class SubLineOut(ORM):
    id: int
    product_id: int
    variant_id: int | None
    product_name: str
    quantity: int
    unit_price: float
    tax_id: int | None
    tax_rate: float
    amount: float

class SubscriptionIn(BaseModel):
    customer_id: int
    plan_id: int | None = None
    template_id: int | None = None
    discount_id: int | None = None
    start_date: date
    expiry_date: date
    payment_terms_days: int = Field(0, ge=0, le=365)
    lines: list[SubLineIn] = []

class SubscriptionOut(ORM):
    id: int
    number: str
    customer_id: int
    customer_name: str
    plan_id: int
    plan_name: str
    template_id: int | None
    discount_id: int | None
    start_date: date
    expiry_date: date
    payment_terms_days: int
    status: str
    quote_valid_until: date | None
    next_billing_date: date | None
    billed_cycles: int
    lines: list[SubLineOut]

class TransitionIn(BaseModel):
    to: Literal["quotation", "confirmed", "active", "closed"]

class PortalRequestIn(BaseModel):
    plan_id: int
    lines: list[SubLineIn] = []


# ---- invoices & payments
class InvoiceLineOut(ORM):
    id: int
    description: str
    quantity: int
    unit_price: float
    amount: float
    discount: float
    tax_rate: float
    tax_amount: float

class PaymentIn(BaseModel):
    method: str = Field(min_length=1, max_length=40)
    amount: float = Field(gt=0)
    paid_on: date | None = None
    notes: str = ""

class PaymentOut(ORM):
    id: int
    invoice_id: int
    method: str
    amount: float
    paid_on: date
    notes: str

class InvoiceOut(ORM):
    id: int
    number: str
    subscription_id: int
    subscription_number: str
    customer_id: int
    customer_name: str
    period_start: date
    period_end: date
    issue_date: date
    due_date: date
    status: str
    is_overdue: bool
    subtotal: float
    discount_total: float
    tax_total: float
    total: float
    amount_paid: float
    outstanding: float
    sent_at: datetime | None

class InvoiceDetail(InvoiceOut):
    lines: list[InvoiceLineOut]
    payments: list[PaymentOut]

class Page(BaseModel):
    items: list
    total: int
