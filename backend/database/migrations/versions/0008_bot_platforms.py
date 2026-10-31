"""Platforms per bot: each bot can serve its own subset of the enabled platforms."""
from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("bots") as table:
        table.add_column(sa.Column("platforms", sa.JSON()))


def downgrade():
    with op.batch_alter_table("bots") as table:
        table.drop_column("platforms")
