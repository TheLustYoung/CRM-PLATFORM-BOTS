"""Unified billing: one order/transaction table for Stars, cards and crypto."""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)


def upgrade():
    op.create_table("orders",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("token", sa.String(48), nullable=False, unique=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("bot_id", sa.String(16), sa.ForeignKey("bots.id"), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False), sa.Column("method", sa.String(24)), sa.Column("currency", sa.String(8)),
        sa.Column("amount", sa.Integer()), sa.Column("status", sa.String(16), nullable=False), sa.Column("provider_ref", sa.String(128)),
        sa.Column("lang", sa.String(8), nullable=False), sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", TZ, nullable=False), sa.Column("paid_at", TZ), sa.Column("expires_at", TZ, nullable=False),
        sa.Column("refunded_at", TZ))
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_method_ref", "orders", ["method", "provider_ref"], unique=True)
    op.create_index("ix_orders_status_created", "orders", ["status", "created_at"])


def downgrade():
    op.drop_table("orders")
