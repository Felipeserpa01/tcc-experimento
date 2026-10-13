from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

import jwt
from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User, UserRole
from app.utils.time import utcnow

# auto_error=False: a ausência de token é tratada aqui, com mensagem e formato padronizados.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]
OptionalToken = Annotated[str | None, Depends(oauth2_scheme)]


def get_now() -> datetime:
    """Relógio da aplicação (UTC). Isolado em uma dependência para ser substituído nos testes."""
    return utcnow()


Now = Annotated[datetime, Depends(get_now)]


def get_user_from_token(db: Session, token: str | None) -> User:
    if not token:
        raise AuthenticationError("Não autenticado")
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token expirado", code="token_expired") from exc
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise AuthenticationError("Token inválido", code="invalid_token") from exc

    # O papel é lido do banco (e não do token) para refletir alterações imediatamente.
    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError("Token inválido", code="invalid_token")
    return user


def get_current_user(db: DbSession, token: OptionalToken) -> User:
    return get_user_from_token(db, token)


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_librarian(user: CurrentUser) -> User:
    if user.role != UserRole.LIBRARIAN:
        raise PermissionDeniedError("Operação permitida apenas para bibliotecários")
    return user


Librarian = Annotated[User, Depends(require_librarian)]


def ensure_self_or_librarian(current_user: User, user_id: int) -> None:
    if current_user.role != UserRole.LIBRARIAN and current_user.id != user_id:
        raise PermissionDeniedError("Você só pode acessar os seus próprios dados")


@dataclass(frozen=True)
class Pagination:
    skip: int
    limit: int


def get_pagination(
    skip: Annotated[int, Query(ge=0, description="Quantidade de registros a pular.")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Máximo de registros retornados.")] = 20,
) -> Pagination:
    return Pagination(skip=skip, limit=limit)


PaginationParams = Annotated[Pagination, Depends(get_pagination)]
