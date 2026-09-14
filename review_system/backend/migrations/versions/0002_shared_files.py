"""Add shared test-result files."""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "shared_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(120), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("preview_html", sa.Text()),
        sa.Column("preview_error", sa.Text()),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("track", sa.String(120)),
        sa.Column("task_id", sa.String(180)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_shared_files_sha256", "shared_files", ["sha256"])
    op.create_index("ix_shared_files_owner_id", "shared_files", ["owner_id"])

def downgrade() -> None:
    op.drop_index("ix_shared_files_owner_id", table_name="shared_files")
    op.drop_index("ix_shared_files_sha256", table_name="shared_files")
    op.drop_table("shared_files")
