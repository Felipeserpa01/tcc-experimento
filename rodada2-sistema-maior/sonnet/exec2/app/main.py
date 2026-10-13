"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.core.enums import UserRole
from app.core.exceptions import register_exception_handlers
from app.core.security import hash_password
from app.database import SessionLocal, init_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.routes import (
    appointments,
    auth,
    billing,
    medical_records,
    patients,
    professionals,
    reports,
    users,
)

settings = get_settings()


def _bootstrap_initial_admin() -> None:
    """Creates a default admin account on first run, if configured via env vars
    and no admin user exists yet. Prevents a chicken-and-egg problem where only
    an admin can create staff accounts, but no admin exists on a fresh database."""
    email = os.getenv("INITIAL_ADMIN_EMAIL")
    password = os.getenv("INITIAL_ADMIN_PASSWORD")
    if not email or not password:
        return

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        if repo.get_by_email(email):
            return
        admin = User(email=email.lower(), hashed_password=hash_password(password), role=UserRole.ADMIN)
        repo.create(admin)
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _bootstrap_initial_admin()
    yield


app = FastAPI(
    title=settings.app_name,
    description="API REST para gestão de uma clínica médica de médio porte.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(patients.router)
app.include_router(professionals.router)
app.include_router(appointments.router)
app.include_router(medical_records.router)
app.include_router(billing.router)
app.include_router(reports.router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}
