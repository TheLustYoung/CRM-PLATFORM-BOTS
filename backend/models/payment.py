from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base
from backend.models.common import now, uid


class Payment(Base):
    """Premium days granted to a user: a Telegram Stars purchase, a referral reward or an administrator's gift."""
    __tablename__ = "premium_payments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bot_id: Mapped[str | None] = mapped_column(ForeignKey("bots.id"))
    source: Mapped[str] = mapped_column(String(16))  # stars | referral | admin
    stars: Mapped[int] = mapped_column(Integer, default=0)
    days: Mapped[int] = mapped_column(Integer)
    # Telegram's telegram_payment_charge_id: one payment can never activate Premium twice.
    charge_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
