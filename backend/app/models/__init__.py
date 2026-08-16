"""SQLAlchemy models.

Phase 1 has no application tables. Import new models here in later phases so
Alembic autogenerate can discover them via `Base.metadata`.
"""

from app.db.base import Base

__all__ = ["Base"]
