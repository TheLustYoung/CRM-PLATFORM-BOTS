from sqlalchemy import select
from backend.config import settings
from backend.models import UploadedFile, PublicLink, now, aware
from backend.services.security import DomainError
from storage.files import delete_object


def public_url(db, file: UploadedFile) -> str | None:
    link = db.scalar(select(PublicLink).where(PublicLink.file_id == file.id, PublicLink.revoked.is_(False)))
    if not link or file.deleted:
        return None
    from backend.services.billing import public_base  # the neutral domain set in the dashboard, else the server default
    return f"{public_base(db)}/f/{link.token}"


def resolve_link(db, token: str) -> UploadedFile:
    link = db.get(PublicLink, token)
    file = db.get(UploadedFile, link.file_id) if link else None
    if not link or link.revoked or not file or file.deleted or aware(file.expires_at) <= now():
        raise DomainError("not_found")
    return file


def revoke_file(db, file: UploadedFile) -> None:
    for link in db.scalars(select(PublicLink).where(PublicLink.file_id == file.id)):
        link.revoked = True
    db.commit()


def delete_file(db, file: UploadedFile) -> None:
    # Revoke first so a storage outage can never leave a working link to a "deleted" file.
    revoke_file(db, file)
    delete_object(file.object_key)
    file.deleted = True
    db.commit()
