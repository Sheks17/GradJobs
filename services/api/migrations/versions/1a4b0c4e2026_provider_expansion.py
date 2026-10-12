"""Provider configuration, source request metrics, deadlines and explicit metadata."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "1a4b0c4e2026"
down_revision = "9f83a21cb4d0"
branch_labels = None
depends_on = None


def upgrade():
    json_type = sa.JSON().with_variant(JSONB(), "postgresql")
    op.add_column(
        "job_sources", sa.Column("provider_config", json_type, nullable=False, server_default="{}")
    )
    op.add_column("jobs", sa.Column("closing_at", sa.DateTime(timezone=True)))
    op.add_column(
        "jobs", sa.Column("provider_metadata", json_type, nullable=False, server_default="{}")
    )
    op.create_index("ix_jobs_closing_at", "jobs", ["closing_at"])
    for name in (
        "request_count",
        "request_latency_ms",
        "failed_requests",
        "rate_limit_responses",
        "upsert_duration_ms",
    ):
        op.add_column(
            "source_syncs", sa.Column(name, sa.Integer(), nullable=False, server_default="0")
        )


def downgrade():
    for name in (
        "request_count",
        "request_latency_ms",
        "failed_requests",
        "rate_limit_responses",
        "upsert_duration_ms",
    ):
        op.drop_column("source_syncs", name)
    op.drop_index("ix_jobs_closing_at", table_name="jobs")
    op.drop_column("jobs", "provider_metadata")
    op.drop_column("jobs", "closing_at")
    op.drop_column("job_sources", "provider_config")
