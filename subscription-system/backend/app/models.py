from datetime import date, datetime, timezone

from sqlalchemy import (Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


ROLES = ("admin", "staff", "customer")
BILLING_PERIODS = ("daily", "weekly", "monthly", "yearly")
SUB_STAGES = ("draft", "quotation", "confirmed", "active", "closed")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PasswordReset(Base):
    __tablename__ = "password_resets"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class Tax(Base):
    __tablename__ = "taxes"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    rate: Mapped[float] = mapped_column(Float)  # percent, e.g. 18 = 18%
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    type: Mapped[str] = mapped_column(String(50), default="service")
    sales_price: Mapped[float] = mapped_column(Float, default=0)
    cost_price: Mapped[float] = mapped_column(Float, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    default_tax_id: Mapped[int | None] = mapped_column(ForeignKey("taxes.id", ondelete="SET NULL"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", lazy="selectin", order_by="ProductVariant.id")


class ProductVariant(Base):
    __tablename__ = "product_variants"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    attribute: Mapped[str] = mapped_column(String(100))  # e.g. "Brand"
    value: Mapped[str] = mapped_column(String(100))      # e.g. "Acme"
    extra_price: Mapped[float] = mapped_column(Float, default=0)  # fixed amount added to the price
    product: Mapped[Product] = relationship(back_populates="variants")


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    price: Mapped[float] = mapped_column(Float, default=0)  # recurring base fee per period
    billing_period: Mapped[str] = mapped_column(String(10), default="monthly")
    min_quantity: Mapped[int] = mapped_column(Integer, default=1)
    available_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    available_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    tax_id: Mapped[int | None] = mapped_column(ForeignKey("taxes.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="active", index=True)  # active|paused|closed
    # lifecycle rules, decided plan-by-plan
    auto_close: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_early_close: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_pause: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    tax: Mapped[Tax | None] = relationship(lazy="joined")


class QuotationTemplate(Base):
    __tablename__ = "quotation_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    validity_days: Mapped[int] = mapped_column(Integer, default=30)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    lines: Mapped[list["TemplateLine"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="TemplateLine.id")


class TemplateLine(Base):
    __tablename__ = "template_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("quotation_templates.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)


class Discount(Base):
    __tablename__ = "discounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(10))  # fixed|percent
    value: Mapped[float] = mapped_column(Float)
    min_purchase: Mapped[float] = mapped_column(Float, default=0)
    min_quantity: Mapped[int] = mapped_column(Integer, default=0)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    usage_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None = unlimited
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True, default="")
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("quotation_templates.id", ondelete="SET NULL"), nullable=True)
    discount_id: Mapped[int | None] = mapped_column(ForeignKey("discounts.id", ondelete="SET NULL"), nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    expiry_date: Mapped[date] = mapped_column(Date)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=0)  # 0 = due on receipt
    status: Mapped[str] = mapped_column(String(12), default="draft", index=True)
    quote_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    billed_cycles: Mapped[int] = mapped_column(Integer, default=0)
    next_billing_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    customer: Mapped[User] = relationship(foreign_keys=[customer_id], lazy="joined")
    plan: Mapped[Plan] = relationship(lazy="joined")
    discount: Mapped[Discount | None] = relationship(lazy="joined")
    lines: Mapped[list["SubscriptionLine"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="SubscriptionLine.id")

    @property
    def customer_name(self):
        return self.customer.name or self.customer.email

    @property
    def plan_name(self):
        return self.plan.name


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float)
    tax_id: Mapped[int | None] = mapped_column(ForeignKey("taxes.id", ondelete="SET NULL"), nullable=True)

    product: Mapped[Product] = relationship(lazy="joined")
    variant: Mapped[ProductVariant | None] = relationship(lazy="joined")
    tax: Mapped[Tax | None] = relationship(lazy="joined")

    @property
    def product_name(self):
        return self.product.name + (f" ({self.variant.value})" if self.variant else "")

    @property
    def tax_rate(self):
        return self.tax.rate if self.tax else 0.0

    @property
    def amount(self):
        return round(self.quantity * self.unit_price, 2)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        # One invoice per subscription per billing cycle: the database itself prevents double-billing.
        UniqueConstraint("subscription_id", "period_start", name="uq_invoice_cycle"),
        Index("ix_invoice_status_due", "status", "due_date"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True, default="")
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    cycle: Mapped[int] = mapped_column(Integer)
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft|confirmed|paid|cancelled
    subtotal: Mapped[float] = mapped_column(Float, default=0)
    discount_total: Mapped[float] = mapped_column(Float, default=0)
    tax_total: Mapped[float] = mapped_column(Float, default=0)
    total: Mapped[float] = mapped_column(Float, default=0)
    amount_paid: Mapped[float] = mapped_column(Float, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    customer: Mapped[User] = relationship(lazy="joined")
    subscription: Mapped[Subscription] = relationship(lazy="joined")
    lines: Mapped[list["InvoiceLine"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="InvoiceLine.id")
    payments: Mapped[list["Payment"]] = relationship(lazy="selectin", order_by="Payment.id")

    @property
    def outstanding(self):
        return round(self.total - self.amount_paid, 2) if self.status in ("confirmed", "paid") else 0.0

    @property
    def customer_name(self):
        return self.customer.name or self.customer.email

    @property
    def subscription_number(self):
        return self.subscription.number

    @property
    def is_overdue(self):
        return self.status == "confirmed" and self.outstanding > 0 and self.due_date < date.today()


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(String(300))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float)
    amount: Mapped[float] = mapped_column(Float)
    discount: Mapped[float] = mapped_column(Float, default=0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0)


class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    method: Mapped[str] = mapped_column(String(40))
    amount: Mapped[float] = mapped_column(Float)
    paid_on: Mapped[date] = mapped_column(Date, index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
