import secrets
from datetime import timedelta
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import select
from backend.config import settings
from backend.models import Admin, now

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))
AUDIENCE = "media-admin"


class InvalidCredentials(Exception):
    pass


def authenticate(db, username: str, password: str) -> str:
    """Return a signed session token. Constant work for unknown users (no username probing)."""
    admin = db.scalar(select(Admin).where(Admin.username == username))
    try:
        valid = hasher.verify(admin.password_hash if admin else DUMMY_HASH, password)
    except VerificationError:
        valid = False
    if not valid or not admin or not admin.active:
        raise InvalidCredentials()
    admin.last_login_at = now()
    db.commit()
    # "v": the account's session version; a new role, password or block makes older sessions invalid
    return jwt.encode({"sub": admin.id, "v": admin.session_version or 1, "exp": now() + timedelta(hours=8), "iat": now(), "aud": AUDIENCE},
                      settings().jwt_secret.get_secret_value(), algorithm="HS256")


def admin_from_token(db, token: str) -> Admin | None:
    try:
        claims = jwt.decode(token, settings().jwt_secret.get_secret_value(), algorithms=["HS256"], audience=AUDIENCE)
    except jwt.PyJWTError:
        return None
    admin = db.get(Admin, claims.get("sub"))
    if not admin or not admin.active or claims.get("v", 1) != (admin.session_version or 1):
        return None
    return admin
