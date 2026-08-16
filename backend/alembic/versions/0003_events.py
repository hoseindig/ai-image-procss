"""Create events table for recognition audit logging.

Revision ID: 0003_events
Revises: 0002_person_enrollment
Create Date: 2026-08-16

Indexes support list/filter by time, camera, person, and event type.
No embeddings or images are stored.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_events"
down_revision: str | Sequence[str] | None = "0002_person_enrollment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("camera_id", sa.String(length=64), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.String(length=36), nullable=True),
        sa.Column("enrollment_id", sa.String(length=36), nullable=True),
        sa.Column("similarity", sa.Float(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_occurred_at", "events", ["occurred_at"], unique=False)
    op.create_index(
        "ix_events_camera_occurred",
        "events",
        ["camera_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_events_person_occurred",
        "events",
        ["person_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_events_type_occurred",
        "events",
        ["event_type", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_events_type_occurred", table_name="events")
    op.drop_index("ix_events_person_occurred", table_name="events")
    op.drop_index("ix_events_camera_occurred", table_name="events")
    op.drop_index("ix_events_occurred_at", table_name="events")
    op.drop_table("events")
