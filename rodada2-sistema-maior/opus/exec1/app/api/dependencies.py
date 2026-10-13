"""Dependencias compartilhadas pelas rotas: sessao, usuario atual e permissoes."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    InvalidTokenError,
    PermissionDeniedError,
)
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repository import UserRepository

settings = get_settings()

bearer_scheme = HTTPBearer(auto_error=False, description="Access token JWT")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/token", auto_error=False
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    oauth_token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve o usuario autenticado a partir do access token."""
    token = credentials.credentials if credentials else oauth_token
    if not token:
        raise InvalidTokenError("Token de acesso nao informado.")

    payload = decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError("Identificador de usuario invalido no token.") from exc

    user = UserRepository(db).get(user_id)
    if user is None:
        raise InvalidTokenError("Usuario do token nao existe mais.")
    if not user.is_active:
        raise AccountInactiveError("Conta desativada.")
    if user.is_locked:
        raise AccountLockedError()
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    """Fabrica de dependencia para controle de acesso por perfil."""
    allowed: set[UserRole] = set(roles)

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise PermissionDeniedError(
                "Seu perfil nao tem permissao para acessar este recurso.",
                details={
                    "your_role": current_user.role.value,
                    "allowed_roles": sorted(role.value for role in allowed),
                },
            )
        return current_user

    return dependency


def roles_description(roles: Iterable[UserRole]) -> str:
    return ", ".join(sorted(role.value for role in roles))


# Atalhos usados nas rotas -------------------------------------------------
require_admin = require_roles(UserRole.ADMIN)
require_staff = require_roles(
    UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST
)
require_front_desk = require_roles(UserRole.ADMIN, UserRole.RECEPTIONIST)
require_doctor = require_roles(UserRole.DOCTOR)
require_any_authenticated = get_current_user
