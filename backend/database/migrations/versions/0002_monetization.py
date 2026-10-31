"""Monetization: Premium end date, referrals and the Premium payments ledger."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)


def upgrade():
    op.add_column("users", sa.Column("premium_until", TZ))
    op.add_column("users", sa.Column("referred_by", sa.BigInteger()))
    op.add_column("users", sa.Column("referral_counted", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_users_referred_by", "users", ["referred_by"])
    op.create_table("premium_payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("bot_id", sa.String(16), sa.ForeignKey("bots.id")),
        sa.Column("source", sa.String(16), nullable=False), sa.Column("stars", sa.Integer(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False), sa.Column("charge_id", sa.String(128), unique=True),
        sa.Column("created_at", TZ, nullable=False))
    op.create_index("ix_premium_payments_user_id", "premium_payments", ["user_id"])
    op.create_index("ix_premium_payments_created_at", "premium_payments", ["created_at"])


def downgrade():
    op.drop_table("premium_payments")
    op.drop_index("ix_users_referred_by", "users")
    for column in ("referral_counted", "referred_by", "premium_until"):
        op.drop_column("users", column)
