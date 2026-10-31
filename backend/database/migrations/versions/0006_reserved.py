"""Reserved revision (kept so the revision chain 0001…0009 stays continuous); no schema changes."""

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
