"""Subscription tiers and credits: the user's paid tier and extra downloads beyond the daily limit."""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as table:
        table.add_column(sa.Column("premium_tier", sa.String(24)))
        table.add_column(sa.Column("credits", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("users") as table:
        table.drop_column("credits")
        table.drop_column("premium_tier")
