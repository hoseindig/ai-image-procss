"""Run the API with `python -m app` from the backend directory."""

from app.core.config import load_settings

if __name__ == "__main__":
    import uvicorn

    settings = load_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug and settings.app_env == "development",
    )
