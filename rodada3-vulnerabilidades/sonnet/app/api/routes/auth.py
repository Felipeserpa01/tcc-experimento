from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DbSession, OptionalUser
from app.core.config import settings
from app.core.exceptions import ForbiddenError, TooManyRequestsError, UnauthorizedError
from app.core.rate_limit import FailureLimiter
from app.core.security import create_access_token
from app.models.user import UserRole
from app.schemas.auth import Token
from app.schemas.common import ErrorResponse
from app.schemas.user import UserCreate, UserRead
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Falhas por (IP, e-mail) e um teto por IP maior, para frear tanto o ataque a uma conta
# quanto a varredura de várias contas. Um atacante em outro IP não tranca a conta da vítima.
_PER_IP_FACTOR = 4
login_limiter = FailureLimiter(settings.login_max_attempts * _PER_IP_FACTOR, settings.login_window_seconds)
login_account_limiter = FailureLimiter(settings.login_max_attempts, settings.login_window_seconds)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={403: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def register(data: UserCreate, db: DbSession, current_user: OptionalUser) -> UserRead:
    """Cadastra um usuário.

    Qualquer pessoa pode se cadastrar como **leitor**. Para cadastrar um **bibliotecário**,
    é necessário estar autenticado como bibliotecário.
    """
    if data.role == UserRole.LIBRARIAN and (current_user is None or not current_user.is_librarian):
        raise ForbiddenError(
            "Apenas bibliotecários autenticados podem cadastrar outros bibliotecários",
            code="librarian_required",
        )
    return user_service.create_user(db, data)


@router.post(
    "/login",
    response_model=Token,
    responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
)
def login(request: Request, form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    """Autentica com e-mail (campo `username`) e senha, retornando um token JWT."""
    ip = request.client.host if request.client else "unknown"
    account_key = f"{ip}|{form.username.strip().lower()}"

    retry_after = max(login_limiter.retry_after(ip), login_account_limiter.retry_after(account_key))
    if retry_after:
        raise TooManyRequestsError(retry_after)

    user = user_service.authenticate(db, form.username, form.password)
    if user is None:
        login_limiter.register_failure(ip)
        login_account_limiter.register_failure(account_key)
        raise UnauthorizedError("E-mail ou senha incorretos", code="invalid_credentials")

    login_account_limiter.reset(account_key)
    return Token(
        access_token=create_access_token(user.id),
        expires_in=settings.access_token_expire_minutes * 60,
    )
