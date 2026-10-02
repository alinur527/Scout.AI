"""Existing accounts have no publication consent: all profiles start private."""

from alembic import op
import sqlalchemy as sa

revision = "0002_privacy"
down_revision = "0001_legacy"


def upgrade():
    op.add_column("player_profiles", sa.Column("scout_visible", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    raise RuntimeError("Downgrade would remove privacy protection; restore a verified backup instead")
