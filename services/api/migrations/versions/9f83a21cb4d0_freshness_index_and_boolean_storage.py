"""Index freshness filtering and normalize conflict boolean storage across dialects.

Revision ID: 9f83a21cb4d0
Revises: 4d3b3cd86b1c
"""

import sqlalchemy as sa
from alembic import op

revision = "9f83a21cb4d0"
down_revision = "4d3b3cd86b1c"
branch_labels = None
depends_on = None


def upgrade():
    # Older SQLite previews could have a quoted 'false' server default, which
    # Python treats as truthy. The stored reasons are authoritative evidence.
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table(
            "jobs",
            table_args=(
                sa.CheckConstraint("early_career_score BETWEEN 0 AND 100"),
                sa.CheckConstraint("salary_min IS NULL OR salary_min >= 0"),
                sa.CheckConstraint("salary_max IS NULL OR salary_max >= 0"),
                sa.CheckConstraint(
                    "salary_min IS NULL OR salary_max IS NULL OR salary_max >= salary_min"
                ),
            ),
        ) as batch:
            batch.alter_column(
                "classification_conflict", existing_type=sa.Boolean(), server_default=sa.false()
            )
        op.execute(
            sa.text(
                "UPDATE jobs SET classification_conflict = "
                "CASE WHEN json_array_length(conflict_reasons)>0 THEN 1 ELSE 0 END"
            )
        )
    else:
        op.alter_column(
            "jobs", "classification_conflict", existing_type=sa.Boolean(), server_default=sa.false()
        )
        op.execute(
            sa.text(
                "UPDATE jobs SET classification_conflict = (jsonb_array_length(conflict_reasons)>0)"
            )
        )
    op.create_index(
        "ix_jobs_active_freshness",
        "jobs",
        ["is_active", sa.text("coalesce(posted_at, first_seen_at)")],
    )
    if dialect == "sqlite":
        op.execute(sa.text("ANALYZE"))


def downgrade():
    op.drop_index("ix_jobs_active_freshness", table_name="jobs")
    # Correct boolean values/defaults are retained; no user/source data is lost.
