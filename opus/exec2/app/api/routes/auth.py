from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DbSession, OptionalToken, get_user_from_token
from app.core.exceptions import PermissionDeniedError
from app.core.security import create_access_token
from app.models import User, UserRole
from app.schemas.auth import LoginRequest, Token
from app.schemas.common import ErrorResponse
from app.schemas.user import UserCreate, UserRead
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _issue_token(user: User) -> Token:
    token, expires_in = create_access_token(user.id, user.role.value)
    return Token(access_token=token, expires_in=expires_in)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastrar usuário",
    responses={
        401: {"model": ErrorResponse, "description": "Cadastro de bibliotecário sem autenticação"},
        403: {"model": ErrorResponse, "description": "Apenas bibliotecários cadastram bibliotecários"},
        409: {"model": ErrorResponse, "description": "E-mail já cadastrado"},
    },
)
def register(data: UserCreate, db: DbSession, token: OptionalToken) -> User:
    """Leitores podem se cadastrar livremente. Bibliotecários só podem ser
    cadastrados por outro bibliotecário autenticado (o primeiro é criado via CLI)."""
    if data.role == UserRole.LIBRARIAN:
        requester = get_user_from_token(db, token)
        if requester.role != UserRole.LIBRARIAN:
            raise PermissionDeniedError("Apenas bibliotecários podem cadastrar outros bibliotecários")
    return user_service.create_user(db, data)


@router.post(
    "/login",
    response_model=Token,
    summary="Login (JSON)",
    responses={401: {"model": ErrorResponse, "description": "Credenciais inválidas"}},
)
def login(credentials: LoginRequest, db: DbSession) -> Token:
    user = user_service.authenticate(db, credentials.email, credentials.password)
    return _issue_token(user)


@router.post(
    "/token",
    response_model=Token,
    summary="Login (formulário OAuth2)",
    responses={401: {"model": ErrorResponse, "description": "Credenciais inválidas"}},
)
def login_with_form(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    """Equivalente ao `/auth/login`, no formato usado pelo botão *Authorize* do Swagger.
    Informe o e-mail no campo `username`."""
    user = user_service.authenticate(db, form.username, form.password)
    return _issue_token(user)
