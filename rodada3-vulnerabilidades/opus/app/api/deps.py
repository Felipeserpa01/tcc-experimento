from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def get_today() -> date:
    """Data atual. É uma dependência para que os testes possam controlar o "relógio"."""
    return date.today()


Today = Annotated[date, Depends(get_today)]


def _user_from_token(db: Session, token: str) -> User:
    subject = decode_access_token(token)
    user = db.get(User, int(subject)) if subject and subject.isdigit() else None
    if user is None:
        raise UnauthorizedError("Token inválido ou expirado", code="invalid_token")
    return user


def get_current_user(db: DbSession, token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    if token is None:
        raise UnauthorizedError()
    return _user_from_token(db, token)


def get_optional_user(db: DbSession, token: Annotated[str | None, Depends(oauth2_scheme)]) -> User | None:
    return _user_from_token(db, token) if token else None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def require_librarian(user: CurrentUser) -> User:
    if not user.is_librarian:
        raise ForbiddenError("Acesso restrito a bibliotecários", code="librarian_required")
    return user


Librarian = Annotated[User, Depends(require_librarian)]


def ensure_self_or_librarian(user: User, owner_id: int) -> None:
    if not user.is_librarian and user.id != owner_id:
        raise ForbiddenError("Você não tem permissão para acessar este recurso", code="forbidden")


@dataclass
class Pagination:
    skip: int
    limit: int


def get_pagination(
    skip: Annotated[int, Query(ge=0, description="Quantidade de registros a pular")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Máximo de registros retornados")] = 20,
) -> Pagination:
    return Pagination(skip=skip, limit=limit)


PageParams = Annotated[Pagination, Depends(get_pagination)]
