"""SQLAlchemy 2.x declarative base.

Application tables are added in later phases. Alembic is wired to this metadata
so `alembic revision --autogenerate` will pick them up when they exist.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
