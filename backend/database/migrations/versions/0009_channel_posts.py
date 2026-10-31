"""Posts of the bots' public channel, managed from the dashboard."""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "channel_posts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("chat", sa.String(64), nullable=False),
        sa.Column("bot_id", sa.String(16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        sa.Column("media", sa.LargeBinary()),
        sa.Column("media_kind", sa.String(8)),
        sa.Column("media_name", sa.String(128)),
        sa.Column("buttons", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="scheduled"),
        sa.Column("publish_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("message_id", sa.BigInteger()),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("error", sa.String(300)),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("admin_users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_channel_posts_status", "channel_posts", ["status"])
    op.create_index("ix_channel_posts_publish_at", "channel_posts", ["publish_at"])


def downgrade():
    op.drop_index("ix_channel_posts_publish_at", "channel_posts")
    op.drop_index("ix_channel_posts_status", "channel_posts")
    op.drop_table("channel_posts")
