"""Retain long provider employment descriptions on PostgreSQL."""

import sqlalchemy as sa
from alembic import op

revision = "a12de0c2026"
down_revision = "1a4b0c4e2026"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite does not enforce VARCHAR lengths; keep its existing table and indexes.
    if op.get_bind().dialect.name != "sqlite":
        op.alter_column("jobs", "employment_type", existing_type=sa.String(100), type_=sa.Text())


def downgrade():
    if op.get_bind().dialect.name != "sqlite":
        # PostgreSQL refuses narrowing if long values exist; never silently truncate them.
        op.alter_column("jobs", "employment_type", existing_type=sa.Text(), type_=sa.String(100))
