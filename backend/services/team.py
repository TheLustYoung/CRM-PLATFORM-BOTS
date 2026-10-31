"""Admin team: accounts, roles and what each role may do in the admin panel.

- Built-in roles are defined here (owner, admin, manager, support, viewer); custom roles live in admin_roles.
- Every /api/admin call is checked against RULES; a call that is not listed there is refused (owners included),
  so a new endpoint cannot become reachable by accident.
- Nobody can hand out more than they have: an account manager only gives roles whose permissions they hold
  themselves and cannot touch accounts with more rights. Nobody changes their own role or blocks themselves,
  and the last active owner cannot be removed.
- A new role, password or block bumps session_version, which signs that person out everywhere at once.
"""
import re
import secrets
from sqlalchemy import func, select
from backend.models import Admin, AdminRole, now

PERMISSIONS = (
    "bots.view", "bots.manage",
    "users.view", "users.manage",
    "downloads.view", "files.manage",
    "ads.manage",
    "money.view", "money.manage",
    "settings.manage",
    "audit.view",
    "team.manage",
)
ALL = frozenset(PERMISSIONS)
BUILTIN = {
    "owner": ("Owner", PERMISSIONS),
    "admin": ("Administrator", tuple(p for p in PERMISSIONS if p != "team.manage")),
    "manager": ("Manager", ("bots.view", "users.view", "users.manage", "downloads.view", "files.manage", "ads.manage", "money.view")),
    "support": ("Support", ("users.view", "users.manage", "downloads.view", "files.manage")),
    "viewer": ("Viewer", ("bots.view", "users.view", "downloads.view", "money.view")),
}

# (methods, path under /api/admin, permission). A tuple of permissions means "any of them". None = any signed-in admin.
_RULES = [
    ("GET", "/me", None), ("GET", "/overview", None), ("GET", "/compatibility", None),
    ("GET", "/bots(/[^/]+/(profile|photo))?", "bots.view"),
    ("PATCH", "/bots/[^/]+", "bots.manage"), ("PUT", "/bots/[^/]+/profile", "bots.manage"),
    ("POST|DELETE", "/bots/[^/]+/photo", "bots.manage"),
    ("GET", "/users(/\\d+)?", "users.view"), ("PATCH", "/users/\\d+", "users.manage"),
    ("POST", "/users/\\d+/premium", "money.manage"),
    ("GET", "/jobs(/[^/]+)?", "downloads.view"), ("GET", "/files", "downloads.view"), ("GET", "/files/[^/]+/content", "downloads.view"),
    ("POST", "/files/[^/]+/revoke", "files.manage"), ("POST", "/files/[^/]+/keep", "files.manage"), ("DELETE", "/files/[^/]+", "files.manage"),
    ("GET|POST", "/broadcasts(/[^/]+)?", "ads.manage"), ("POST", "/broadcasts/[^/]+/delete", "ads.manage"),
    ("GET", "/broadcasts/[^/]+/photo", "ads.manage"),
    ("GET|PUT", "/channel", "ads.manage"), ("POST", "/channel/posts", "ads.manage"),
    ("POST", "/channel/posts/[^/]+/(edit|publish|pin|delete)", "ads.manage"), ("GET", "/channel/posts/[^/]+/media", "ads.manage"),
    ("GET", "/monetization(/stats)?", "money.view"), ("PUT", "/monetization", "money.manage"),
    ("POST", "/monetization/channel-test", "money.manage"),
    ("GET", "/payments(/orders|/revenue)?", "money.view"), ("PUT", "/payments", "money.manage"),
    ("POST", "/payments/[^/]+/test", "money.manage"), ("POST", "/payments/orders/[^/]+/refund", "money.manage"),
    # the free-downloads limit lives in the shared limits and is edited on the Monetization page too
    ("GET", "/settings", ("settings.manage", "money.view")), ("PATCH", "/settings", ("settings.manage", "money.manage")),
    ("GET", "/audit", "audit.view"),
    ("GET", "/analytics(\\.csv)?", ("bots.view", "money.view")),
    ("GET|PUT", "/monitoring", "settings.manage"), ("POST", "/monitoring/check", "settings.manage"),
    ("GET", "/translations(/[\\w-]+)?", "settings.manage"), ("PUT", "/translations/[\\w-]+", "settings.manage"),
    ("POST", "/translations/[\\w-]+/(enable|disable)", "settings.manage"),
    ("GET|PUT|DELETE", "/bots/[^/]+/token", "bots.manage"),
    ("GET|POST|PATCH|PUT|DELETE", "/team(/accounts|/roles)?(/[^/]+)?", "team.manage"),
]
RULES = [(set(m.split("|")), re.compile("/api/admin" + p + r"\Z"), perm) for m, p, perm in _RULES]
USERNAME = re.compile(r"[A-Za-z0-9_.-]{2,56}\Z")
DELETED = "~"  # deleted accounts with audit history are renamed "name~abc123" and blocked (names never contain "~")
MIN_PASSWORD = 12  # same as `python -m backend.cli create-admin`


class TeamError(Exception):
    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code, self.status = code, status


def roles(db) -> dict[str, dict]:
    custom = {r.id: {"id": r.id, "name": r.name, "permissions": [p for p in PERMISSIONS if p in (r.permissions or [])], "builtin": False}
              for r in db.scalars(select(AdminRole).order_by(AdminRole.name))}
    result = {k: {"id": k, "name": name, "permissions": list(perms), "builtin": True} for k, (name, perms) in BUILTIN.items()}
    result.update(custom)
    used = dict(db.execute(select(Admin.role, func.count()).where(~Admin.username.contains(DELETED)).group_by(Admin.role)).all())
    for role in result.values():
        role["accounts"] = used.get(role["id"], 0)
    return result


