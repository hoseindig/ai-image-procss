"""Request-scoped FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.cameras.manager import CameraManager
from app.core.config import Settings
from app.db.session import Database


def get_settings_dep(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("Application settings are not initialized")
    return settings


def get_database(request: Request) -> Database:
    database = getattr(request.app.state, "database", None)
    if not isinstance(database, Database):
        raise RuntimeError("Database is not initialized")
    return database


def get_started_at(request: Request) -> datetime:
    started_at = getattr(request.app.state, "started_at", None)
    if not isinstance(started_at, datetime):
        raise RuntimeError("Application start time is not initialized")
    return started_at


def get_session(database: Annotated[Database, Depends(get_database)]) -> Iterator[Session]:
    with database.session() as session:
        yield session


def get_camera_manager(request: Request) -> CameraManager:
    manager = getattr(request.app.state, "camera_manager", None)
    if not isinstance(manager, CameraManager):
        raise RuntimeError("Camera manager is not initialized")
    return manager


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
SessionDep = Annotated[Session, Depends(get_session)]
StartedAtDep = Annotated[datetime, Depends(get_started_at)]
CameraManagerDep = Annotated[CameraManager, Depends(get_camera_manager)]
