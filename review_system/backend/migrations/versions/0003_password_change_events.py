"""Add idempotent password-change audit records."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "password_change_events" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "password_change_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "request_id"),
    )
    op.create_index("ix_password_change_events_user_id", "password_change_events", ["user_id"])
    op.create_index("ix_password_change_events_created_at", "password_change_events", ["created_at"])


def downgrade() -> None:
    if "password_change_events" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("password_change_events")
