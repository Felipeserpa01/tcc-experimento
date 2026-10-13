from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.error_handlers import register_exception_handlers
from app.db.session import engine
from app.db.base import DeclarativeBase
from app.api.v1 import auth


def create_app() -> FastAPI:
    # Create tables
    DeclarativeBase.metadata.create_all(bind=engine)

    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug
    )

    # Register exception handlers
    register_exception_handlers(app)

    # Add CORS middleware
    if isinstance(settings.allowed_origins, str):
        allowed_origins = [settings.allowed_origins]
    else:
        allowed_origins = settings.allowed_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    def health():
        return {"status": "ok", "version": settings.app_version}

    # Include routers
    app.include_router(auth.router, prefix="/api/v1")

    return app


app = create_app()
