"""Criacao do schema e bootstrap do administrador inicial."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registra os modelos no metadata)
from app.core.config import get_settings
from app.core.security import hash_password, validate_password_strength
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.enums import UserRole
from app.models.user import User

logger = logging.getLogger("clinica.init")


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def create_first_admin(db: Session) -> User | None:
    """Cria o administrador inicial a partir das variaveis de ambiente."""
    settings = get_settings()
    email = (settings.first_admin_email or "").strip().lower()
    password = settings.first_admin_password

    if not email or not password:
        logger.info(
            "FIRST_ADMIN_EMAIL/FIRST_ADMIN_PASSWORD nao configurados: "
            "nenhum administrador inicial foi criado."
        )
        return None

    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing is not None:
        return existing

    try:
        validate_password_strength(password)
    except Exception as exc:  # pragma: no cover - erro de configuracao
        logger.error("FIRST_ADMIN_PASSWORD nao atende a politica de senha: %s", exc)
        return None

    admin = User(
        email=email,
        full_name=settings.first_admin_name,
        hashed_password=hash_password(password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    logger.info("Administrador inicial criado: %s", admin.email)
    return admin


def init_db() -> None:
    settings = get_settings()
    create_tables()
    settings.upload_path.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        create_first_admin(db)
    finally:
        db.close()
