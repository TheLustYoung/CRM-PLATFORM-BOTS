"""Dashboard «Payments»: card/crypto buttons and their providers, provider keys, the neutral domain,
transactions, refunds and revenue."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from backend.database import session
from backend.api.deps import admin_required, audit, require, row
from backend.models import Order, User
from backend.services import billing
from backend.services.payments import PaymentError, catalog
from workers.telegram import Telegram, TelegramError

router = APIRouter(prefix="/api/admin/payments", tags=["admin"], dependencies=[Depends(admin_required)])
PAGE = 50
HIDDEN = {"token", "details"}  # the token opens the payment page; details hold provider ids


class CategoryUpdate(BaseModel):
    enabled: bool | None = None
    provider: str | None = Field(default=None, max_length=40)


class PaymentsUpdate(BaseModel):
    stars_enabled: bool | None = None
    public_url: str | None = Field(default=None, max_length=200)
    card: CategoryUpdate | None = None
    crypto: CategoryUpdate | None = None
    # provider -> field -> value; None keeps the stored value, "" removes it
    providers: dict[str, dict[str, str | None]] | None = None


@router.get("")
def get_payments(db=Depends(session)):
    return billing.public_view(db)


@router.put("")
def put_payments(data: PaymentsUpdate, db=Depends(session), admin=Depends(admin_required)):
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    try:
        billing.save(db, update)
    except ValidationError as error:  # keep only the human message
        raise HTTPException(400, error.errors()[0]["msg"].removeprefix("Value error, ")) from None
    changed = sorted(update) + [f"providers.{p}" for p in (data.providers or {})]
    audit(db, admin, "payments.update", ", ".join(changed) or "nothing")  # never the keys themselves
    return billing.public_view(db)


@router.post("/{provider}/test")
def test_provider(provider: str, db=Depends(session)):
    info = catalog().get(provider)
    if not info:
        raise HTTPException(404, "Unknown provider")
    if not info["module"]:
        return {"ok": False, "detail": "The fields are saved. This provider is switched on with the next update."}
    config = billing.config(db, provider)
    if not info["module"].configured(config):
        return {"ok": False, "detail": "Enter the keys first"}
    try:
        return {"ok": True, "detail": info["module"].check(config)}
    except PaymentError as error:
        return {"ok": False, "detail": str(error)}


@router.get("/orders")
def orders(status: str | None = None, method: str | None = None, user_id: int | None = None,
           offset: int = Query(0, ge=0), db=Depends(session)):
    statement = select(Order, User.username).join(User, User.id == Order.user_id).where(Order.method.is_not(None))
    if status:
        statement = statement.where(Order.status == status)
    if method:
        statement = statement.where(Order.method == method)
    if user_id:
        statement = statement.where(Order.user_id == user_id)
    items = db.execute(statement.order_by(Order.created_at.desc()).offset(offset).limit(PAGE)).all()
    return [{**{k: v for k, v in row(o).items() if k not in HIDDEN}, "username": name} for o, name in items]


@router.post("/orders/{id}/refund")
def refund(id: str, db=Depends(session), admin=Depends(admin_required)):
    order = require(db, Order, id)
    try:
        if order.method == "stars":
            with Telegram(order.bot_id) as telegram:
                billing.refund(db, order, telegram)
        else:
            billing.refund(db, order)
    except TelegramError as error:
        raise HTTPException(400, f"Telegram: {error.description}") from None
    except PaymentError as error:
        raise HTTPException(400, str(error)) from None
    audit(db, admin, "payments.refund", f"{order.id} · {order.method}")
    return {k: v for k, v in row(order).items() if k not in HIDDEN}


@router.get("/revenue")
def revenue(db=Depends(session)):
    return billing.revenue(db)
