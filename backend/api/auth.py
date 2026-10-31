from fastapi import APIRouter, Depends, HTTPException, Request, Response
from backend.config import settings
from backend.database import session
from backend.api.deps import admin_required, check_origin
from backend.api.schemas import Login
from backend.services.auth import authenticate, InvalidCredentials
from backend.services.limits import rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(data: Login, request: Request, response: Response, db=Depends(session)):
    check_origin(request)
    rate_limit(f"login:{request.client.host}", 10, 300)
    try:
        token = authenticate(db, data.username, data.password)
    except InvalidCredentials:
        raise HTTPException(401, "Invalid credentials") from None
    response.set_cookie("session", token, httponly=True, secure=settings().cookie_secure, samesite="strict", max_age=28800, path="/api")
    return {"username": data.username}


@router.post("/logout")
def logout(response: Response, admin=Depends(admin_required)):
    response.delete_cookie("session", path="/api", secure=settings().cookie_secure, httponly=True, samesite="strict")
    return {"ok": True}
