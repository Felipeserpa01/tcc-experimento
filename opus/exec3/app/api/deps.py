from datetime import date
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.clock import get_today
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

# auto_error=False para devolvermos nossa própria mensagem de erro 401.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]
Today = Annotated[date, Depends(get_today)]


def get_current_user(db: DbSession, token: Annotated[str | None, Depends(oauth2_scheme)]) -> User:
    if not token:
        raise AuthenticationError("Não autenticado.")

    payload = decode_access_token(token)
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Token inválido.") from exc

    # O perfil é sempre lido do banco, não do token: mudanças de perfil valem imediatamente.
    user = db.get(User, user_id)
    if user is None:
        raise AuthenticationError("Usuário do token não existe mais.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_librarian(user: CurrentUser) -> User:
    if not user.is_librarian:
        raise PermissionDeniedError("Operação permitida apenas para bibliotecários.")
    return user


Librarian = Annotated[User, Depends(require_librarian)]


def ensure_self_or_librarian(current_user: User, target_user_id: int) -> None:
    if not current_user.is_librarian and current_user.id != target_user_id:
        raise PermissionDeniedError("Você só pode acessar os seus próprios dados.")
