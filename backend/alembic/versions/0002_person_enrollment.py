"""Person and enrollment_samples tables.

Revision ID: 0002_person_enrollment
Revises: 0001_initial
Create Date: 2026-08-16

Phase 7A: persistent Person IDs and face embedding gallery samples.
Embeddings are stored as 512-byte little-endian float32 blobs (128-D).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_person_enrollment"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "persons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("display_name"),
    )
    op.create_table(
        "enrollment_samples",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("person_id", sa.String(length=36), nullable=False),
        sa.Column("embedding", sa.LargeBinary(), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("normalized", sa.Boolean(), nullable=False),
        sa.Column("face_width", sa.Float(), nullable=True),
        sa.Column("face_height", sa.Float(), nullable=True),
        sa.Column("sharpness", sa.Float(), nullable=True),
        sa.Column("brightness", sa.Float(), nullable=True),
        sa.Column("source_track_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("enrollment_samples", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_enrollment_samples_person_id"),
            ["person_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("enrollment_samples", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_enrollment_samples_person_id"))
    op.drop_table("enrollment_samples")
    op.drop_table("persons")
