"""Top-level API router. Route modules stay thin."""

from fastapi import APIRouter

from app.api.routes import cameras, events, health, persons, recognition_test

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(cameras.router)
api_router.include_router(persons.router)
api_router.include_router(events.router)
api_router.include_router(recognition_test.router)
