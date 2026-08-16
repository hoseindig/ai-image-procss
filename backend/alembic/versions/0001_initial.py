"""Initial schema placeholder.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-16

Phase 1 has no application tables. This revision establishes Alembic history
so later phases can autogenerate against the same metadata.
"""

from collections.abc import Sequence

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
