"""Ad posts sent to the bots' users from the dashboard, with per-user message ids for deletion."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)


def upgrade():
    op.create_table("broadcasts",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("text", sa.Text(), nullable=False),
        sa.Column("button_text", sa.String(64)), sa.Column("button_url", sa.String(300)), sa.Column("photo", sa.LargeBinary()),
        sa.Column("photo_ids", sa.JSON(), nullable=False), sa.Column("bots", sa.JSON(), nullable=False),
        sa.Column("skip_premium", sa.Boolean(), nullable=False), sa.Column("status", sa.String(16), nullable=False),
        sa.Column("audience", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("admin_users.id"), nullable=False),
        sa.Column("created_at", TZ, nullable=False), sa.Column("finished_at", TZ), sa.Column("deleted_at", TZ))
    op.create_index("ix_broadcasts_created_at", "broadcasts", ["created_at"])
    op.create_table("broadcast_messages",
        sa.Column("broadcast_id", sa.String(36), sa.ForeignKey("broadcasts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), primary_key=True), sa.Column("bot_id", sa.String(16), nullable=False),
        sa.Column("message_id", sa.BigInteger()), sa.Column("deleted", sa.Boolean(), nullable=False),
        sa.Column("delete_failed", sa.Boolean(), nullable=False),
        sa.Column("sent_at", TZ, nullable=False))


def downgrade():
    op.drop_table("broadcast_messages")
    op.drop_table("broadcasts")
