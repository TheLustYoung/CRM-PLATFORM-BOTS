import secrets
from fastapi import Depends, HTTPException, Request
from sqlalchemy.inspection import inspect
from backend.config import settings, BOT_KINDS
from backend.database import session
from backend.models import Audit
from backend.services import team
from backend.services.auth import admin_from_token


def check_origin(request: Request):
    """CSRF protection for cookie-authenticated admin requests."""
    if request.method not in {"GET", "HEAD", "OPTIONS"} and request.headers.get("origin") != settings().admin_origin:
        raise HTTPException(403, "Invalid origin")


def admin_required(request: Request, db=Depends(session)):
    check_origin(request)
    admin = admin_from_token(db, request.cookies.get("session", ""))
    if not admin:
        raise HTTPException(401, "Authentication required")
    # Role check for the admin API (see backend.services.team.RULES; calls not listed there are refused)
    if request.url.path.startswith("/api/admin") and not team.allowed(team.permissions(db, admin), request.method, request.url.path):
        raise HTTPException(403, "no_permission")
    return admin


def bot_required(request: Request) -> str:
    """Bots authenticate with a per-bot service key; a leaked key affects one bot only."""
    kind = request.headers.get("x-bot-kind", "")
    supplied = request.headers.get("x-service-key", "")
    if kind not in BOT_KINDS or not secrets.compare_digest(supplied, settings().service_key(kind)):
        raise HTTPException(401, "Unauthorized")
    return kind


def row(obj) -> dict:
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}


def require(db, model, id):
    item = db.get(model, id)
    if not item:
        raise HTTPException(404, "Not found")
    return item


def audit(db, admin, action: str, target) -> None:
    db.add(Audit(admin_id=admin.id, action=action, target=str(target)[:128]))
    db.commit()
