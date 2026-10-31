"""Admin team: accounts and roles (permission team.manage, checked in admin_required)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from backend.api.deps import admin_required, audit, require
from backend.database import session
from backend.models import Admin
from backend.services import team
from backend.services.auth import hasher

router = APIRouter(prefix="/api/admin/team", tags=["admin"], dependencies=[Depends(admin_required)])


class AccountCreate(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)
    role: str = Field(max_length=40)


class AccountPatch(BaseModel):
    role: str | None = Field(None, max_length=40)
    active: bool | None = None
    password: str | None = Field(None, max_length=256)


class RoleBody(BaseModel):
    name: str = Field(max_length=64)
    permissions: list[str] = Field(default_factory=list, max_length=len(team.PERMISSIONS))


def refused(error: team.TeamError):
    return HTTPException(error.status, error.code)


@router.get("")
def overview(db=Depends(session), admin=Depends(admin_required)):
    accounts = db.scalars(select(Admin).where(~Admin.username.contains(team.DELETED)).order_by(Admin.username))
    return {"accounts": [team.public(a) for a in accounts], "roles": list(team.roles(db).values()),
            "permissions": list(team.PERMISSIONS), "me": admin.id}


@router.post("/accounts")
def create(data: AccountCreate, db=Depends(session), admin=Depends(admin_required)):
    try:
        created = team.create_account(db, admin, data.username, data.password, data.role, hasher)
    except team.TeamError as error:
        raise refused(error) from None
    audit(db, admin, "team.account.create", f"{created.username}:{created.role}")
    return team.public(created)


@router.patch("/accounts/{id}")
def update(id: str, data: AccountPatch, db=Depends(session), admin=Depends(admin_required)):
    target = require(db, Admin, id)
    try:
        team.update_account(db, admin, target, hasher, role=data.role, active=data.active, password=data.password or None)
    except team.TeamError as error:
        raise refused(error) from None
    changes = [f"role={data.role}" if data.role else "", f"active={data.active}" if data.active is not None else "",
               "password" if data.password else ""]
    audit(db, admin, "team.account.update", f"{target.username}:{','.join(c for c in changes if c)}")
    return team.public(target)


@router.delete("/accounts/{id}")
def delete(id: str, db=Depends(session), admin=Depends(admin_required)):
    target = require(db, Admin, id)
    name = target.username
    try:
        team.delete_account(db, admin, target)
    except team.TeamError as error:
        raise refused(error) from None
    audit(db, admin, "team.account.delete", name)
    return {"ok": True}


@router.post("/roles")
def create_role(data: RoleBody, db=Depends(session), admin=Depends(admin_required)):
    try:
        role = team.save_role(db, admin, None, data.name, data.permissions)
    except team.TeamError as error:
        raise refused(error) from None
    audit(db, admin, "team.role.create", role["name"])
    return role


@router.put("/roles/{id}")
def update_role(id: str, data: RoleBody, db=Depends(session), admin=Depends(admin_required)):
    try:
        role = team.save_role(db, admin, id, data.name, data.permissions)
    except team.TeamError as error:
        raise refused(error) from None
    audit(db, admin, "team.role.update", role["name"])
    return role


@router.delete("/roles/{id}")
def delete_role(id: str, db=Depends(session), admin=Depends(admin_required)):
    try:
        team.delete_role(db, admin, id)
    except team.TeamError as error:
        raise refused(error) from None
    audit(db, admin, "team.role.delete", id)
    return {"ok": True}
