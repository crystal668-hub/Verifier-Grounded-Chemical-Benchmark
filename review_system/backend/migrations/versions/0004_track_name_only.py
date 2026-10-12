"""Use the canonical track name without a separate display name."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "snapshot_tracks" not in tables:
        return
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("snapshot_tracks")}
    if "display_name" in columns:
        with op.batch_alter_table("snapshot_tracks") as batch_op:
            batch_op.drop_column("display_name")


def downgrade() -> None:
    tables = sa.inspect(op.get_bind()).get_table_names()
    if "snapshot_tracks" not in tables:
        return
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("snapshot_tracks")}
    if "display_name" not in columns:
        op.add_column("snapshot_tracks", sa.Column("display_name", sa.String(240), nullable=True))
        op.execute(sa.text("UPDATE snapshot_tracks SET display_name = name"))
        with op.batch_alter_table("snapshot_tracks") as batch_op:
            batch_op.alter_column("display_name", existing_type=sa.String(240), nullable=False)
