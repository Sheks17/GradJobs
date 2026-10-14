"""Add a compact source-content fingerprint; preserve all existing data."""

import sqlalchemy as sa
from alembic import op

revision = "c53e0a2026"
down_revision = "b42f0c2026"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("jobs", sa.Column("ingestion_fingerprint", sa.String(64), nullable=True))


def downgrade():
    op.drop_column("jobs", "ingestion_fingerprint")
