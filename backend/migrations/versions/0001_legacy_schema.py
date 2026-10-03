"""Create the original schema, or adopt only its verified table/column layout."""

from alembic import op
import sqlalchemy as sa

revision = "0001_legacy"
down_revision = None

LEGACY_COLUMNS = {
    "users": {"id", "username", "password_hash", "role", "created_at"},
    "player_profiles": {"user_id", "full_name", "position", "age", "team", "bio"},
    "analysis_jobs": {"id", "user_id", "status", "stage", "progress", "original_filename", "stored_filename", "selected_player_id", "demo", "created_at", "started_at", "completed_at", "error", "video", "gallery", "tracks", "calibration", "result"},
}


def upgrade():
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names()) - {"alembic_version"}
    if tables:
        if tables != set(LEGACY_COLUMNS) or any(
            {c["name"] for c in inspector.get_columns(table)} != columns
            for table, columns in LEGACY_COLUMNS.items()
        ):
            raise RuntimeError("Unrecognized legacy database schema; restore/review a backup before migration")
        for table, primary in (("users", "id"), ("player_profiles", "user_id"), ("analysis_jobs", "id")):
            if inspector.get_pk_constraint(table)["constrained_columns"] != [primary]:
                raise RuntimeError("Legacy primary key differs from supported schema")
        unique = inspector.get_unique_constraints("users") + [index for index in inspector.get_indexes("users") if index["unique"]]
        if not any(constraint["column_names"] == ["username"] for constraint in unique):
            raise RuntimeError("Legacy username uniqueness constraint is missing")
        for table in ("player_profiles", "analysis_jobs"):
            if not any(
                fk["constrained_columns"] == ["user_id"] and fk["referred_table"] == "users" and fk["referred_columns"] == ["id"]
                for fk in inspector.get_foreign_keys(table)
            ):
                raise RuntimeError("Legacy ownership foreign key is missing")
        return
    op.create_table("users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(40), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_table("player_profiles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("position", sa.String(30), nullable=False),
        sa.Column("age", sa.Integer(), nullable=True),
        sa.Column("team", sa.String(100), nullable=False),
        sa.Column("bio", sa.Text(), nullable=False))
    op.create_table("analysis_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("stage", sa.String(24), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("stored_filename", sa.String(50), nullable=False),
        sa.Column("selected_player_id", sa.Integer(), nullable=True),
        sa.Column("demo", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("video", sa.JSON(), nullable=False),
        sa.Column("gallery", sa.JSON(), nullable=False),
        sa.Column("tracks", sa.JSON(), nullable=False),
        sa.Column("calibration", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True))
    op.create_index("ix_analysis_jobs_user_id", "analysis_jobs", ["user_id"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])


def downgrade():
    raise RuntimeError("Destructive downgrade is unsupported; restore a verified backup instead")
