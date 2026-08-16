"""Top-level API router. Route modules stay thin."""

from fastapi import APIRouter

from app.api.routes import cameras, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(cameras.router)
