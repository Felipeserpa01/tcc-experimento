from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DbSession
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserOut, UserRegister
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Autenticação"])


def _issue_token(user: User) -> Token:
    return Token(
        access_token=create_access_token(user.id, user.role.value),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastro público de leitor",
    responses={409: {"description": "E-mail já cadastrado"}},
)
def register(data: UserRegister, db: DbSession) -> User:
    """Cria uma conta do tipo **leitor**. Bibliotecários são criados por outro bibliotecário em `POST /users`."""
    return user_service.create_user(db, data, role=UserRole.READER)


@router.post(
    "/login",
    response_model=Token,
    summary="Login com JSON",
    responses={401: {"description": "Credenciais inválidas"}},
)
def login(data: LoginRequest, db: DbSession) -> Token:
    user = user_service.authenticate(db, data.email, data.password)
    return _issue_token(user)


@router.post(
    "/token",
    response_model=Token,
    summary="Login com formulário OAuth2 (usado pelo botão Authorize do Swagger)",
    responses={401: {"description": "Credenciais inválidas"}},
)
def login_form(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    """Informe o **e-mail** no campo `username`."""
    user = user_service.authenticate(db, form.username, form.password)
    return _issue_token(user)
