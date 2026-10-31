import hashlib
import mimetypes
from datetime import timedelta
from pathlib import Path
from sqlalchemy import select
from backend.models import UploadedFile, PublicLink, now, uid
from backend.services.security import DomainError, safe_filename
from storage.backends import backend

# Not in every OS mime database (e.g. Windows): keep types consistent across servers.
for _type, _ext in (("image/webp", ".webp"), ("video/webm", ".webm"), ("audio/mp4", ".m4a"), ("audio/ogg", ".opus")):
    mimetypes.add_type(_type, _ext)


def ensure_bucket():
    backend().ensure()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def put_file(db, job, path: Path, retention_days: int) -> UploadedFile:
    """Upload, verify integrity (size + SHA-256 stored), create one public link."""
    # Deterministic key: a retried job reuses the object instead of creating orphans.
    name = safe_filename(path.name)
    key = f"jobs/{job.id}/{name}"
    existing = db.scalar(select(UploadedFile).where(UploadedFile.object_key == key))
    if existing:
        if existing.deleted:
            raise DomainError("expired")
        return existing
    mime = mimetypes.guess_type(name)[0] or "application/octet-stream"
    size = path.stat().st_size
    checksum = sha256(path)
    if backend().upload(path, key, mime) != size:
        raise DomainError("failed")
    file = UploadedFile(id=uid(), user_id=job.user_id, bot_id=job.bot_id, job_id=job.id, object_key=key, name=name,
                        size=size, mime=mime[:100], sha256=checksum, expires_at=now() + timedelta(days=retention_days))
    db.add(file)
    db.flush()
    db.add(PublicLink(file_id=file.id))
    db.commit()
    return file


def open_object(key: str):
    """(chunk iterator, close function). Raises ObjectMissing if the storage lost the object."""
    return backend().open(key)


def download_to(key: str, destination: Path) -> None:
    backend().download_to(key, destination)


def delete_object(key: str) -> None:
    backend().delete(key)
