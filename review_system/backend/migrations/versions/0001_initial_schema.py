"""Create the review-system schema, including deployment security audit data."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _create(name: str, *columns, **kwargs) -> None:
    if name not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(name, *columns, **kwargs)


def upgrade() -> None:
    timestamp = sa.DateTime(timezone=True)
    _create("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(120), nullable=False), sa.Column("password_hash", sa.String(300), nullable=False), sa.Column("role", sa.String(30), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("created_at", timestamp, nullable=False), sa.UniqueConstraint("username"))
    _create("sessions", sa.Column("token_hash", sa.String(64), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("csrf_token", sa.String(64), nullable=False), sa.Column("expires_at", timestamp, nullable=False))
    _create("login_attempts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("username", sa.String(120), nullable=False), sa.Column("source_ip", sa.String(64), nullable=False), sa.Column("successful", sa.Boolean(), nullable=False), sa.Column("created_at", timestamp, nullable=False))
    _create("source_snapshots", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("commit", sa.String(80), nullable=False), sa.Column("fingerprint", sa.String(64), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("error", sa.Text()), sa.Column("created_at", timestamp, nullable=False), sa.UniqueConstraint("fingerprint"))
    _create("snapshot_tracks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("source_snapshots.id"), nullable=False), sa.Column("name", sa.String(120), nullable=False), sa.Column("version", sa.String(40), nullable=False), sa.Column("display_name", sa.String(240), nullable=False), sa.UniqueConstraint("snapshot_id", "name"))
    _create("snapshot_tasks", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("track_id", sa.Integer(), sa.ForeignKey("snapshot_tracks.id"), nullable=False), sa.Column("task_id", sa.String(180), nullable=False), sa.Column("version", sa.Integer(), nullable=False), sa.Column("fingerprint", sa.String(64), nullable=False), sa.Column("review_status", sa.String(30), nullable=False), sa.Column("data_json", sa.Text(), nullable=False), sa.Column("view_json", sa.Text(), nullable=False), sa.Column("scoring_json", sa.Text(), nullable=False), sa.Column("schema_json", sa.Text(), nullable=False), sa.Column("attachments_json", sa.Text(), nullable=False), sa.UniqueConstraint("track_id", "task_id"))
    _create("comments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("target_type", sa.String(30), nullable=False), sa.Column("target_id", sa.String(220), nullable=False), sa.Column("snapshot_fingerprint", sa.String(64)), sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("parent_id", sa.Integer(), sa.ForeignKey("comments.id")), sa.Column("body", sa.Text(), nullable=False), sa.Column("resolved", sa.Boolean(), nullable=False), sa.Column("created_at", timestamp, nullable=False))
    _create("review_events", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("target_type", sa.String(30), nullable=False), sa.Column("target_id", sa.String(220), nullable=False), sa.Column("from_status", sa.String(30)), sa.Column("to_status", sa.String(30), nullable=False), sa.Column("note", sa.Text()), sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", timestamp, nullable=False))
    _create("drafts", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("track", sa.String(120), nullable=False), sa.Column("title", sa.String(240), nullable=False), sa.Column("status", sa.String(30), nullable=False), sa.Column("current_revision", sa.Integer(), nullable=False), sa.Column("approved_revision", sa.Integer()), sa.Column("source_fingerprint", sa.String(64)), sa.Column("created_at", timestamp, nullable=False), sa.Column("updated_at", timestamp, nullable=False))
    _create("draft_revisions", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("draft_id", sa.Integer(), sa.ForeignKey("drafts.id"), nullable=False), sa.Column("revision", sa.Integer(), nullable=False), sa.Column("payload_json", sa.Text(), nullable=False), sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("created_at", timestamp, nullable=False), sa.UniqueConstraint("draft_id", "revision"))
    _create("attachments", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("target_type", sa.String(30), nullable=False), sa.Column("target_id", sa.String(220), nullable=False), sa.Column("name", sa.String(255), nullable=False), sa.Column("media_type", sa.String(120), nullable=False), sa.Column("size", sa.Integer(), nullable=False), sa.Column("storage_path", sa.String(500), nullable=False), sa.Column("content", sa.Text()), sa.Column("created_at", timestamp, nullable=False))
    _create("shared_files", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("media_type", sa.String(120), nullable=False), sa.Column("size", sa.Integer(), nullable=False), sa.Column("sha256", sa.String(64), nullable=False), sa.Column("storage_path", sa.String(500), nullable=False), sa.Column("preview_html", sa.Text()), sa.Column("preview_error", sa.Text()), sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False), sa.Column("track", sa.String(120)), sa.Column("task_id", sa.String(180)), sa.Column("created_at", timestamp, nullable=False))


def downgrade() -> None:
    for table in ("attachments", "draft_revisions", "drafts", "review_events", "comments", "snapshot_tasks", "snapshot_tracks", "source_snapshots", "login_attempts", "sessions", "users"):
        if table in sa.inspect(op.get_bind()).get_table_names():
            op.drop_table(table)
