from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base
from backend.models.common import now, uid


class Order(Base):
    """One purchase attempt and its transaction, whatever the payment method.

    pending → paid | failed | expired | canceled, and paid → refunded. `amount` is in minor units of `currency`
    (cents for USD, whole Stars for XTR). `provider_ref` is the provider's id (Stripe session, Telegram charge,
    crypto invoice) and is unique per method, so a repeated webhook can never activate Premium twice.
    """
    __tablename__ = "orders"
    __table_args__ = (Index("ix_orders_method_ref", "method", "provider_ref", unique=True), Index("ix_orders_status_created", "status", "created_at"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    token: Mapped[str] = mapped_column(String(48), unique=True)  # secret part of the payment page URL
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    bot_id: Mapped[str] = mapped_column(ForeignKey("bots.id"))
    days: Mapped[int] = mapped_column(Integer)
    method: Mapped[str | None] = mapped_column(String(24))  # stars | stripe | crypto modules; None until chosen
    currency: Mapped[str | None] = mapped_column(String(8))
    amount: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    provider_ref: Mapped[str | None] = mapped_column(String(128))
    lang: Mapped[str] = mapped_column(String(8), default="en")
    details: Mapped[dict] = mapped_column(JSON, default=dict)  # provider data needed later (payment intent for refunds…)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
