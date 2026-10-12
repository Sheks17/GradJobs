"""Add ingestion run summaries and observable source cooldowns without changing job data."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "b42f0c2026"
down_revision = "a12de0c2026"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("job_sources", sa.Column("last_error_at", sa.DateTime(timezone=True)))
    op.add_column("job_sources", sa.Column("disabled_reason", sa.Text()))
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column(
            "summary",
            sa.JSON().with_variant(JSONB(), "postgresql"),
            nullable=False,
            server_default="{}",
        ),
    )
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"])


def downgrade():
    op.drop_table("ingestion_runs")
    op.drop_column("job_sources", "disabled_reason")
    op.drop_column("job_sources", "last_error_at")
