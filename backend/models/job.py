from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base
from backend.models.common import now, uid


class Job(Base):
    """Metadata extraction, download or upload request processed by a worker."""
    __tablename__ = "download_jobs"
    __table_args__ = (UniqueConstraint("user_id", "bot_id", "request_key"), Index("ix_jobs_status_created", "status", "created_at"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bot_id: Mapped[str] = mapped_column(ForeignKey("bots.id"), index=True)
    request_key: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(16))  # metadata | download | upload
    source_url: Mapped[str | None] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(64), default="telegram")
    selected_format: Mapped[str | None] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued | processing | completed | failed
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    output_file_id: Mapped[str | None] = mapped_column(ForeignKey("uploaded_files.id"))


class Usage(Base):
    """One row per accepted job; used for daily limits and statistics."""
    __tablename__ = "usage_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bot_id: Mapped[str] = mapped_column(ForeignKey("bots.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("download_jobs.id"), unique=True)
    bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
