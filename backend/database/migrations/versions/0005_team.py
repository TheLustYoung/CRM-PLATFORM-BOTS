"""Team: roles and permissions for admin accounts. Existing admins become owners, so nobody loses access."""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)


def upgrade():
    op.create_table("admin_roles",
        sa.Column("id", sa.String(40), primary_key=True), sa.Column("name", sa.String(64), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False), sa.Column("builtin", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("admin_users") as table:
        table.add_column(sa.Column("role", sa.String(40), nullable=False, server_default="owner"))
        table.add_column(sa.Column("session_version", sa.Integer(), nullable=False, server_default="1"))
        table.add_column(sa.Column("created_at", TZ))
        table.add_column(sa.Column("created_by", sa.String(64)))
        table.add_column(sa.Column("last_login_at", TZ))


def downgrade():
    with op.batch_alter_table("admin_users") as table:
        for column in ("last_login_at", "created_by", "created_at", "session_version", "role"):
            table.drop_column(column)
    op.drop_table("admin_roles")
