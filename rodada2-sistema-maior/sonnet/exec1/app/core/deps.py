from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import TokenType, decode_token
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise UnauthorizedError("Token de autenticação não fornecido.")

    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise UnauthorizedError(str(exc)) from exc

    if payload.get("type") != TokenType.ACCESS.value:
        raise UnauthorizedError("Tipo de token inválido para esta operação.")

    user_id = payload.get("sub")
    user = db.get(User, int(user_id)) if user_id else None
    if user is None:
        raise UnauthorizedError("Usuário não encontrado.")
    if not user.is_active:
        raise ForbiddenError("Usuário inativo.")

    return user


def require_roles(*allowed_roles: UserRole):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise ForbiddenError("Você não tem permissão para executar esta ação.")
        return current_user

    return dependency


def get_client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None
