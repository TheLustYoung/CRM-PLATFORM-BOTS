"""Initial schema (frozen; later changes go into new revisions)."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)


def upgrade():
    op.create_table("users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("username", sa.String(64)), sa.Column("first_name", sa.String(128)), sa.Column("language_code", sa.String(16)),
        sa.Column("banned", sa.Boolean(), nullable=False), sa.Column("daily_limit", sa.Integer()),
        sa.Column("created_at", TZ, nullable=False), sa.Column("last_seen", TZ, nullable=False))
    op.create_table("bots",
        sa.Column("id", sa.String(16), primary_key=True), sa.Column("username", sa.String(64)),
        sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("daily_limit", sa.Integer(), nullable=False),
        sa.Column("welcome_text", sa.Text()), sa.Column("last_seen", TZ))
    op.create_table("bot_users",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("bot_id", sa.String(16), sa.ForeignKey("bots.id"), primary_key=True),
        sa.Column("created_at", TZ, nullable=False))
    op.create_table("user_preferences",
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("language", sa.String(8), nullable=False))
    op.create_table("uploaded_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("bot_id", sa.String(16), sa.ForeignKey("bots.id")),
        sa.Column("job_id", sa.String(36), nullable=False), sa.Column("object_key", sa.String(256), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False), sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("mime", sa.String(100), nullable=False), sa.Column("sha256", sa.String(64)),
        sa.Column("downloads", sa.BigInteger(), nullable=False),
        sa.Column("created_at", TZ, nullable=False), sa.Column("expires_at", TZ, nullable=False),
        sa.Column("deleted", sa.Boolean(), nullable=False))
    op.create_table("download_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("bot_id", sa.String(16), sa.ForeignKey("bots.id"), nullable=False),
        sa.Column("request_key", sa.String(160), nullable=False), sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("source_url", sa.Text()), sa.Column("platform", sa.String(64), nullable=False),
        sa.Column("selected_format", sa.String(256)), sa.Column("status", sa.String(16), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False), sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("error", sa.String(256)),
        sa.Column("created_at", TZ, nullable=False), sa.Column("started_at", TZ), sa.Column("completed_at", TZ),
        sa.Column("output_file_id", sa.String(36), sa.ForeignKey("uploaded_files.id")),
        sa.UniqueConstraint("user_id", "bot_id", "request_key"))
    op.create_table("public_file_links",
        sa.Column("token", sa.String(64), primary_key=True),
        sa.Column("file_id", sa.String(36), sa.ForeignKey("uploaded_files.id"), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False))
    op.create_table("platform_compatibility",
        sa.Column("platform", sa.String(64), primary_key=True), sa.Column("extractor", sa.String(100), nullable=False),
        sa.Column("status", sa.String(40), nullable=False), sa.Column("last_test_date", TZ),
        sa.Column("limitations", sa.Text(), nullable=False))
    op.create_table("usage_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("bot_id", sa.String(16), sa.ForeignKey("bots.id"), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("download_jobs.id"), nullable=False, unique=True),
        sa.Column("bytes", sa.BigInteger(), nullable=False), sa.Column("created_at", TZ, nullable=False))
    op.create_table("admin_users",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("username", sa.String(64), unique=True, nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False))
    op.create_table("system_settings",
        sa.Column("key", sa.String(64), primary_key=True), sa.Column("value", sa.JSON(), nullable=False))
    op.create_table("audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("admin_id", sa.String(36), sa.ForeignKey("admin_users.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False), sa.Column("target", sa.String(128), nullable=False),
        sa.Column("created_at", TZ, nullable=False))
    for table, columns in {
        "users": ["username", "last_seen"], "download_jobs": ["user_id", "bot_id"],
        "uploaded_files": ["user_id", "job_id", "expires_at"], "public_file_links": ["file_id"],
        "usage_records": ["user_id", "bot_id", "created_at"], "audit_logs": ["created_at"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_index("ix_jobs_status_created", "download_jobs", ["status", "created_at"])


def downgrade():
    for name in ["audit_logs", "system_settings", "admin_users", "usage_records", "platform_compatibility", "public_file_links",
                 "download_jobs", "uploaded_files", "user_preferences", "bot_users", "bots", "users"]:
        op.drop_table(name)