def permissions(db, admin: Admin) -> frozenset[str]:
    if admin.role in BUILTIN:
        return frozenset(BUILTIN[admin.role][1])
    role = db.get(AdminRole, admin.role)
    return frozenset(role.permissions or []) & ALL if role else frozenset()


def allowed(perms: frozenset[str], method: str, path: str) -> bool:
    method = "GET" if method == "HEAD" else method
    for methods, pattern, permission in RULES:
        if method in methods and pattern.match(path):
            if permission is None:
                return True
            wanted = permission if isinstance(permission, tuple) else (permission,)
            return any(p in perms for p in wanted)
    return False


def public(admin: Admin) -> dict:
    return {"id": admin.id, "username": admin.username, "role": admin.role, "active": admin.active,
            "created_at": admin.created_at, "created_by": admin.created_by, "last_login_at": admin.last_login_at}


def _active_owners(db) -> int:
    return db.scalar(select(func.count()).select_from(Admin).where(Admin.role == "owner", Admin.active.is_(True)))


def _check_role(db, actor_perms: frozenset[str], role: str):
    known = roles(db)
    if role not in known:
        raise TeamError("unknown_role")
    if not set(known[role]["permissions"]) <= actor_perms:
        raise TeamError("role_above_you", 403)


def _check_target(db, actor: Admin, actor_perms: frozenset[str], target: Admin):
    if not permissions(db, target) <= actor_perms:
        raise TeamError("above_you", 403)


def create_account(db, actor: Admin, username: str, password: str, role: str, hasher) -> Admin:
    username = (username or "").strip()
    if not USERNAME.match(username):
        raise TeamError("bad_username")
    if len(password or "") < MIN_PASSWORD:
        raise TeamError("short_password")
    _check_role(db, permissions(db, actor), role)
    if db.scalar(select(Admin).where(func.lower(Admin.username) == username.lower())):
        raise TeamError("username_taken")
    admin = Admin(username=username, password_hash=hasher.hash(password), role=role, created_by=actor.username, created_at=now())
    db.add(admin)
    db.commit()
    return admin


def update_account(db, actor: Admin, target: Admin, hasher, role: str | None = None, active: bool | None = None,
                   password: str | None = None) -> Admin:
    perms = permissions(db, actor)
    if target.id == actor.id and (role is not None or active is False):
        raise TeamError("not_yourself")
    _check_target(db, actor, perms, target)
    if role is not None:
        _check_role(db, perms, role)
    if password is not None and len(password) < MIN_PASSWORD:
        raise TeamError("short_password")
    losing_owner = target.role == "owner" and target.active and ((role is not None and role != "owner") or active is False)
    if losing_owner and _active_owners(db) <= 1:
        raise TeamError("last_owner")
    if role is not None:
        target.role = role
    if active is not None:
        target.active = active
    if password is not None:
        target.password_hash = hasher.hash(password)
    if role is not None or active is not None or password is not None:
        target.session_version = (target.session_version or 1) + 1
    db.commit()
    return target


def delete_account(db, actor: Admin, target: Admin) -> None:
    """Accounts with audit history are blocked instead of deleted, so the audit log keeps who did what."""
    if target.id == actor.id:
        raise TeamError("not_yourself")
    _check_target(db, actor, permissions(db, actor), target)
    if target.role == "owner" and target.active and _active_owners(db) <= 1:
        raise TeamError("last_owner")
    from backend.models import Audit
    if db.scalar(select(func.count()).select_from(Audit).where(Audit.admin_id == target.id)):
        target.active, target.session_version = False, (target.session_version or 1) + 1
        target.username = f"{target.username[:56]}{DELETED}{secrets.token_hex(3)}"  # frees the name for a new account
    else:
        db.delete(target)
    db.commit()


def save_role(db, actor: Admin, role_id: str | None, name: str, wanted: list[str]) -> dict:
    name, wanted_set = (name or "").strip(), set(wanted or [])
    perms = permissions(db, actor)
    if not 1 <= len(name) <= 64:
        raise TeamError("bad_role_name")
    if not wanted_set <= ALL:
        raise TeamError("unknown_permission")
    if not wanted_set <= perms:
        raise TeamError("role_above_you", 403)
    if role_id is None:
        role = AdminRole(id="r-" + secrets.token_hex(4), builtin=False)
        db.add(role)
    else:
        if role_id in BUILTIN:
            raise TeamError("builtin_role")
        role = db.get(AdminRole, role_id)
        if not role:
            raise TeamError("not_found", 404)
        if not set(role.permissions or []) <= perms:
            raise TeamError("role_above_you", 403)
    role.name, role.permissions = name, [p for p in PERMISSIONS if p in wanted_set]
    db.flush()
    for admin in db.scalars(select(Admin).where(Admin.role == role.id)):  # changed rights: sign in again
        admin.session_version = (admin.session_version or 1) + 1
    db.commit()
    return roles(db)[role.id]


def delete_role(db, actor: Admin, role_id: str) -> None:
    if role_id in BUILTIN:
        raise TeamError("builtin_role")
    role = db.get(AdminRole, role_id)
    if not role:
        raise TeamError("not_found", 404)
    if not set(role.permissions or []) <= permissions(db, actor):
        raise TeamError("role_above_you", 403)
    if db.scalar(select(func.count()).select_from(Admin).where(Admin.role == role_id, ~Admin.username.contains(DELETED))):
        raise TeamError("role_in_use")
    for gone in db.scalars(select(Admin).where(Admin.role == role_id)):  # deleted accounts kept for the audit log
        gone.role = "viewer"
    db.delete(role)
    db.commit()
